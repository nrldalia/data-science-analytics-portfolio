from pathlib import Path
import os,json
root=Path(__file__).resolve().parent.parent;release=root/'outputs/V1.8.0'
notes='''# V1.8.0 — Independent New Store review

Enhances V1.7.0. Data Streams now has a compact Review New Stores action and an audit link opening a dedicated review page. Flagged stores show read-only received IDs, editable Store Name, Store Address, Active/Inactive status and exception Yes/No. Select one or multiple pending stores and choose Approve New Stores. Only selected details are saved; unselected stores remain pending. Back navigation confirms discarding unsaved edits.

Approve Job and Approve New Stores are independent. Approve Job changes only the job approval state and its audit entry. New Store approval adds reviewed stores without changing job status; it is available for completed, interrupted or approved jobs. Cancelled jobs cannot add stores. Store approval records a configuration version, review decision/time/generated code and a distinct action audit. The configuration originally pinned to the job remains unchanged.

Approval validates that each distinct selected ID was actually flagged by that run, validates store details, and atomically saves approved stores, global MY6 allocations, configuration history, review metadata and audit. Already-reviewed selections are rejected. Stores registered by another run are not duplicated or overwritten and are marked Already registered. Invalid selection/details leave all stores, codes and versions unchanged. Existing stores added by earlier job-approval releases are recognized rather than added again.

Use the same outputs/V1.3.A1.bat launcher. Close the old server window and reopen it for V1.8.0 at http://127.0.0.1:5001/.

Local data is backed up consistently. Databases, uploads, personal configuration, dependencies and build output are excluded from GitHub.
'''
for name in ['README.md','CHANGELOG_V1.8.0.md']:(release/name).write_text(notes,encoding='utf-8')
(release/'VALIDATION.md').write_text('Production Vite build and backend tests passed. New Store review checks cover partial approvals and metadata, independent job/store approval states, sequential storecodes, pinned run snapshots, configuration versions, action audits, repeat approval rejection, atomic invalid selection/details, cross-run duplicate/overwrite prevention and cancellation guards. Interactive browser verification was not performed.\n',encoding='utf-8')
entries=[]
for current,dirs,files in os.walk(release):
 dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','dist','.venv','.git','sample_data'}]
 for name in files:
  p=Path(current)/name
  if name=='app-config.json' or name.startswith(('LOCAL_','.timestamp-')):continue
  if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
  entries.append(dict(path='versions/V1.8.0/'+p.relative_to(release).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
entries.extend([dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=(root/'outputs/V1.3.A1.bat').read_text(encoding='utf-8-sig')),dict(path='README.md',mode='100644',type='blob',content=notes)])
(root/'work/store_review_manifest.json').write_text(json.dumps(entries,ensure_ascii=False),encoding='utf-8')
print(f'Prepared {len(entries)} source files')
