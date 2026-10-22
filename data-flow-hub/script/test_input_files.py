import io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import test_batch_jobs as fixtures
from input_file_io import read_records,validate_profiles,parse_hash
from input_files import CODEx_ROOT
from database import get_db_connection

class InputFileTests(unittest.TestCase):
    setUp=fixtures.BatchJobTests.setUp
    tearDown=fixtures.BatchJobTests.tearDown
    finish=fixtures.BatchJobTests.finish
    jobs=fixtures.BatchJobTests.jobs
    def profile(self,**overrides):
        return {'id':'','purpose':'Transaction','fileType':'Text','delimiter':'Pipe','encoding':'cp1252','isZipFolder':False,
            'filename':'sales.txt','filePath':str(CODEx_ROOT/'incoming'),'maxColumns':2,'headerRow':2,'readMode':'Manual','watchInterval':60,**overrides}
    def save(self,profile,**secret):
        response=self.client.post(f'/api/v1/retailers/{self.retailer}/input-files',json={'profile':profile,**secret})
        self.assertEqual(response.status_code,200,response.data)
        return response.get_json()['inputFile']
    def sample(self,p,source=b'note\nsku|name\n item |caf\xe9\n',filename='sample.txt'):
        return self.client.post(f"/api/v1/retailers/{self.retailer}/input-files/{p['id']}/sample",data={'file':(io.BytesIO(source),filename)})
    def profiles(self):return self.client.get(f'/api/v1/retailers/{self.retailer}/input-files').get_json()['inputFiles']
    def test_distinct_samples_and_rule_preview(self):
        a=self.save(self.profile());b=self.save(self.profile(purpose='Master Product',filename='products.txt'))
        self.assertEqual(self.sample(a).status_code,200)
        self.assertEqual(self.sample(b,b'note\nsku|name\n master |product\n').status_code,200)
        rows=self.profiles();self.assertEqual(rows[0]['sample']['rows'][0]['name'],'caf\xe9')
        result=self.client.post(f'/api/v1/retailers/{self.retailer}/preview',json={'pipeline':[self.rule],'inputFileId':b['id']}).get_json()
        self.assertEqual(result['final'][0]['sku'],'master')
        self.save({**a,'delimiter':'Comma'})
        self.assertFalse(self.profiles()[1]['sample']['settingsMatch'])
        self.assertEqual(self.client.post(f'/api/v1/retailers/{self.retailer}/preview',json={'pipeline':[self.rule],'inputFileId':a['id']}).status_code,400)

    def test_sheet_secret_is_encrypted_and_not_in_history(self):
        password='PRIVATE-password-for-input'
        p=self.save(self.profile(fileType='Excel (.xlsx)',filename='book.xlsx',headerRow=1),passwordMode='set',password=password)
        self.assertTrue(self.profiles()[0]['hasPassword'])
        with get_db_connection() as db:
            secret=db.execute('SELECT protected FROM input_file_secrets WHERE retailer_id=?',(self.retailer,)).fetchone()[0]
            self.assertNotIn(password.encode(),secret)
        history=self.client.get(f'/api/v1/retailers/{self.retailer}/configuration-history').get_json()
        self.assertNotIn(password,json.dumps(history));self.assertNotIn(password,json.dumps(self.profiles()))
        from openpyxl import Workbook
        import msoffcrypto
        wb=Workbook();wb.active.append(['sku']);wb.active.append([' item ']);plain=io.BytesIO();wb.save(plain);wb.close()
        encrypted=io.BytesIO();msoffcrypto.OfficeFile(io.BytesIO(plain.getvalue())).encrypt(password,encrypted)
        response=self.sample(p,encrypted.getvalue(),'encrypted.xlsx');self.assertEqual(response.status_code,200,response.data)
        self.save(p,passwordMode='clear');self.assertFalse(self.profiles()[0]['hasPassword'])
        self.assertEqual(self.sample(p,encrypted.getvalue(),'encrypted.xlsx').status_code,400)

    def test_zip_validation_header_columns_and_json(self):
        p=self.save(self.profile(isZipFolder=True,filename='sales.txt',zipFolderName='sales.zip'))
        def zip_source(name,content):
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:z.writestr(name,content)
            return out.getvalue()
        self.assertEqual(self.sample(p,zip_source('nested/sales.txt',b'note\nsku|name\nx|y\n'),'sample.zip').status_code,200)
        self.assertEqual(self.sample(p,zip_source('../sales.txt',b'x'),'sample.zip').status_code,400)
        self.assertEqual(self.sample(p,zip_source('sales.txt',b'note\nsku|name|other\nx|y|z\n'),'sample.zip').status_code,400)
        q=self.save(self.profile(fileType='JSON',filename='products.json',purpose='Master Product',headerRow=1))
        self.assertEqual(self.sample(q,b'[{"sku":"a","name":"b"}]','sample.json').status_code,200)
        self.assertEqual(self.sample(q,b'[{"sku":"a","name":"b","extra":"c"}]','sample.json').status_code,400)
        self.assertEqual(self.sample(q,b'{}'*500000,'sample.json').status_code,413)

    def test_profile_batch_uses_captured_parser_and_reprocess(self):
        p=self.save(self.profile())
        source=b'note\nsku|name\n item |caf\xe9\n'
        data={'file':(io.BytesIO(source),'sales.txt'),'retailerId':self.retailer,'inputFileId':p['id'],'period':'2026-W41'}
        report=self.client.post('/api/v1/batches/preprocessing',data=data).get_json()['report'];self.assertTrue(report['ready'])
        data['file']=(io.BytesIO(source),'sales.txt')
        response=self.client.post('/api/v1/batches',data=data);self.assertEqual(response.status_code,202,response.data)
        aid=response.get_json()['attemptId']
        self.save({**p,'delimiter':'Comma'})
        self.finish(aid);job=self.jobs()[0];self.assertEqual(job['status'],'Completed');self.assertEqual(job['metrics']['inputFile']['delimiter'],'Pipe')
        with get_db_connection() as db:
            self.assertEqual(json.loads(db.execute('SELECT output FROM batch_jobs WHERE id=?',(aid,)).fetchone()[0])[0]['sku'],'item')
            self.assertIsNone(db.execute('SELECT * FROM batch_input_records WHERE id=?',(aid,)).fetchone())
        self.save(p)
        retry=self.client.post('/api/v1/batches/'+aid+'/reprocess');self.assertEqual(retry.status_code,202,retry.data)
        self.finish(retry.get_json()['attemptId']);self.assertEqual(len(self.jobs()),2)

    def test_path_manual_and_watcher_stability_dedup_and_archive(self):
        with tempfile.TemporaryDirectory() as td, patch('input_files.CODEx_ROOT', Path(td)):
            path=Path(td)/'sales.txt';path.write_bytes(b'note\nsku|name\nx|y\n')
            p=self.save(self.profile(filePath=str(path.parent),readMode='Automatic'))
            poll=fixtures.app.app.extensions['input_poll_once']
            poll(force=True)
            with get_db_connection() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM batch_attempts').fetchone()[0],0)
            poll(force=True)
            with get_db_connection() as db:attempts=[r['id'] for r in db.execute('SELECT id FROM batch_attempts')]
            self.assertEqual(len(attempts),1);self.finish(attempts[0]);poll(force=True)
            self.assertEqual(len(self.jobs()),1)
            path.write_bytes(b'note\nsku|name\nchanged|y\n');poll(force=True);poll(force=True)
            with get_db_connection() as db:changed=[r['id'] for r in db.execute('SELECT id FROM batch_attempts')]
            self.assertEqual(len(changed),1);self.finish(changed[0]);self.assertEqual(len(self.jobs()),2)
            manual=self.client.post(f"/api/v1/retailers/{self.retailer}/input-files/{p['id']}/read",json={'period':'2026-W42'})
            self.assertEqual(manual.status_code,202,manual.data);self.finish(manual.get_json()['attemptId']);self.assertEqual(len(self.jobs()),3)
            self.client.post('/api/v1/retailers/archive',json={'ids':[self.retailer]})
            path.write_bytes(b'note\nsku|name\narchived|y\n');poll(force=True);poll(force=True);self.assertEqual(len(self.jobs()),3)
            self.assertEqual(self.client.post(f"/api/v1/retailers/{self.retailer}/input-files/{p['id']}/read",json={}).status_code,409)

    def test_path_scope_and_bad_settings(self):
        from input_files import scoped_files
        p=self.profile(id='INPUT-probe',filePath=str(CODEx_ROOT.parent/'outside-inputs'))
        with self.assertRaisesRegex(ValueError,'inside the configured input root'):scoped_files(p)
        for key,value in [('maxColumns',0),('headerRow',0),('encoding','bad-codec')]:
            response=self.client.post(f'/api/v1/retailers/{self.retailer}/input-files',json={'profile':self.profile(**{key:value})});self.assertEqual(response.status_code,400)
        p=self.save(self.profile());self.sample(p)
        self.client.delete(f"/api/v1/retailers/{self.retailer}/input-files/{p['id']}")
        self.assertEqual(self.profiles(),[])
        with get_db_connection() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM input_file_samples WHERE retailer_id=?',(self.retailer,)).fetchone()[0],0)

    def test_readiness_checks_each_input_sample(self):
        a=self.save(self.profile());b=self.save(self.profile(purpose='Master Product',filename='master.txt'))
        def state():return next(r for r in self.client.get('/api/v1/retailers').get_json()['retailers'] if r['id']==self.retailer)['processingReadiness']
        self.sample(a);self.assertEqual(state()['status'],'Needs sample check')
        self.sample(b);self.assertEqual(state()['status'],'Ready for preprocessing')
        self.save({**b,'headerRow':1});self.assertEqual(state()['status'],'Needs sample check')

    def test_previous_week_baseline_matches_input_profile(self):
        a=self.save(self.profile());b=self.save(self.profile(purpose='Master Product',filename='master.txt'))
        def run(p,period,source):
            response=self.client.post('/api/v1/batches',data={'file':(io.BytesIO(source),'source.txt'),'retailerId':self.retailer,'inputFileId':p['id'],'period':period})
            self.assertEqual(response.status_code,202,response.data)
            aid=response.get_json()['attemptId'];self.finish(aid);return next(j for j in self.jobs() if j['id']==aid)
        first=b'note\nsku|name\na|short\n'
        run(a,'2026-W40',first);run(b,'2026-W40',b'note\nsku|name\nb|much longer master product text\n')
        job=run(a,'2026-W41',b'note\nsku|name\na|changed\n')
        self.assertEqual(job['metrics']['previousFileSizeBytes'],len(first))


class InputRootTests(unittest.TestCase):
    def test_default_and_legacy_roots(self):
        import input_files
        for source, expected in [
            ('/tmp/portfolio/data-flow-hub/script/input_files.py', '/tmp/portfolio/data-flow-hub'),
            ('/tmp/Codex/portfolio/data-flow-hub/script/input_files.py', '/tmp/Codex'),
        ]:
            with self.subTest(source=source), patch.dict('os.environ', {}, clear=True), patch('input_files.__file__', source):
                self.assertEqual(input_files.resolve_input_root(), Path(expected))

    def test_explicit_root_and_symlink_escape(self):
        import input_files
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            root = Path(folder).resolve()
            with patch.dict('os.environ', {'DATAFLOW_INPUT_ROOT': str(root)}):
                self.assertEqual(input_files.resolve_input_root(), root)
            (root/'escape').symlink_to(outside, target_is_directory=True)
            with patch('input_files.CODEx_ROOT', root):
                with self.assertRaisesRegex(ValueError, 'configured input root'):
                    input_files.scoped_files({'filePath': str(root/'escape')})

    def test_invalid_explicit_root(self):
        import input_files
        with patch.dict('os.environ', {'DATAFLOW_INPUT_ROOT': 'relative/incoming'}):
            with self.assertRaisesRegex(ValueError, 'absolute'):
                input_files.resolve_input_root()
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict('os.environ', {'DATAFLOW_INPUT_ROOT': str(Path(folder)/'missing')}):
                with self.assertRaisesRegex(ValueError, 'existing directory'):
                    input_files.resolve_input_root()

if __name__=='__main__':unittest.main()
