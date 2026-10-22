from file_workflow import launch_state,execute_state,step,mapped
from kpi_records import evaluate_kpi,register_kpi_routes
from input_files import profile_records
from retailer_archive import archive_state
from compare_runs import register_compare_routes
from preprocessing import register_preprocessing_routes, preprocessing_report, parse_source, check_configuration
"""One committed retailer/week batch, with cancellable staged replacements."""
from store_review import register_store_review_routes
from configuration_history import record_version, version_summary
import io
import json
import multiprocessing
import threading
import time
import uuid
from datetime import datetime, timezone
from flask import request, jsonify
from werkzeug.datastructures import FileStorage
from database import get_db_connection, begin_write, column_names, IntegrityError
from retailer_setup import apply_pipeline, validate_pipeline, validate_retailer, assign_store_codes
from batch_history import migrate_run_history
from batch_metrics import input_metrics, received_metrics, public_metrics, previous_period

FINDING_CODES={'numeric':'RULE_NUMERIC_INVALID','date':'RULE_DATE_INVALID','required':'VALIDATION_REQUIRED',
               'range':'VALIDATION_RANGE','pattern':'VALIDATION_PATTERN','unique':'VALIDATION_DUPLICATE'}

FINDING_REASONS={'numeric':'invalid numeric values','date':'invalid date values','required':'missing required values',
                 'range':'values outside the allowed range or invalid numbers','pattern':'values not matching the configured pattern','unique':'duplicate values'}
CANCELLATION_REASONS={'INPUT_PARSE_ERROR':'The input file could not be parsed.',
 'RULE_WORKER_START_ERROR':'The execution worker could not start.', 'RULE_PROCESS_EXIT':'The worker stopped before returning a result.',
 'JOB_TIMEOUT':'The job exceeded its processing time limit.', 'JOB_CANCELLED_BY_USER':'The operator cancelled this job.',
 'JOB_SERVER_RESTARTED':'The server restarted before the job completed.', 'JOB_INTERNAL_ERROR':'An unexpected internal processing error stopped the job.'}

def now(): return datetime.now(timezone.utc).isoformat()
def decode(value, default): return json.loads(value) if value else default

def execute_step(records, rule, queue):
    try:
        output, steps, issues, trace = apply_pipeline(records, [rule])
        queue.put({'output':output, 'issueCount':len(issues), 'changedCells':len(trace)})
    except (ValueError, TypeError, KeyError) as exc:
        message=str(exc)
        code='RULE_FIELD_MISSING' if 'does not exist' in message else 'RULE_TARGET_EXISTS' if 'already exists' in message else 'RULE_CONFIG_INVALID'
        queue.put({'errorCode':code,'message':message})
    except Exception:
        queue.put({'errorCode':'RULE_EXECUTION_ERROR','message':'Rule execution failed unexpectedly.'})

def execute_parse(source, filename, parser, queue):
    try:
        file=FileStorage(stream=io.BytesIO(source),filename=filename)
        try:records,_,_=parser(file)
        finally:file.close()
        queue.put({'output':records})
    except Exception:
        queue.put({'errorCode':'INPUT_PARSE_ERROR','message':'The input file could not be parsed.'})

def public_job(row):
    return {k:row[k] for k in ['id','retailer_id','retailer_name','period','start_time','end_time','status','filename']} | {
        'errorCodes':decode(row['error_codes'],[]), 'hasAudit':row['status']!='Cancelled Job' and bool(row['audit']),
        'metrics':public_metrics(decode(row['metrics'],{})), 'lastAttempt':decode(row['last_attempt'],None)}

def register_batch_routes(app, parse_upload, error):
    register_kpi_routes(app,error)
    register_compare_routes(app,error)
    register_store_review_routes(app,error)
    register_preprocessing_routes(app,parse_upload,error)
    with get_db_connection() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS batch_jobs(
            id TEXT PRIMARY KEY,retailer_id TEXT NOT NULL,retailer_name TEXT NOT NULL,period TEXT NOT NULL,
            start_time TEXT NOT NULL,end_time TEXT,status TEXT NOT NULL,filename TEXT NOT NULL,
            source BYTEA NOT NULL,pipeline TEXT NOT NULL,output TEXT,audit TEXT,error_codes TEXT,last_attempt TEXT)''')
        db.execute('''CREATE TABLE IF NOT EXISTS batch_attempts(
            id TEXT PRIMARY KEY,retailer_id TEXT NOT NULL,retailer_name TEXT NOT NULL,period TEXT NOT NULL,
            start_time TEXT NOT NULL,filename TEXT NOT NULL,source BYTEA NOT NULL,pipeline TEXT NOT NULL,
            deadline DOUBLE PRECISION NOT NULL,progress TEXT NOT NULL)''')

    with get_db_connection() as db:
        for table in ['batch_jobs','batch_attempts']:
            if 'metrics' not in column_names(db,table):
                db.execute(f'ALTER TABLE {table} ADD COLUMN metrics TEXT')
            if getattr(db, 'dialect', 'sqlite') == 'postgresql':
                db.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS rowid BIGINT GENERATED BY DEFAULT AS IDENTITY')

    with get_db_connection() as db:
        migrate_run_history(db)
        db.execute('CREATE TABLE IF NOT EXISTS batch_input_records(id TEXT PRIMARY KEY,records TEXT NOT NULL)')

    def finalize(aid, status, output=None, audit=None, codes=None):
        with get_db_connection() as db:
            begin_write(db)
            attempt=db.execute('SELECT * FROM batch_attempts WHERE id=?',(aid,)).fetchone()
            if not attempt: return False
            cancelled=status=='Cancelled Job'
            ended=None if cancelled else now()
            metrics=decode(attempt['metrics'],{})
            stop_code=next((code for code in (codes or []) if code in CANCELLATION_REASONS),None)
            if cancelled and stop_code:
                progress=decode(attempt['progress'],{})
                metrics['cancellationDetails']={'reason':CANCELLATION_REASONS[stop_code],'errorCode':stop_code,
                    'sequence':progress.get('sequence'),'ruleName':progress.get('ruleName'),
                    'attempt':progress.get('attempt')}
            saved_metrics=json.dumps(metrics)
            db.execute('INSERT INTO batch_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (aid,attempt['retailer_id'],attempt['retailer_name'],attempt['period'],attempt['start_time'],ended,status,
                 attempt['filename'],attempt['source'],attempt['pipeline'],None if cancelled else json.dumps(output),
                 None if cancelled else json.dumps(audit or []),json.dumps(codes or []),None,saved_metrics))
            db.execute('DELETE FROM batch_input_records WHERE id=?',(aid,))
            db.execute('DELETE FROM batch_attempts WHERE id=?',(aid,))
            return True

    def active(aid):
        with get_db_connection() as db: return db.execute('SELECT * FROM batch_attempts WHERE id=?',(aid,)).fetchone()

    def process_result(aid, target, args, deadline):
        context=multiprocessing.get_context('spawn');queue=context.Queue(maxsize=1)
        process=context.Process(target=target,args=(*args,queue))
        try:process.start()
        except Exception:
            queue.close()
            return {'errorCode':'RULE_WORKER_START_ERROR','message':'The execution worker could not start.'}
        try:
            while True:
                if not active(aid):return None
                if time.time()>=deadline:
                    finalize(aid,'Cancelled Job',codes=['JOB_TIMEOUT']);return None
                try:return queue.get(timeout=0.1)
                except Exception:
                    if not process.is_alive():return {'errorCode':'RULE_PROCESS_EXIT','message':'The worker stopped before returning a result.'}
        finally:
            if process.is_alive():process.terminate()
            process.join(timeout=2);queue.close()

    def run(aid):
        attempt=active(aid)
        if not attempt:return
        audit=[];interrupted=False;codes=[]
        try:
            started=now();parse_clock=time.monotonic()
            with get_db_connection() as db:cached=db.execute('SELECT records FROM batch_input_records WHERE id=?',(aid,)).fetchone()
            if cached:records=json.loads(cached['records'])
            elif app.testing and app.config.get('BATCH_TEST_EXECUTOR'):
                file=FileStorage(stream=io.BytesIO(attempt['source']),filename=attempt['filename'])
                try:records,_,_=parse_upload(file)
                finally:file.close()
            else:
                result=process_result(aid,execute_parse,(attempt['source'],attempt['filename'],parse_upload),attempt['deadline'])
                if result is None:return
                if result.get('errorCode'):
                    finalize(aid,'Cancelled Job',codes=[result['errorCode']]);return
                if result.get('state') is not None:state=result['state']
                records=result['output']
            audit.append({'sequence':0,'ruleName':'File parsing','category':'Ingestion','attempt':1,'startTime':started,'endTime':now(),'durationMs':round((time.monotonic()-parse_clock)*1000),'result':'Successful','errorCode':None,'message':f'{len(records)} rows parsed.'})
        except Exception:
            finalize(aid,'Cancelled Job',codes=['INPUT_PARSE_ERROR']);return
        state=records if isinstance(records,dict) and 'datasets' in records else None
        if state:records=state['current']
        metrics=decode(attempt['metrics'],{})
        received_metrics(metrics,records)
        pipeline=decode(attempt['pipeline'],[])
        # Cleaning count is the output at the last Cleaning step, before later transformations.
        metrics['rowsAfterCleaning']=len(records) if not any(r['category']=='Cleaning' for r in pipeline) else None
        with get_db_connection() as db:db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid))
        for sequence, rule in enumerate(pipeline,1):
            if rule['operation']=='kpi':continue
            for retry in range(1,4):
                attempt=active(aid)
                if not attempt:return
                if time.time()>=attempt['deadline']:
                    finalize(aid,'Cancelled Job',codes=['JOB_TIMEOUT']);return
                started=now();clock=time.monotonic()
                progress={'sequence':sequence,'ruleName':rule.get('name',rule['operation']),'attempt':retry,'totalRules':len(pipeline)}
                with get_db_connection() as db: db.execute('UPDATE batch_attempts SET progress=? WHERE id=?',(json.dumps(progress),aid))
                result=None
                executor=app.config.get('BATCH_TEST_EXECUTOR')
                if state is not None and rule.get('operation')=='kpi':
                    result={'state':state,'output':records,'issueCount':0,'changedCells':0}
                elif state is not None:
                    if app.testing:
                        try:result=step(state,rule)
                        except (ValueError,KeyError,TypeError) as exc:result={'errorCode':'LINK_OR_LAYOUT_ERROR','message':str(exc)}
                    else:result=process_result(aid,execute_state,(state,rule),attempt['deadline'])
                    if result is None:return
                elif app.testing and executor:
                    try:result=executor(records,rule)
                    except Exception:result={'errorCode':'RULE_EXECUTION_ERROR','message':'Rule execution failed unexpectedly.'}
                else:
                    result=process_result(aid,execute_step,(records,rule),attempt['deadline'])
                    if result is None:return
                if not active(aid):return
                if time.time()>=attempt['deadline']:
                    finalize(aid,'Cancelled Job',codes=['JOB_TIMEOUT']);return
                findings=result.get('issueCount',0)
                failed=bool(result.get('errorCode')) or findings>0
                code=result.get('errorCode') or (FINDING_CODES.get(rule['operation'],'RULE_VALIDATION_FAILED') if findings else None)
                reason=result.get('message') or (f"{findings} {FINDING_REASONS.get(rule['operation'],'data validation findings')} in field {rule.get('field','(unspecified)')}." if findings else 'Rule executed successfully.')
                audit.append({'sequence':sequence,'ruleId':rule['id'],'ruleName':rule.get('name',rule['operation']),'category':rule['category'],'attempt':retry,
                              'startTime':started,'endTime':now(),'durationMs':round((time.monotonic()-clock)*1000),'result':'Fail Execution' if failed or findings else 'Successful',
                              'executionCode':'908' if failed else '909',
                              'errorCode':code,'message':reason,
                              'issueCount':findings,'changedCells':result.get('changedCells',0)})
                if failed:
                    detail={'sequence':sequence,'ruleId':rule['id'],'ruleName':rule.get('name',rule['operation']),
                        'category':rule['category'],'field':rule.get('field',''),'attempt':retry,'maxAttempts':3,
                        'errorCode':code,'reason':reason[:1000],'issueCount':findings,'recoveredOnAttempt':None}
                    metrics.setdefault('failureDetails',[])
                    if metrics['failureDetails'] and metrics['failureDetails'][-1]['sequence']==sequence:
                        metrics['failureDetails'][-1]=detail
                    else:metrics['failureDetails'].append(detail)
                    with get_db_connection() as db:db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid))
                    interrupted=True
                    if code not in codes:codes.append(code)
                    if retry==3:finalize(aid,'Cancelled Job',codes=codes+['RULE_RETRY_LIMIT']);return
                    continue
                interrupted=interrupted or bool(findings)
                if code and code not in codes:codes.append(code)
                if retry>1 and metrics.get('failureDetails'):
                    metrics['failureDetails'][-1]['recoveredOnAttempt']=retry
                    with get_db_connection() as db:db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid))
                if result.get('state') is not None:state=result['state']
                records=result['output']
                if rule['category']=='Cleaning':
                    metrics['rowsAfterCleaning']=len(records)
                    with get_db_connection() as db:db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid))
                break
        if not active(aid):return
        if time.time()>=attempt['deadline']:finalize(aid,'Cancelled Job',codes=['JOB_TIMEOUT']);return
        with get_db_connection() as db:
            begin_write(db)
            if not db.execute('SELECT id FROM batch_attempts WHERE id=?',(aid,)).fetchone():return
            try:records=mapped(records,metrics.get('columnMapping',[]),metrics.get('analyticsColumns',[]))
            except ValueError as exc:
                metrics['failureDetails']=[{'sequence':len(pipeline)+1,'ruleName':'Column Mapping','category':'Column Mapping','field':'','attempt':1,'maxAttempts':1,'errorCode':'OUTPUT_MAPPING_ERROR','reason':str(exc),'issueCount':0}]
                db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid));mapping_error=True
            else:
                mapping_error=False
                if metrics.get('columnMapping'):
                    stamp=now();audit.append({'sequence':len(pipeline)+1,'ruleName':'Column Mapping','category':'Column Mapping','attempt':1,'startTime':stamp,'endTime':stamp,'durationMs':0,'result':'Successful','executionCode':'909','errorCode':None,'message':f'{len(metrics["columnMapping"])} output columns selected and ordered; {len(metrics.get("analyticsColumns",[]))} analytics columns saved.'})
            selected=next((r for r in pipeline if r['operation']=='kpi' and (not r.get('inputFileId') or r['inputFileId']==metrics.get('inputFile',{}).get('id'))),None)
            profile=metrics.get('inputFile')
            kpi=evaluate_kpi(db,attempt['retailer_id'],attempt['period'],records,{**profile,'kpi':selected['kpi']}) if selected and profile and not mapping_error else None
            if kpi is not None:
                metrics['kpi']=kpi
                if kpi['flagged']:interrupted=True;codes.append('KPI_REVIEW_REQUIRED')
                db.execute('UPDATE batch_attempts SET metrics=? WHERE id=?',(json.dumps(metrics),aid))
                stamp=now();audit.append({'sequence':next(i for i,r in enumerate(pipeline,1) if r['id']==selected['id']),'ruleId':selected['id'],'ruleName':selected.get('name','KPI checks'),'category':'KPI','attempt':1,'startTime':stamp,'endTime':stamp,'durationMs':0,'result':'Review required' if kpi['flagged'] else 'Successful','errorCode':'KPI_REVIEW_REQUIRED' if kpi['flagged'] else None,'message':'; '.join(kpi['flags']) or 'Store, retailer and row-count KPIs are within range.'})
        if mapping_error:finalize(aid,'Cancelled Job',codes=['OUTPUT_MAPPING_ERROR']);return
        if time.time()>=attempt['deadline']:finalize(aid,'Cancelled Job',codes=['JOB_TIMEOUT']);return
        finalize(aid,'Completed with Interruption' if interrupted else 'Completed',records,audit,codes)

    def launch(retailer_id,period,filename,source,store_field='',expected_hash=None,input_file_id=None):
        try:
            year,week=period.split('-W');datetime.fromisocalendar(int(year),int(week),1)
            if period!=f'{int(year):04d}-W{int(week):02d}':raise ValueError()
        except (ValueError,AttributeError):return error('Choose a valid ISO week, for example 2026-W41.')
        profile=None
        try:
            if input_file_id:checked_records,profile=profile_records(retailer_id,input_file_id,source,filename)
            else:checked_records=parse_source(source,filename,parse_upload)
        except ValueError as exc:return error('Preprocessing check failed: '+str(exc))
        except Exception:return jsonify(success=False,error='Preprocessing check failed: input file could not be parsed.',report={'ready':False,'filename':filename,'period':period,'fileSizeBytes':len(source),'issues':[{'code':'INPUT_PARSE_ERROR','message':'Supply a nonempty CSV, XLSX or JSON file with valid headers.','sequence':None,'ruleName':'','field':''}],'warnings':[]}),400
        with get_db_connection() as db:
            row=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(retailer_id,)).fetchone()
            captured=json.loads(row['payload']) if row else {}
        state=None;linked_inputs=[]
        special=any(r.get('operation') in ['join','kpi'] for r in captured.get('pipeline',[]))
        if special and not profile:return error('Select the saved primary Input File Settings for this workflow.')
        if any(r.get('operation')=='join' for r in captured.get('pipeline',[])) and captured.get('primaryInputId') and input_file_id!=captured['primaryInputId']:return error('Start linked processing with the configured primary input.')
        if profile and (captured.get('workflowVersion')==1 or any(r.get('operation') in ['join','kpi'] for r in captured.get('pipeline',[]))):
            try:state,linked_inputs=launch_state(retailer_id,captured,input_file_id,checked_records)
            except (ValueError,OSError) as exc:return error('Linked input check failed: '+str(exc))
        with get_db_connection() as db:
            begin_write(db)
            retailer=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(retailer_id,)).fetchone()
            if not retailer:return error('Retailer not found.',404)
            if archive_state(db,retailer_id)['archived']:return error('Archived retailers cannot start or reprocess jobs. Restore the retailer first.',409)
            config=json.loads(retailer['payload']);pipeline=config.get('pipeline',[])
            if state is not None and config!=captured:return error('Setup changed while reading linked files. Check again.',409)
            if profile is not None and next((p for p in config.get('inputFiles',[]) if p['id']==input_file_id),None)!=profile:return error('Input settings changed. Check the input again.',409)
            report=check_configuration(config,checked_records,period,filename,source,store_field)
            if state is not None:
                from file_workflow import schema_issues
                report['issues'].extend(schema_issues(state,config));report['ready']=not report['issues']
            if expected_hash and expected_hash!=report['configurationHash']:return jsonify(success=False,error='Setup changed since preprocessing. Run the check again.',report=report),409
            if not report['ready']:return jsonify(success=False,error='Resolve the preprocessing errors before starting.',report=report),400
            try:validate_pipeline(pipeline)
            except ValueError as exc:return error(str(exc))
            if not isinstance(store_field,str) or len(store_field)>200:return error('Store ID column must be at most 200 characters.')
            previous=db.execute("SELECT source FROM batch_jobs WHERE retailer_id=? AND period=? AND status!='Cancelled Job' AND json_extract(metrics,'$.inputFile.id') IS NOT DISTINCT FROM ? ORDER BY end_time DESC, start_time DESC, rowid DESC LIMIT 1",(retailer_id,previous_period(period),input_file_id)).fetchone()
            metrics=input_metrics(source,period,config.get('stores',[]),previous,store_field.strip())
            metrics['columnMapping']=config.get('columnMapping',[]);metrics['analyticsColumns']=config.get('analyticsColumns',[]);metrics['linkedInputs']=linked_inputs
            if profile is not None:metrics['inputFile']=profile
            metrics['preprocessing']={k:report[k] for k in ['checkedAt','configurationHash','fileSha256','warnings']}
            metrics['configurationVersion']=version_summary(record_version(db,retailer_id,config,'Configuration captured at launch'))
            aid='BATCH-'+uuid.uuid4().hex[:12]
            deadline=time.time()+float(app.config.get('BATCH_TIMEOUT_SECONDS',300))
            try:
                db.execute('INSERT INTO batch_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)',(aid,retailer_id,config['name'],period,now(),filename,source,json.dumps(pipeline),deadline,'{}',json.dumps(metrics)))
            except IntegrityError:return error('A job is already processing for this retailer and week.',409)
            if profile is not None:db.execute('INSERT INTO batch_input_records VALUES(?,?)',(aid,json.dumps(state if state is not None else checked_records)))
        if app.config.get('BATCH_DEFER_WORKER') and app.testing:
            pass
        else:
            def guarded():
                try:run(aid)
                except Exception:
                    app.logger.exception('Batch worker failed')
                    finalize(aid,'Cancelled Job',codes=['JOB_INTERNAL_ERROR'])
            threading.Thread(target=guarded,daemon=True).start()
        return jsonify(success=True,attemptId=aid),202

    @app.route('/api/v1/batches',methods=['GET','POST'])
    def batches():
        if request.method=='GET':
            with get_db_connection() as db:
                jobs=[public_job(r) for r in db.execute('SELECT * FROM batch_jobs ORDER BY start_time DESC, rowid DESC')]
                pending=[{k:r[k] for k in ['id','retailer_id','retailer_name','period','start_time','filename']} | {'progress':decode(r['progress'],{})} for r in db.execute('SELECT * FROM batch_attempts ORDER BY start_time DESC, rowid DESC')]
            return jsonify(success=True,jobs=jobs,active=pending)
        file=request.files.get('file')
        if not file or not file.filename:return error('Select a batch data file.')
        return launch(request.form.get('retailerId',''),request.form.get('period',''),file.filename,file.read(),request.form.get('storeIdField',''),request.form.get('expectedConfigurationHash'),request.form.get('inputFileId') or None)

    @app.route('/api/v1/batches/<aid>/status')
    def status(aid):
        attempt=active(aid)
        if attempt:return jsonify(success=True,processing=True,progress=decode(attempt['progress'],{}))
        with get_db_connection() as db:
            job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(aid,)).fetchone()
            if job:return jsonify(success=True,processing=False,job=public_job(job))
            row=db.execute("SELECT last_attempt FROM batch_jobs WHERE json_extract(last_attempt,'$.id')=?",(aid,)).fetchone()
        if row:return jsonify(success=True,processing=False,job=decode(row['last_attempt'],{}))
        return error('Job no longer exists; it may have been replaced.',404)

    @app.route('/api/v1/batches/<jid>/audit')
    def audit(jid):
        with get_db_connection() as db:job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
        if not job:return error('Job not found.',404)
        if job['status']=='Cancelled Job':return error('Cancelled jobs have no audit log.',404)
        return jsonify(success=True,job=public_job(job),entries=decode(job['audit'],[]))

    @app.route('/api/v1/batches/<jid>/configuration')
    def batch_configuration(jid):
        with get_db_connection() as db:
            job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
            if not job:return error('Job not found.',404)
            reference=decode(job['metrics'],{}).get('configurationVersion')
            if not reference:return error('Configuration version was not captured for this historical run.',404)
            row=db.execute('SELECT * FROM retailer_configuration_versions WHERE id=? AND retailer_id=?',(reference['id'],job['retailer_id'])).fetchone()
            if not row:return error('Configuration snapshot unavailable.',404)
        return jsonify(success=True,version=version_summary(row),configuration=json.loads(row['payload']))

    @app.route('/api/v1/batches/<jid>/reprocess',methods=['POST'])
    def reprocess(jid):
        with get_db_connection() as db:job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
        if not job:return error('Job not found.',404)
        body=request.get_json(silent=True)
        if body is None:body={}
        if not isinstance(body,dict):return error('Invalid reprocessing request.')
        if decode(job['metrics'],{}).get('historyRecoveryNote'):return error('Original input was not retained for this recovered run. Upload the file as a new batch.')
        return launch(job['retailer_id'],body.get('period',job['period']),job['filename'],job['source'],decode(job['metrics'],{}).get('storeIdField',''),body.get('expectedConfigurationHash'),decode(job['metrics'],{}).get('inputFile',{}).get('id'))

    @app.route('/api/v1/batches/<jid>/approve',methods=['POST'])
    def approve(jid):
        with get_db_connection() as db:
            begin_write(db);job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
            if not job:return error('Job not found.',404)
            if db.execute('SELECT id FROM batch_attempts WHERE retailer_id=? AND period=?',(job['retailer_id'],job['period'])).fetchone():return error('Wait for or cancel the reprocessing attempt before approving.',409)
            if job['status'] not in ['Completed','Completed with Interruption']:return error('Only completed jobs can be approved.',409)
            metrics=decode(job['metrics'],{})
            if metrics.get('kpi',{}).get('flagged') and not metrics['kpi'].get('review'):return error('Record a manual KPI check before approving this job.',409)
            entries=decode(job['audit'],[])
            stamp=now();metrics['approvedAt']=stamp
            db.execute('UPDATE batch_jobs SET metrics=? WHERE id=?',(json.dumps(metrics),jid))
            entries.append({'sequence':None,'ruleName':'Job approval','category':'Action','attempt':1,'startTime':stamp,'endTime':stamp,'durationMs':0,'result':'Successful','errorCode':None,'message':'Approved by operator action.'})
            db.execute('UPDATE batch_jobs SET status=?,audit=? WHERE id=?',('Approved Job',json.dumps(entries),jid))
        return jsonify(success=True)

    @app.route('/api/v1/batches/<jid>/cancel',methods=['POST'])
    def cancel(jid):
        if active(jid) and finalize(jid,'Cancelled Job',codes=['JOB_CANCELLED_BY_USER']):return jsonify(success=True)
        with get_db_connection() as db:
            begin_write(db);job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
            if not job:return error('Job not found.',404)
            if db.execute('SELECT id FROM batch_attempts WHERE retailer_id=? AND period=?',(job['retailer_id'],job['period'])).fetchone():return error('Cancel the active reprocessing attempt using its Cancel Job button.',409)
            metrics=decode(job['metrics'],{})
            metrics['cancellationDetails']={'reason':CANCELLATION_REASONS['JOB_CANCELLED_BY_USER'],'errorCode':'JOB_CANCELLED_BY_USER'}
            db.execute('UPDATE batch_jobs SET metrics=? WHERE id=?',(json.dumps(metrics),jid))
            db.execute('UPDATE batch_jobs SET status=?,end_time=NULL,audit=NULL,output=NULL,error_codes=? WHERE id=?',('Cancelled Job',json.dumps(['JOB_CANCELLED_BY_USER']),jid))
        return jsonify(success=True)

    # Spawned rule processes import the main module on Windows; recovery runs only in the server.
    if multiprocessing.current_process().name=='MainProcess':
        with get_db_connection() as db:stale=[r['id'] for r in db.execute('SELECT id FROM batch_attempts')]
        for aid in stale:finalize(aid,'Cancelled Job',codes=['JOB_SERVER_RESTARTED'])
    app.extensions['batch_launch']=launch
    app.extensions['batch_run']=run
    app.extensions['batch_finalize']=finalize
