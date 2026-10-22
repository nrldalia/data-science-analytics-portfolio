from pathlib import Path
import shutil,sqlite3,json
base=Path('outputs/V1.5.0');root=Path('outputs/V1.5.A1')
shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist','.venv','*.db','*.db-wal','*.db-shm'),dirs_exist_ok=True)
for rel in ['script/app.py','frontend-github/src/app.jsx','Setup_Windows.bat','Start_V1.5.0.bat']:
 p=root/rel;s=p.read_text(encoding='utf-8').replace('V1.5.0','V1.5.A1').replace("version='1.5.0'","version='1.5.A1'")
 if rel.startswith('Start_'):p.unlink();p=root/'Start_V1.5.A1.bat'
 p.write_text(s,encoding='utf-8')
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name;d=json.loads(p.read_text());d['version']='1.5.1'
 if '' in d.get('packages',{}):d['packages']['']['version']='1.5.1'
 p.write_text(json.dumps(d,indent=2),encoding='utf-8')
p=Path('outputs/V1.3.A1.bat');p.write_text(p.read_text().replace('V1.5.0','V1.5.A1').replace("'1.5.0'","'1.5.A1'"),encoding='utf-8')
if (base/'script/dataflow.db').exists():
 with sqlite3.connect(base/'script/dataflow.db') as a,sqlite3.connect(root/'script/dataflow.db') as b:a.backup(b)
p=root/'script/batch_jobs.py';s=p.read_text(encoding='utf-8')
s=s.replace("        return launch(job['retailer_id'],job['period'],job['filename'],job['source'],decode(job['metrics'],{}).get('storeIdField',''))", "        body=request.get_json(silent=True)\n        if body is None:body={}\n        if not isinstance(body,dict):return error('Invalid reprocessing request.')\n        return launch(job['retailer_id'],body.get('period',job['period']),job['filename'],job['source'],decode(job['metrics'],{}).get('storeIdField',''))")
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/BatchLogs.jsx';s=p.read_text(encoding='utf-8')
s=s.replace("[audit,setAudit]=useState(null)","[audit,setAudit]=useState(null),[reprocessJob,setReprocessJob]=useState(null),[reprocessPeriod,setReprocessPeriod]=useState('')")
s=s.replace('type="week" required className={input} value={period}', 'type="text" placeholder="2026-W41" pattern="[0-9]{4}-W[0-9]{2}" maxLength={8} required className={input} value={period}')
s=s.replace("onChange={e=>setPeriod(e.target.value)}", "onChange={e=>setPeriod(e.target.value.toUpperCase())}")
s=s.replace("onClick={()=>action(job.id,'reprocess')}","onClick={()=>{setReprocessJob(job);setReprocessPeriod(job.period);}}")
marker=' return <div className="space-y-6" data-testid="batch-logs">'
s=s.replace(marker,""" async function submitReprocess(e){e.preventDefault();setBusy(true);setError('');try{await api(`/batches/${reprocessJob.id}/reprocess`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({period:reprocessPeriod})});setNotice(`Reprocessing started for ${reprocessPeriod}. ${reprocessPeriod===reprocessJob.period?'The previous job remains until this attempt succeeds.':'The original week is retained. An existing job in the selected week remains until this attempt succeeds.'}`);setReprocessJob(null);await refresh();}catch(e){setError(e.message);}finally{setBusy(false);}}
"""+marker)
s=s.replace('  {audit&&<div', '''  {reprocessJob&&<div className="fixed inset-0 bg-slate-950/85 z-50 flex items-center justify-center p-5"><form onSubmit={submitReprocess} role="dialog" aria-modal="true" aria-label="Reprocess batch" className="bg-[#1e293b] border border-slate-600 rounded-xl w-full max-w-lg p-5 space-y-4"><h3 className="text-lg font-semibold">Reprocess Batch</h3><p className="text-sm text-slate-400">{reprocessJob.retailer_name} · Original week: {reprocessJob.period}</p><label className="block text-sm space-y-2">Period (ISO Week)<input aria-label="Reprocess ISO week" className={input} type="text" placeholder="2026-W41" pattern="[0-9]{4}-W[0-9]{2}" maxLength={8} required value={reprocessPeriod} onChange={e=>setReprocessPeriod(e.target.value.toUpperCase())}/></label><p className="text-xs text-slate-400">Enter YYYY-Www, for example 2026-W41. The chosen week sets the previous-week file-size comparison. A successful job replaces any existing job for the same retailer and chosen week.</p>{error&&<p role="alert" className="text-sm text-rose-300">{error}</p>}<div className="flex justify-end gap-3"><button type="button" className={button} disabled={busy} onClick={()=>setReprocessJob(null)}>Cancel</button><button type="submit" className={button+' bg-cyan-600'} disabled={busy}>{busy?'Starting…':'Start Reprocessing'}</button></div></form></div>}
  {audit&&<div''')
p.write_text(s,encoding='utf-8')
print('V1.5.A1 prepared')
