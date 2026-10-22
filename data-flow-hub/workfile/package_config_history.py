from pathlib import Path
import os,json
root=Path(__file__).resolve().parent.parent;release=root/'outputs/V1.7.0'
notes='''# V1.7.0 — Retailer configuration history and batch provenance

Enhances V1.6.A1. Save Configuration records a numbered, timestamped complete retailer snapshot, including retailer details, stores, exact rule order, descriptions, operation settings and conditions. Snapshots carry a stable identity and SHA-256 of canonical content. Unchanged saves reuse the latest version; failed saves do not create versions. Configuration update and version creation share a transaction. New-store approval also versions its setup change.

Configuration History in Client / Setup opens read-only versions with ordered rules and saved stores. Viewing history never replaces current configuration. No restore action is introduced.

Each new batch captures the exact configuration version at launch within the same transaction as its input/pipeline snapshot. Data Streams displays a Configuration vN link for successful, failed and cancelled runs. The audit shows the version number, and the link opens the full captured snapshot. Reprocessing uses the latest saved configuration and captures its version. Later setup changes or store approval cannot change an older run's snapshot. Versions remain available for retained batch audits after retailer deletion.

Existing retailer setups receive a baseline on first startup. Earlier setup edits cannot be reconstructed. Old batches without recorded provenance are labeled Configuration version not captured; their current setup is not claimed as the one used historically. Uploaded sample contents are not part of configuration snapshots.

Use the same outputs/V1.3.A1.bat launcher. Close the old server window and reopen it for V1.7.0 at http://127.0.0.1:5001/.

Local data is copied using SQLite backup. Databases, samples, personal configuration, installed dependencies and build output are excluded from GitHub.
'''
for name in ['README.md','CHANGELOG_V1.7.0.md']:(release/name).write_text(notes,encoding='utf-8')
(release/'VALIDATION.md').write_text('Production Vite build and backend tests passed. History tests cover version creation, unchanged saves, immutable older descriptions, failed-save atomicity, batch snapshot pinning despite later changes, reprocessing latest version, history retention after retailer deletion, store-approval versioning and honest legacy provenance. Interactive browser verification was not performed.\n',encoding='utf-8')
entries=[]
for current,dirs,files in os.walk(release):
 dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','dist','.venv','.git','sample_data'}]
 for name in files:
  p=Path(current)/name
  if name=='app-config.json' or name.startswith(('LOCAL_','.timestamp-')):continue
  if p.suffix not in {'.py','.sql','.txt','.jsx','.js','.css','.html','.json','.md','.bat'} and name not in {'.gitignore','LICENSE'}:continue
  entries.append(dict(path='versions/V1.7.0/'+p.relative_to(release).as_posix(),mode='100644',type='blob',content=p.read_text(encoding='utf-8-sig')))
entries.extend([dict(path='versions/V1.3.A1/V1.3.A1.bat',mode='100644',type='blob',content=(root/'outputs/V1.3.A1.bat').read_text(encoding='utf-8-sig')),dict(path='README.md',mode='100644',type='blob',content=notes)])
(root/'work/config_history_manifest.json').write_text(json.dumps(entries,ensure_ascii=False),encoding='utf-8')
print(f'Prepared {len(entries)} source files')
