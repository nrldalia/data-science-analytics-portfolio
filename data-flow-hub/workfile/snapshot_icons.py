from pathlib import Path
import os,json
root=Path('outputs/V1.3.A2')
(root/'VALIDATION.md').write_text('''# V1.3.A2 validation

Production React/Vite/Tailwind build passed. Action controls retain their original handlers, availability predicates, busy/disabled states and cancel confirmation. Icons include accessible labels and title tooltips, with visible keyboard focus outlines. No backend processing logic changed.

Live browser interaction of this amendment has not been verified. Close the previous server window and use the updated single V1.3.A1.bat launcher for local review.
''',encoding='utf-8')
elements=[]
for folder,dirs,files in os.walk(root):
 dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','.git','.venv','dist','sample_data'}]
 for name in files:
  p=Path(folder)/name
  if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
  if name=='app-config.json' or name.startswith('LOCAL_') or '.timestamp-' in name:continue
  elements.append(dict(path='versions/V1.3.A2/'+p.relative_to(root).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
elements.append(dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=Path('outputs/V1.3.A1.bat').read_text()))
elements.append(dict(path='README.md',mode='100644',type='blob',content='''# DataFlow version history

Latest amendment: [V1.3.A2 — Compact Data Streams actions](versions/V1.3.A2/README.md).

Use the single [V1.3.A1.bat launcher](versions/V1.3.A1/V1.3.A1.bat), updated to launch V1.3.A2. Keep the version folders beside one another.

- V1.1.0: cleaning logs and exports.
- V1.2.0: retailer setup and ordered rules.
- V1.2.A1: batch execution audit, retries and replacements.
- V1.3.0: ordered rules table, descriptions and condition popups.
- V1.3.A1: one-click localhost launcher.
- [V1.3.A2](versions/V1.3.A2/CHANGELOG_V1.3.A2.md): compact action icons with tooltips and accessible labels.

Source snapshots exclude databases, uploads, credentials and installed dependencies.
'''))
Path('work/a2_manifest.json').write_text(json.dumps(elements),encoding='utf-8')
print(len(elements),'source entries prepared')
