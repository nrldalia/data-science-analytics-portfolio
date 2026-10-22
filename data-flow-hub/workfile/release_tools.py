from pathlib import Path
import shutil,sqlite3,json,os
ROOT=Path(__file__).resolve().parent.parent
def clone(old,new,npm):
 base=ROOT/'outputs'/old;root=ROOT/'outputs'/new
 shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist','.venv','*.db','*.db-wal','*.db-shm'),dirs_exist_ok=True)
 for rel in ['script/app.py','frontend-github/src/app.jsx','Setup_Windows.bat',f'Start_{old}.bat']:
  p=root/rel;s=p.read_text(encoding='utf-8').replace(old,new).replace("version='"+old[1:]+"'","version='"+new[1:]+"'")
  if rel.startswith('Start_'):p.unlink();p=root/f'Start_{new}.bat'
  p.write_text(s,encoding='utf-8')
 for name in ['package.json','package-lock.json']:
  p=root/'frontend-github'/name;d=json.loads(p.read_text());d['version']=npm
  if '' in d.get('packages',{}):d['packages']['']['version']=npm
  p.write_text(json.dumps(d,indent=2),encoding='utf-8')
 if (base/'script/dataflow.db').exists():
  with sqlite3.connect(base/'script/dataflow.db') as a,sqlite3.connect(root/'script/dataflow.db') as b:a.backup(b)
 return root
def package(version,notes,validation,launcher=False):
 release=ROOT/'outputs'/version
 for name in ['README.md',f'CHANGELOG_{version}.md']:(release/name).write_text(notes,encoding='utf-8')
 (release/'VALIDATION.md').write_text(validation,encoding='utf-8')
 entries=[]
 for current,dirs,files in os.walk(release):
  dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','dist','.venv','.git','sample_data'}]
  for name in files:
   p=Path(current)/name
   if name=='app-config.json' or name.startswith(('LOCAL_','.timestamp-')):continue
   if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
   entries.append(dict(path=f'versions/{version}/'+p.relative_to(release).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
 entries.append(dict(path='README.md',mode='100644',type='blob',content=notes))
 if launcher:entries.append(dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=(ROOT/'outputs/V1.3.A1.bat').read_text(encoding='utf-8-sig')))
 (ROOT/'work'/f'{version}_manifest.json').write_text(json.dumps(entries,ensure_ascii=False),encoding='utf-8')
 print(f'{version}: {len(entries)} source files')
