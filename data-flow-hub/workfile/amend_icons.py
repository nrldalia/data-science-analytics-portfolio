from pathlib import Path
import shutil,json,sqlite3
base=Path('outputs/V1.3.0');root=Path('outputs/V1.3.A2')
shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','.venv','dist','*.db','*.db-wal','*.db-shm'),dirs_exist_ok=True)
p=root/'frontend-github/src/BatchLogs.jsx';s=p.read_text(encoding='utf-8')
s=s.replace('{Pencil,Plus,RefreshCw,X}', '{Pencil,Plus,RefreshCw,X,Check,LoaderCircle}')
s=s.replace("const input=", "const iconButton=button+' h-8 w-8 p-0 shrink-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400';\nconst input=")
s=s.replace("className={button+' text-rose-300'} onClick={()=>action(a.id,'cancel')}>Cancel Job</button>", "className={iconButton+' text-rose-300'} aria-label=\"Cancel Job\" title=\"Cancel Job\" onClick={()=>action(a.id,'cancel')}><X size={16} aria-hidden=\"true\"/></button>")
s=s.replace('className="p-3 min-w-48"><div className="flex flex-wrap gap-2">', 'className="p-3"><div className="flex items-center gap-2 whitespace-nowrap">')
s=s.replace("className={button} onClick={()=>action(job.id,'reprocess')}>Reprocess</button>", "className={iconButton+' text-cyan-300'} aria-label=\"Reprocess\" title=\"Reprocess\" onClick={()=>action(job.id,'reprocess')}><RefreshCw size={16} aria-hidden=\"true\"/></button>")
s=s.replace("className={button} onClick={()=>action(job.id,'approve')}>Approve Job</button>", "className={iconButton+' text-emerald-300'} aria-label=\"Approve Job\" title=\"Approve Job\" onClick={()=>action(job.id,'approve')}><Check size={16} aria-hidden=\"true\"/></button>")
s=s.replace("className={button+' text-rose-300'} onClick={()=>action(job.id,'cancel')}>Cancel Job</button>", "className={iconButton+' text-rose-300'} aria-label=\"Cancel Job\" title=\"Cancel Job\" onClick={()=>action(job.id,'cancel')}><X size={16} aria-hidden=\"true\"/></button>")
s=s.replace('<span className="text-cyan-300">Replacement processing…</span>', '<span role="status" aria-label="Replacement processing" title="Replacement processing" className="inline-flex h-8 w-8 items-center justify-center text-cyan-300"><LoaderCircle size={16} className="animate-spin motion-reduce:animate-none" aria-hidden="true"/><span className="sr-only">Replacement processing</span></span>')
s=s.replace('className={button} onClick={()=>showAudit(job.id)}><Pencil size={15}/>', 'title="Open audit logs" className={iconButton} onClick={()=>showAudit(job.id)}><Pencil size={15} aria-hidden="true"/>')
p.write_text(s,encoding='utf-8')
for rel in ['frontend-github/src/app.jsx','script/app.py','Setup_Windows.bat']:
 p=root/rel;s=p.read_text(encoding='utf-8').replace('V1.3.0','V1.3.A2').replace("version='1.3.0'","version='1.3.A2'");p.write_text(s,encoding='utf-8')
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name;d=json.loads(p.read_text());d['version']='1.3.2'
 if '' in d.get('packages',{}): d['packages']['']['version']='1.3.2'
 p.write_text(json.dumps(d,indent=2))
p=root/'Start_V1.3.0.bat';(root/'Start_V1.3.A2.bat').write_text(p.read_text().replace('V1.3.0','V1.3.A2'));p.unlink()
# Keep the one entry-point filename the user already uses.
p=Path('outputs/V1.3.A1.bat');p.write_text(p.read_text().replace('V1.3.0','V1.3.A2').replace("'1.3.0'","'1.3.A2'"))
db=base/'script/dataflow.db'
if db.exists():
 with sqlite3.connect(db) as source,sqlite3.connect(root/'script/dataflow.db') as target: source.backup(target)
(root/'CHANGELOG_V1.3.A2.md').write_text('''# V1.3.A2 — Compact Data Streams actions

Replaces Reprocess, Approve Job and Cancel Job text buttons with refresh, check and X icons in compact 32-pixel square controls. Applies the same cancel icon to active jobs. Adds title tooltips, accessible button names and keyboard focus outlines. Pending replacement work uses a spinner with an accessible status. Aligns the audit pencil with the same square control style.

Retains status-based action availability, busy states, existing handlers and the cancellation confirmation. The existing single V1.3.A1.bat entry point now launches V1.3.A2. Local data is preserved through SQLite backup and excluded from GitHub.
''',encoding='utf-8')
(root/'README.md').write_text('''# DataFlow V1.3.A2

Use the existing single V1.3.A1.bat launcher, updated to start this amendment at http://127.0.0.1:5001/. Close the previous server window before launching the new version. Keep the application folder beside the launcher.

Data Streams actions: circular arrow = Reprocess; check = Approve Job; X = Cancel Job. Hover to see a tooltip. The pencil opens Audit Logs. A spinner indicates replacement work is processing. Status and availability rules are unchanged.

For a fresh GitHub checkout, run Setup_Windows.bat and then Start_V1.3.A2.bat. Rules Configure enhancements from V1.3.0 remain included.
''',encoding='utf-8')
print('V1.3.A2 prepared; single launcher updated')
