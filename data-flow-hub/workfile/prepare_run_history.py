from pathlib import Path
import shutil,sqlite3,json
base=Path('outputs/V1.5.A1');root=Path('outputs/V1.6.0')
shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist','.venv','*.db','*.db-wal','*.db-shm'),dirs_exist_ok=True)
for rel in ['script/app.py','frontend-github/src/app.jsx','Setup_Windows.bat','Start_V1.5.A1.bat']:
 p=root/rel;s=p.read_text(encoding='utf-8').replace('V1.5.A1','V1.6.0').replace("version='1.5.A1'","version='1.6.0'")
 if rel.startswith('Start_'):p.unlink();p=root/'Start_V1.6.0.bat'
 p.write_text(s,encoding='utf-8')
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name;d=json.loads(p.read_text());d['version']='1.6.0'
 if '' in d.get('packages',{}):d['packages']['']['version']='1.6.0'
 p.write_text(json.dumps(d,indent=2),encoding='utf-8')
p=Path('outputs/V1.3.A1.bat');p.write_text(p.read_text().replace('V1.5.A1','V1.6.0').replace("'1.5.A1'","'1.6.0'"),encoding='utf-8')
if (base/'script/dataflow.db').exists():
 with sqlite3.connect(base/'script/dataflow.db') as a,sqlite3.connect(root/'script/dataflow.db') as b:a.backup(b)
p=root/'script/batch_jobs.py';s=p.read_text(encoding='utf-8')
s=s.replace('from batch_metrics import','from batch_history import migrate_run_history\nfrom batch_metrics import',1)
s=s.replace("    def finalize(aid, status, output=None, audit=None, codes=None):", "    with get_db_connection() as db:migrate_run_history(db)\n\n    def finalize(aid, status, output=None, audit=None, codes=None):")
start=s.index("            previous=db.execute('SELECT * FROM batch_jobs")
end=s.index("            db.execute('DELETE FROM batch_attempts",start)
s=s[:start]+"""            db.execute('INSERT INTO batch_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (aid,attempt['retailer_id'],attempt['retailer_name'],attempt['period'],attempt['start_time'],ended,status,
                 attempt['filename'],attempt['source'],attempt['pipeline'],None if cancelled else json.dumps(output),
                 None if cancelled else json.dumps(audit or []),json.dumps(codes or []),None,attempt['metrics']))
"""+s[end:]
s=s.replace("AND status!='Cancelled Job'\"", "AND status!='Cancelled Job' ORDER BY end_time DESC, start_time DESC, rowid DESC LIMIT 1\"")
s=s.replace('ORDER BY start_time DESC\'','ORDER BY start_time DESC, rowid DESC\'')
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/BatchLogs.jsx';s=p.read_text(encoding='utf-8')
s=s.replace('One recorded job per retailer and ISO week.','Every run has its own log row, including repeated retailer/week runs.')
s=s.replace('New Batch Job / Replacement','New Batch Job')
s=s.replace('A successful replacement deletes the previous job and its process logs.','Each run keeps its own job and process logs, including failed runs.')
s=s.replace('A previous job is kept if this is a replacement attempt.','Other runs and their audits are retained.')
s=s.replace('The previous job remains until this attempt succeeds.','This run creates a new log row; previous runs remain.')
s=s.replace('The original week is retained. An existing job in the selected week remains until this attempt succeeds.','The original run and all existing runs are retained.')
s=s.replace('A successful job replaces any existing job for the same retailer and chosen week.','Every run creates its own log row, even for the same retailer and week.')
s=s.replace('Replacement processing','Run processing')
s=s.replace("['Retailer Name','Period','Start Time'", "['Retailer Name','Period','Start Time'")
s=s.replace("{job.filename}</div>","{job.filename}</div><div className=\"font-mono text-slate-500 mt-1\">{job.id}</div>")
p.write_text(s,encoding='utf-8')
print('V1.6.0 prepared')
