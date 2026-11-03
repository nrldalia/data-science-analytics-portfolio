"""Operational trends retain receipt scope and immutable historical denominators."""
import csv
import io
import json
import unittest
import uuid
from datetime import datetime, timezone

from operational_trends import build_trends, percentile, duration
import test_app as fixtures
from database import get_db_connection

NOW = datetime(2026, 12, 1, tzinfo=timezone.utc)


def run(identity, period='2026-W40', status='Approved Job', retailer='R1',
        expected=('A', 'B'), received=('A',), approved='2026-10-03T10:00:00Z',
        order=1, profile='INPUT-trans', **patch):
    metrics = dict(
        inputFile={'id': profile, 'filename': 'sales.csv', 'purpose': 'Transaction'},
        approvedAt=approved,
        rowsReceived=3, rowsAfterCleaning=3,
        lineage={'rootJobId': identity, 'reprocessOf': None, 'attemptNumber': 1},
        operational=dict(expectedStoreIds=list(expected), receivedExpectedStoreIds=list(received),
                         rowsReceived=3, rowsOutput=3, rowsChecked=3, issueRows=1,
                         durationMs=1000, statusAtCompletion='Completed', ruleRetryCount=0))
    metrics.update(patch.pop('metrics', {}))
    result = dict(id=identity, retailer_id=retailer, retailer_name='Retailer '+retailer,
                period=period, filename='sales.csv', status=status,
                start_time='2026-10-01T10:00:00+00:00', end_time='2026-10-01T10:00:01+00:00',
                metrics=metrics, _order=order)
    return result | patch


class OperationalTrendTests(unittest.TestCase):
    def report(self, rows, end='2026-W40', weeks=1, **kwargs):
        return build_trends(rows, [], end, weeks, current=NOW, **kwargs)

    def test_cleaning_rows_are_not_substituted_by_final_mapping_rows(self):
        receipt=run('different-stage-counts')
        receipt['metrics']['rowsAfterCleaning']=3
        receipt['metrics']['operational']['rowsOutput']=1
        self.assertEqual(self.report([receipt])['latest']['rowsAfterCleaning'],3)
        receipt['metrics']['rowsAfterCleaning']=None
        self.assertIsNone(self.report([receipt])['latest']['rowsAfterCleaning'])

    def test_published_uses_latest_approval_not_latest_processing_and_pending_revision(self):
        older = run('old', approved='2026-10-05T10:00:00Z', order=1)
        newer = run('new', approved='2026-10-04T10:00:00Z', order=2, received=('A', 'B'),
                    start_time='2026-10-03T10:00:00Z')
        pending = run('pending',status='Completed',order=3,start_time='2026-10-06T10:00:00Z')
        bucket = self.report([older,newer,pending])['latest']
        self.assertEqual(bucket['approvedRunIds'],['old'])
        self.assertTrue(bucket['revised']);self.assertTrue(bucket['pendingRevision'])
        self.assertEqual(bucket['coveragePercent'],50)
        self.assertEqual(bucket['rowsReceived'],3)
        self.assertEqual(bucket['attemptCount'],3)

    def test_roster_matching_excludes_unknown_and_inactive_ids(self):
        row = run('receipt',expected=('A','B'),received=('a','UNKNOWN','INACTIVE'))
        bucket=self.report([row])['latest']
        self.assertEqual(bucket['expectedStores'],2)
        self.assertEqual(bucket['receivedExpectedStores'],1)
        self.assertEqual(bucket['missingStores'],1)
        self.assertEqual(bucket['coveragePercent'],50)

    def test_legacy_roster_is_frozen_and_unmapped_legacy_is_unavailable(self):
        metrics=dict(inputFile={'id':'INPUT-trans'},expectedStores=[{'key':'A'},{'key':'B'}],
                     missingStores=[{'key':'B'}],storeIdField='Store ID',
                     rowsReceived=3,rowsAfterCleaning=3)
        row=run('legacy');row['metrics']=metrics
        bucket=self.report([row])['latest']
        self.assertEqual(bucket['coveragePercent'],50)
        self.assertIsNone(bucket['firstAttemptSuccessRate'])
        self.assertIsNone(bucket['qualityIssueRate'])
        metrics['storeIdField']=''
        self.assertIsNone(self.report([row])['latest']['coveragePercent'])

    def test_iso_year_missing_and_provisional_periods_are_not_zero(self):
        rows=[run('prior','2025-W52'),run('pending','2026-W02',status='Completed')]
        report=self.report(rows,end='2026-W02',weeks=3)
        self.assertEqual([b['period'] for b in report['periods']],['2025-W52','2026-W01','2026-W02'])
        self.assertEqual([b['state'] for b in report['periods']],['published','missing','provisional'])
        self.assertIsNone(report['periods'][1]['coveragePercent'])
        self.assertIsNone(report['periods'][2]['rowsReceived'])
        self.assertIsNone(report['latest']['coverageChangePoints'])

    def test_scope_dedup_weighted_coverage_and_partial_scope_metrics(self):
        small=run('small',retailer='SMALL',expected=('A',),received=('A',))
        big=run('big',retailer='BIG',expected=('A','B','C'),received=())
        report=self.report([small,big])
        self.assertEqual(report['latest']['coveragePercent'],25)
        report=self.report([small,big,run('next','2026-W41',retailer='SMALL')],end='2026-W41',weeks=2)
        self.assertEqual(report['latest']['state'],'partial')
        self.assertIsNone(report['latest']['coveragePercent'])
        self.assertIsNone(report['latest']['rowsReceived'])
        self.assertEqual(len(report['latest']['publishedSnapshots']),1)

    def test_rolling_coverage_weights_denominators_and_gaps_break_window(self):
        rows=[run('w'+str(i),'2026-W'+str(37+i),expected=tuple(str(x) for x in range(i+1)),
                  received=('0',)) for i in range(4)]
        bucket=self.report(rows,end='2026-W40',weeks=4)['latest']
        self.assertAlmostEqual(bucket['rollingCoveragePercent'],40)
        self.assertEqual(bucket['rollingCoverageWeeks'],4)
        self.assertIsNone(self.report(rows[1:],end='2026-W40',weeks=4)['latest']['rollingCoveragePercent'])

    def test_lineage_rates_count_families_not_retries_or_approvals(self):
        first=run('first',status='Cancelled Job',metrics={'lineage':{'rootJobId':'first','attemptNumber':1},
                    'operational':{'statusAtCompletion':'Cancelled Job','ruleRetryCount':0}})
        second=run('second',metrics={'lineage':{'rootJobId':'first','attemptNumber':2},
                    'operational':{'statusAtCompletion':'Completed','ruleRetryCount':0}})
        clean=run('clean')
        bucket=self.report([first,second,clean])['latest']
        self.assertEqual(bucket['firstAttemptSuccessRate'],50)
        self.assertEqual(bucket['reprocessingRate'],50)
        clean['metrics']['operational']['ruleRetryCount']=1
        self.assertEqual(self.report([first,second,clean])['latest']['firstAttemptSuccessRate'],0)
        del clean['metrics']['lineage']
        self.assertIsNone(self.report([first,second,clean])['latest']['reprocessingRate'])

    def test_percentiles_durations_and_quality_unknown_are_explicit(self):
        self.assertAlmostEqual(percentile([1,2,10],.95),9.2)
        invalid=run('invalid',order=2,metrics={'operational':{'durationMs':-1}})
        self.assertIsNone(duration(invalid))
        valid=run('valid')
        bucket=self.report([valid,invalid])['latest']
        self.assertEqual(bucket['durationSampleCount'],1)
        self.assertEqual(bucket['durationUnavailableCount'],1)
        self.assertIsNone(bucket['qualityIssueRate'])
        self.assertIsNone(bucket['onTimeCoveragePercent'])


class OperationalTrendApiTests(unittest.TestCase):
    def setUp(self):
        self.client=fixtures.module.app.test_client()
        self.rid='TRENDS-'+uuid.uuid4().hex
        self.profile='INPUT-'+uuid.uuid4().hex
        self.identity='JOB-'+uuid.uuid4().hex
        metrics=run(self.identity,retailer=self.rid,profile=self.profile)['metrics']
        with get_db_connection() as db:
            db.execute('INSERT INTO batch_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (self.identity,self.rid,'=Unsafe retailer','2026-W40',
                        '2026-10-01T10:00:00Z','2026-10-01T10:00:01Z','Approved Job',
                        'sales.csv',b'abc','[]','[]','[]','[]',None,json.dumps(metrics)))

    def test_filters_csv_and_period_validation(self):
        args=f'?retailerId={self.rid}&inputFileId={self.profile}&endPeriod=2026-W40&weeks=2'
        response=self.client.get('/api/v1/kpi-trends'+args)
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.json['latest']['approvedRunIds'],[self.identity])
        self.assertEqual(response.json['previous']['state'],'missing')
        self.assertEqual(len(response.json['availableProfiles']),1)
        exported=self.client.get('/api/v1/kpi-trends'+args+'&format=csv')
        self.assertEqual(exported.status_code,200)
        rows=list(csv.DictReader(io.StringIO(exported.data.decode('utf-8-sig'))))
        self.assertEqual(rows[0]['coveragePercent'],'')
        self.assertEqual(rows[1]['approvedRunIds'],self.identity)
        for query in ('?weeks=0','?weeks=53','?weeks=1.5','?endPeriod=2026-W99','?format=zip'):
            self.assertEqual(self.client.get('/api/v1/kpi-trends'+query).status_code,400)


if __name__=='__main__':
    unittest.main()
