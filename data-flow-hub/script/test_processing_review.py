"""Processing evidence/review/retry regression checks in isolated application fixtures."""
import csv
import io
import json
import queue
import subprocess
import sys
import unittest
import zipfile
from unittest.mock import patch

from openpyxl import load_workbook

import test_batch_jobs as fixtures
from database import get_db_connection
from retailer_setup import apply_pipeline


def execute_with_evidence(records, rule):
    output, steps, issues, trace = apply_pipeline(records, [rule])
    return dict(output=output, issueCount=len(issues), changedCells=len(trace),
                issues=issues, issueRows=sorted({item['row'] for item in issues}), trace=trace)


class ProcessingReviewTests(unittest.TestCase):
    setUp = fixtures.BatchJobTests.setUp
    tearDown = fixtures.BatchJobTests.tearDown
    finish = fixtures.BatchJobTests.finish
    jobs = fixtures.BatchJobTests.jobs

    def start(self, source=b'sku,store_id\n x ,A\n', period='2026-W41'):
        response = self.client.post('/api/v1/batches', data={
            'file': (io.BytesIO(source), '../untrusted.csv'), 'retailerId': self.retailer,
            'period': period, 'storeIdField': 'store_id'})
        self.assertEqual(response.status_code, 202, response.data)
        return response.json['attemptId']

    def report(self, identity):
        response = self.client.get('/api/v1/batches/' + identity + '/processing-report')
        self.assertEqual(response.status_code, 200, response.data)
        return response.json['report']

    def configure_stores(self):
        self.config['stores'] = [dict(key='A', name='A'), dict(key='B', name='B'),
                                 dict(key='I', name='Inactive', status='Inactive')]
        self.assertEqual(self.client.put('/api/v1/retailers/' + self.retailer, json=self.config).status_code, 200)

    def test_production_worker_returns_bounded_actual_findings_and_exact_rows(self):
        channel = queue.Queue()
        rule = dict(self.rule, operation='numeric', category='Transformation')
        __import__('batch_jobs').execute_step([{'sku': 'bad'} for _ in range(5001)], rule, channel)
        result = channel.get_nowait()
        self.assertEqual(result['issueCount'], 5001)
        self.assertEqual(len(result['issues']), 5000)
        self.assertEqual(len(result['issueRows']), 5001)
        self.assertTrue(result['findingsTruncated'])
        __import__('batch_jobs').execute_step([{'sku': ' x '}], self.rule, channel)
        cleaned = channel.get_nowait()
        self.assertEqual(cleaned['trace'][0]['before'], ' x ')
        self.assertEqual(cleaned['trace'][0]['after'], 'x')

    def test_active_progress_is_measured_and_exports_wait_for_completion(self):
        identity = self.start()
        report = self.report(identity)
        self.assertEqual(report['progress']['stage'], 'Parsing input')
        self.assertEqual(report['progress']['percent'], 0)
        self.assertEqual(report['progress']['totalRules'], 1)
        self.assertIsNotNone(report['job']['receivedAt'])
        self.assertFalse(report['canApprove'])
        self.assertIsNone(report['fingerprint'])
        self.assertEqual(self.client.get('/api/v1/batches/' + identity + '/evidence.zip').status_code, 409)
        self.finish(identity)
        done = self.report(identity)
        self.assertEqual(done['progress']['percent'], 100)
        self.assertIsNotNone(done['job']['finishedAt'])
        self.assertGreaterEqual(done['progress']['elapsedSeconds'], 0)

    def test_snapshot_reconciliation_uses_captured_active_roster(self):
        self.configure_stores()
        identity = self.start(b'sku,store_id\nx,A\ny,I\nz,NEW\n')
        self.finish(identity)
        report = self.report(identity)
        self.assertEqual(report['reconciliation']['expectedStores'], 2)
        self.assertEqual(report['reconciliation']['receivedExpectedStores'], 1)
        self.assertEqual(report['reconciliation']['coveragePercent'], 50)
        self.assertEqual(report['reconciliation']['rowsOutput'], 3)
        self.config['stores'] = []
        self.client.put('/api/v1/retailers/' + self.retailer, json=self.config)
        self.assertEqual(self.report(identity)['reconciliation'], report['reconciliation'])

    def test_review_is_stale_safe_one_time_and_does_not_approve(self):
        self.configure_stores()
        identity = self.start()
        self.finish(identity)
        report = self.report(identity)
        self.assertTrue(report['reviewRecommended'])
        self.assertTrue(report['canApprove'])
        url = '/api/v1/batches/' + identity + '/processing-review'
        body = dict(checked=True, note='Checked missing-store reconciliation.', fingerprint='wrong')
        self.assertEqual(self.client.post(url, json=body).status_code, 409)
        body['fingerprint'] = report['fingerprint']
        self.assertEqual(self.client.post(url, json=body).status_code, 200)
        self.assertEqual(self.client.post(url, json=body).status_code, 409)
        reread = self.report(identity)
        self.assertEqual(reread['job']['status'], 'Completed')
        self.assertFalse(reread['reviewRecommended'])
        self.assertEqual(reread['review']['note'], body['note'])

    def test_cancelled_row_findings_and_partial_audit_are_explicit(self):
        fixtures.app.app.config['BATCH_TEST_EXECUTOR'] = execute_with_evidence
        self.config['pipeline'] = [dict(self.rule, operation='numeric', category='Transformation')]
        self.client.put('/api/v1/retailers/' + self.retailer, json=self.config)
        original = b'sku,store_id\nprivate-invalid-value,A\n2,A\n'
        identity = self.start(original)
        self.finish(identity)
        report = self.report(identity)
        self.assertEqual(report['job']['status'], 'Cancelled Job')
        self.assertFalse(report['canApprove'])
        self.assertIsNone(report['job']['end_time'])
        self.assertIsNotNone(report['job']['finishedAt'])
        rows = [item for item in report['issues'] if item['code'] == 'ROW_VALIDATION']
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(item['row'] == 1 for item in rows))
        self.assertNotIn('private-invalid-value', json.dumps(self.jobs()))
        self.assertEqual(self.client.get('/api/v1/batches/' + identity + '/audit').status_code, 404)
        with get_db_connection() as db:
            metrics = json.loads(db.execute('SELECT metrics FROM batch_jobs WHERE id=?', (identity,)).fetchone()[0])
        self.assertEqual(metrics['operational']['issueRows'], 1)
        self.assertEqual(metrics['operational']['rowsChecked'], 2)
        archive = self.client.get('/api/v1/batches/' + identity + '/evidence.zip')
        with zipfile.ZipFile(io.BytesIO(archive.data)) as bundle:
            self.assertEqual(bundle.read('original/source.bin'), original)
            self.assertNotIn('output.json', bundle.namelist())
            self.assertEqual(len(json.loads(bundle.read('execution_audit.json'))), 4)
            self.assertFalse(any('..' in name for name in bundle.namelist()))

    def test_retry_lineage_and_concurrent_retry_protection(self):
        original = self.start()
        self.finish(original)
        url = '/api/v1/batches/' + original + '/reprocess'
        first = self.client.post(url)
        self.assertEqual(first.status_code, 202)
        identity = first.json['attemptId']
        self.assertEqual(self.client.post(url).status_code, 409)
        self.assertFalse(self.report(original)['canReprocess'])
        self.finish(identity)
        report = self.report(identity)
        self.assertEqual(report['lineage'], dict(rootJobId=original, reprocessOf=original, attemptNumber=2))
        self.assertEqual(self.report(original)['lineage']['attemptNumber'], 1)
        self.assertEqual(len(self.jobs()), 2)
        self.assertEqual(self.report(original)['job']['status'], 'Completed')

    def test_output_csv_headers_and_cells_are_spreadsheet_safe(self):
        self.config['pipeline'] = []
        self.client.put('/api/v1/retailers/' + self.retailer, json=self.config)
        original = b'=2+2,store_id\n=1+1,A\n'
        identity = self.start(original)
        self.finish(identity)
        archive = self.client.get('/api/v1/batches/' + identity + '/evidence.zip')
        with zipfile.ZipFile(io.BytesIO(archive.data)) as bundle:
            exported = list(csv.reader(io.StringIO(bundle.read('output.csv').decode('utf-8-sig'))))
            self.assertEqual(exported[0][0], "'=2+2")
            self.assertEqual(exported[1][0], "'=1+1")
            self.assertEqual(bundle.read('original/source.bin'), original)
            self.assertIn('=2+2', json.loads(bundle.read('output.json'))[0])

    def test_archived_reviews_and_approval_are_blocked(self):
        self.configure_stores()
        identity = self.start()
        self.finish(identity)
        report = self.report(identity)
        self.assertEqual(self.client.post('/api/v1/retailers/archive', json={'ids': [self.retailer]}).status_code, 200)
        reread = self.report(identity)
        self.assertFalse(reread['canReview'])
        self.assertFalse(reread['canApprove'])
        self.assertEqual(self.client.post('/api/v1/batches/' + identity + '/processing-review',
                                         json=dict(checked=True, note='Reviewed.', fingerprint=report['fingerprint'])).status_code, 409)
        self.assertEqual(self.client.post('/api/v1/batches/' + identity + '/approve').status_code, 409)

    def test_report_shows_bounded_private_before_after_events(self):
        fixtures.app.app.config['BATCH_TEST_EXECUTOR'] = execute_with_evidence
        original = b'sku,store_id\n' + b' private-cell-value ,A\n' * 40
        identity = self.start(original)
        self.finish(identity)
        report = self.report(identity)
        self.assertEqual(len(report['changes']), 25)
        self.assertEqual(report['changeTotal'], 40)
        self.assertEqual(report['reportedChangeCount'], 40)
        self.assertTrue(report['changesTruncated'])
        self.assertEqual(report['changes'][0]['before'], ' private-cell-value ')
        self.assertEqual(report['changes'][0]['after'], 'private-cell-value')
        self.assertEqual(report['changes'][0]['sequence'], 1)
        self.assertEqual(report['changes'][0]['attempt'], 1)
        self.assertNotIn('private-cell-value', json.dumps(self.jobs()))
        archive = self.client.get('/api/v1/batches/' + identity + '/evidence.zip')
        with zipfile.ZipFile(io.BytesIO(archive.data)) as bundle:
            self.assertEqual(bundle.read('original/source.bin'), original)
            self.assertEqual(len(json.loads(bundle.read('output.json'))), 40)
            self.assertEqual(len(json.loads(bundle.read('processing_evidence.json'))['steps'][0]['changes']), 40)

    def test_stopped_progress_uses_retained_successful_rule_evidence(self):
        fixtures.app.app.config['BATCH_TEST_EXECUTOR'] = execute_with_evidence
        numeric = dict(id='numeric', name='Validate sales', field='sales',
                       category='Transformation', operation='numeric')
        self.config['pipeline'] = [self.rule, numeric]
        self.client.put('/api/v1/retailers/' + self.retailer, json=self.config)
        identity = self.start(b'sku,store_id,sales\n x ,A,bad\n')
        self.finish(identity)
        report = self.report(identity)
        self.assertEqual(report['job']['status'], 'Cancelled Job')
        self.assertEqual(report['progress']['completedRules'], 1)
        self.assertEqual(report['progress']['totalRules'], 2)
        self.assertIsNone(report['progress']['percent'])
        self.assertEqual(report['changes'][0]['before'], ' x ')
        self.assertEqual(report['changes'][0]['after'], 'x')
        self.assertIn('not a final output preview', ' '.join(report['availability']))

    def test_active_progress_does_not_infer_completed_rules_from_sequence(self):
        self.config['pipeline'] = [self.rule, dict(self.rule, id='trim-again')]
        self.client.put('/api/v1/retailers/' + self.retailer, json=self.config)
        identity = self.start()
        with get_db_connection() as db:
            db.execute('UPDATE batch_attempts SET progress=? WHERE id=?',
                       (json.dumps(dict(sequence=2, ruleName='Trim again', attempt=1)), identity))
        report = self.report(identity)
        self.assertEqual(report['progress']['completedRules'], 0)
        with get_db_connection() as db:
            __import__('processing_review').capture_audit(db, identity, [
                dict(sequence=1, result='Successful')])
        self.assertEqual(self.report(identity)['progress']['completedRules'], 1)

    def test_cli_application_import_does_not_recover_live_jobs(self):
        identity = self.start()
        # A separate process mirrors demo/maintenance CLI imports while the
        # server is running. check_postgres.py supplies its isolated schema URL.
        child = subprocess.run([sys.executable, '-c', 'import app'],
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(child.returncode, 0, child.stderr)
        pending = self.client.get('/api/v1/batches').json['active']
        self.assertEqual([job['id'] for job in pending], [identity])
        self.assertEqual(self.jobs(), [])

    def test_explicit_server_recovery_is_idempotent_and_preserves_source(self):
        source = b'sku,store_id\n retained ,A\n'
        identity = self.start(source)
        recover = fixtures.app.app.extensions['batch_recover']
        self.assertEqual(recover(), 1)
        self.assertEqual(recover(), 0)
        jobs = self.jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['id'], identity)
        self.assertEqual(jobs[0]['status'], 'Cancelled Job')
        self.assertIn('JOB_SERVER_RESTARTED', jobs[0]['errorCodes'])
        with get_db_connection() as db:
            stored = db.execute('SELECT source FROM batch_jobs WHERE id=?', (identity,)).fetchone()[0]
        self.assertEqual(bytes(stored), source)

    def test_completed_cancellation_retains_final_and_approval_audit_privately(self):
        fixtures.app.app.config['BATCH_TEST_EXECUTOR'] = execute_with_evidence
        original = b'sku,store_id\n retained ,A\n'
        identity = self.start(original)
        self.finish(identity)
        self.assertEqual(self.client.post('/api/v1/batches/' + identity + '/approve').status_code, 200)
        self.assertEqual(self.client.post('/api/v1/batches/' + identity + '/cancel').status_code, 200)
        public = next(job for job in self.jobs() if job['id'] == identity)
        self.assertEqual(public['status'], 'Cancelled Job')
        self.assertFalse(public['hasAudit'])
        self.assertIsNone(public['end_time'])
        self.assertEqual(self.client.get('/api/v1/batches/' + identity + '/audit').status_code, 404)
        with get_db_connection() as db:
            stored = db.execute('SELECT output,audit FROM batch_jobs WHERE id=?', (identity,)).fetchone()
        self.assertIsNone(stored['output'])
        self.assertIsNone(stored['audit'])
        exported = self.client.get('/api/v1/batches/' + identity + '/evidence.zip')
        with zipfile.ZipFile(io.BytesIO(exported.data)) as bundle:
            self.assertEqual(bundle.read('original/source.bin'), original)
            self.assertNotIn('output.json', bundle.namelist())
            audit = json.loads(bundle.read('execution_audit.json'))
            self.assertTrue(any(event['ruleName'] == 'Job approval' for event in audit))
            self.assertEqual(audit[-1]['ruleName'], 'Job cancellation')
            self.assertTrue(any(event['ruleName'] == 'Trim SKU' for event in audit))

    def test_direct_exports_include_all_rows_and_preserve_text_ids_and_numbers(self):
        fixtures.app.app.config['BATCH_TEST_EXECUTOR'] = execute_with_evidence
        self.config['pipeline'] = [self.rule, dict(id='sales', name='Numeric sales',
            category='Transformation', operation='numeric', field='sales')]
        self.client.put('/api/v1/retailers/' + self.retailer, json=self.config)
        source = ('sku,store_id,sales\n' + ''.join(f' {i:03d} ,A,12.5\n' for i in range(1, 41))).encode()
        identity = self.start(source)
        self.assertFalse(self.report(identity)['canExport'])
        self.assertEqual(self.client.get('/api/v1/batches/' + identity + '/output').status_code, 409)
        self.finish(identity)
        self.assertTrue(self.report(identity)['canExport'])
        base = '/api/v1/batches/' + identity + '/output?format='
        exported = {}
        for kind in ('csv', 'json', 'xlsx'):
            response = self.client.get(base + kind)
            self.assertEqual(response.status_code, 200, response.data[:200])
            self.assertIn('processed_data.' + kind, response.headers['Content-Disposition'])
            exported[kind] = response.data
        csv_rows = list(csv.DictReader(io.StringIO(exported['csv'].decode('utf-8-sig'))))
        self.assertEqual(len(csv_rows), 40)
        self.assertEqual(csv_rows[0]['sku'], '001')
        json_rows = json.loads(exported['json'])
        self.assertEqual(len(json_rows), 40)
        self.assertEqual(json_rows[0]['sku'], '001')
        self.assertEqual(json_rows[0]['sales'], 12.5)
        book = load_workbook(io.BytesIO(exported['xlsx']), read_only=True, data_only=False)
        try:
            rows = list(book.active.values)
            self.assertEqual(len(rows), 41)
            self.assertEqual(rows[1][0], '001')
            self.assertEqual(rows[1][2], 12.5)
        finally:
            book.close()
        with get_db_connection() as db:
            stored = db.execute('SELECT source FROM batch_jobs WHERE id=?', (identity,)).fetchone()[0]
        self.assertEqual(bytes(stored), source)
        self.assertEqual(self.client.post('/api/v1/batches/' + identity + '/approve').status_code, 200)
        self.assertTrue(self.report(identity)['canExport'])
        self.assertEqual(self.client.get(base + 'json').status_code, 200)
        self.assertEqual(self.client.post('/api/v1/batches/' + identity + '/cancel').status_code, 200)
        self.assertFalse(self.report(identity)['canExport'])
        self.assertEqual(self.client.get(base + 'json').status_code, 409)

    def test_direct_csv_xlsx_are_formula_safe_while_json_preserves_literals(self):
        self.config['pipeline'] = []
        self.client.put('/api/v1/retailers/' + self.retailer, json=self.config)
        source = b'=2+2,store_id\n=1+1,A\n'
        identity = self.start(source)
        self.finish(identity)
        base = '/api/v1/batches/' + identity + '/output?format='
        csv_rows = list(csv.reader(io.StringIO(self.client.get(base + 'csv').data.decode('utf-8-sig'))))
        self.assertEqual(csv_rows[0][0], "'=2+2")
        self.assertEqual(csv_rows[1][0], "'=1+1")
        book = load_workbook(io.BytesIO(self.client.get(base + 'xlsx').data), read_only=True, data_only=False)
        try:
            self.assertEqual(book.active['A1'].value, "'=2+2")
            self.assertNotEqual(book.active['A1'].data_type, 'f')
            self.assertEqual(book.active['A2'].value, "'=1+1")
            self.assertNotEqual(book.active['A2'].data_type, 'f')
        finally:
            book.close()
        self.assertEqual(json.loads(self.client.get(base + 'json').data)[0]['=2+2'], '=1+1')
        with get_db_connection() as db:
            self.assertEqual(bytes(db.execute('SELECT source FROM batch_jobs WHERE id=?', (identity,)).fetchone()[0]), source)

    def test_output_export_errors_and_excel_bounds_do_not_truncate(self):
        self.assertEqual(self.client.get('/api/v1/batches/missing/output').status_code, 404)
        identity = self.start()
        self.finish(identity)
        base = '/api/v1/batches/' + identity + '/output?format='
        self.assertEqual(self.client.get(base + 'unsupported').status_code, 400)
        from processing_review import xlsx_bytes
        with patch('processing_review.MAX_EXCEL_DATA_ROWS', 1), self.assertRaisesRegex(ValueError, 'row or column limits'):
            xlsx_bytes([{'a': 1}, {'a': 2}], ['a'])
        with patch('processing_review.MAX_EXCEL_COLUMNS', 1), self.assertRaisesRegex(ValueError, 'row or column limits'):
            xlsx_bytes([{'a': 1, 'b': 2}], ['a', 'b'])
        with self.assertRaisesRegex(ValueError, '32,767'):
            xlsx_bytes([{'a': 'x' * 32768}], ['a'])
        with self.assertRaisesRegex(ValueError, 'control characters'):
            xlsx_bytes([{'a': 'bad\x01value'}], ['a'])
        with get_db_connection() as db:
            db.execute('UPDATE batch_jobs SET output=NULL WHERE id=?', (identity,))
        self.assertFalse(self.report(identity)['canExport'])
        self.assertEqual(self.client.get(base + 'json').status_code, 409)

    def test_unknown_and_invalid_query_have_structured_errors(self):
        self.assertEqual(self.client.get('/api/v1/batches/unknown/processing-report').status_code, 404)
        identity = self.start()
        for query in ('page=0', 'pageSize=2000', 'severity=unknown'):
            self.assertEqual(self.client.get('/api/v1/batches/' + identity + '/processing-report?' + query).status_code, 400)


if __name__ == '__main__':
    unittest.main()
