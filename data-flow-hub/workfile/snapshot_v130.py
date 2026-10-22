from pathlib import Path
import os,json
root=Path('outputs/V1.3.0')
elements=[]
excluded={'node_modules','__pycache__','.git','.venv','dist','sample_data'}
suffixes={'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'}
for folder,dirs,files in os.walk(root):
 dirs[:]=[d for d in dirs if d not in excluded]
 for name in files:
  p=Path(folder)/name;rel=p.relative_to(root)
  if p.suffix not in suffixes and name not in {'.gitignore','LICENSE'}:continue
  if name=='app-config.json' or name.startswith('LOCAL_') or '.timestamp-' in name:continue
  elements.append({'path':'versions/V1.3.0/'+rel.as_posix(),'mode':'100644','type':'blob','content':p.read_text(encoding='utf-8-sig')})
elements.append({'path':'README.md','mode':'100644','type':'blob','content':'''# DataFlow version history

Latest enhancement: [V1.3.0 — Rules Configure table and conditions](versions/V1.3.0/README.md).

- [V1.1.0](versions/V1.1.0/CHANGELOG_V1.1.0.md): 25-entry cleaning logs and exports.
- [V1.2.0](versions/V1.2.0/CHANGELOG_V1.2.0.md): retailer setup and ordered rules.
- [V1.2.A1](versions/V1.2.A1/CHANGELOG_V1.2.A1.md): batch execution audit, retry and replacement behavior.
- [V1.3.0](versions/V1.3.0/CHANGELOG_V1.3.0.md): single-component rule selection, ordered table, descriptions, prefilled execution messages, Edit and Condition popups, conditional processing and exact cross-component sequence.

Each release starts from the latest enhancement and amendments. Source snapshots exclude databases, uploads, credentials and installed dependencies. Open the latest version folder and follow its README for Windows setup and local execution.
'''})
Path('work/v130_manifest.json').write_text(json.dumps(elements),encoding='utf-8')
print(f'{len(elements)} source entries prepared; no database, upload or dependency directories included.')
