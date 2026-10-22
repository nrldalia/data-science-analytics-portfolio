from pathlib import Path
import json,shutil
root=Path('outputs/V1.2.A1')
shutil.copy('work/batch_jobs.py',root/'script/batch_jobs.py')
shutil.copy('work/BatchLogs.jsx',root/'frontend-github/src/BatchLogs.jsx')
p=root/'script/app.py';s=p.read_text().replace("version='1.2.0'","version='1.2.A1'").replace('V1.2.0','V1.2.A1')
s=s.replace('register_retailer_routes(app, parse_upload, error)','register_retailer_routes(app, parse_upload, error)\nfrom batch_jobs import register_batch_routes\nregister_batch_routes(app, parse_upload, error)')
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/app.jsx';s=p.read_text(encoding='utf-8')
s="import BatchLogs from './BatchLogs';\n"+s
s=s.replace("const [activeTab, setActiveTab] = useState('Retailer Data Setup');","const [activeTab, setActiveTab] = useState('Data Streams');\n  const [batchFile, setBatchFile] = useState(null);")
a=s.index('  const handleFileUpload = (e) => {');b=s.index('  const runCleaning =',a)
s=s[:a]+'''  const handleFileUpload = (e) => {
    const file = e.target.files[0]; if (!file) return;
    setBatchFile(file); setActiveTab('Data Streams'); e.target.value='';
  };
'''+s[b:]
a=s.index('          {/* TAB 2: DATA STREAMS MODULE */}');b=s.index('          {/* TAB 3: QUALITY ANALYTICS MODULE */}',a)
s=s[:a]+'''          {/* TAB 2: DATA STREAMS MODULE */}
          {activeTab === 'Data Streams' && <BatchLogs incomingFile={batchFile} onFileAccepted={() => setBatchFile(null)} />}

'''+s[b:]
s=s.replace('V1.2.0','V1.2.A1').replace('${runs.length} saved full-dataset runs available in Data Streams.','${runs.length} earlier uploads available in Quality Analytics. Retailer/week batches are recorded in Data Streams.')
p.write_text(s,encoding='utf-8')
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name;data=json.loads(p.read_text());data['version']='1.2.1'
 if '' in data.get('packages',{}):data['packages']['']['version']='1.2.1'
 p.write_text(json.dumps(data,indent=2))
old=root/'Start_V1.2.0.bat';new=root/'Start_V1.2.A1.bat';new.write_text(old.read_text().replace('V1.2.0','V1.2.A1'));old.unlink()
p=root/'Setup_Windows.bat';p.write_text(p.read_text().replace('Start_V1.2.0.bat','Start_V1.2.A1.bat'))
shutil.copytree('outputs/V1.2.0/frontend-github/node_modules',root/'frontend-github/node_modules',dirs_exist_ok=True)
(root/'frontend-github/dist/assets').mkdir(parents=True,exist_ok=True)
print('V1.2.A1 prepared.')
