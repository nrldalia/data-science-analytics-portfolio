from pathlib import Path
import os,json
root=Path('outputs/V1.4.A1')
(root/'VALIDATION.md').write_text('''# V1.4.A1 validation

Production React/Vite/Tailwind build passed. All 43 backend tests passed across store management, rule configuration, retailer setup, batch jobs and existing app endpoints. Six new store tests cover generated/persistent codes, code stability across Store ID and shared Retailer Key changes, distinct codes, invalid values/identities, atomic duplicate-key rejection and legacy-store migration on save.

Live browser interaction of the new store page remains unverified. Close the previous server window and run the updated single V1.3.A1.bat directly in Windows to review V1.4.A1.
''',encoding='utf-8')
entries=[]
for folder,dirs,files in os.walk(root):
 dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','dist','.venv','.git','sample_data'}]
 for name in files:
  p=Path(folder)/name
  if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
  if name=='app-config.json' or name.startswith('LOCAL_') or '.timestamp-' in name:continue
  entries.append(dict(path='versions/V1.4.A1/'+p.relative_to(root).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
entries.append(dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=Path('outputs/V1.3.A1.bat').read_text()))
entries.append(dict(path='README.md',mode='100644',type='blob',content='''# DataFlow version history

Latest amendment: [V1.4.A1 — Store Table Management](versions/V1.4.A1/README.md).

Use the single [V1.3.A1.bat launcher](versions/V1.3.A1/V1.3.A1.bat), updated to open V1.4.A1. Keep version folders beside one another.

- V1.1.0: cleaning logs and exports.
- V1.2.0: retailer setup and ordered rules.
- V1.2.A1: batch audits, retries and replacements.
- V1.3.0: ordered rules table and conditions.
- V1.3.A1: single localhost launcher.
- V1.3.A2: compact Data Streams action icons.
- V1.4.0: component rule popups and execution codes.
- [V1.4.A1](versions/V1.4.A1/CHANGELOG_V1.4.A1.md): store status table, separate edit page, shared retailer-key editing, exception/address fields and immutable generated SUITE storecodes.

Source snapshots exclude databases, uploads, credentials and installed dependencies.
'''))
Path('work/stores_manifest.json').write_text(json.dumps(entries),encoding='utf-8')
print(len(entries),'source entries prepared')
