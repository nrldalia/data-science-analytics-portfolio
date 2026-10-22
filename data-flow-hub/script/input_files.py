"""Per-input samples, credentials, scoped path reads and stable-file monitoring."""
import copy,fnmatch,hashlib,json,threading,time,uuid
from datetime import datetime,timezone,timedelta
from pathlib import Path
from flask import request,jsonify
from database import get_db_connection, begin_write, identity_column
from input_file_io import validate_profiles,read_records,parse_hash,protect_password,reveal_password,LIMIT
from retailer_archive import archive_state
SAMPLE_LIMIT=1000000
def resolve_input_root():
    from os import environ
    configured = environ.get('DATAFLOW_INPUT_ROOT')
    if configured:
        root = Path(configured).expanduser()
        if not root.is_absolute():
            raise ValueError('DATAFLOW_INPUT_ROOT must be an absolute directory path.')
        if not root.is_dir():
            raise ValueError('DATAFLOW_INPUT_ROOT must name an existing directory.')
        return root.resolve()
    project = Path(__file__).resolve().parents[1]
    return next((p for p in project.parents if p.name.lower() == 'codex'), project)

# Retain this name for callers that already import the input scope.
CODEx_ROOT=resolve_input_root()
def now():return datetime.now(timezone.utc).isoformat()
def current_week():
    d=datetime.now(timezone(timedelta(hours=8))).isocalendar();return f'{d.year:04d}-W{d.week:02d}'
def load_profile(db,rid,pid):
    row=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(rid,)).fetchone()
    if not row:raise ValueError('Retailer setup no longer exists.')
    config=json.loads(row['payload']);profile=next((p for p in config.get('inputFiles',[]) if p['id']==pid),None)
    if not profile:raise ValueError('Input file settings no longer exist. Select a saved input file.')
    secret=db.execute('SELECT protected FROM input_file_secrets WHERE retailer_id=? AND input_id=?',(rid,pid)).fetchone()
    return config,profile,reveal_password(secret['protected']) if secret else ''
def profile_records(rid,pid,source,filename):
    with get_db_connection() as db:config,profile,password=load_profile(db,rid,pid)
    return read_records(source,filename,profile,password),profile
def profile_parser(rid,pid):
    with get_db_connection() as db:_,profile,password=load_profile(db,rid,pid)
    def parse(file):
        source=file.read();return read_records(source,file.filename,profile,password),profile['fileType'],source
    return parse
def scoped_files(profile):
    if not profile['filePath'].strip():raise ValueError('Save a file path before reading it.')
    path=Path(profile['filePath']).resolve()
    root=CODEx_ROOT.resolve()
    if not path.is_relative_to(root):raise ValueError('File path must stay inside the configured input root.')
    pattern=profile.get('zipFolderName') if profile['isZipFolder'] and profile.get('settingsVersion')==2 else profile['filename']
    if path.is_file():
        if not fnmatch.fnmatch(path.name,pattern):raise ValueError('File path name does not match Filename.')
        return [path]
    if not path.is_dir():raise ValueError('File path does not exist or is not accessible.')
    matches=[]
    for child in path.iterdir():
        if fnmatch.fnmatch(child.name,pattern) and child.is_file():
            resolved=child.resolve()
            if not resolved.is_relative_to(root):raise ValueError('Matched file resolves outside the Codex folder.')
            matches.append(resolved)
            if len(matches)>100:raise ValueError('Filename matches more than 100 files; use a narrower pattern.')
    return sorted(matches)
def bounded_read(path,limit=LIMIT,expected_signature=None):
    before=path.stat()
    if expected_signature is not None and (before.st_size,before.st_mtime_ns)!=expected_signature:raise ValueError('File changed since the stable scan. Wait for delivery to complete.')
    if before.st_size>limit:raise ValueError('File exceeds the size limit.')
    with path.open('rb') as f:source=f.read(limit+1)
    after=path.stat()
    if len(source)>limit:raise ValueError('File exceeds the size limit.')
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('File is still changing. Try again after delivery completes.')
    return source
def sample_public(row,profile):
    if not row:return None
    records=json.loads(row['records']);return {'filename':row['filename'],'byteSize':row['byte_size'],'totalRows':len(records),'columns':list(dict.fromkeys(k for r in records for k in r)),
        'rows':records[:25],'settingsMatch':row['settings_hash']==parse_hash(profile)}

def register_input_routes(app,error):
    from retailer_setup import validate_retailer
    from configuration_history import record_version,version_summary
    with get_db_connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS input_file_samples(retailer_id TEXT,input_id TEXT,filename TEXT,records TEXT,byte_size INTEGER,settings_hash TEXT,PRIMARY KEY(retailer_id,input_id))')
        db.execute('CREATE TABLE IF NOT EXISTS input_file_secrets(retailer_id TEXT,input_id TEXT,protected BYTEA,PRIMARY KEY(retailer_id,input_id))')
        db.execute('CREATE TABLE IF NOT EXISTS batch_input_records(id TEXT PRIMARY KEY,records TEXT NOT NULL)')
        db.execute(f'CREATE TABLE IF NOT EXISTS input_deliveries(id {identity_column(db)},retailer_id TEXT,input_id TEXT,fingerprint TEXT,status TEXT,message TEXT,job_id TEXT,created_at TEXT,UNIQUE(retailer_id,input_id,fingerprint))')
    @app.route('/api/v1/retailers/<rid>/input-files',methods=['GET','POST'])
    def profiles(rid):
        with get_db_connection() as db:
            if request.method=='POST':begin_write(db)
            row=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(rid,)).fetchone()
            if not row:return error('Save the retailer before adding input files.',404)
            config=json.loads(row['payload'])
            if request.method=='GET':
                profiles=[]
                for p in config.get('inputFiles',[]):
                    secret=db.execute('SELECT 1 FROM input_file_secrets WHERE retailer_id=? AND input_id=?',(rid,p['id'])).fetchone()
                    sample=db.execute('SELECT * FROM input_file_samples WHERE retailer_id=? AND input_id=?',(rid,p['id'])).fetchone()
                    events=[dict(r) for r in db.execute('SELECT status,message,job_id,created_at FROM input_deliveries WHERE retailer_id=? AND input_id=? ORDER BY id DESC LIMIT 5',(rid,p['id']))]
                    profiles.append(p|{'hasPassword':bool(secret),'sample':sample_public(sample,p),'deliveries':events})
                return jsonify(success=True,inputFiles=profiles)
            if archive_state(db,rid)['archived']:return error('Restore this retailer before changing input files.',409)
            body=request.get_json(silent=True)
            if not isinstance(body,dict):return error('Invalid input file request.')
            supplied=body.get('profile');mode=body.get('passwordMode','keep')
            if mode not in ['keep','set','clear']:return error('Choose a valid password action.')
            if not isinstance(supplied,dict):return error('Invalid input file settings.')
            pid=supplied.get('id') or 'INPUT-'+uuid.uuid4().hex
            previous=next((p for p in config.get('inputFiles',[]) if p['id']==pid),None)
            supplied={**supplied,'settingsVersion':2}
            for key,default in [('readMode','Manual'),('watchInterval',60),('maxColumns',100),('headerRow',1)]:
                if supplied.get(key) in [None,'']:supplied[key]=default
            if supplied.get('fileType')!='Excel (.xlsx)' or supplied.get('hasSheetPassword') is False:mode='clear'
            if mode=='clear' and not db.execute('SELECT 1 FROM input_file_secrets WHERE retailer_id=? AND input_id=?',(rid,pid)).fetchone():mode='keep'
            if supplied.get('hasSheetPassword') and mode=='keep' and not db.execute('SELECT 1 FROM input_file_secrets WHERE retailer_id=? AND input_id=?',(rid,pid)).fetchone():return error('Enter a password or choose No for Has Sheet Password.')
            profile={**supplied,'id':pid,'passwordRevision':(previous or {}).get('passwordRevision',0)+(1 if mode!='keep' else 0)}
            try:profile=validate_profiles([profile])[0]
            except (ValueError,TypeError):return error('Invalid input file settings. Check names, choices, Max Columns and Header Row.')
            config['inputFiles']=[p for p in config.get('inputFiles',[]) if p['id']!=pid]+[profile]
            try:config=validate_retailer(config)
            except ValueError as exc:return error(str(exc))
            if mode=='set':
                password=body.get('password')
                if not isinstance(password,str) or not password or len(password)>500:return error('Enter a sheet password of at most 500 characters.')
                try:protected=protect_password(password)
                except ValueError as exc:return error(str(exc))
                db.execute('INSERT INTO input_file_secrets VALUES(?,?,?) ON CONFLICT(retailer_id,input_id) DO UPDATE SET protected=excluded.protected',(rid,pid,protected))
            elif mode=='clear':db.execute('DELETE FROM input_file_secrets WHERE retailer_id=? AND input_id=?',(rid,pid))
            db.execute('UPDATE retailer_configs SET payload=? WHERE id=?',(json.dumps(config),rid))
            version=record_version(db,rid,config,'Input file settings saved')
        return jsonify(success=True,inputFile=profile,configurationVersion=version_summary(version))

    @app.route('/api/v1/retailers/<rid>/input-files/<pid>',methods=['DELETE'])
    def remove_profile(rid,pid):
        with get_db_connection() as db:
            begin_write(db);row=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(rid,)).fetchone()
            if not row:return error('Retailer not found.',404)
            if archive_state(db,rid)['archived']:return error('Restore before removing input files.',409)
            config=json.loads(row['payload']);profiles=config.get('inputFiles',[])
            if not any(p['id']==pid for p in profiles):return error('Input file not found.',404)
            config['inputFiles']=[p for p in profiles if p['id']!=pid]
            from file_workflow import required_inputs
            if pid in required_inputs(config.get('pipeline',[]),config.get('primaryInputId')):return error('Remove this input from rules and primary input selection before deleting it.',409)
            db.execute('UPDATE retailer_configs SET payload=? WHERE id=?',(json.dumps(config),rid))
            for table in ['input_file_samples','input_file_secrets']:db.execute(f'DELETE FROM {table} WHERE retailer_id=? AND input_id=?',(rid,pid))
            record_version(db,rid,config,'Input file removed')
        return jsonify(success=True)

    @app.route('/api/v1/retailers/<rid>/input-files/<pid>/sample',methods=['GET','POST'])
    def profile_sample(rid,pid):
        try:
            with get_db_connection() as db:
                _,profile,password=load_profile(db,rid,pid)
                if request.method=='GET':return jsonify(success=True,sample=sample_public(db.execute('SELECT * FROM input_file_samples WHERE retailer_id=? AND input_id=?',(rid,pid)).fetchone(),profile))
                if archive_state(db,rid)['archived']:return error('Restore before uploading samples.',409)
            file=request.files.get('file')
            if not file or not file.filename:return error('Choose a sample for this input file.')
            source=file.read(SAMPLE_LIMIT)
            if len(source)>=SAMPLE_LIMIT:return error('Each sample must be smaller than 1 MB.',413)
            records=read_records(source,file.filename,profile,password,limit=SAMPLE_LIMIT-1)
            if len(records)>10000:return error('Samples support at most 10,000 data rows.')
            with get_db_connection() as db:
                begin_write(db);_,latest,_=load_profile(db,rid,pid)
                if archive_state(db,rid)['archived'] or parse_hash(latest)!=parse_hash(profile):return error('Input settings changed. Refresh and upload again.',409)
                db.execute('INSERT INTO input_file_samples VALUES(?,?,?,?,?,?) ON CONFLICT(retailer_id,input_id) DO UPDATE SET filename=excluded.filename,records=excluded.records,byte_size=excluded.byte_size,settings_hash=excluded.settings_hash',(rid,pid,file.filename,json.dumps(records),len(source),parse_hash(profile)))
                result=sample_public(db.execute('SELECT * FROM input_file_samples WHERE retailer_id=? AND input_id=?',(rid,pid)).fetchone(),profile)
            return jsonify(success=True,sample=result)
        except (ValueError,OSError) as exc:return error(str(exc))

    @app.route('/api/v1/retailers/<rid>/input-files/<pid>/read',methods=['POST'])
    def read_path(rid,pid):
        try:
            with get_db_connection() as db:
                _,profile,_=load_profile(db,rid,pid)
                if archive_state(db,rid)['archived']:return error('Restore before processing.',409)
            files=scoped_files(profile)
            if len(files)!=1:return error('Read From Path needs exactly one matching file. Narrow Filename or use a full file path.')
            source=bounded_read(files[0]);body=request.get_json(silent=True) or {}
            if not isinstance(body,dict):return error('Invalid read request.')
            return app.extensions['batch_launch'](rid,body.get('period',current_week()),files[0].name,source,input_file_id=pid)
        except (ValueError,OSError):return error('Cannot read the input. Check the path inside Codex, Filename, size limit and access permissions.')

    observations={};last_scan={};poll_lock=threading.Lock()
    def poll_once(force=False):
        if not poll_lock.acquire(blocking=False):return
        try:
            with get_db_connection() as db:
                configs=[(r['id'],json.loads(r['payload'])) for r in db.execute('SELECT * FROM retailer_configs') if not archive_state(db,r['id'])['archived']]
            for rid,config in configs:
                for p in config.get('inputFiles',[]):
                    if any(r.get('operation')=='join' for r in config.get('pipeline',[])) and config.get('primaryInputId') and p['id']!=config['primaryInputId']:continue
                    if p['readMode']!='Automatic':continue
                    key=(rid,p['id']);clock=time.monotonic()
                    if not force and clock-last_scan.get(key,-999999)<p['watchInterval']:continue
                    last_scan[key]=clock
                    try:files=scoped_files(p)
                    except (ValueError,OSError) as exc:
                        record_delivery(rid,p['id'],'path:'+hashlib.sha256((p['filePath']+p['filename']).encode()).hexdigest(),'Blocked',str(exc));continue
                    for path in files:
                        signature=None
                        try:
                            stat=path.stat();identity=(*key,str(path));signature=(stat.st_size,stat.st_mtime_ns)
                            if observations.get(identity)!=signature:observations[identity]=signature;continue
                            source=bounded_read(path,expected_signature=signature);period=current_week();digest=hashlib.sha256(source).hexdigest()
                            fingerprint=hashlib.sha256((str(path)+digest).encode()).hexdigest()
                            with get_db_connection() as db:
                                existing=db.execute('SELECT status FROM input_deliveries WHERE retailer_id=? AND input_id=? AND fingerprint=?',(rid,p['id'],fingerprint)).fetchone()
                            if existing and existing['status']=='Queued':continue
                            blocked_key=fingerprint+':'+hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
                            with get_db_connection() as db:
                                if db.execute('SELECT 1 FROM input_deliveries WHERE retailer_id=? AND input_id=? AND fingerprint=?',(rid,p['id'],blocked_key)).fetchone():continue
                            with app.app_context():
                                response,status=app.extensions['batch_launch'](rid,period,path.name,source,input_file_id=p['id'])
                                data=response.get_json()
                            if status==202:record_delivery(rid,p['id'],fingerprint,'Queued','Automatic input accepted.',data['attemptId'])
                            else:record_delivery(rid,p['id'],blocked_key,'Blocked',data.get('error','Preprocessing failed.'))
                        except (ValueError,OSError) as exc:
                            record_delivery(rid,p['id'],'file:'+hashlib.sha256((str(path)+str(signature)).encode()).hexdigest(),'Blocked',str(exc))
        finally:poll_lock.release()
    app.extensions['input_poll_once']=poll_once
    def watch():
        while True:
            time.sleep(2)
            if app.testing:continue
            try:poll_once()
            except Exception:app.logger.warning('Input watcher could not complete this scan.')
    import multiprocessing,os
    if multiprocessing.current_process().name=='MainProcess' and os.getenv('DATAFLOW_WATCH_ENABLED','1')!='0':
        threading.Thread(target=watch,daemon=True).start()

def record_delivery(rid,pid,fingerprint,status,message,job_id=None):
    with get_db_connection() as db:db.execute('INSERT INTO input_deliveries(retailer_id,input_id,fingerprint,status,message,job_id,created_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT DO NOTHING',(rid,pid,fingerprint,status,message[:1000],job_id,now()))
