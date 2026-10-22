from input_files import profile_parser
from retailer_archive import archive_state
"""Read-only schema/configuration checks before creating a batch run."""
import hashlib,io,json,re
from datetime import datetime,timezone
from werkzeug.datastructures import FileStorage
from flask import request,jsonify
from database import get_db_connection
from retailer_setup import validate_pipeline

def configuration_hash(config):
    return hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()

def parse_source(source,filename,parser):
    file=FileStorage(stream=io.BytesIO(source),filename=filename)
    try:return parser(file)[0]
    finally:file.close()

def check_configuration(config,records,period,filename,source,store_field=''):
    issues=[];warnings=[];columns=set(k for row in records or [] for k in row)
    def issue(code,message,sequence=None,rule=None):issues.append(dict(code=code,message=message,sequence=sequence,ruleName=(rule or {}).get('name',''),field=(rule or {}).get('field','')))
    try:
        year,week=period.split('-W');datetime.fromisocalendar(int(year),int(week),1)
        if period!=f'{int(year):04d}-W{int(week):02d}':raise ValueError()
    except (ValueError,AttributeError,TypeError):issue('INVALID_PERIOD','Choose a valid ISO week in YYYY-Www format.')
    if not isinstance(store_field,str) or len(store_field)>200:issue('INVALID_STORE_FIELD','Store ID field must be text of at most 200 characters.')
    elif store_field.strip() and store_field.strip() not in columns:issue('STORE_FIELD_MISSING',f'Store ID field "{store_field.strip()}" is not in the file.')
    if not config:issue('RETAILER_MISSING','Choose an existing saved retailer setup.')
    else:
        if config.get('archived'):issue('RETAILER_ARCHIVED','Restore this retailer before processing.')
        pipeline=config.get('pipeline',[])
        if not isinstance(pipeline,list):issue('INVALID_PIPELINE','Saved rules must be a list.');pipeline=[]
        if len(pipeline)>100:issue('INVALID_PIPELINE','Use at most 100 rules.')
        seen=set()
        for sequence,rule in enumerate(pipeline,1):
            if not isinstance(rule,dict):issue('INVALID_RULE','Rule is not a valid configuration.',sequence);continue
            if isinstance(rule.get('id'),str):
                if rule['id'] in seen:issue('DUPLICATE_RULE_ID','Each rule needs a unique ID.',sequence,rule)
                seen.add(rule['id'])
            try:validate_pipeline([rule])
            except (ValueError,TypeError) as exc:issue('REFERENCE_ONLY' if rule.get('operation')=='reference' else 'INVALID_RULE',str(exc),sequence,rule);continue
            if rule.get('operation') in ['join','kpi'] or rule.get('inputFileId') or rule.get('stage')=='Layout':continue
            field=rule['field'];condition=rule.get('condition')
            if field not in columns:issue('RULE_FIELD_MISSING',f'Field "{field}" is unavailable at this sequence. Select an existing field or move its rename rule earlier.',sequence,rule)
            if condition and condition['field'] not in columns:issue('CONDITION_FIELD_MISSING',f'Condition field "{condition["field"]}" is unavailable at this sequence.',sequence,rule)
            if rule['operation']=='date':
                fmt=rule['dateFormat'];tokens=re.findall(r'%(.|$)',fmt)
                if any(token not in 'aAbBcdHIjmMpSUwWxXyYfzZGgVu%' for token in tokens):issue('INVALID_DATE_FORMAT','Source date format has an unsupported or incomplete directive. Example: %d/%m/%Y.',sequence,rule)
                else:
                    try:datetime.strptime('',fmt)
                    except re.error:issue('INVALID_DATE_FORMAT','Date format repeats a directive or has an invalid pattern.',sequence,rule)
                    except ValueError as exc:
                        if any(text in str(exc) for text in ['must be used with','incompatible with','bad directive','stray %']):issue('INVALID_DATE_FORMAT',str(exc),sequence,rule)
            if rule['operation']=='rename' and field in columns:
                target=rule['target']
                if target!=field and target in columns:issue('RENAME_TARGET_EXISTS',f'Rename target "{target}" already exists.',sequence,rule)
                else:
                    if not condition:columns.discard(field)
                    else:warnings.append(f'Rule {sequence}: a conditional rename may leave some rows without "{target}". Review the sample preview.')
                    columns.add(target)
        if not pipeline:warnings.append('No rules configured. This job will only parse and record the input.')
        if not config.get('stores'):warnings.append('No registered stores. Received stores will be flagged as new when Store IDs are available.')
    if not store_field:
        candidates=[c for c in set(k for row in records or [] for k in row) if re.sub(r'[^a-z0-9]','',c.lower()) in {'storeid','retailerstoreid','storecode','retailerstorecode','storekey'}]
        if len(candidates)!=1:warnings.append('Store ID field cannot be detected uniquely. Store counts and New/Missing Store flags may be unavailable; enter an override if needed.')
    return dict(ready=not issues,checkedAt=datetime.now(timezone.utc).isoformat(),configurationHash=configuration_hash(config) if config else None,
                retailerName=(config or {}).get('name',''),period=period,filename=filename,fileSizeBytes=len(source),fileSha256=hashlib.sha256(source).hexdigest(),rowsReceived=len(records or []),
                columns=sorted(set(k for row in records or [] for k in row)),issues=issues,warnings=warnings)

def preprocessing_report(config,source,filename,period,store_field,parser):
    try:records=parse_source(source,filename,parser)
    except Exception:
        report=check_configuration(config,[],period,filename,source,store_field)
        report['issues'].insert(0,dict(code='INPUT_PARSE_ERROR',message='File cannot be parsed. Supply a nonempty CSV, XLSX or JSON file with valid headers.',sequence=None,ruleName='',field=''))
        report['ready']=False
        return report
    return check_configuration(config,records,period,filename,source,store_field)

def extend_workflow_report(report,config,rid,pid,source,filename,parser):
    if not config or not (config.get('workflowVersion')==1 or any(r.get('operation') in ['join','kpi'] for r in config.get('pipeline',[]))):return report
    try:
        if not pid:raise ValueError('Select the saved primary Input File Settings.')
        if any(r.get('operation')=='join' for r in config.get('pipeline',[])) and config.get('primaryInputId') and pid!=config['primaryInputId']:raise ValueError('Select the configured primary input for linked processing.')
        from file_workflow import launch_state,schema_issues
        state,linked=launch_state(rid,config,pid,parse_source(source,filename,parser))
        report['linkedInputs']=linked;report['issues'].extend(schema_issues(state,config))
    except (ValueError,OSError,KeyError) as exc:report['issues'].append({'code':'LINKED_INPUT_ERROR','message':str(exc),'sequence':None,'ruleName':'Link Files','field':''})
    report['ready']=not report['issues'];return report

def register_preprocessing_routes(app,parser,error):
    @app.route('/api/v1/batches/preprocessing',methods=['POST'])
    def preprocessing_upload():
        file=request.files.get('file')
        if not file or not file.filename:return error('Select a data file to check.')
        rid=request.form.get('retailerId','')
        with get_db_connection() as db:
            row=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(rid,)).fetchone()
            config=json.loads(row['payload']) if row else None
            if config is not None and archive_state(db,rid)['archived']:config['archived']=True
        selected_parser=parser
        if request.form.get('inputFileId'):
            try:selected_parser=profile_parser(rid,request.form['inputFileId'])
            except ValueError as exc:return error(str(exc))
        source=file.read();pid=request.form.get('inputFileId')
        report=preprocessing_report(config,source,file.filename,request.form.get('period',''),request.form.get('storeIdField',''),selected_parser)
        if config and (config.get('workflowVersion')==1 or any(r.get('operation') in ['join','kpi'] for r in config.get('pipeline',[]))):
            try:
                if not pid:raise ValueError('Select the saved primary Input File Settings.')
                if any(r.get('operation')=='join' for r in config.get('pipeline',[])) and config.get('primaryInputId') and pid!=config['primaryInputId']:raise ValueError('Select the configured primary input for linked processing.')
                from file_workflow import launch_state,schema_issues
                state,linked=launch_state(rid,config,pid,parse_source(source,file.filename,selected_parser))
                report['linkedInputs']=linked;report['issues'].extend(schema_issues(state,config))
            except (ValueError,OSError,KeyError) as exc:report['issues'].append({'code':'LINKED_INPUT_ERROR','message':str(exc),'sequence':None,'ruleName':'Link Files','field':''})
            report['ready']=not report['issues']
        return jsonify(success=True,report=report)

    @app.route('/api/v1/batches/<jid>/preprocessing',methods=['POST'])
    def preprocessing_reprocess(jid):
        body=request.get_json(silent=True)
        if body is None:body={}
        if not isinstance(body,dict):return error('Invalid preprocessing request.')
        with get_db_connection() as db:
            job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
            if not job:return error('Job not found.',404)
            row=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(job['retailer_id'],)).fetchone()
            config=json.loads(row['payload']) if row else None
            if config is not None and archive_state(db,job['retailer_id'])['archived']:config['archived']=True
        selected_parser=parser
        pid=json.loads(job['metrics'] or '{}').get('inputFile',{}).get('id')
        if pid:
            try:selected_parser=profile_parser(job['retailer_id'],pid)
            except ValueError as exc:return error(str(exc))
        report=preprocessing_report(config,job['source'],job['filename'],body.get('period',job['period']),json.loads(job['metrics'] or '{}').get('storeIdField',''),selected_parser)
        extend_workflow_report(report,config,job['retailer_id'],pid,job['source'],job['filename'],selected_parser)
        return jsonify(success=True,report=report)
