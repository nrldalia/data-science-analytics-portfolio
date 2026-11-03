"""Evidence-based processing reports, explicit exception acknowledgement and exports."""
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import time
import zipfile

from flask import jsonify, request, send_file
from database import begin_write, get_db_connection
from retailer_archive import archive_state

MAX_EVIDENCE = 5000
MAX_EXCEL_DATA_ROWS = 1048575
MAX_EXCEL_COLUMNS = 16384


def decode(value, default):
    return json.loads(value) if value else default


def stamp():
    return datetime.now(timezone.utc).isoformat()


def duration_ms(start, end):
    try:
        seconds = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
        return round(seconds * 1000) if math.isfinite(seconds) and seconds >= 0 else None
    except (TypeError, ValueError):
        return None


def safe_cell(value):
    text = str('' if value is None else value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')) else text


def csv_bytes(rows, fields):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
    csv.writer(stream).writerow([safe_cell(field) for field in fields])
    for row in rows:
        writer.writerow({k: safe_cell(row.get(k)) for k in fields})
    return stream.getvalue().encode('utf-8-sig')



def excel_cell(value):
    # Stored outputs are JSON-compatible values. Preserve numeric/boolean types
    # while representing complex JSON values as explicit text in a spreadsheet.
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Excel cannot represent non-finite numbers. Choose another output format.')
        return value
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, allow_nan=False)
    if not isinstance(value, str):
        raise ValueError('Excel cannot represent an output value. Choose JSON output.')
    value = safe_cell(value)
    if len(value) > 32767:
        raise ValueError('Excel cell text exceeds 32,767 characters. Choose CSV or JSON output.')
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    if ILLEGAL_CHARACTERS_RE.search(value):
        raise ValueError('Excel cannot represent control characters in this output. Choose CSV or JSON output.')
    return value


def xlsx_bytes(rows, fields):
    if len(rows) > MAX_EXCEL_DATA_ROWS or len(fields) > MAX_EXCEL_COLUMNS:
        raise ValueError('Output exceeds Excel worksheet row or column limits. Choose CSV or JSON output.')
    # Validate before starting a streaming worksheet so unsupported values cannot
    # be silently truncated or leave partially written worksheet streams.
    headers = [excel_cell(field) for field in fields]
    for row in rows:
        for field in fields:
            excel_cell(row.get(field))
    from openpyxl import Workbook
    book = Workbook(write_only=True)
    try:
        sheet = book.create_sheet('Processed data')
        sheet.append(headers)
        for row in rows:
            sheet.append([excel_cell(row.get(field)) for field in fields])
        stream = io.BytesIO()
        book.save(stream)
        return stream.getvalue()
    finally:
        book.close()


def capture_step(db, aid, result, rule, sequence, attempt):
    """Retain bounded evidence separately from globally listed metrics."""
    row = db.execute('SELECT payload FROM batch_processing_evidence WHERE id=?', (aid,)).fetchone()
    data = decode(row['payload'], {'steps': []}) if row else {'steps': []}
    used = sum(len(s['findings']) + len(s['changes']) for s in data['steps'])
    remaining = max(0, MAX_EVIDENCE - used)
    findings = []
    for item in result.get('issues', [])[:remaining]:
        findings.append({'row': item.get('row'), 'field': str(item.get('field', ''))[:500],
                         'message': str(item.get('issue', 'Validation finding'))[:1000]})
    remaining -= len(findings)
    changes = []
    for item in result.get('trace', [])[:remaining]:
        changes.append({k: (str(item.get(k))[:1000] if k in ('before', 'after') else item.get(k))
                        for k in ('row', 'field', 'before', 'after', 'action')})
    data['steps'].append({'sequence': sequence, 'attempt': attempt, 'ruleId': rule['id'],
                          'ruleName': rule.get('name', rule['operation']),
                          'inputScope': rule.get('inputFileId') or 'current',
                          'findings': findings, 'changes': changes,
                          'findingCount': result.get('issueCount', 0),
                          'changeCount': result.get('changedCells', 0),
                          'rowFindingsAvailable': 'issues' in result,
                          'changesAvailable': 'trace' in result,
                          'truncated': bool(result.get('findingsTruncated') or result.get('traceTruncated')) or len(findings) < len(result.get('issues', [])) or
                                       len(changes) < len(result.get('trace', []))})
    db.execute('INSERT INTO batch_processing_evidence VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
               (aid, json.dumps(data)))



def capture_audit(db, aid, entries):
    row = db.execute('SELECT payload FROM batch_processing_evidence WHERE id=?', (aid,)).fetchone()
    data = decode(row['payload'], {'steps': []}) if row else {'steps': []}
    data['executionAudit'] = entries
    db.execute('INSERT INTO batch_processing_evidence VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
               (aid, json.dumps(data)))


def finalize_operational(metrics, status, started, ended, output):
    expected = [s['key'] for s in metrics.get('expectedStores', [])] if 'expectedStores' in metrics else None
    matched = metrics.get('receivedExpectedStoreIds')
    metrics['operational'] = {
        'calculationVersion': 1, 'expectedStoreIds': expected,
        'receivedExpectedStoreIds': matched,
        'rowsReceived': metrics.get('rowsReceived'),
        'rowsOutput': len(output) if output is not None else None,
        'rowsChecked': metrics.get('qualityRowsChecked'),
        'issueRows': metrics.get('qualityIssueRows'),
        'ruleRetryCount': metrics.get('ruleRetryCount', 0),
        'completedAt': ended, 'durationMs': duration_ms(started, ended),
        'statusAtCompletion': status,
    }
    return metrics


def report_fingerprint(row):
    # Acknowledgements themselves do not change the evidence under review.
    metrics = decode(row['metrics'], {})
    metrics.pop('processingReview', None)
    payload = {k: row[k] for k in ('id', 'status', 'source', 'pipeline', 'output', 'error_codes')}
    payload['source'] = hashlib.sha256(bytes(payload['source'])).hexdigest()
    payload['metrics'] = metrics
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def report_for(db, row, active=False):
    metrics = decode(row['metrics'], {})
    pipeline = decode(row['pipeline'], [])
    progress = decode(row['progress'], {}) if active else {}
    evidence_row = db.execute('SELECT payload FROM batch_processing_evidence WHERE id=?', (row['id'],)).fetchone()
    evidence = decode(evidence_row['payload'], {}) if evidence_row else {}
    audit = evidence.get('executionAudit', []) if active else decode(row['audit'], [])
    if not audit and evidence.get('executionAudit'):
        audit = evidence['executionAudit']
    operational = metrics.get('operational', {})
    total_rules = len(pipeline)
    completed_rules = len({e['sequence'] for e in audit
                           if isinstance(e.get('sequence'), int) and
                           1 <= e['sequence'] <= total_rules and e.get('result') == 'Successful'})
    if not active and row['status'] == 'Cancelled Job' and not audit:
        # Historical cancelled jobs may predate private execution evidence.
        completed_rules = None
    if active:
        stage = 'Processing rules' if progress.get('sequence') else 'Parsing input'
        percent = round(completed_rules / total_rules * 100) if total_rules else None
    else:
        stage = 'Approved' if row['status'] == 'Approved Job' else 'Stopped' if row['status'] == 'Cancelled Job' else 'Awaiting review / approval'
        percent = 100 if row['status'] != 'Cancelled Job' else None
        if percent == 100:
            completed_rules = total_rules
    expected = metrics.get('expectedStores')
    missing = metrics.get('missingStores')
    matched = metrics.get('receivedExpectedStoreIds')
    if matched is None and expected is not None and missing is not None:
        missing_keys = {s['key'].casefold() for s in missing}
        matched = [s['key'] for s in expected if s['key'].casefold() not in missing_keys]
    expected_count = len(expected) if expected is not None else None
    coverage = round(len(matched) / expected_count * 100, 2) if expected_count and matched is not None else None
    issues = []
    def add(severity, code, message, **extra):
        issues.append(dict(id=str(len(issues) + 1), severity=severity, code=code, message=message,
                           row=None, field='', ruleName='', attempt=None, recovered=False) | extra)
    for detail in metrics.get('failureDetails', []):
        recovered = bool(detail.get('recoveredOnAttempt'))
        add('warning' if recovered else 'error', detail.get('errorCode') or 'RULE_FAILURE',
            detail.get('reason') or 'A rule did not complete.', field=detail.get('field', ''),
            ruleName=detail.get('ruleName', ''), attempt=detail.get('attempt'), recovered=recovered)
    cancellation = metrics.get('cancellationDetails')
    if cancellation:
        add('error', cancellation.get('errorCode', 'JOB_CANCELLED'), cancellation.get('reason', 'Job stopped.'),
            ruleName=cancellation.get('ruleName') or '', attempt=cancellation.get('attempt'))
    for code, key, message in [('MISSING_STORES', 'missingStores', 'expected active stores were not received.'),
                               ('NEW_STORES', 'newStores', 'received store IDs are not registered.')]:
        if metrics.get(key):
            add('warning', code, f"{len(metrics[key])} {message}")
    if metrics.get('rowsWithoutStoreId'):
        add('warning', 'MISSING_STORE_ID', f"{metrics['rowsWithoutStoreId']} rows have no store ID.")
    if metrics.get('storeComparisonNote') and matched is None:
        add('warning', 'STORE_MAPPING_UNAVAILABLE', metrics['storeComparisonNote'])
    for message in metrics.get('kpi', {}).get('flags', []):
        add('warning', 'KPI_REVIEW_REQUIRED', message)
    changes = []
    reported_changes = 0
    for step in evidence.get('steps', []):
        reported_changes += step.get('changeCount', 0)
        for change in step.get('changes', []):
            changes.append({**change, 'sequence': step['sequence'], 'ruleName': step['ruleName'],
                            'attempt': step['attempt']})
    for step in evidence.get('steps', []):
        # Repeat rule attempts remain visible, but are never treated as distinct source rows.
        for finding in step.get('findings', []):
            add('error', 'ROW_VALIDATION', finding['message'], row=finding.get('row'),
                field=finding.get('field', ''), ruleName=step['ruleName'], attempt=step['attempt'])
    available = []
    if metrics.get('processingReportVersion') != 1:
        available.append('Historical run: detailed processing evidence and retry lineage may not have been captured.')
    if any(s.get('truncated') for s in evidence.get('steps', [])):
        available.append('Detailed evidence is capped at 5,000 events; totals and original input remain available.')
    if any(not s.get('rowFindingsAvailable') and s.get('findingCount') for s in evidence.get('steps', [])):
        available.append('Some rule failures have aggregate counts only; row-level findings were not returned by the worker.')
    if len(changes) > 25:
        available.append('The report shows the first 25 captured transformation events. Download the evidence ZIP for all retained events.')
    if changes:
        available.append('Transformations are captured rule-attempt events, including failed or retried attempts; they are not a final output preview.')
    if any(not s.get('changesAvailable') and s.get('changeCount') for s in evidence.get('steps', [])):
        available.append('Some transformation counts have no cell-level evidence returned by the worker.')
    if matched is None:
        available.append('Store coverage is unavailable because the source store mapping was not captured.')
    if metrics.get('qualityIssueRows') is None:
        available.append('A comparable row-level issue rate is unavailable for this workflow.')
    if not active and row['status'] == 'Cancelled Job':
        available.append('Cancelled runs have no published output or legacy execution audit. Captured processing evidence may contain partial execution attempts.')
    review = metrics.get('processingReview')
    archived = archive_state(db, row['retailer_id'])['archived']
    pending = db.execute('SELECT id FROM batch_attempts WHERE retailer_id=? AND period=? LIMIT 1', (row['retailer_id'], row['period'])).fetchone()
    finished = None if active else operational.get('completedAt') or row['end_time']
    elapsed = duration_ms(row['start_time'], stamp() if active else finished)
    completed = not active and row['status'] in ('Completed', 'Completed with Interruption')
    job = {k: row[k] for k in ('id', 'retailer_id', 'retailer_name', 'period', 'filename', 'start_time')}
    job.update(status='Processing' if active else row['status'], end_time=None if active else row['end_time'],
               receivedAt=metrics.get('receivedAt'), finishedAt=finished)
    return dict(job=job, progress=dict(stage=stage, percent=percent, completedRules=completed_rules,
                                      totalRules=total_rules, elapsedSeconds=elapsed / 1000 if elapsed is not None else None, ruleName=progress.get('ruleName'),
                                      attempt=progress.get('attempt')),
                lineage=metrics.get('lineage'), reconciliation=dict(
                    rowsReceived=metrics.get('rowsReceived'), rowsAfterCleaning=metrics.get('rowsAfterCleaning'),
                    rowsOutput=operational.get('rowsOutput'), expectedStores=expected_count,
                    receivedExpectedStores=len(matched) if matched is not None else None,
                    coveragePercent=coverage, missingStores=missing, newStores=metrics.get('newStores'),
                    rowsWithoutStoreId=metrics.get('rowsWithoutStoreId')),
                issues=issues, issueTotal=len(issues), review=review,
                changes=changes[:25], changeTotal=len(changes) if evidence or metrics.get('processingReportVersion') == 1 else None,
                reportedChangeCount=reported_changes if evidence or metrics.get('processingReportVersion') == 1 else None,
                changesTruncated=len(changes) > 25 or any(s.get('truncated') for s in evidence.get('steps', [])),
                reviewRecommended=bool(issues and not review), fingerprint=None if active else report_fingerprint(row),
                canReview=completed and bool(issues) and not review and not archived and not pending,
                canApprove=completed and not archived and not pending and not (metrics.get('kpi', {}).get('flagged') and not metrics['kpi'].get('review')),
                canReprocess=not active and not archived and not pending and not metrics.get('historyRecoveryNote'),
                canExport=not active and row['status'] in ('Completed', 'Completed with Interruption', 'Approved Job') and row['output'] is not None,
                availability=available)


def register_processing_routes(app, error):
    with get_db_connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS batch_processing_evidence(id TEXT PRIMARY KEY,payload TEXT NOT NULL)')

    def get_row(db, jid):
        row = db.execute('SELECT id,retailer_id,retailer_name,period,start_time,filename,pipeline,progress,metrics FROM batch_attempts WHERE id=?', (jid,)).fetchone()
        return (row, True) if row else (db.execute('SELECT * FROM batch_jobs WHERE id=?', (jid,)).fetchone(), False)

    @app.get('/api/v1/batches/<jid>/processing-report')
    def processing_report(jid):
        try:
            page = int(request.args.get('page', 1))
            size = int(request.args.get('pageSize', 25))
            severity = request.args.get('severity', 'all')
            if page < 1 or size not in (10, 25, 50, 100) or severity not in ('all', 'warning', 'error'):
                raise ValueError()
        except (ValueError, TypeError):
            return error('Use valid page, pageSize (10/25/50/100) and severity (all/warning/error).')
        with get_db_connection() as db:
            row, active = get_row(db, jid)
            if not row:
                return error('Job not found.', 404)
            report = report_for(db, row, active)
        filtered = [i for i in report['issues'] if severity == 'all' or i['severity'] == severity]
        report.update(issues=filtered[(page - 1) * size:page * size], issueTotal=len(filtered), page=page, pageSize=size)
        return jsonify(success=True, report=report)

    @app.post('/api/v1/batches/<jid>/processing-review')
    def processing_review(jid):
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or body.get('checked') is not True or not isinstance(body.get('note'), str) or not body['note'].strip() or len(body['note']) > 1000 or not isinstance(body.get('fingerprint'), str):
            return error('Confirm the check, include the report fingerprint and enter a note up to 1,000 characters.')
        with get_db_connection() as db:
            begin_write(db)
            row = db.execute('SELECT * FROM batch_jobs WHERE id=?', (jid,)).fetchone()
            if not row:
                return error('Completed job not found.', 404)
            report = report_for(db, row)
            if body['fingerprint'] != report['fingerprint']:
                return error('The run changed. Refresh the processing report before reviewing.', 409)
            if not report['canReview']:
                return error('Only an unreviewed completed run with exceptions on an active retailer can be acknowledged.', 409)
            review = dict(checkedAt=stamp(), note=body['note'].strip(), reportFingerprint=report['fingerprint'])
            metrics = decode(row['metrics'], {})
            metrics['processingReview'] = review
            audit = decode(row['audit'], [])
            audit.append(dict(sequence=None, ruleName='Processing exception acknowledgement', category='Action',
                              attempt=1, startTime=review['checkedAt'], endTime=review['checkedAt'],
                              durationMs=0, result='Successful', errorCode=None, message=review['note']))
            db.execute('UPDATE batch_jobs SET metrics=?,audit=? WHERE id=?', (json.dumps(metrics), json.dumps(audit), jid))
        return jsonify(success=True, review=review)

    @app.get('/api/v1/batches/<jid>/exceptions.csv')
    def exception_export(jid):
        with get_db_connection() as db:
            row, active = get_row(db, jid)
            if not row:
                return error('Job not found.', 404)
            report = report_for(db, row, active)
        data = csv_bytes(report['issues'], ['id', 'severity', 'code', 'message', 'row', 'field', 'ruleName', 'attempt', 'recovered'])
        return send_file(io.BytesIO(data), mimetype='text/csv', as_attachment=True, download_name='processing_exceptions.csv')

    @app.get('/api/v1/batches/<jid>/output')
    def output_export(jid):
        kind = request.args.get('format', 'csv')
        if kind not in ('csv', 'json', 'xlsx'):
            return error('Choose csv, json or xlsx output format.')
        with get_db_connection() as db:
            row, active = get_row(db, jid)
            if not row:
                return error('Job not found.', 404)
            if active or row['status'] not in ('Completed', 'Completed with Interruption', 'Approved Job'):
                return error('Only completed or approved runs have downloadable processed output.', 409)
            if row['output'] is None:
                return error('Processed output was not retained for this historical run.', 409)
            try:
                output = decode(row['output'], None)
            except (ValueError, TypeError):
                return error('Processed output is unavailable for export.', 409)
        if not isinstance(output, list) or any(not isinstance(item, dict) for item in output):
            return error('Processed output is unavailable for export.', 409)
        try:
            if kind == 'json':
                data = json.dumps(output, ensure_ascii=False, allow_nan=False).encode('utf-8')
                mime = 'application/json'
            else:
                fields = list(dict.fromkeys(key for item in output for key in item))
                if kind == 'csv':
                    data = csv_bytes(output, fields)
                    mime = 'text/csv'
                else:
                    data = xlsx_bytes(output, fields)
                    mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        except (ValueError, TypeError, UnicodeError) as exc:
            if kind == 'xlsx' and isinstance(exc, ValueError) and str(exc).startswith(('Excel ', 'Output exceeds Excel ')):
                return error(str(exc))
            return error('This output cannot be represented in the selected format. Choose another output format.')
        return send_file(io.BytesIO(data), mimetype=mime, as_attachment=True,
                         download_name='processed_data.' + kind)

    @app.get('/api/v1/batches/<jid>/evidence.zip')
    def evidence_export(jid):
        with get_db_connection() as db:
            row, active = get_row(db, jid)
            if not row:
                return error('Job not found.', 404)
            if active:
                return error('Wait until this run stops before exporting its evidence.', 409)
            report = report_for(db, row)
            evidence_row = db.execute('SELECT payload FROM batch_processing_evidence WHERE id=?', (jid,)).fetchone()
            payload = decode(evidence_row['payload'], {}) if evidence_row else {}
        output = decode(row['output'], None)
        content = io.BytesIO()
        with zipfile.ZipFile(content, 'w', zipfile.ZIP_DEFLATED) as archive:
            # Fixed member paths never depend on untrusted uploaded filenames.
            archive.writestr('original/source.bin', bytes(row['source']))
            archive.writestr('rules.json', json.dumps(decode(row['pipeline'], []), indent=2))
            archive.writestr('metrics.json', json.dumps(decode(row['metrics'], {}), indent=2))
            archive.writestr('report.json', json.dumps(report, indent=2))
            archive.writestr('processing_evidence.json', json.dumps(payload, indent=2))
            archive.writestr('execution_audit.json', json.dumps(payload.get('executionAudit', decode(row['audit'], [])), indent=2))
            if output is not None:
                archive.writestr('output.json', json.dumps(output, ensure_ascii=False))
                fields = list(dict.fromkeys(k for item in output for k in item))
                archive.writestr('output.csv', csv_bytes(output, fields))
            archive.writestr('README.txt', 'Original upload is retained as original/source.bin. Its original name is in report.json.\n'
                             'Acknowledgement does not edit data or replace KPI review. Historical/cancelled evidence can be incomplete; see report availability.\n')
        content.seek(0)
        return send_file(content, mimetype='application/zip', as_attachment=True, download_name='processing_evidence.zip')
