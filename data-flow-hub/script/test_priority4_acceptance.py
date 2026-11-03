"""Independent Priority 4 acceptance checks using real API launches and rules.

Run with check_postgres.py; its disposable schema isolates application records.
"""
import csv
import hashlib
import io
import json
import unittest
import zipfile

import test_batch_jobs as fixtures
from database import get_db_connection
from retailer_setup import apply_pipeline


def execute_real_rule(records, rule):
    output, steps, issues, trace = apply_pipeline(records, [rule])
    return {'output': output, 'issueCount': len(issues), 'issues': issues,
            'changedCells': len(trace), 'trace': trace}


class Priority4AcceptanceTests(unittest.TestCase):
    tearDown = fixtures.BatchJobTests.tearDown
    finish = fixtures.BatchJobTests.finish
    jobs = fixtures.BatchJobTests.jobs

    def setUp(self):
        fixtures.BatchJobTests.setUp(self)
        fixtures.app.app.config['BATCH_TEST_EXECUTOR'] = execute_real_rule

    def configuration(self):
        return next(r for r in self.client.get('/api/v1/retailers').json['retailers']
                    if r['id'] == self.retailer)

    def configure(self, **changes):
        response = self.client.put('/api/v1/retailers/' + self.retailer,
                                   json={**self.configuration(), **changes})
        self.assertEqual(response.status_code, 200, response.data)
        return response.json['retailer']

    def launch(self, period='2026-W02', source=b'sku,Store ID\n item ,A\n',
               filename='receipt.csv', store_field='Store ID', profile=None):
        data = {'retailerId': self.retailer, 'period': period,
                'file': (io.BytesIO(source), filename)}
        if store_field is not None:
            data['storeIdField'] = store_field
        if profile:
            data['inputFileId'] = profile
        response = self.client.post('/api/v1/batches', data=data)
        self.assertEqual(response.status_code, 202, response.data)
        return response.json['attemptId']

    def report(self, jid, query=''):
        response = self.client.get('/api/v1/batches/' + jid + '/processing-report' + query)
        self.assertEqual(response.status_code, 200, response.data)
        return response.json['report']

    def approve(self, jid):
        response = self.client.post('/api/v1/batches/' + jid + '/approve')
        self.assertEqual(response.status_code, 200, response.data)

    def trends(self, end='2026-W03', weeks=4, **filters):
        response = self.client.get('/api/v1/kpi-trends',
                                   query_string={'retailerId': self.retailer,
                                                 'endPeriod': end, 'weeks': weeks,
                                                 **filters})
        self.assertEqual(response.status_code, 200, response.data)
        return response.json

    def test_processing_report_and_downloads_preserve_original_evidence(self):
        self.configure(stores=[{'key': 'A', 'name': 'Active A'},
                               {'key': 'B', 'name': 'Missing B'},
                               {'key': 'I', 'name': 'Inactive I', 'status': 'Inactive'}])
        source = b'sku,Store ID,=2+2\n item ,A,normal\n extra ,I,=1+1\n new ,N,@example\n'
        jid = self.launch(source=source, filename='../unsafe.csv')
        pending = self.report(jid)
        if pending['progress']['percent'] is not None:
            self.assertLess(pending['progress']['percent'], 100)
        self.finish(jid)
        report = self.report(jid)
        self.assertEqual(report['job']['status'], 'Completed')
        self.assertEqual(report['progress']['percent'], 100)
        reconciliation = report['reconciliation']
        self.assertEqual(reconciliation['rowsReceived'], 3)
        self.assertEqual(reconciliation['rowsOutput'], 3)
        self.assertEqual(reconciliation['expectedStores'], 2)
        self.assertEqual(reconciliation['receivedExpectedStores'], 1)
        self.assertEqual(reconciliation['coveragePercent'], 50)
        self.assertEqual([s['key'] for s in reconciliation['missingStores']], ['B'])
        self.assertEqual([s['key'] for s in reconciliation['newStores']], ['N'])
        response = self.client.get('/api/v1/batches/' + jid + '/evidence.zip')
        self.assertEqual(response.status_code, 200, response.data)
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            self.assertTrue(all(not n.startswith('/') and '..' not in n.split('/')
                                for n in archive.namelist()))
            self.assertEqual(archive.read('original/source.bin'), source)
            self.assertIn('rules.json', archive.namelist())
            self.assertEqual(json.loads(archive.read('metrics.json'))['sourceSha256'], hashlib.sha256(source).hexdigest())
            self.assertIn('execution_audit.json', archive.namelist())
            self.assertEqual(json.loads(archive.read('output.json'))[0]['sku'], 'item')
            self.assertEqual(json.loads(archive.read('output.json'))[1]['=2+2'], '=1+1')
            csv_rows = list(csv.reader(io.StringIO(archive.read('output.csv').decode('utf-8-sig'))))
            self.assertEqual(csv_rows[0][-1], "'=2+2")
            self.assertEqual(csv_rows[2][-1], "'=1+1")
        with get_db_connection() as db:
            saved = db.execute('SELECT source,output FROM batch_jobs WHERE id=?', (jid,)).fetchone()
            self.assertEqual(saved['source'], source)
            self.assertEqual(json.loads(saved['output'])[0]['sku'], 'item')
        self.assertEqual(self.report(jid)['fingerprint'], report['fingerprint'])

    def test_failed_rows_are_private_and_retry_retains_source_and_lineage(self):
        numeric = {**self.rule, 'operation': 'numeric', 'category': 'Transformation'}
        self.configure(pipeline=[numeric])
        source = b'sku,Store ID\nPRIVATE-invalid-cell,A\n'
        failed = self.launch(source=source)
        self.finish(failed)
        report = self.report(failed)
        self.assertEqual(report['job']['status'], 'Cancelled Job')
        self.assertTrue(any(i.get('row') == 1 and i.get('field') == 'sku'
                            for i in report['issues']))
        self.assertNotIn('PRIVATE-invalid-cell', json.dumps(self.jobs()))
        exported = self.client.get('/api/v1/batches/' + failed + '/exceptions.csv')
        self.assertEqual(exported.status_code, 200)
        self.assertGreater(len(list(csv.reader(io.StringIO(exported.data.decode('utf-8-sig'))))), 1)
        self.assertNotIn('PRIVATE-invalid-cell', exported.data.decode('utf-8-sig'))
        self.configure(pipeline=[self.rule])
        response = self.client.post('/api/v1/batches/' + failed + '/reprocess')
        self.assertEqual(response.status_code, 202, response.data)
        replacement = response.json['attemptId']
        self.assertEqual(self.client.post('/api/v1/batches/' + failed + '/reprocess').status_code, 409)
        self.finish(replacement)
        retry = self.report(replacement)
        self.assertEqual(retry['job']['status'], 'Completed')
        self.assertEqual(retry['lineage']['rootJobId'], failed)
        self.assertEqual(retry['lineage']['reprocessOf'], failed)
        self.assertEqual(retry['lineage']['attemptNumber'], 2)
        self.assertEqual(self.report(failed)['job']['status'], 'Cancelled Job')
        with get_db_connection() as db:
            for jid in (failed, replacement):
                self.assertEqual(db.execute('SELECT source FROM batch_jobs WHERE id=?',
                                            (jid,)).fetchone()[0], source)

    def test_review_is_fingerprint_bound_single_use_and_not_approval(self):
        calls = []
        def recovered(records, rule):
            calls.append(1)
            if len(calls) == 1:
                return {'errorCode': 'RULE_EXECUTION_ERROR', 'message': 'Temporary worker failure.'}
            return execute_real_rule(records, rule)
        fixtures.app.app.config['BATCH_TEST_EXECUTOR'] = recovered
        jid = self.launch()
        self.finish(jid)
        report = self.report(jid)
        self.assertEqual(report['job']['status'], 'Completed with Interruption')
        self.assertTrue(report['canReview'])
        path = '/api/v1/batches/' + jid + '/processing-review'
        self.assertEqual(self.client.post(path, json={'checked': True, 'note': 'Reviewed',
                                                      'fingerprint': 'stale'}).status_code, 409)
        response = self.client.post(path, json={'checked': True,
                                               'note': 'Verified recovery against original source.',
                                               'fingerprint': report['fingerprint']})
        self.assertEqual(response.status_code, 200, response.data)
        reviewed = self.report(jid)
        self.assertTrue(reviewed['review'])
        self.assertEqual(reviewed['job']['status'], 'Completed with Interruption')
        self.assertEqual(self.client.post(path, json={'checked': True, 'note': 'Again',
                                                      'fingerprint': reviewed['fingerprint']}).status_code, 409)
        self.approve(jid)
        self.assertEqual(self.report(jid)['job']['status'], 'Approved Job')
        rates = self.trends(end='2026-W02', weeks=1)['periods'][0]
        self.assertEqual(rates['firstAttemptSuccessRate'], 0)
        self.assertEqual(rates['reprocessingRate'], 0)

    def test_active_and_archived_runs_cannot_be_reviewed_or_exported_as_complete(self):
        jid = self.launch()
        self.assertEqual(self.client.get('/api/v1/batches/' + jid + '/evidence.zip').status_code, 409)
        response = self.client.post('/api/v1/batches/' + jid + '/processing-review',
                                    json={'checked': True, 'note': 'Premature', 'fingerprint': 'active'})
        self.assertIn(response.status_code, (404, 409))
        self.finish(jid)
        report = self.report(jid)
        self.assertTrue(report['canReview'])
        archived = self.client.post('/api/v1/retailers/archive', json={'ids': [self.retailer]})
        self.assertEqual(archived.status_code, 200, archived.data)
        now_archived = self.report(jid)
        self.assertFalse(now_archived['canReview'])
        self.assertFalse(now_archived['canApprove'])
        self.assertFalse(now_archived['canReprocess'])
        response = self.client.post('/api/v1/batches/' + jid + '/processing-review',
                                    json={'checked': True, 'note': 'Cannot review archived',
                                          'fingerprint': now_archived['fingerprint']})
        self.assertEqual(response.status_code, 409)
        self.assertIsNone(self.report(jid)['review'])
        self.assertEqual(self.client.post('/api/v1/batches/' + jid + '/approve').status_code, 409)

    def test_trends_publish_latest_approval_keep_gaps_and_frozen_rosters(self):
        self.configure(stores=[{'key': 'A', 'name': 'A'},
                               {'key': 'B', 'name': 'B'},
                               {'key': 'I', 'name': 'I', 'status': 'Inactive'}])
        old = self.launch('2025-W52', b'sku,Store ID\na,A\ni,I\nn,N\n')
        self.finish(old); self.approve(old)
        provisional = self.launch('2026-W01')
        self.finish(provisional)
        self.configure(stores=[{'key': 'A', 'name': 'A'}, {'key': 'C', 'name': 'C'}])
        first = self.launch('2026-W02', b'sku,Store ID\na,A\nc,C\n')
        self.finish(first); self.approve(first)
        self.configure(stores=[{'key': 'A', 'name': 'A'}, {'key': 'C', 'name': 'C'},
                               {'key': 'D', 'name': 'D'}])
        response = self.client.post('/api/v1/batches/' + first + '/reprocess')
        self.assertEqual(response.status_code, 202, response.data)
        latest = response.json['attemptId']
        self.finish(latest); self.approve(latest)
        data = self.trends(inputFileId='legacy')
        buckets = {p['period']: p for p in data['periods']}
        self.assertEqual(list(buckets), ['2025-W52', '2026-W01', '2026-W02', '2026-W03'])
        self.assertEqual(buckets['2025-W52']['coveragePercent'], 50)
        self.assertEqual(buckets['2025-W52']['expectedStores'], 2)
        self.assertEqual(buckets['2026-W01']['state'], 'provisional')
        self.assertIsNone(buckets['2026-W01']['coveragePercent'])
        self.assertEqual(buckets['2026-W03']['state'], 'missing')
        self.assertIsNone(buckets['2026-W03']['coveragePercent'])
        self.assertEqual(buckets['2026-W02']['approvedRunIds'], [latest])
        self.assertAlmostEqual(buckets['2026-W02']['coveragePercent'], 200 / 3, places=2)
        self.assertTrue(buckets['2026-W02']['revised'])
        self.assertEqual(buckets['2026-W02']['attemptCount'], 2)
        self.assertEqual(buckets['2026-W02']['firstAttemptSuccessRate'], 100)
        self.assertEqual(buckets['2026-W02']['reprocessingRate'], 100)
        self.assertIsNone(buckets['2026-W02']['onTimeCoveragePercent'])
        self.assertIsNotNone(buckets['2026-W02']['medianDurationSeconds'])
        self.assertIsNotNone(buckets['2026-W02']['p95DurationSeconds'])
        self.assertEqual(self.report(first)['job']['status'], 'Approved Job')
        self.assertEqual(self.report(old)['job']['status'], 'Approved Job')

    def test_saved_input_profiles_have_separate_publication_scopes(self):
        self.configure(stores=[{'key': 'A', 'name': 'A'}, {'key': 'B', 'name': 'B'}])
        profiles = []
        for name in ('first.csv', 'second.csv'):
            profile = {'id': '', 'purpose': 'Transaction', 'fileType': 'CSV',
                       'delimiter': 'Comma', 'encoding': 'utf-8', 'isZipFolder': False,
                       'filename': name, 'filePath': 'incoming', 'maxColumns': 2,
                       'headerRow': 1, 'readMode': 'Manual', 'watchInterval': 60}
            result = self.client.post('/api/v1/retailers/' + self.retailer + '/input-files',
                                      json={'profile': profile})
            self.assertEqual(result.status_code, 200, result.data)
            profiles.append(result.json['inputFile']['id'])
        first = self.launch(profile=profiles[0], source=b'sku,Store ID\na,A\n')
        self.finish(first); self.approve(first)
        second = self.launch(profile=profiles[1], source=b'sku,Store ID\na,A\nb,B\n')
        self.finish(second); self.approve(second)
        combined = self.trends(end='2026-W02', weeks=1)['periods'][0]
        self.assertEqual(set(combined['approvedRunIds']), {first, second})
        self.assertEqual(combined['publishedScopes'], 2)
        self.assertEqual(combined['coveragePercent'], 75)
        self.assertEqual(self.trends(end='2026-W02', weeks=1,
                                     inputFileId=profiles[0])['periods'][0]['coveragePercent'], 50)
        self.assertEqual(self.trends(end='2026-W02', weeks=1,
                                     inputFileId=profiles[1])['periods'][0]['coveragePercent'], 100)
        legacy = self.trends(end='2026-W02', weeks=1, inputFileId='legacy')['periods'][0]
        self.assertEqual(legacy['state'], 'missing')
        self.assertIsNone(legacy['coveragePercent'])

    def test_unmapped_input_does_not_invent_zero_coverage(self):
        self.configure(stores=[{'key': 'A', 'name': 'Expected A'}])
        jid = self.launch(source=b'sku\n item \n', store_field=None)
        self.finish(jid); self.approve(jid)
        period = self.trends(end='2026-W02', weeks=1)['periods'][0]
        self.assertEqual(period['state'], 'published')
        self.assertIsNone(period['coveragePercent'])
        self.assertIsNone(period['receivedExpectedStores'])
        self.assertIsNone(period['onTimeCoveragePercent'])


if __name__ == '__main__':
    unittest.main()
