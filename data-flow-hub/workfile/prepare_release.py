import json
from pathlib import Path

root=Path('outputs/V1.2.0')
for name in ['Start_V1.1.0.bat','LOCAL_V1.1.0.md']:
    p=root/name
    if p.exists():p.unlink()
(root/'README.md').write_text((root/'README_V1.2.0.md').read_text(encoding='utf-8'),encoding='utf-8')
p=root/'Setup_Windows.bat';s=p.read_text().replace('Run Start_DataFlow.bat next.','Run Start_V1.2.0.bat next.');p.write_text(s)
p=root/'frontend-github/package-lock.json'
if p.exists():
    lock=json.loads(p.read_text());lock['version']='1.2.0'
    if '' in lock.get('packages',{}):lock['packages']['']['version']='1.2.0'
    p.write_text(json.dumps(lock,indent=2))
(root/'VALIDATION.md').write_text('''# V1.2.0 validation

Production frontend build passed (React, Vite and Tailwind).

17 backend tests cover preserved cleaning, saved history, original evidence, CSV/Excel processing and exports, dormant AI, retailer persistence, mandatory sender email, optional recipient email, retailer/store key uniqueness, reusable rule definitions, strict sample-size limits, sequence-dependent processing and validation, rename handling, invalid-value retention, 25-row previews and full sample CSV export.

Interactive browser testing is unavailable in this session: the browser automation service timed out. Use Start_V1.2.0.bat directly in Windows to view the application. The earlier sandbox-hosted localhost server was unreachable from the browser.
''',encoding='utf-8')

# Publish source snapshots only. Never include local databases, uploaded files or runtimes.
allowed_suffix={'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat','.csv'}
excluded={'node_modules','__pycache__','.git','.venv','dist'}
def snapshot(directory,version):
    elements=[]
    for f in directory.rglob('*'):
        relative=f.relative_to(directory)
        if any(part in excluded for part in relative.parts):continue
        if not f.is_file() or (f.suffix not in allowed_suffix and f.name not in {'.gitignore','LICENSE'}):continue
        if f.name.startswith('LOCAL_') or f.name in {'app-config.json','Start_V1.1.0.bat'}:continue
        elements.append({'path':f'versions/{version}/{relative.as_posix()}','mode':'100644','type':'blob','content':f.read_text(encoding='utf-8-sig')})
    return elements
manifest={'V1.1.0':snapshot(Path('outputs/DataFlow_V1.1.0'),'V1.1.0'),'V1.2.0':snapshot(root,'V1.2.0')}
Path('work/release_manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
print({version:len(files) for version,files in manifest.items()})
