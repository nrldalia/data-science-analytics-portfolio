from pathlib import Path
import os,json
root=Path('outputs/V1.4.0')
(root/'VALIDATION.md').write_text('''# V1.4.0 validation

Production React/Vite/Tailwind build passed. All 37 backend tests passed. Batch audit assertions verify 909 on successful rule execution and 908/909 on a failed attempt followed by recovery. Existing rule conditions, description persistence, exact sequence, batch retry, cancellation and replacement tests remain passing.

Live browser interaction of the new popup workflow remains unverified. The session-started localhost server was not reachable from the in-app browser during prior verification. Close the prior server window and launch the updated single V1.3.A1.bat directly in Windows to review V1.4.0.
''',encoding='utf-8')
entries=[]
for folder,dirs,files in os.walk(root):
 dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','dist','.venv','.git','sample_data'}]
 for name in files:
  p=Path(folder)/name
  if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
  if name=='app-config.json' or name.startswith('LOCAL_') or '.timestamp-' in name:continue
  entries.append(dict(path='versions/V1.4.0/'+p.relative_to(root).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
entries.append(dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=Path('outputs/V1.3.A1.bat').read_text()))
entries.append(dict(path='README.md',mode='100644',type='blob',content='''# DataFlow version history

Latest enhancement: [V1.4.0 — Component rule popups](versions/V1.4.0/README.md).

Use the single [V1.3.A1.bat launcher](versions/V1.3.A1/V1.3.A1.bat), updated to open V1.4.0. Keep the version folders beside one another.

- V1.1.0: cleaning logs and exports.
- V1.2.0: retailer setup and ordered rules.
- V1.2.A1: batch audits, retries and replacements.
- V1.3.0: ordered rules table and conditions.
- V1.3.A1: single localhost launcher.
- V1.3.A2: compact Data Streams action icons.
- [V1.4.0](versions/V1.4.0/CHANGELOG_V1.4.0.md): component buttons and description popups, 909/908 execution messages, one row per individual rule and separate description/condition editing.

Source snapshots exclude databases, uploads, credentials and installed dependencies.
'''))
Path('work/v140_manifest.json').write_text(json.dumps(entries),encoding='utf-8')
print(len(entries),'source entries prepared')
