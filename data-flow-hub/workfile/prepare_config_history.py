from pathlib import Path
import shutil,sqlite3,json
base=Path('outputs/V1.6.A1');root=Path('outputs/V1.7.0')
shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist','.venv','*.db','*.db-wal','*.db-shm'),dirs_exist_ok=True)
for rel in ['script/app.py','frontend-github/src/app.jsx','Setup_Windows.bat','Start_V1.6.A1.bat']:
 p=root/rel;s=p.read_text(encoding='utf-8').replace('V1.6.A1','V1.7.0').replace("version='1.6.A1'","version='1.7.0'")
 if rel.startswith('Start_'):p.unlink();p=root/'Start_V1.7.0.bat'
 p.write_text(s,encoding='utf-8')
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name;d=json.loads(p.read_text());d['version']='1.7.0'
 if '' in d.get('packages',{}):d['packages']['']['version']='1.7.0'
 p.write_text(json.dumps(d,indent=2),encoding='utf-8')
p=Path('outputs/V1.3.A1.bat');p.write_text(p.read_text().replace('V1.6.A1','V1.7.0').replace("'1.6.A1'","'1.7.0'"),encoding='utf-8')
if (base/'script/dataflow.db').exists():
 with sqlite3.connect(base/'script/dataflow.db') as a,sqlite3.connect(root/'script/dataflow.db') as b:a.backup(b)
p=root/'script/retailer_setup.py';s=p.read_text(encoding='utf-8').replace('import copy','from configuration_history import initialize_history, record_version, version_summary\nimport copy',1)
s=s.replace('        initialize_store_sequence(db)','        initialize_store_sequence(db)\n        initialize_history(db)',1)
s=s.replace("            return jsonify(success=True,retailer=body | {'id':rid})","                version=record_version(db,rid,body,'Setup saved')\n            return jsonify(success=True,retailer=body | {'id':rid},configurationVersion=version_summary(version))")
marker="    @app.route('/api/v1/retailers/delete'"
s=s.replace(marker,"""    @app.route('/api/v1/retailers/<rid>/configuration-history')
    def configuration_history(rid):
        with get_db_connection() as db:
            rows=db.execute('SELECT * FROM retailer_configuration_versions WHERE retailer_id=? ORDER BY version DESC',(rid,)).fetchall()
        return jsonify(success=True,versions=[version_summary(row) | {'configuration':json.loads(row['payload'])} for row in rows])

"""+marker)
p.write_text(s,encoding='utf-8')
p=root/'script/batch_jobs.py';s=p.read_text(encoding='utf-8').replace('import io','from configuration_history import record_version, version_summary\nimport io',1)
s=s.replace("        with get_db_connection() as db:\n            retailer=db.execute", "        with get_db_connection() as db:\n            db.execute('BEGIN IMMEDIATE')\n            retailer=db.execute",1)
s=s.replace("            metrics=input_metrics(source,period,config.get('stores',[]),previous,store_field.strip())", "            metrics=input_metrics(source,period,config.get('stores',[]),previous,store_field.strip())\n            metrics['configurationVersion']=version_summary(record_version(db,retailer_id,config,'Configuration captured at launch'))")
s=s.replace("                db.execute('UPDATE retailer_configs SET payload=? WHERE id=?',(json.dumps(updated),job['retailer_id']))", "                db.execute('UPDATE retailer_configs SET payload=? WHERE id=?',(json.dumps(updated),job['retailer_id']))\n                record_version(db,job['retailer_id'],updated,'New stores approved')")
marker="    @app.route('/api/v1/batches/<jid>/reprocess'"
s=s.replace(marker,"""    @app.route('/api/v1/batches/<jid>/configuration')
    def batch_configuration(jid):
        with get_db_connection() as db:
            job=db.execute('SELECT * FROM batch_jobs WHERE id=?',(jid,)).fetchone()
            if not job:return error('Job not found.',404)
            reference=decode(job['metrics'],{}).get('configurationVersion')
            if not reference:return error('Configuration version was not captured for this historical run.',404)
            row=db.execute('SELECT * FROM retailer_configuration_versions WHERE id=? AND retailer_id=?',(reference['id'],job['retailer_id'])).fetchone()
            if not row:return error('Configuration snapshot unavailable.',404)
        return jsonify(success=True,version=version_summary(row),configuration=json.loads(row['payload']))

"""+marker)
p.write_text(s,encoding='utf-8')
print('V1.7.0 prepared')
