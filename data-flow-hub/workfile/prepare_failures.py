from pathlib import Path
import shutil,sqlite3,json
base=Path('outputs/V1.9.0');root=Path('outputs/V1.9.A1')
shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist','.venv','*.db','*.db-wal','*.db-shm'),dirs_exist_ok=True)
for rel in ['script/app.py','frontend-github/src/app.jsx','Setup_Windows.bat','Start_V1.9.0.bat']:
 p=root/rel;s=p.read_text(encoding='utf-8').replace('V1.9.0','V1.9.A1').replace("version='1.9.0'","version='1.9.A1'")
 if rel.startswith('Start_'):p.unlink();p=root/'Start_V1.9.A1.bat'
 p.write_text(s,encoding='utf-8')
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name;d=json.loads(p.read_text());d['version']='1.9.1'
 if '' in d.get('packages',{}):d['packages']['']['version']='1.9.1'
 p.write_text(json.dumps(d,indent=2),encoding='utf-8')
p=Path('outputs/V1.3.A1.bat');p.write_text(p.read_text().replace('V1.9.0','V1.9.A1').replace("'1.9.0'","'1.9.A1'"),encoding='utf-8')
if (base/'script/dataflow.db').exists():
 with sqlite3.connect(base/'script/dataflow.db') as a,sqlite3.connect(root/'script/dataflow.db') as b:a.backup(b)
p=root/'script/batch_jobs.py';s=p.read_text(encoding='utf-8')
s=s.replace('def now():', '''FINDING_REASONS={'numeric':'invalid numeric values','date':'invalid date values','required':'missing required values',
                 'range':'values outside the allowed range or invalid numbers','pattern':'values not matching the configured pattern','unique':'duplicate values'}
CANCELLATION_REASONS={'INPUT_PARSE_ERROR':'The input file could not be parsed.',
 'JOB_TIMEOUT':'The job exceeded its processing time limit.', 'JOB_CANCELLED_BY_USER':'The operator cancelled this job.',
 'JOB_SERVER_RESTARTED':'The server restarted before the job completed.', 'JOB_INTERNAL_ERROR':'An unexpected internal processing error stopped the job.'}

def now():''')
s=s.replace("            ended=None if cancelled else now()", """            ended=None if cancelled else now()
            metrics=decode(attempt['metrics'],{})
            stop_code=next((code for code in (codes or []) if code in CANCELLATION_REASONS),None)
            if cancelled and stop_code:
                progress=decode(attempt['progress'],{})
                metrics['cancellationDetails']={'reason':CANCELLATION_REASONS[stop_code],'errorCode':stop_code,
                    'sequence':progress.get('sequence'),'ruleName':progress.get('ruleName'),
                    'attempt':progress.get('attempt')}
            saved_metrics=json.dumps(metrics)""")
s=s.replace("None,attempt['metrics']))", "None,saved_metrics))")
s=s.replace("                if failed:\n                    interrupted=True", """                if failed:
                    reason=result.get('message') or f"{findings} {FINDING_REASONS.get(rule['operation'],'data validation findings')} in field {rule.get('field','(unspecified)')}."
                    detail={'sequence':sequence,'ruleId':rule['id'],'ruleName':rule.get('name',rule['operation']),
                        'category':rule['category'],'field':rule.get('field',''),'attempt':retry,'maxAttempts':3,
                        'errorCode':code,'reason':reason[:1000],'issueCount':findings,'recoveredOnAttempt':None}
                    metrics.setdefault('failureDetails',[])
                    if metrics['failureDetails'] and metrics['failureDetails'][-1]['sequence']==sequence:
                        metrics['failureDetails'][-1]=detail
                    else:metrics['failureDetails'].append(detail)
                    with get_db_connection() as db:db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid))
                    interrupted=True""")
s=s.replace("                records=result['output']", """                if retry>1 and metrics.get('failureDetails'):
                    metrics['failureDetails'][-1]['recoveredOnAttempt']=retry
                    with get_db_connection() as db:db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid))
                records=result['output']""") # only rule success indentation
s=s.replace("            db.execute('UPDATE batch_jobs SET status=?,end_time=NULL", """            metrics=decode(job['metrics'],{})
            metrics['cancellationDetails']={'reason':CANCELLATION_REASONS['JOB_CANCELLED_BY_USER'],'errorCode':'JOB_CANCELLED_BY_USER'}
            db.execute('UPDATE batch_jobs SET metrics=? WHERE id=?',(json.dumps(metrics),jid))
            db.execute('UPDATE batch_jobs SET status=?,end_time=NULL""")
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/BatchLogs.jsx';s=p.read_text(encoding='utf-8')
s=s.replace("const codes={", "const codes={RULE_WORKER_START_ERROR:'Execution worker could not start',")
component='''function FailureDetails({job}){
 const details=job.metrics?.failureDetails||[],stop=job.metrics?.cancellationDetails;
 return <div className="mt-2 space-y-2 text-xs max-w-sm break-words">
 {stop&&<div className="rounded border border-rose-500/30 p-2"><p>{stop.reason}</p>{stop.ruleName&&<p className="mt-1 text-slate-400">Stopped during rule {stop.sequence}: {stop.ruleName} · attempt {stop.attempt}/3</p>}</div>}
 {details.map(detail=><div key={detail.sequence} className="rounded border border-slate-600 p-2 space-y-1">
 <p className="font-semibold">Rule {detail.sequence}: {detail.ruleName}</p><p className="text-slate-400">{detail.category} · {detail.recoveredOnAttempt?`Recovered on attempt ${detail.recoveredOnAttempt}/${detail.maxAttempts} after ${detail.attempt} failed attempt(s)`:`Failed attempts: ${detail.attempt}/${detail.maxAttempts}`}</p><p>{detail.reason}</p>
 </div>)}
 {job.status==='Cancelled Job'&&!stop&&!details.length&&<p className="text-slate-400">Failure details were not captured for this historical run.</p>}
 </div>;
}

'''
s=s.replace('function AuditMetrics(',component+'function AuditMetrics(')
s=s.replace('<ErrorCodes values={job.errorCodes}/>', '<ErrorCodes values={job.errorCodes}/><FailureDetails job={job}/>')
p.write_text(s,encoding='utf-8')
print('V1.9.A1 prepared')
