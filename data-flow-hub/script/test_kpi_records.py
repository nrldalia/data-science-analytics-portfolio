import io,json,unittest
import test_batch_jobs as fixtures
from database import get_db_connection
from kpi_records import evaluate_kpi,validate_kpi,totals,average,change

SETTINGS={'weeks':8,'storeLimit':30,'retailerLimit':30,'countLimit':40,'salesField':'sales','quantityField':'qty','storeField':'store'}
PROFILE={'id':'kpi-input','purpose':'Transaction','kpi':SETTINGS}
def rows(a=100,b=100):return [{'sku':' x ','store':'A','sales':a,'qty':2},{'sku':' y ','store':'B','sales':b,'qty':3}]

class KPITests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs
    def baseline(self,period='2026-W40',records=None,status='Completed',profile='kpi-input',jid='baseline'):
        with get_db_connection() as db:
            db.execute('INSERT INTO batch_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(jid,self.retailer,'Retailer',period,'2026-10-01T00:00:00Z','2026-10-01T00:01:00Z',status,'sales.csv',b'',json.dumps([]),json.dumps(records if records is not None else rows()),json.dumps([]),json.dumps([]),None,json.dumps({'inputFile':{'id':profile,'purpose':'Transaction'}})))
    def evaluate(self,records=None,period='2026-W41',profile=None):
        with get_db_connection() as db:return evaluate_kpi(db,self.retailer,period,records if records is not None else rows(),profile or PROFILE)
    def run_kpi(self):
        profile={'id':'','purpose':'Transaction','fileType':'CSV','delimiter':'Comma','encoding':'utf-8','isZipFolder':False,'filename':'sales.csv','filePath':str(__import__('input_files').CODEx_ROOT/'incoming'),'maxColumns':4,'headerRow':1,'readMode':'Manual','watchInterval':60,'kpi':SETTINGS}
        response=self.client.post(f'/api/v1/retailers/{self.retailer}/input-files',json={'profile':profile})
        self.assertEqual(response.status_code,200,response.data);saved=response.get_json()['inputFile']
        config=next(r for r in self.client.get('/api/v1/retailers').get_json()['retailers'] if r['id']==self.retailer)
        config['pipeline'].append({'id':'kpi-rule','operation':'kpi','category':'KPI','name':'KPI Checks','description':'Check weekly KPIs.','inputFileId':saved['id'],'kpi':SETTINGS})
        self.assertEqual(self.client.put('/api/v1/retailers/'+self.retailer,json=config).status_code,200)
        response=self.client.post('/api/v1/batches',data={'file':(io.BytesIO(b'sku,store,sales,qty\nx,A,100,2\ny,B,100,3\n'),'sales.csv'),'retailerId':self.retailer,'period':'2026-W41','inputFileId':saved['id']})
        self.assertEqual(response.status_code,202,response.data);jid=response.get_json()['attemptId']
        return jid,saved
    def test_any_store_flags_even_when_retailer_and_mean_do_not(self):
        self.baseline();k=self.evaluate(rows(150,50))
        self.assertTrue(k['flagged']);self.assertEqual(k['retailerPercent'],0);self.assertEqual(k['storePercent'],0)
        self.assertEqual([s['percent'] for s in k['stores']],[50,-50]);self.assertEqual(k['quantity'],5)
    def test_boundary_ranges_and_count(self):
        self.baseline();k=self.evaluate(rows(130,70));self.assertFalse(k['flagged'])
        k=self.evaluate(rows(140,140));self.assertTrue(k['flagged']);self.assertEqual(k['retailerPercent'],40)
        k=self.evaluate(rows()+rows());self.assertEqual(k['countPercent'],100);self.assertTrue(k['flagged'])
    def test_one_eligible_run_per_week_and_input_isolation(self):
        self.baseline(records=rows(1,1),jid='old')
        self.baseline(records=rows(200,200),jid='latest')
        self.baseline(records=rows(999,999),jid='unapproved',status='Completed with Interruption')
        self.baseline(records=rows(999,999),jid='cancelled',status='Cancelled Job')
        self.baseline(records=rows(999,999),jid='other',profile='other-input')
        self.baseline(period='2026-W39',records=rows(100,100),jid='older-week',status='Approved Job')
        self.baseline(period='2026-W42',records=rows(999,999),jid='future')
        k=self.evaluate(rows(150,150));self.assertEqual(k['weeksUsed'],2);self.assertEqual(k['baselineSales'],300)
        self.assertEqual({b['jobId'] for b in k['baselineRuns']},{'latest','older-week'});self.assertEqual(len(k['missingWeeks']),6);self.assertFalse(k['flagged'])
    def test_new_missing_and_zero_baseline_stores(self):
        self.baseline();k=self.evaluate([{'store':'C','sales':200,'qty':5}])
        self.assertTrue(k['flagged']);self.assertEqual([s['percent'] for s in k['stores']],[-100,-100,None])
        with get_db_connection() as db:db.execute('DELETE FROM batch_jobs')
        self.baseline(records=rows(0,0));self.assertFalse(self.evaluate(rows(0,0))['flagged']);self.assertTrue(self.evaluate()['flagged'])
    def test_iso_year_boundary_and_missing_history(self):
        self.baseline(period='2025-W52');k=self.evaluate(period='2026-W01');self.assertEqual(k['weeksUsed'],1)
        self.assertEqual(k['baselineRuns'][0]['period'],'2025-W52');self.assertFalse(k['flagged'])
        k=self.evaluate(period='2025-W01');self.assertEqual(k['weeksUsed'],0);self.assertTrue(k['flagged'])
    def test_invalid_fields_do_not_report_partial_totals_or_values(self):
        invalid=rows();invalid[1]['sales']='PRIVATE-invalid-value'
        k=self.evaluate(invalid);self.assertIsNone(k['sales']);self.assertTrue(k['flagged']);self.assertNotIn('PRIVATE',json.dumps(k))
        self.assertTrue(totals(rows(),validate_kpi(None))['issues'])
    def test_validation_master_skip_and_large_numbers(self):
        for bad in [{'weeks':True},{'weeks':0},{'weeks':53},{'storeLimit':float('nan')},{'countLimit':-1},{'salesField':1}]:
            with self.assertRaises(ValueError):validate_kpi(bad)
        with get_db_connection() as db:self.assertIsNone(evaluate_kpi(db,self.retailer,'2026-W41',rows(),{**PROFILE,'purpose':'Master Product'}))
        self.assertEqual(average([1e308,1e308]),1e308);self.assertEqual(change(1e308,-1e308),200)
    def test_bootstrap_review_required_before_approval_and_timestamps(self):
        jid,saved=self.run_kpi();self.finish(jid);job=self.jobs()[0]
        self.assertEqual(job['status'],'Completed with Interruption');self.assertIn('KPI_REVIEW_REQUIRED',job['errorCodes'])
        path='/api/v1/batches/'+jid
        self.assertEqual(self.client.post(path+'/approve').status_code,409)
        self.assertEqual(self.client.post(path+'/kpi-review',json={'checked':False,'note':'Reviewed'}).status_code,400)
        self.assertEqual(self.client.post(path+'/kpi-review',json={'checked':True,'note':' '}).status_code,400)
        response=self.client.post(path+'/kpi-review',json={'checked':True,'note':'Checked first-week totals against source.'})
        self.assertEqual(response.status_code,200);self.assertTrue(response.get_json()['review']['checkedAt'])
        self.assertEqual(self.client.post(path+'/kpi-review',json={'checked':True,'note':'Again'}).status_code,409)
        self.assertEqual(self.client.post(path+'/approve').status_code,200)
        record=self.client.get('/api/v1/kpi-records').get_json()['records'][0]
        self.assertEqual(record['status'],'Approved Job');self.assertTrue(record['approvedAt']);self.assertTrue(record['kpi']['review']['checkedAt'])
        audit=self.client.get(path+'/audit').get_json()['entries'];self.assertTrue(any(e['ruleName']=='Manual KPI review' for e in audit))
        self.assertEqual(self.client.post(path+'/approve').status_code,409)
    def test_settings_snapshot_and_cancelled_record(self):
        jid,saved=self.run_kpi()
        response=self.client.post(f'/api/v1/retailers/{self.retailer}/input-files',json={'profile':{**saved,'kpi':{**SETTINGS,'weeks':2,'storeLimit':99}}})
        self.assertEqual(response.status_code,200);self.finish(jid)
        record=self.client.get('/api/v1/kpi-records').get_json()['records'][0]
        self.assertEqual(record['kpi']['settings']['weeks'],8);self.assertEqual(record['kpi']['settings']['storeLimit'],30)
        self.client.post('/api/v1/batches/'+jid+'/cancel')
        self.assertEqual(self.client.get('/api/v1/kpi-records').get_json()['records'][0]['status'],'Cancelled Job')
        self.assertEqual(self.client.post('/api/v1/batches/'+jid+'/kpi-review',json={'checked':True,'note':'Reviewed'}).status_code,409)
    def test_records_exclude_master_and_preserve_historical_unavailable(self):
        self.baseline()
        with get_db_connection() as db:
            db.execute('UPDATE batch_jobs SET metrics=?', (json.dumps({'inputFile':{'id':'x','purpose':'Master Product'}}),))
        self.assertEqual(self.client.get('/api/v1/kpi-records').get_json()['records'],[])
        self.baseline(jid='transaction')
        records=self.client.get('/api/v1/kpi-records').get_json()['records'];self.assertEqual(len(records),1);self.assertIsNone(records[0]['kpi'])

if __name__=='__main__':unittest.main()
