from pathlib import Path
import os,json
root=Path(__file__).resolve().parent.parent;release=root/'outputs/V1.6.A1'
notes='''# V1.6.A1 — Client list and nested retailer Setup

Amends V1.6.0. Client is the first sidebar module and initial page. Replaces the placeholder Clients dashboard with a saved-retailer table containing an unlabeled checkbox column, Retailer Name, Setup Status and Edit. Removes the separate Retailer Data Setup sidebar entry. Edit opens the existing complete setup within Client, including retailer/store details, Rules Configure, sample upload and previews. Back to Client returns to a refreshed list. Add Retailer opens a new setup. Unsaved setup changes require discard confirmation when returning.

Setup Status is Ready when saved details, at least one store and executable rules in Cleaning, Transformation and Validation exist; otherwise Setup incomplete. A configuration containing an unimplemented rule reference displays Reference only. These are setup completeness indicators, not claims of successful batch execution.

Supports individual selection, select all with a mixed-selection state, and Delete with selected count. Deletion confirms the selected retailer count and removes configurations and samples in one transaction. Missing selections or a selected retailer with an active batch reject the entire operation. Recorded batch jobs and audits remain accessible. Storecode registry and sequence are retained so deleted storecodes are never reused. Reprocessing a deleted retailer requires a new setup and upload.

Use the same outputs/V1.3.A1.bat launcher. Close the old server window and reopen it for V1.6.A1 at http://127.0.0.1:5001/.

Local data is backed up consistently. Databases, uploads, personal configuration, dependencies and build output are excluded from GitHub.
'''
for name in ['README.md','CHANGELOG_V1.6.A1.md']:(release/name).write_text(notes,encoding='utf-8')
(release/'VALIDATION.md').write_text('Production Vite build and backend regression tests passed. Bulk-delete tests cover removal of selected configurations/samples, retained batch audits and storecode registry, rejection of active jobs, and atomic rejection of invalid or missing selections. Interactive browser verification was not performed.\n',encoding='utf-8')
entries=[]
for current,dirs,files in os.walk(release):
 dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','dist','.venv','.git','sample_data'}]
 for name in files:
  p=Path(current)/name
  if name=='app-config.json' or name.startswith(('LOCAL_','.timestamp-')):continue
  if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
  entries.append(dict(path='versions/V1.6.A1/'+p.relative_to(release).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
entries.extend([dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=(root/'outputs/V1.3.A1.bat').read_text(encoding='utf-8-sig')),dict(path='README.md',mode='100644',type='blob',content=notes)])
(root/'work/client_manifest.json').write_text(json.dumps(entries,ensure_ascii=False),encoding='utf-8')
print(f'Prepared {len(entries)} source files')
