from pathlib import Path
import shutil,sqlite3,json
base=Path('outputs/V1.7.0');root=Path('outputs/V1.8.0')
shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist','.venv','*.db','*.db-wal','*.db-shm'),dirs_exist_ok=True)
for rel in ['script/app.py','frontend-github/src/app.jsx','Setup_Windows.bat','Start_V1.7.0.bat']:
 p=root/rel;s=p.read_text(encoding='utf-8').replace('V1.7.0','V1.8.0').replace("version='1.7.0'","version='1.8.0'")
 if rel.startswith('Start_'):p.unlink();p=root/'Start_V1.8.0.bat'
 p.write_text(s,encoding='utf-8')
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name;d=json.loads(p.read_text());d['version']='1.8.0'
 if '' in d.get('packages',{}):d['packages']['']['version']='1.8.0'
 p.write_text(json.dumps(d,indent=2),encoding='utf-8')
p=Path('outputs/V1.3.A1.bat');p.write_text(p.read_text().replace('V1.7.0','V1.8.0').replace("'1.7.0'","'1.8.0'"),encoding='utf-8')
if (base/'script/dataflow.db').exists():
 with sqlite3.connect(base/'script/dataflow.db') as a,sqlite3.connect(root/'script/dataflow.db') as b:a.backup(b)
p=root/'script/batch_jobs.py';s=p.read_text(encoding='utf-8')
s=s.replace('from configuration_history import','from store_review import register_store_review_routes\nfrom configuration_history import',1)
s=s.replace('def register_batch_routes(app, parse_upload, error):','def register_batch_routes(app, parse_upload, error):\n    register_store_review_routes(app,error)')
start=s.index("            metrics=decode(job['metrics'],{})",s.index('    def approve(jid):'))
end=s.index("            entries=decode(job['audit'],[])",start)
s=s[:start]+s[end:]
p.write_text(s,encoding='utf-8')
# Existing tests now use independent store approval with an explicit reviewed selection.
for name in ['test_batch_metrics.py','test_configuration_history.py']:
 p=root/'script'/name;s=p.read_text(encoding='utf-8')
 if name=='test_batch_metrics.py':
  s=s.replace("        self.assertEqual(len(stores()),2);self.assertRegex(stores()[1]['suiteCode'],r'^MY6[0-9]{7}$')", "        self.assertEqual(len(stores()),1)\n        self.assertEqual(self.client.post('/api/v1/batches/'+aid+'/stores/review',json={'stores':[{'key':'NEW','name':'New store','address':'Test Road','status':'Active','exception':False}]}).status_code,200)\n        self.assertEqual(len(stores()),2);self.assertRegex(stores()[1]['suiteCode'],r'^MY6[0-9]{7}$')")
 else:
  s=s.replace("        self.assertEqual(len(self.history()),2);self.assertEqual(self.history()[0]['reason'],'New stores approved')", "        self.assertEqual(len(self.history()),1)\n        self.assertEqual(self.client.post('/api/v1/batches/'+aid+'/stores/review',json={'stores':[{'key':'NEW','name':'New store','address':'Test Road','status':'Active','exception':False}]}).status_code,200)\n        self.assertEqual(len(self.history()),2);self.assertEqual(self.history()[0]['reason'],'New stores approved')")
 p.write_text(s,encoding='utf-8')
print('V1.8.0 prepared')
