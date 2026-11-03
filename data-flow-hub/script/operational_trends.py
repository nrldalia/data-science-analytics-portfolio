"""Approved weekly operational snapshots, separated from per-attempt diagnostics."""
import csv
import io
import json
import math
from datetime import datetime, timedelta, timezone
from statistics import median
from zoneinfo import ZoneInfo

from flask import jsonify, request, send_file
from database import get_db_connection

VERSION = 'operational-v1'
SUCCESS = {'Completed', 'Approved Job'}
FINISHED = SUCCESS | {'Completed with Interruption', 'Cancelled Job'}
PROVISIONAL = {'Completed', 'Completed with Interruption'}


def iso_monday(period):
    if not isinstance(period, str):
        raise ValueError('Use a valid endPeriod in YYYY-Www format.')
    try:
        year, week = period.split('-W')
        day = datetime.fromisocalendar(int(year), int(week), 1)
        if period != f'{int(year):04d}-W{int(week):02d}':
            raise ValueError()
        return day
    except (ValueError, TypeError):
        raise ValueError('Use a valid endPeriod in YYYY-Www format.') from None


def iso_period(day):
    year, week, _ = day.isocalendar()
    return f'{year:04d}-W{week:02d}'


def stamp(value):
    if not isinstance(value, str) or not ('T' in value or ' ' in value):
        return None
    try:
        day = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return day.replace(tzinfo=timezone.utc) if day.tzinfo is None else day.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def ids(values):
    if not isinstance(values, list):
        return None
    if any(not isinstance(v, str) or not v.strip() for v in values):
        return None
    return {v.strip().casefold() for v in values}


def metric_dict(value):
    if isinstance(value, dict):
        return value
    try:
        result = json.loads(value or '{}')
        return result if isinstance(result, dict) else {}
    except (TypeError, ValueError):
        return {}


def scope(row):
    profile = metric_dict(row.get('metrics')).get('inputFile') or {}
    return row['retailer_id'], profile.get('id') or 'legacy'


def duration(row):
    metrics = metric_dict(row.get('metrics'))
    operational = metrics.get('operational') or {}
    value = operational.get('durationMs')
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
        return value / 1000
    if 'durationMs' in operational:
        return None
    start, end = stamp(row.get('start_time')), stamp(row.get('end_time'))
    if start is not None and end is not None and end >= start:
        return (end - start).total_seconds()
    return None


def percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def roster_counts(metrics):
    operational = metrics.get('operational') or {}
    if 'expectedStoreIds' in operational:
        expected = ids(operational.get('expectedStoreIds'))
        received = ids(operational.get('receivedExpectedStoreIds'))
    else:
        old_expected = metrics.get('expectedStores')
        expected = ids([s.get('key') for s in old_expected if isinstance(s, dict)]) if isinstance(old_expected, list) and all(isinstance(s, dict) for s in old_expected) else None
        missing = metrics.get('missingStores')
        missing_ids = ids([s.get('key') for s in missing if isinstance(s, dict)]) if isinstance(missing, list) and all(isinstance(s, dict) for s in missing) else None
        received = expected - missing_ids if expected is not None and missing_ids is not None and metrics.get('storeIdField') else None
    if expected is None or received is None:
        return None, None, None, None, 'Captured expected roster or store mapping is unavailable.'
    matched = received & expected
    return len(expected), len(matched), len(expected - matched), (100 * len(matched) / len(expected) if expected else None), ('No expected active stores in the captured roster.' if not expected else 'Captured active-store roster; unknown and inactive stores do not increase coverage.')


def snapshot(row):
    metrics = metric_dict(row.get('metrics'))
    operational = metrics.get('operational') or {}
    expected, received, missing, coverage, note = roster_counts(metrics)
    checked = count(operational.get('rowsChecked'))
    issue_rows = count(operational.get('issueRows'))
    if issue_rows is not None and (checked is None or issue_rows > checked):
        issue_rows = None
    profile = metrics.get('inputFile') or {}
    return dict(jobId=row['id'], retailerId=row['retailer_id'], retailerName=row['retailer_name'],
                inputFileId=profile.get('id') or 'legacy', inputFileName=profile.get('filename') or 'Legacy defaults',
                period=row['period'], approvedAt=metrics.get('approvedAt'), receivedAt=metrics.get('receivedAt'),
                sourceSha256=metrics.get('sourceSha256'), expectedStores=expected, receivedExpectedStores=received,
                missingStores=missing, coveragePercent=coverage, coverageNote=note,
                rowsReceived=count(operational.get('rowsReceived', metrics.get('rowsReceived'))),
                rowsAfterCleaning=count(metrics.get('rowsAfterCleaning')),
                rowsChecked=checked, issueRows=issue_rows,
                qualityIssueRate=100 * issue_rows / checked if issue_rows is not None and checked else None,
                durationSeconds=duration(row))


def sum_known(snapshots, field):
    values = [s[field] for s in snapshots]
    return sum(values) if values and all(v is not None for v in values) else None


def family_rates(attempts):
    if not attempts:
        return None, None
    families = {}
    for row in attempts:
        lineage = metric_dict(row.get('metrics')).get('lineage') or {}
        number = count(lineage.get('attemptNumber'))
        root = lineage.get('rootJobId')
        if not root or not number:
            return None, None
        families.setdefault((*scope(row), root), []).append((number, row))
    retried = sum(any(number > 1 for number, _ in family) for family in families.values())
    success = 0
    for family in families.values():
        first = [row for number, row in family if number == 1]
        if len(first) != 1:
            return None, 100 * retried / len(families)
        row = first[0]
        original = (metric_dict(row.get('metrics')).get('operational') or {}).get('statusAtCompletion', row['status'])
        if original not in FINISHED:
            return None, 100 * retried / len(families)
        retries = count((metric_dict(row.get('metrics')).get('operational') or {}).get('ruleRetryCount'))
        if retries is None:
            return None, 100 * retried / len(families)
        success += original in SUCCESS and retries == 0
    return 100 * success / len(families), 100 * retried / len(families)


def build_trends(jobs, active, end_period, weeks, retailer_id='', input_id='', current=None):
    end = iso_monday(end_period)
    periods = [iso_period(end - timedelta(weeks=i)) for i in range(weeks - 1, -1, -1)]
    selected = [dict(row) for row in jobs if row.get('period') in periods and (not retailer_id or row['retailer_id'] == retailer_id) and (not input_id or scope(row)[1] == input_id)]
    running = [dict(row) for row in active if row.get('period') in periods and (not retailer_id or row['retailer_id'] == retailer_id) and (not input_id or scope(row)[1] == input_id)]
    observed = {scope(row) for row in selected + running}
    now = current or datetime.now(ZoneInfo('Asia/Kuala_Lumpur'))
    current_monday = iso_monday(iso_period(now))
    result = []
    minimum = datetime.min.replace(tzinfo=timezone.utc)
    for period in periods:
        rows = [r for r in selected if r['period'] == period]
        pending = [r for r in running if r['period'] == period]
        groups = {}
        for row in rows:
            groups.setdefault(scope(row), []).append(row)
        published, provisional = [], []
        for scoped_rows in groups.values():
            approved = [r for r in scoped_rows if r['status'] == 'Approved Job']
            unapproved = [r for r in scoped_rows if r['status'] in PROVISIONAL]
            if unapproved:
                provisional.append(max(unapproved, key=lambda r: (stamp(r.get('start_time')) or minimum, r.get('_order', 0))))
            if approved:
                chosen = max(approved, key=lambda r: (stamp(metric_dict(r.get('metrics')).get('approvedAt')) or minimum, r.get('_order', 0)))
                item = snapshot(chosen)
                item['revised'] = len(approved) > 1
                item['pendingRevision'] = any((stamp(r.get('start_time')) or minimum, r.get('_order', 0)) > (stamp(chosen.get('start_time')) or minimum, chosen.get('_order', 0)) for r in unapproved)
                published.append(item)
        for item in published:
            item['approvalTimeUnavailable'] = stamp(item['approvedAt']) is None
        expected = sum_known(published, 'expectedStores')
        matched = sum_known(published, 'receivedExpectedStores')
        checked = sum_known(published, 'rowsChecked')
        issues = sum_known(published, 'issueRows')
        full = bool(published) and len(published) == len(observed)
        counts = {name: sum_known(published, name) if full else None for name in ('expectedStores', 'receivedExpectedStores', 'missingStores', 'rowsReceived', 'rowsAfterCleaning', 'rowsChecked', 'issueRows')}
        valid_durations = [duration(r) for r in rows if r['status'] in FINISHED]
        samples = [d for d in valid_durations if d is not None]
        first, reprocessing = family_rates(rows + pending)
        state = ('published' if full else 'partial') if published else ('provisional' if provisional or pending else 'missing')
        result.append(dict(period=period, state=state, publishedScopes=len(published),
                           provisionalScopes=len({scope(r) for r in provisional + pending}),
                           expectedScopes=len(observed), approvedRunIds=[s['jobId'] for s in published],
                           provisionalRunIds=[r['id'] for r in provisional], activeRunIds=[r['id'] for r in pending],
                           revised=any(s['revised'] for s in published), pendingRevision=any(s['pendingRevision'] for s in published),
                           isOpen=iso_monday(period) >= current_monday, attemptCount=len(rows) + len(pending),
                           **counts, coveragePercent=(100 * matched / expected if full and expected and matched is not None else None),
                           qualityIssueRate=(100 * issues / checked if full and checked and issues is not None else None),
                           medianDurationSeconds=median(samples) if samples else None,
                           p95DurationSeconds=percentile(samples, .95), durationSampleCount=len(samples),
                           durationUnavailableCount=len(valid_durations) - len(samples), firstAttemptSuccessRate=first,
                           reprocessingRate=reprocessing, onTimeCoveragePercent=None, publishedSnapshots=published))
    for index, bucket in enumerate(result):
        window = result[max(0, index - 3):index + 1]
        available = [b for b in window if b['coveragePercent'] is not None]
        bucket['rollingCoverageWeeks'] = len(available)
        # A rolling value requires a complete consecutive four-week window.
        window_expected = sum(b['expectedStores'] for b in available)
        bucket['rollingCoveragePercent'] = (100 * sum(b['receivedExpectedStores'] for b in window) / window_expected if len(window) == 4 and len(available) == 4 and window_expected else None)
        prior = result[index - 1]['coveragePercent'] if index else None
        bucket['coverageChangePoints'] = bucket['coveragePercent'] - prior if bucket['coveragePercent'] is not None and prior is not None else None
    return dict(calculationVersion=VERSION, startPeriod=periods[0], endPeriod=end_period,
                weeks=weeks, filters=dict(retailerId=retailer_id, inputFileId=input_id),
                periods=result, latest=result[-1], previous=result[-2] if len(result) > 1 else None,
                notes=[
                    'Coverage and row metrics use one latest-approved run per retailer/input-profile/week; provisional and cancelled runs are excluded.',
                    'Expected scope counts describe scopes observed in the selected range, not a contractual delivery schedule. Partial published scopes have unavailable aggregate metrics.',
                    'Coverage uses captured active-store rosters and sums matched/expected counts across scopes. A store counts once per input scope.',
                    'Duration median and interpolated p95 summarize valid completed-attempt durations; sample and unavailable counts are shown separately.',
                    'Logical rates use recorded retailer/profile/week/root families, including cancelled roots. First-attempt success requires the first attempt to complete without interruption and with zero rule retries; unknown lineage or retry counts make this rate unavailable. Reprocessing counts families with another submitted attempt, not rule retries.',
                    'Four-week rolling coverage sums matched/expected counts over four consecutive available published weeks. It does not average percentages; missing periods are gaps, never zero.',
                    'On-time coverage is unavailable: submission deadlines have not been captured. Open weeks are not directly comparable to completed weeks.',
                    'Operational metrics are separate from sales KPI records; no sales or quantities are inferred.'
                ])


def csv_cell(value):
    if value is None:
        return ''
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')) else text


def register_operational_routes(app, error):
    @app.get('/api/v1/kpi-trends')
    def operational_trends():
        try:
            weeks_text = request.args.get('weeks', '8')
            if not weeks_text.isdigit() or not 1 <= int(weeks_text) <= 52:
                raise ValueError('weeks must be a whole number from 1 to 52.')
            weeks = int(weeks_text)
            end_period = request.args.get('endPeriod') or iso_period(datetime.now(ZoneInfo('Asia/Kuala_Lumpur')))
            end = iso_monday(end_period)
            start_period = iso_period(end - timedelta(weeks=weeks - 1))
            retailer_id = request.args.get('retailerId', '')
            input_id = request.args.get('inputFileId', '')
            if len(retailer_id) > 200 or len(input_id) > 200:
                raise ValueError('Invalid retailer or input-profile filter.')
            kind = request.args.get('format', 'json')
            if kind not in ('json', 'csv'):
                raise ValueError('Choose json or csv format.')
            where = 'period>=? AND period<=?'
            parameters = [start_period, end_period]
            if retailer_id:
                where += ' AND retailer_id=?'
                parameters.append(retailer_id)
            with get_db_connection() as db:
                # Trends need captured metadata, never original uploads, outputs or audits.
                jobs = [dict(r) for r in db.execute(
                    'SELECT id,retailer_id,retailer_name,period,start_time,end_time,status,metrics,rowid AS _order FROM batch_jobs WHERE ' + where,
                    parameters).fetchall()]
                active = [dict(r) for r in db.execute(
                    "SELECT id,retailer_id,retailer_name,period,start_time,NULL AS end_time,'Processing' AS status,metrics,rowid AS _order FROM batch_attempts WHERE " + where,
                    parameters).fetchall()]
                configs = [dict(r) for r in db.execute('SELECT id,payload FROM retailer_configs').fetchall()]
            report = build_trends(jobs, active, end_period, weeks, retailer_id, input_id)
            retailer_options = {r['retailer_id']: r['retailer_name'] for r in jobs + active}
            profiles = {}
            for row in jobs + active:
                rid, pid = scope(row)
                profile = metric_dict(row.get('metrics')).get('inputFile') or {}
                profiles[(rid, pid)] = dict(id=pid, name=profile.get('filename') or 'Legacy defaults',
                                           retailerId=rid, retailerName=row['retailer_name'])
            for row in configs:
                config = metric_dict(row['payload'])
                retailer_options[row['id']] = config.get('name', row['id'])
                profiles.setdefault((row['id'], 'legacy'), dict(id='legacy', name='Legacy defaults',
                                                              retailerId=row['id'], retailerName=config.get('name', row['id'])))
                for profile in config.get('inputFiles', []):
                    profiles.setdefault((row['id'], profile['id']), dict(id=profile['id'], name=profile.get('filename') or profile['id'], retailerId=row['id'], retailerName=config.get('name', row['id'])))
            if retailer_id and retailer_id not in retailer_options:
                return error('Retailer not found.', 404)
            if input_id and not any(pid == input_id and (not retailer_id or rid == retailer_id) for rid, pid in profiles):
                return error('Input profile not found in this scope.', 404)
            report['availableRetailers'] = [dict(id=key, name=value) for key, value in sorted(retailer_options.items(), key=lambda item: item[1].casefold())]
            report['availableProfiles'] = sorted(profiles.values(), key=lambda p: (p['retailerName'].casefold(), p['name'].casefold(), p['id']))
            if kind == 'csv':
                fields = ['period', 'state', 'publishedScopes', 'expectedScopes', 'attemptCount', 'expectedStores', 'receivedExpectedStores', 'missingStores', 'coveragePercent', 'coverageChangePoints', 'rollingCoveragePercent', 'rollingCoverageWeeks', 'rowsReceived', 'rowsAfterCleaning', 'rowsChecked', 'issueRows', 'qualityIssueRate', 'medianDurationSeconds', 'p95DurationSeconds', 'durationSampleCount', 'durationUnavailableCount', 'firstAttemptSuccessRate', 'reprocessingRate', 'onTimeCoveragePercent', 'revised', 'pendingRevision', 'isOpen']
                stream = io.StringIO(newline='')
                writer = csv.writer(stream)
                writer.writerow(['calculationVersion', 'retailerId', 'inputFileId', *fields, 'approvedRunIds'])
                for bucket in report['periods']:
                    writer.writerow([csv_cell(report['calculationVersion']), csv_cell(retailer_id), csv_cell(input_id), *[csv_cell(bucket[field]) for field in fields], csv_cell(';'.join(bucket['approvedRunIds']))])
                return send_file(io.BytesIO(stream.getvalue().encode('utf-8-sig')), mimetype='text/csv', as_attachment=True, download_name='weekly_operational_trends.csv')
            return jsonify(success=True, **report)
        except (ValueError, OverflowError) as exc:
            return error(str(exc))
