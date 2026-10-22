from pathlib import Path
import shutil, sqlite3, json
base=Path('outputs/V1.4.A3'); root=Path('outputs/V1.5.0')
shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist','.venv','*.db','*.db-wal','*.db-shm'),dirs_exist_ok=True)
for rel in ['script/app.py','frontend-github/src/app.jsx','Setup_Windows.bat','Start_V1.4.A3.bat']:
 p=root/rel;s=p.read_text(encoding='utf-8').replace('V1.4.A3','V1.5.0').replace("version='1.4.A3'","version='1.5.0'")
 if rel.startswith('Start_'):p.unlink();p=root/'Start_V1.5.0.bat'
 p.write_text(s,encoding='utf-8')
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name;d=json.loads(p.read_text());d['version']='1.5.0'
 if '' in d.get('packages',{}):d['packages']['']['version']='1.5.0'
 p.write_text(json.dumps(d,indent=2))
p=Path('outputs/V1.3.A1.bat');p.write_text(p.read_text().replace('V1.4.A3','V1.5.0').replace("'1.4.A3'","'1.5.0'"))
if (base/'script/dataflow.db').exists():
 with sqlite3.connect(base/'script/dataflow.db') as a,sqlite3.connect(root/'script/dataflow.db') as b:a.backup(b)
print('V1.5.0 prepared')
