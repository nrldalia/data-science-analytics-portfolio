from pathlib import Path
import os,json
root=Path(__file__).resolve().parent.parent;release=root/'outputs/V1.5.A1'
notes='''# V1.5.A1 — Editable ISO week

Replaces the browser-dependent week input with an editable YYYY-Www text field when starting a batch. The current Malaysia ISO week remains the default. Input accepts any valid ISO week, with backend checks for actual calendar week existence.

The Reprocess icon now opens a popup with the original period prefilled and an editable ISO week. The chosen week drives retailer/week uniqueness and the previous-week file-size baseline. Reprocessing in the same week preserves the existing successful-replacement behavior. Choosing another week keeps the original job/audit and creates or replaces the target-week job only upon success. A cancelled attempt preserves any previous target-week job. Concurrent jobs in the same retailer/week are rejected. Existing API clients that omit the period retain same-week reprocessing.

Use the existing outputs/V1.3.A1.bat launcher. Close the old server window and reopen it to load V1.5.A1 at http://127.0.0.1:5001/.

Local data is copied using SQLite backup. Databases, uploads, personal configuration, dependencies and build output are excluded from GitHub.
'''
for name in ['README.md','CHANGELOG_V1.5.A1.md']:(release/name).write_text(notes,encoding='utf-8')
(release/'VALIDATION.md').write_text('Production Vite build and backend tests passed. ISO-week tests cover cross-week reprocessing and baseline recalculation, default same-week replacement, invalid weeks/request shapes, concurrent target-week rejection and cancelled replacement preservation. Interactive browser verification was not performed.\n',encoding='utf-8')
entries=[]
for current,dirs,files in os.walk(release):
 dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','dist','.venv','.git','sample_data'}]
 for name in files:
  p=Path(current)/name
  if name=='app-config.json' or name.startswith(('LOCAL_','.timestamp-')):continue
  if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
  entries.append(dict(path='versions/V1.5.A1/'+p.relative_to(release).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
entries.extend([dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=(root/'outputs/V1.3.A1.bat').read_text(encoding='utf-8-sig')),dict(path='README.md',mode='100644',type='blob',content=notes)])
(root/'work/iso_week_manifest.json').write_text(json.dumps(entries,ensure_ascii=False),encoding='utf-8')
print(f'Prepared {len(entries)} source files')
