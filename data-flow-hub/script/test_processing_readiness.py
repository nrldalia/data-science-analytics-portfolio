import unittest,io
import test_batch_jobs as fixtures
class ReadinessTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    def state(self):
        return next(r for r in self.client.get('/api/v1/retailers').get_json()['retailers'] if r['id']==self.retailer)['processingReadiness']
    def sample(self,source):
        return self.client.post('/api/v1/retailers/'+self.retailer+'/sample',data={'file':(io.BytesIO(source),'sample.csv')})
    def test_sample_schema_and_optional_components(self):
        self.assertEqual(self.state()['status'],'Needs sample check')
        self.sample(b'sku\nitem\n');state=self.state()
        self.assertEqual(state['status'],'Ready for preprocessing');self.assertTrue(state['ready'])
        self.assertTrue(any('No registered stores' in w for w in state['warnings']))
        self.sample(b'wrong\nitem\n');state=self.state()
        self.assertEqual(state['status'],'Needs attention');self.assertIn('RULE_FIELD_MISSING',[i['code'] for i in state['issues']])
        self.assertEqual(self.client.get('/api/v1/batches').get_json()['jobs'],[])
    def test_reference_and_archive_are_not_ready(self):
        reference={'id':'ref','name':'Hash','category':'Transformation','operation':'reference','field':'sku'}
        self.client.put('/api/v1/retailers/'+self.retailer,json={**self.config,'pipeline':[reference]})
        self.assertEqual(self.state()['status'],'Needs attention')
        self.client.post('/api/v1/retailers/archive',json={'ids':[self.retailer]})
        self.assertEqual(self.state()['status'],'Archived')
        self.client.post('/api/v1/retailers/restore',json={'ids':[self.retailer]})
        self.assertEqual(self.state()['status'],'Needs attention')
    def test_no_rules_is_explicit_parse_only_not_false_incomplete(self):
        self.client.put('/api/v1/retailers/'+self.retailer,json={**self.config,'pipeline':[]})
        self.sample(b'sku\nitem\n');state=self.state()
        self.assertEqual(state['status'],'Ready for preprocessing')
        self.assertTrue(any('No rules configured' in w for w in state['warnings']))
