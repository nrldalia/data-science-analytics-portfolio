from pathlib import Path
import shutil,sqlite3,json
base=Path('outputs/V1.8.0');root=Path('outputs/V1.9.0')
shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist','.venv','*.db','*.db-wal','*.db-shm'),dirs_exist_ok=True)
for rel in ['script/app.py','frontend-github/src/app.jsx','Setup_Windows.bat','Start_V1.8.0.bat']:
 p=root/rel;s=p.read_text(encoding='utf-8').replace('V1.8.0','V1.9.0').replace("version='1.8.0'","version='1.9.0'")
 if rel.startswith('Start_'):p.unlink();p=root/'Start_V1.9.0.bat'
 p.write_text(s,encoding='utf-8')
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name;d=json.loads(p.read_text());d['version']='1.9.0'
 if '' in d.get('packages',{}):d['packages']['']['version']='1.9.0'
 p.write_text(json.dumps(d,indent=2),encoding='utf-8')
p=Path('outputs/V1.3.A1.bat');p.write_text(p.read_text().replace('V1.8.0','V1.9.0').replace("'1.8.0'","'1.9.0'"),encoding='utf-8')
if (base/'script/dataflow.db').exists():
 with sqlite3.connect(base/'script/dataflow.db') as a,sqlite3.connect(root/'script/dataflow.db') as b:a.backup(b)
p=root/'script/batch_jobs.py';s=p.read_text(encoding='utf-8')
s='from preprocessing import register_preprocessing_routes, preprocessing_report, parse_source, check_configuration\n'+s
s=s.replace('    register_store_review_routes(app,error)','    register_store_review_routes(app,error)\n    register_preprocessing_routes(app,parse_upload,error)')
s=s.replace("def launch(retailer_id,period,filename,source,store_field=''):","def launch(retailer_id,period,filename,source,store_field='',expected_hash=None):")
needle="        with get_db_connection() as db:\n            db.execute('BEGIN IMMEDIATE')\n            retailer=db.execute"
s=s.replace(needle,"""        try:checked_records=parse_source(source,filename,parse_upload)
        except Exception:return jsonify(success=False,error='Preprocessing check failed: input file could not be parsed.',report=preprocessing_report(None,source,filename,period,store_field,parse_upload)),400
"""+needle,1)
s=s.replace("            try:validate_pipeline(pipeline)","""            report=check_configuration(config,checked_records,period,filename,source,store_field)
            if expected_hash and expected_hash!=report['configurationHash']:return jsonify(success=False,error='Setup changed since preprocessing. Run the check again.',report=report),409
            if not report['ready']:return jsonify(success=False,error='Resolve the preprocessing errors before starting.',report=report),400
            try:validate_pipeline(pipeline)""",1)
s=s.replace("            metrics['configurationVersion']=", "            metrics['preprocessing']={k:report[k] for k in ['checkedAt','configurationHash','fileSha256','warnings']}\n            metrics['configurationVersion']=",1)
s=s.replace("request.form.get('storeIdField',''))", "request.form.get('storeIdField',''),request.form.get('expectedConfigurationHash'))",1)
s=s.replace("decode(job['metrics'],{}).get('storeIdField',''))", "decode(job['metrics'],{}).get('storeIdField',''),body.get('expectedConfigurationHash'))",1)
p.write_text(s,encoding='utf-8')
print('V1.9.0 prepared')
