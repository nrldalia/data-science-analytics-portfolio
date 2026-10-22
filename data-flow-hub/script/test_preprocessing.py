import io,json,unittest
import test_batch_jobs as fixtures
from preprocessing import check_configuration
from database import get_db_connection

class PreprocessingTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    start=fixtures.BatchJobTests.start
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs
    def check(self,source=b'sku,Store ID\na,S1\n'):
        return self.client.post('/api/v1/batches/preprocessing',data={'file':(io.BytesIO(source),'batch.csv'),'retailerId':self.retailer,'period':'2026-W41'}).get_json()['report']

    def test_valid_check_read_only_and_confirmation_records_receipt(self):
        report=self.check();self.assertTrue(report['ready']);self.assertEqual(report['rowsReceived'],1)
        self.assertEqual(self.jobs(),[]);self.assertEqual(self.client.get('/api/v1/batches').get_json()['active'],[])
        response=self.client.post('/api/v1/batches',data={'file':(io.BytesIO(b'sku,Store ID\na,S1\n'),'batch.csv'),'retailerId':self.retailer,'period':'2026-W41','expectedConfigurationHash':report['configurationHash']})
        self.assertEqual(response.status_code,202);self.finish(response.get_json()['attemptId'])
        self.assertEqual(self.jobs()[0]['metrics']['preprocessing']['configurationHash'],report['configurationHash'])

    def test_missing_fields_and_condition_and_reference_only_all_reported(self):
        pipeline=[{**self.rule,'field':'absent'},{**self.rule,'id':'condition','condition':{'field':'missing','operator':'blank'}},{'id':'ref','name':'SHA-256','category':'Transformation','operation':'reference'}]
        self.client.put('/api/v1/retailers/'+self.retailer,json={**self.config,'pipeline':pipeline})
        report=self.check();self.assertFalse(report['ready'])
        self.assertEqual({i['code'] for i in report['issues']},{'RULE_FIELD_MISSING','CONDITION_FIELD_MISSING','REFERENCE_ONLY'})
        response=self.client.post('/api/v1/batches',data={'file':(io.BytesIO(b'sku\na\n'),'batch.csv'),'retailerId':self.retailer,'period':'2026-W41'})
        self.assertEqual(response.status_code,400);self.assertEqual(self.jobs(),[])

    def test_rename_sequence_and_invalid_settings(self):
        rename={**self.rule,'id':'rename','category':'Transformation','operation':'rename','target':'code'}
        trim={**self.rule,'field':'code'}
        report=check_configuration({**self.config,'pipeline':[rename,trim]},[{'sku':' a '}],'2026-W41','a.csv',b'a')
        self.assertTrue(report['ready'])
        report=check_configuration({**self.config,'pipeline':[trim,rename]},[{'sku':' a '}],'2026-W41','a.csv',b'a')
        self.assertFalse(report['ready'])
        invalid={**self.rule,'operation':'range','category':'Validation','min':'100','max':'0'}
        report=check_configuration({**self.config,'pipeline':[invalid]},[{'sku':'a'}],'2026-W41','a.csv',b'a')
        self.assertEqual(report['issues'][0]['code'],'INVALID_RULE')

    def test_stale_configuration_check_cannot_start(self):
        report=self.check();self.client.put('/api/v1/retailers/'+self.retailer,json={**self.config,'pipeline':[{**self.rule,'operation':'uppercase'}]})
        response=self.client.post('/api/v1/batches',data={'file':(io.BytesIO(b'sku\na\n'),'batch.csv'),'retailerId':self.retailer,'period':'2026-W41','expectedConfigurationHash':report['configurationHash']})
        self.assertEqual(response.status_code,409);self.assertEqual(self.jobs(),[])

    def test_parse_failure_is_blocked_but_data_findings_still_execute(self):
        report=self.check(b'');self.assertFalse(report['ready']);self.assertEqual(report['issues'][0]['code'],'INPUT_PARSE_ERROR')
        numeric={**self.rule,'operation':'numeric','category':'Transformation'}
        self.client.put('/api/v1/retailers/'+self.retailer,json={**self.config,'pipeline':[numeric]})
        self.assertTrue(self.check(b'sku\ninvalid\n')['ready'])
        aid=self.start(source=b'sku\ninvalid\n');self.finish(aid)
        self.assertEqual(self.jobs()[0]['status'],'Cancelled Job')
