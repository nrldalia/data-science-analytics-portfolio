import unittest,io,json
import test_batch_jobs as fixtures
from database import get_db_connection
class ArchiveTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    start=fixtures.BatchJobTests.start
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs
    complete=fixtures.BatchJobTests.complete
    def archive(self,ids=None):return self.client.post('/api/v1/retailers/archive',json={'ids':ids or [self.retailer]})
    def test_retained_setup_samples_history_and_restore(self):
        job=self.complete()
        self.client.post('/api/v1/retailers/'+self.retailer+'/sample',data={'file':(io.BytesIO(b'sku\nx\n'),'sample.csv')})
        with get_db_connection() as db:before=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(self.retailer,)).fetchone()[0]
        self.assertEqual(self.archive().status_code,200)
        row=next(r for r in self.client.get('/api/v1/retailers').get_json()['retailers'] if r['id']==self.retailer);self.assertTrue(row['archived'])
        self.assertEqual(self.client.get('/api/v1/retailers/'+self.retailer+'/sample').get_json()['sample']['totalRows'],1)
        self.assertEqual(self.client.get('/api/v1/batches/'+job['id']+'/audit').status_code,200)
        self.assertEqual(self.client.post('/api/v1/batches/'+job['id']+'/reprocess').status_code,409)
        self.assertEqual(self.client.put('/api/v1/retailers/'+self.retailer,json=self.config).status_code,409)
        report=self.client.post('/api/v1/batches/'+job['id']+'/preprocessing',json={}).get_json()['report'];self.assertFalse(report['ready']);self.assertIn('RETAILER_ARCHIVED',[i['code'] for i in report['issues']])
        self.assertEqual(self.client.post('/api/v1/retailers/restore',json={'ids':[self.retailer]}).status_code,200)
        with get_db_connection() as db:self.assertEqual(db.execute('SELECT payload FROM retailer_configs WHERE id=?',(self.retailer,)).fetchone()[0],before)
        self.assertEqual([e['action'] for e in self.client.get('/api/v1/retailers/'+self.retailer+'/archive-history').get_json()['events']],['Restored','Archived'])
        aid=self.start();self.finish(aid);self.assertEqual(len(self.jobs()),2)
    def test_running_and_bulk_atomicity(self):
        aid=self.start();self.assertEqual(self.archive().status_code,409)
        self.client.post('/api/v1/batches/'+aid+'/cancel')
        self.assertEqual(self.archive([self.retailer,'missing']).status_code,404)
        row=next(r for r in self.client.get('/api/v1/retailers').get_json()['retailers'] if r['id']==self.retailer);self.assertFalse(row['archived'])
        self.assertEqual(self.archive().status_code,200)
        self.assertEqual(self.archive().get_json()['changedIds'],[])
        response=self.client.post('/api/v1/batches',data={'file':(io.BytesIO(b'sku\nx\n'),'batch.csv'),'retailerId':self.retailer,'period':'2026-W41'});self.assertEqual(response.status_code,409)
