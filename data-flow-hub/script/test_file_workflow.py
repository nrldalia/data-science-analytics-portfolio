import io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import test_batch_jobs as fixtures
from database import get_db_connection
from file_workflow import join_records,walkthrough,validate_output,step
from input_file_io import read_records,validate_profiles
from input_files import scoped_files,CODEx_ROOT

class WorkflowTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs
    def profile(self,filename='sales.csv',**kw):
        p={'id':'','purpose':'Transaction','fileType':'CSV','delimiter':'Comma','encoding':'utf-8','isZipFolder':False,'filename':filename,'filePath':str(CODEx_ROOT/'incoming'),'maxColumns':100,'headerRow':1,'readMode':'Manual','watchInterval':60,**kw}
        response=self.client.post(f'/api/v1/retailers/{self.retailer}/input-files',json={'profile':p});self.assertEqual(response.status_code,200,response.data)
        return response.get_json()['inputFile']
    def sample(self,p,source):
        response=self.client.post(f"/api/v1/retailers/{self.retailer}/input-files/{p['id']}/sample",data={'file':(io.BytesIO(source),p['filename'])});self.assertEqual(response.status_code,200,response.data)
    def configure(self,profiles,pipeline,**extra):
        config={**self.config,'inputFiles':profiles,'pipeline':pipeline,'workflowVersion':1,'primaryInputId':profiles[0]['id'],**extra}
        response=self.client.put('/api/v1/retailers/'+self.retailer,json=config);self.assertEqual(response.status_code,200,response.data)
        return response.get_json()['retailer']
    def link(self,a,b,kind='Left'):
        return {'id':'link','name':'Link Files','description':'Attach product names.','operation':'join','category':'Link Files','leftInputId':a,'rightInputId':b,'joinType':kind,'leftField':'sku','rightField':'sku','rightPrefix':'product_'}
    def test_all_join_types_and_duplicate_keys(self):
        a=[{'sku':'x','sales':1},{'sku':'z','sales':2}];b=[{'sku':'x','name':'one'},{'sku':'x','name':'two'},{'sku':'q','name':'three'}]
        expected={'Inner':2,'Left':3,'Right':3,'Full Outer':4,'Cross':6}
        for kind,count in expected.items():
            output=join_records(a,b,self.link('a','b',kind));self.assertEqual(len(output),count);self.assertIn('product_sku',output[0])
        self.assertIsNone(join_records(a,b,self.link('a','b','Right'))[-1]['sales'])
    def test_blank_keys_do_not_match_and_trimmed_keys_match(self):
        rule=self.link('a','b','Inner')
        self.assertEqual(join_records([{'sku':''}],[{'sku':''}],rule),[])
        self.assertEqual(len(join_records([{'sku':' x '}],[{'sku':'x'}],rule)),1)
        self.assertEqual(join_records([{'sku':'X'}],[{'sku':'x'}],rule),[])
    def test_join_bounds_and_colliding_prefix(self):
        with patch('file_workflow.MAX_ROWS',2):
            with self.assertRaisesRegex(ValueError,'100,000'):join_records([{'sku':'x'}]*2,[{'sku':'x'}]*2,self.link('a','b','Cross'))
        with self.assertRaisesRegex(ValueError,'collide'):join_records([{'sku':'x','product_sku':'existing'}],[{'sku':'x'}],self.link('a','b'))
    def test_zip_name_scoping_and_matching_member(self):
        p=self.profile('sales.csv',isZipFolder=True,zipFolderName='delivery.zip')
        source=io.BytesIO()
        with zipfile.ZipFile(source,'w') as z:z.writestr('nested/sales.csv','sku,sales\nx,10\n');z.writestr('nested/other.csv','other\ny\n')
        self.assertEqual(read_records(source.getvalue(),'delivery.zip',p)[0]['sales'],'10')
        with tempfile.TemporaryDirectory(dir=CODEx_ROOT) as folder:
            path=Path(folder)/'delivery.zip';path.write_bytes(source.getvalue())
            self.assertEqual(scoped_files({**p,'filePath':folder}),[path.resolve()])
        with self.assertRaisesRegex(ValueError,'exactly one'):read_records(source.getvalue(),'delivery.zip',{**p,'filename':'missing.csv'})
    def test_mandatory_path_zip_name_and_optional_defaults(self):
        p=self.profile()
        for override in [{'filePath':''},{'delimiter':''},{'encoding':''},{'isZipFolder':True,'zipFolderName':''}]:
            r=self.client.post(f'/api/v1/retailers/{self.retailer}/input-files',json={'profile':{**p,**override}});self.assertEqual(r.status_code,400)
        r=self.client.post(f'/api/v1/retailers/{self.retailer}/input-files',json={'profile':{**p,'headerRow':'','maxColumns':'','readMode':''}});self.assertEqual(r.status_code,200)
        self.assertEqual(r.get_json()['inputFile']['headerRow'],1);self.assertEqual(r.get_json()['inputFile']['maxColumns'],100)
    def test_password_yes_requires_secret_and_no_hides_and_clears(self):
        p=self.profile('book.xlsx',fileType='Excel (.xlsx)')
        base=f'/api/v1/retailers/{self.retailer}/input-files'
        self.assertEqual(self.client.post(base,json={'profile':{**p,'hasSheetPassword':True}}).status_code,400)
        self.assertEqual(self.client.post(base,json={'profile':{**p,'hasSheetPassword':True},'passwordMode':'set','password':'private-test'}).status_code,200)
        self.assertEqual(self.client.post(base,json={'profile':{**p,'hasSheetPassword':False}}).status_code,200)
        with get_db_connection() as db:self.assertIsNone(db.execute('SELECT 1 FROM input_file_secrets WHERE retailer_id=?',(self.retailer,)).fetchone())
    def test_sample_walkthrough_scoped_rules_link_layout_mapping_and_analytics(self):
        a=self.profile();b=self.profile('product.csv',purpose='Master Product')
        self.sample(a,b'sku,sales,store,qty\n x ,10,A,2\n');self.sample(b,b'sku,name\nx,apple\n')
        pipeline=[self.rule,self.link(a['id'],b['id']),{'id':'upper','name':'Uppercase product','description':'Normalise names.','operation':'uppercase','category':'Cleaning','field':'name','stage':'Layout'}]
        config=self.configure([a,b],pipeline,columnMapping=[{'source':'sales','name':'Revenue'},{'source':'name','name':'Product'}],analyticsColumns=['Revenue'])
        r=self.client.post(f'/api/v1/retailers/{self.retailer}/preview',json={'pipeline':pipeline,'inputFileId':a['id'],'workflow':{'columnMapping':config['columnMapping'],'analyticsColumns':['Revenue']}})
        self.assertEqual(r.status_code,200,r.data);d=r.get_json();self.assertEqual(d['steps'][0]['after'][0]['sku'],'x');self.assertEqual(d['steps'][1]['after'][0]['name'],'apple');self.assertEqual(d['steps'][2]['after'][0]['name'],'APPLE')
        self.assertEqual(list(d['final'][0]),['Revenue','Product']);self.assertEqual(d['analyticsColumns'],['Revenue'])
        self.assertEqual(config['primaryInputId'],a['id'])
        exported=self.client.post(f'/api/v1/retailers/{self.retailer}/example.csv',json={'pipeline':pipeline,'inputFileId':a['id'],'workflow':{'columnMapping':config['columnMapping'],'analyticsColumns':['Revenue']}})
        self.assertEqual(exported.status_code,200);self.assertEqual(exported.data.decode('utf-8-sig').splitlines(),['Revenue,Product','10,APPLE'])
    def test_layout_before_link_and_stale_linked_sample_rejected(self):
        a=self.profile();b=self.profile('product.csv',purpose='Master Product')
        self.sample(a,b'sku\nx\n');self.sample(b,b'sku\nx\n')
        layout={**self.rule,'stage':'Layout'}
        r=self.client.put('/api/v1/retailers/'+self.retailer,json={**self.config,'inputFiles':[a,b],'pipeline':[layout,self.link(a['id'],b['id'])]});self.assertEqual(r.status_code,400)
        pipeline=[self.link(a['id'],b['id'])];self.configure([a,b],pipeline)
        self.client.post(f'/api/v1/retailers/{self.retailer}/input-files',json={'profile':{**b,'delimiter':'Pipe'}})
        r=self.client.post(f'/api/v1/retailers/{self.retailer}/preview',json={'pipeline':pipeline,'inputFileId':a['id'],'workflow':{}});self.assertEqual(r.status_code,400)
    def test_mapping_and_analytics_configuration_validation(self):
        for extra in [{'columnMapping':[{'source':'sku','name':'X'},{'source':'sales','name':'X'}]},{'columnMapping':[{'source':'sku','name':'Code'}],'analyticsColumns':['sales']},{'analyticsColumns':['sku','sku']}]:
            with self.assertRaises(ValueError):validate_output({**self.config,**extra})
    def test_linked_batch_captures_companion_before_path_changes(self):
        with tempfile.TemporaryDirectory(dir=CODEx_ROOT) as folder:
            companion=Path(folder)/'product.csv';companion.write_text('sku,name\nx,apple\n')
            a=self.profile();b=self.profile('product.csv',purpose='Master Product',filePath=str(companion))
            pipeline=[self.link(a['id'],b['id']),{'id':'upper','name':'Upper product','description':'Normalise.','operation':'uppercase','category':'Cleaning','field':'name','stage':'Layout'}]
            self.configure([a,b],pipeline,columnMapping=[{'source':'name','name':'Product'},{'source':'sales','name':'Sales'}],analyticsColumns=['Sales'])
            data={'file':(io.BytesIO(b'sku,sales\nx,10\n'),'sales.csv'),'retailerId':self.retailer,'period':'2026-W41','inputFileId':a['id']}
            response=self.client.post('/api/v1/batches',data=data);self.assertEqual(response.status_code,202,response.data);jid=response.get_json()['attemptId']
            companion.write_text('sku,name\nx,CHANGED\n');self.finish(jid);job=next(j for j in self.jobs() if j['id']==jid)
            self.assertEqual(job['status'],'Completed');self.assertNotIn('kpi',job['metrics']);self.assertEqual(job['metrics']['analyticsColumns'],['Sales']);self.assertEqual(job['metrics']['linkedInputs'][0]['rowsReceived'],1)
            with get_db_connection() as db:
                output=json.loads(db.execute('SELECT output FROM batch_jobs WHERE id=?',(jid,)).fetchone()[0]);self.assertEqual(output,[{'Product':'APPLE','Sales':'10'}]);self.assertIsNone(db.execute('SELECT * FROM batch_input_records WHERE id=?',(jid,)).fetchone())
            audit=self.client.get('/api/v1/batches/'+jid+'/audit').get_json();self.assertNotIn('APPLE',json.dumps(audit))
    def test_linked_preprocessing_missing_path_and_secondary_start_blocked(self):
        a=self.profile();b=self.profile('missing.csv',purpose='Master Product');self.configure([a,b],[self.link(a['id'],b['id'])])
        def data(pid):return {'file':(io.BytesIO(b'sku\nx\n'),'sales.csv'),'retailerId':self.retailer,'period':'2026-W41','inputFileId':pid}
        r=self.client.post('/api/v1/batches/preprocessing',data=data(a['id']));self.assertFalse(r.get_json()['report']['ready']);self.assertTrue(any(i['code']=='LINKED_INPUT_ERROR' for i in r.get_json()['report']['issues']))
        self.assertEqual(self.client.post('/api/v1/batches',data=data(b['id'])).status_code,400);self.assertEqual(self.jobs(),[])
    def test_referenced_input_cannot_be_deleted(self):
        a=self.profile();b=self.profile('product.csv',purpose='Master Product');self.configure([a,b],[self.link(a['id'],b['id'])])
        self.assertEqual(self.client.delete(f"/api/v1/retailers/{self.retailer}/input-files/{b['id']}").status_code,409)
    def test_empty_inner_join_completes_layout_without_fabricating_rows(self):
        state={'datasets':{'a':[{'sku':'x'}],'b':[{'sku':'z','name':'apple'}]},'current':[{'sku':'x'}],'primary':'a','linked':False}
        pipeline=[self.link('a','b','Inner'),{'id':'upper','name':'Upper','description':'Names','operation':'uppercase','category':'Cleaning','field':'name','stage':'Layout'}]
        output,preview=walkthrough(state,{'inputFiles':[{'id':'a'},{'id':'b'}],'primaryInputId':'a','pipeline':pipeline});self.assertEqual(output,[]);self.assertEqual(preview['totalRows'],0)
    def test_validation_failure_after_link_is_logged_after_three_attempts(self):
        with tempfile.TemporaryDirectory(dir=CODEx_ROOT) as folder:
            companion=Path(folder)/'product.csv';companion.write_text('sku,name\nx,\n')
            a=self.profile();b=self.profile('product.csv',purpose='Master Product',filePath=str(companion))
            self.configure([a,b],[self.link(a['id'],b['id']),{'id':'required','name':'Required product name','description':'Require name','operation':'required','category':'Validation','field':'name','stage':'Layout'}])
            r=self.client.post('/api/v1/batches',data={'file':(io.BytesIO(b'sku,sales\nx,10\n'),'sales.csv'),'retailerId':self.retailer,'period':'2026-W41','inputFileId':a['id']});self.assertEqual(r.status_code,202,r.data);self.finish(r.get_json()['attemptId']);job=self.jobs()[0]
            self.assertEqual(job['status'],'Cancelled Job');self.assertIn('VALIDATION_REQUIRED',job['errorCodes']);self.assertEqual(job['metrics']['failureDetails'][0]['attempt'],3);self.assertFalse(job['hasAudit'])

if __name__=='__main__':unittest.main()
