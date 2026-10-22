import json,unittest,time
import test_batch_jobs as fixtures
from database import get_db_connection

class FailureDetailTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    start=fixtures.BatchJobTests.start
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs
    complete=fixtures.BatchJobTests.complete

    def test_three_failures_visible_without_cancelled_audit(self):
        fixtures.app.app.config['BATCH_TEST_EXECUTOR']=lambda records,rule:{'errorCode':'RULE_EXECUTION_ERROR','message':'Worker stopped before returning a result.'}
        job=self.complete();detail=job['metrics']['failureDetails'][0]
        self.assertEqual((detail['sequence'],detail['ruleName'],detail['attempt'],detail['maxAttempts']),(1,'Trim SKU',3,3))
        self.assertEqual(detail['reason'],'Worker stopped before returning a result.')
        self.assertEqual(self.client.get('/api/v1/batches/'+job['id']+'/status').get_json()['job']['metrics']['failureDetails'],[detail])
        self.assertIsNone(job['end_time']);self.assertFalse(job['hasAudit'])
        self.assertEqual(self.client.get('/api/v1/batches/'+job['id']+'/audit').status_code,404)

    def test_numeric_failure_counts_exclude_data(self):
        rule={**self.rule,'operation':'numeric','category':'Transformation'}
        self.client.put('/api/v1/retailers/'+self.retailer,json={**self.config,'pipeline':[rule]})
        aid=self.start(source=b'sku\nprivate-value-a\nprivate-value-b\n');self.finish(aid)
        job=self.jobs()[0];detail=job['metrics']['failureDetails'][0]
        self.assertEqual(detail['issueCount'],2)
        self.assertEqual(detail['reason'],'2 invalid numeric values in field sku.')
        self.assertNotIn('private-value',json.dumps(job))

    def test_recovery_and_operator_cancellation_are_distinct(self):
        calls=[]
        def flaky(records,rule):
            calls.append(1)
            return {'errorCode':'RULE_EXECUTION_ERROR','message':'Temporary worker failure.'} if len(calls)==1 else fixtures.execute(records,rule)
        fixtures.app.app.config['BATCH_TEST_EXECUTOR']=flaky
        job=self.complete();detail=job['metrics']['failureDetails'][0]
        self.assertEqual((detail['attempt'],detail['recoveredOnAttempt']),(1,2))
        self.assertEqual(job['status'],'Completed with Interruption')
        self.client.post('/api/v1/batches/'+job['id']+'/cancel')
        self.assertEqual(self.jobs()[0]['metrics']['cancellationDetails']['errorCode'],'JOB_CANCELLED_BY_USER')

    def test_timeout_keeps_current_rule_context(self):
        aid=self.start()
        with get_db_connection() as db:
            db.execute('UPDATE batch_attempts SET deadline=?,progress=? WHERE id=?',(time.time()-1,json.dumps({'sequence':1,'ruleName':'Trim SKU','attempt':2}),aid))
        self.finish(aid);detail=self.jobs()[0]['metrics']['cancellationDetails']
        self.assertEqual((detail['errorCode'],detail['sequence'],detail['attempt']),('JOB_TIMEOUT',1,2))

if __name__=='__main__':unittest.main()
