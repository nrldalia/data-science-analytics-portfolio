import unittest,json
import test_batch_jobs as fixtures
from database import get_db_connection
class CompareRunTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    start=fixtures.BatchJobTests.start
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs
    complete=fixtures.BatchJobTests.complete
    def compare(self,a,b):return self.client.get('/api/v1/batches/compare',query_string={'left':a,'right':b})
    def test_counts_and_rule_changes_without_data(self):
        a=self.complete();rule={**self.rule,'description':'Changed explanation'}
        self.client.put('/api/v1/retailers/'+self.retailer,json={**self.config,'pipeline':[rule]})
        bid=self.start(source=b'sku\nsecret-a\nsecret-b\n');self.finish(bid)
        result=self.compare(a['id'],bid).get_json();self.assertEqual(result['deltas']['rowsReceived'],1)
        self.assertEqual(result['ruleChanges'][0]['change'],'Changed');self.assertNotIn('secret-a',json.dumps(result))
        self.assertEqual(len(self.jobs()),2)
    def test_cancelled_unavailable_and_invalid_choices(self):
        a=self.complete();bid=self.start();self.client.post('/api/v1/batches/'+bid+'/cancel')
        result=self.compare(a['id'],bid).get_json();self.assertIsNone(result['deltas']['durationSeconds']);self.assertIsNone(result['deltas']['rowsReceived'])
        self.assertEqual(self.compare(bid,bid).status_code,400);self.assertEqual(self.compare(bid,'missing').status_code,404)
        other=self.client.post('/api/v1/retailers',json={**self.config,'key':'OTHER_COMPARE'}).get_json()['retailer']['id']
        with get_db_connection() as db:db.execute('UPDATE batch_jobs SET retailer_id=? WHERE id=?',(other,bid))
        self.assertEqual(self.compare(a['id'],bid).status_code,400)
