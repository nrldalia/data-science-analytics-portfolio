from pathlib import Path
import shutil, json
base=Path('outputs/V1.2.A1'); root=Path('outputs/V1.3.0')
shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist','.venv'),dirs_exist_ok=True)
for rel in ['script/app.py','frontend-github/src/app.jsx','Setup_Windows.bat']:
 p=root/rel; p.write_text(p.read_text(encoding='utf-8-sig').replace('V1.2.A1','V1.3.0').replace("version='1.2.A1'","version='1.3.0'"),encoding='utf-8')
p=root/'Start_V1.2.A1.bat'; (root/'Start_V1.3.0.bat').write_text(p.read_text().replace('V1.2.A1','V1.3.0')); p.unlink()
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name; d=json.loads(p.read_text()); d['version']='1.3.0'
 if '' in d.get('packages',{}): d['packages']['']['version']='1.3.0'
 p.write_text(json.dumps(d,indent=2))
print('V1.3.0 prepared')
