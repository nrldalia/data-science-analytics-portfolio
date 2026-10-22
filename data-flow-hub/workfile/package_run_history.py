from pathlib import Path
import os,json
root=Path(__file__).resolve().parent.parent;release=root/'outputs/V1.6.0'
notes='''# V1.6.0 — Separate batch log for every run

Enhances V1.5.A1. Every accepted run has a distinct Run ID and log row, including successful, interrupted, failed and user-cancelled runs for the same retailer/week. Successful runs no longer delete earlier jobs, sources, outputs or audits. Failed reprocessing creates its own Cancelled Job row with diagnostic codes rather than attaching a lastAttempt to the previous job. After three rule failures the row includes the operation error and RULE_RETRY_LIMIT. Cancelled jobs retain empty end time and audit, as requested earlier.

Both historical jobs and active attempts permit repeated retailer/week runs. Finalization is transactional and cancellation cannot later become completion. Store approval still adds only unknown stores with globally sequential MY6 codes. File-size deviation snapshots the latest successful/approved run from exactly the previous ISO week, selected by completion/start time and stable row order. Failed runs are excluded from that baseline.

Schema migration removes retailer/week uniqueness while retaining existing data. The most recent nested cancellation metadata retained by earlier releases is recovered as its own row. Its original file content and metrics were not retained and cannot be reconstructed; reprocessing that recovered row asks the user to upload the file. Earlier runs already deleted by the old overwrite behavior cannot be recovered.

The UI identifies runs by Run ID and updates batch/reprocess text to describe retained history. All ISO-week editing and audit receipt metrics remain available.

Use the same outputs/V1.3.A1.bat launcher. Close the old server window and reopen it for V1.6.0 at http://127.0.0.1:5001/.

Local databases are backed up consistently. Databases, uploads, personal configuration, installed dependencies and build output are excluded from GitHub.
'''
for name in ['README.md','CHANGELOG_V1.6.0.md']:(release/name).write_text(notes,encoding='utf-8')
(release/'VALIDATION.md').write_text('Production Vite build and backend tests passed. Tests cover repeated successful runs with preserved source/audit, visible failed/cancelled rows and error codes, concurrent same-week runs, cancel races, ISO-week changes, store metrics and approval, plus transactional/idempotent history schema migration and recovery of retained cancellation metadata. Interactive browser verification was not performed.\n',encoding='utf-8')
entries=[]
for current,dirs,files in os.walk(release):
 dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','dist','.venv','.git','sample_data'}]
 for name in files:
  p=Path(current)/name
  if name=='app-config.json' or name.startswith(('LOCAL_','.timestamp-')):continue
  if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
  entries.append(dict(path='versions/V1.6.0/'+p.relative_to(release).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
entries.extend([dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=(root/'outputs/V1.3.A1.bat').read_text(encoding='utf-8-sig')),dict(path='README.md',mode='100644',type='blob',content=notes)])
(root/'work/run_history_manifest.json').write_text(json.dumps(entries,ensure_ascii=False),encoding='utf-8')
print(f'Prepared {len(entries)} source files')
