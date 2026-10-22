from pathlib import Path
import os,json
root=Path(__file__).resolve().parent.parent;release=root/'outputs/V1.9.A1'
notes='''# V1.9.A1 — Clearer failure details

Amends V1.9.0. Data Streams shows each failed rule's name, category, sequence, failed attempt count, error code and reason directly in the job log. Data findings include affected-value counts and the configured field, without exposing source or cleaned values. Retries that recover show the successful attempt separately from the failed attempt count.

Timeout, operator cancellation, restart and internal-error explanations are recorded separately, with the current rule/attempt context when available. Cancelled jobs retain empty End Time and Audit Logs. Their failure summaries remain available in the log and status API. Historical runs without recorded summaries are labelled as unavailable; no details are invented.

Use the existing outputs/V1.3.A1.bat launcher. Close the old server window and reopen it to load V1.9.A1 at http://127.0.0.1:5001/.

Local database copied through SQLite backup. Databases, uploads, personal configuration, dependencies and generated build files are excluded from GitHub.
'''
for name in ['README.md','CHANGELOG_V1.9.A1.md']:(release/name).write_text(notes,encoding='utf-8')
(release/'VALIDATION.md').write_text('Production build and 91 backend tests passed. Added tests verify three-attempt rule failure details in log/status responses, cancelled audit restrictions, count-only numeric failure explanations, recovered retries versus operator cancellation, and timeout context. Interactive browser verification was not performed.\n',encoding='utf-8')
entries=[]
for current,dirs,files in os.walk(release):
 dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','dist','.venv','.git','sample_data'}]
 for name in files:
  p=Path(current)/name
  if name=='app-config.json' or name.startswith(('LOCAL_','.timestamp-')):continue
  if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
  entries.append(dict(path='versions/V1.9.A1/'+p.relative_to(release).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
entries.extend([dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=(root/'outputs/V1.3.A1.bat').read_text(encoding='utf-8-sig')),dict(path='README.md',mode='100644',type='blob',content=notes)])
(root/'work/failures_manifest.json').write_text(json.dumps(entries,ensure_ascii=False),encoding='utf-8')
print(f'Prepared {len(entries)} source files')
