from pathlib import Path
root=Path('outputs/V1.13.0')
p=root/'script/input_file_io.py';s=p.read_text(encoding='utf-8');s=s.replace('    result=[];seen=set()', '    from kpi_records import validate_kpi\n    result=[];seen=set()',1);s=s.replace("'passwordRevision':int(p.get('passwordRevision',0))}","'passwordRevision':int(p.get('passwordRevision',0)), 'kpi':validate_kpi(p.get('kpi'))}");p.write_text(s,encoding='utf-8')
p=root/'script/batch_jobs.py';s=p.read_text(encoding='utf-8');s='from kpi_records import evaluate_kpi,register_kpi_routes\n'+s;s=s.replace('    register_compare_routes(app,error)','    register_kpi_routes(app,error)\n    register_compare_routes(app,error)',1)
s=s.replace("        finalize(aid,'Completed with Interruption' if interrupted", """        with get_db_connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT id FROM batch_attempts WHERE id=?',(aid,)).fetchone():return
            kpi=evaluate_kpi(db,attempt['retailer_id'],attempt['period'],records,metrics.get('inputFile'))
            if kpi is not None:
                metrics['kpi']=kpi
                if kpi['flagged']:interrupted=True;codes.append('KPI_REVIEW_REQUIRED')
                db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid))
                stamp=now();audit.append({'sequence':None,'ruleName':'KPI checks','category':'KPI','attempt':1,'startTime':stamp,'endTime':stamp,'durationMs':0,'result':'Review required' if kpi['flagged'] else 'Successful','errorCode':'KPI_REVIEW_REQUIRED' if kpi['flagged'] else None,'message':'; '.join(kpi['flags']) or 'Store, retailer and row-count KPIs are within range.'})
        finalize(aid,'Completed with Interruption' if interrupted""",1)
s=s.replace("            entries=decode(job['audit'],[])\n            stamp=now();entries.append", """            metrics=decode(job['metrics'],{})
            if metrics.get('kpi',{}).get('flagged') and not metrics['kpi'].get('review'):return error('Record a manual KPI check before approving this job.',409)
            entries=decode(job['audit'],[])
            stamp=now();metrics['approvedAt']=stamp
            db.execute('UPDATE batch_jobs SET metrics=? WHERE id=?',(json.dumps(metrics),jid))
            entries.append""",1)
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/app.jsx';s=p.read_text(encoding='utf-8');s="import KPIRecords from './KPIRecords';\n"+s;s=s.replace("{ name: 'Data Streams', icon: Database },", "{ name: 'Data Streams', icon: Database },\n              { name: 'KPI Records', icon: BarChart3 },",1);s=s.replace("          {activeTab === 'Client'", "          {activeTab === 'KPI Records' && <KPIRecords />}\n          {activeTab === 'Client'",1);p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/BatchLogs.jsx';s=p.read_text(encoding='utf-8');s=s.replace('const codes={','const codes={KPI_REVIEW_REQUIRED:\'Manual KPI review required\',',1);s=s.replace("disabled={busy||!!pending} className={iconButton+' text-emerald-300'}", "disabled={busy||!!pending||(job.metrics?.kpi?.flagged&&!job.metrics.kpi.review)} className={iconButton+' text-emerald-300'}",1);s=s.replace('title="Approve Job"',"title={job.metrics?.kpi?.flagged&&!job.metrics.kpi.review?'Review this run in KPI Records before approval':'Approve Job'}",1)
s=s.replace('<FailureDetails job={job}/>',"<FailureDetails job={job}/>{job.metrics?.kpi?.flagged&&<p className=\"mt-2 text-amber-300\">KPI {job.metrics.kpi.review?'manually reviewed':'review required — open KPI Records'}</p>}{job.metrics?.approvedAt&&<p className=\"mt-2 text-slate-400\">Approved {stamp(job.metrics.approvedAt)}</p>}",1)
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/InputFiles.jsx';s=p.read_text(encoding='utf-8');s=s.replace("readMode:'Manual',watchInterval:60}","readMode:'Manual',watchInterval:60,kpi:{weeks:8,storeLimit:30,retailerLimit:30,countLimit:40,salesField:'',quantityField:'',storeField:''}}",1)
s=s.replace('onUpdated,onUseSample})','onUpdated,onUseSample,ruleFields=[]})')
s=s.replace("function edit(p){setDraft(p?", "function edit(p){if(p)p={...p,kpi:{...blank().kpi,...p.kpi}};setDraft(p?",1)
s=s.replace('const update=(k,v)=>', "const kpiUpdate=(key,value)=>setDraft(d=>({...d,kpi:{...d.kpi,[key]:value}}));\n const columns=[...new Set([...(profiles.find(p=>p.id===draft?.id)?.sample?.columns||[]),...ruleFields])];\n const update=(k,v)=>",1)
s=s.replace('<p className="text-xs text-slate-400">Delimiter applies', '''{draft.purpose==='Transaction'&&<fieldset className="border border-slate-600 rounded p-3 space-y-3"><legend className="text-sm font-semibold">KPI Checks (Transaction)</legend><p className="text-xs text-slate-400">Select final fields after rules. Upload a sample to populate the field choices. Missing or invalid KPI fields require manual review.</p><div className="grid md:grid-cols-3 gap-3">{[['salesField','Sales Field'],['quantityField','Quantity Field'],['storeField','Store ID Field']].map(([key,label])=><label className="text-sm" key={key}>{label}<select className={input} value={draft.kpi[key]} onChange={e=>kpiUpdate(key,e.target.value)}><option value="">Choose a field</option>{[...new Set([...columns,draft.kpi[key]].filter(Boolean))].map(c=><option key={c}>{c}</option>)}</select></label>)}{[['weeks','Previous Weeks',1,52],['storeLimit','Store Range ±%',0,1000],['retailerLimit','Retailer Range ±%',0,1000],['countLimit','Count Range ±%',0,1000]].map(([key,label,min,max])=><label className="text-sm" key={key}>{label}<input className={input} type="number" required min={min} max={max} step={key==='weeks'?1:'any'} value={draft.kpi[key]} onChange={e=>kpiUpdate(key,Number(e.target.value))}/></label>)}</div><p className="text-xs text-slate-400">Defaults: ±30% store sales, ±30% retailer sales, ±40% row count, previous 8 weeks. Any store outside its range flags the run.</p></fieldset>}<p className="text-xs text-slate-400">Delimiter applies''',1)
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/RetailerSetup.jsx';s=p.read_text(encoding='utf-8').replace('<InputFiles retailerId={config.id}', '<InputFiles retailerId={config.id} ruleFields={config.pipeline.filter(r=>r.operation===\'rename\').map(r=>r.target)}');p.write_text(s,encoding='utf-8')
p=root/'script/test_input_files.py';s=p.read_text(encoding='utf-8').replace("self.assertEqual(job['status'],'Completed');self.assertEqual(job['metrics']['inputFile']", "self.assertEqual(job['status'],'Completed with Interruption');self.assertEqual(job['metrics']['inputFile']");p.write_text(s,encoding='utf-8')
print('KPI processing and settings connected')
