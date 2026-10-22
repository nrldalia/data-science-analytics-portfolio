import json, os
from pathlib import Path
root=Path(__file__).resolve().parent.parent
release=root/'outputs/V1.5.0'
notes='''# V1.5.0 — Batch audit receipt metrics

Enhances V1.4.A3 with persisted batch audit metrics: Rows Received, Rows Count (after data cleaning), unique Stores Received, Store Table + New Stores total, New Stores and Missing Stores lists, File Size in bytes, and Deviated File Size in signed bytes/percentage with Increase, Decrease or Unchanged.

Received rows/stores describe parsed input. The cleaning count is the row count after the last successful Cleaning rule; without Cleaning rules it equals received rows. Store comparison snapshots the retailer store table at job start. IDs are compared without surrounding whitespace or case differences. Duplicate received IDs count once. Missing Stores means active registered stores absent from input; known inactive stores are not new. Store Table + New Stores counts all registered unique IDs plus new received IDs. Blank received IDs are counted separately.

Store IDs are detected from common Store ID / Retailer Store ID / Store Code / Store Key headers; ambiguous or absent columns produce Unavailable rather than invented counts. The batch upload form supports an optional exact field override. Store names are taken from a Store Name field where available, otherwise the ID is used.

New stores are flagged for review and added only when the user approves the job, with globally sequential MY6 codes. Store additions and job approval are atomic. Existing and missing stores are retained. Invalid new store IDs/names must be resolved in Store Table Management before approval. Reprocessing cancellation preserves the previous job metrics and does not add stores.

File-size comparison uses the same retailer's completed job from exactly the preceding ISO week, including ISO year boundaries. Source byte sizes are used. Missing/cancelled baselines produce Unavailable; a zero baseline yields no percentage. Comparison values are saved with the batch so later changes do not rewrite its audit. Previous jobs without metric snapshots display Unavailable. Schema migration preserves existing jobs and data.

Use the existing outputs/V1.3.A1.bat launcher. Close the old server window and reopen it for V1.5.0 at http://127.0.0.1:5001/.

Databases, uploaded data, personal configuration, installed dependencies and build output are excluded from GitHub.
'''
for name in ['README.md','CHANGELOG_V1.5.0.md']:(release/name).write_text(notes,encoding='utf-8')
(release/'VALIDATION.md').write_text('''# Validation

Production Vite build passed. Regression and metric tests cover week/year boundaries, byte/percentage deviation, unavailable and zero baselines, duplicate/blank Store IDs, active missing stores and inactive known stores, metric persistence, adding new stores only on approval with MY6 codes, repeat-approval protection and cancelled-replacement preservation.

Interactive browser verification was not performed in this session.
''',encoding='utf-8')
entries=[]
for current,dirs,files in os.walk(release):
 dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','dist','.venv','.git','sample_data'}]
 for name in files:
  p=Path(current)/name
  if name=='app-config.json' or name.startswith(('LOCAL_','.timestamp-')):continue
  if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
  entries.append(dict(path='versions/V1.5.0/'+p.relative_to(release).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
entries.extend([dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=(root/'outputs/V1.3.A1.bat').read_text(encoding='utf-8-sig')),dict(path='README.md',mode='100644',type='blob',content=notes)])
(root/'work/audit_metrics_manifest.json').write_text(json.dumps(entries,ensure_ascii=False),encoding='utf-8')
print(f'Prepared {len(entries)} source files')
