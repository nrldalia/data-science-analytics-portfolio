from pathlib import Path
import shutil,sqlite3,json
base=Path('outputs/V1.6.0');root=Path('outputs/V1.6.A1')
shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist','.venv','*.db','*.db-wal','*.db-shm'),dirs_exist_ok=True)
for rel in ['script/app.py','frontend-github/src/app.jsx','Setup_Windows.bat','Start_V1.6.0.bat']:
 p=root/rel;s=p.read_text(encoding='utf-8').replace('V1.6.0','V1.6.A1').replace("version='1.6.0'","version='1.6.A1'")
 if rel.startswith('Start_'):p.unlink();p=root/'Start_V1.6.A1.bat'
 p.write_text(s,encoding='utf-8')
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name;d=json.loads(p.read_text());d['version']='1.6.1'
 if '' in d.get('packages',{}):d['packages']['']['version']='1.6.1'
 p.write_text(json.dumps(d,indent=2),encoding='utf-8')
p=Path('outputs/V1.3.A1.bat');p.write_text(p.read_text().replace('V1.6.0','V1.6.A1').replace("'1.6.0'","'1.6.A1'"),encoding='utf-8')
if (base/'script/dataflow.db').exists():
 with sqlite3.connect(base/'script/dataflow.db') as a,sqlite3.connect(root/'script/dataflow.db') as b:a.backup(b)
p=root/'frontend-github/src/app.jsx';s=p.read_text(encoding='utf-8')
s=s.replace("import RetailerSetup from './RetailerSetup';","import Client from './Client';")
s=s.replace("useState('Data Streams')","useState('Client')",1)
s=s.replace("              { name: 'Retailer Data Setup', icon: Building2 },\n",'').replace("{ name: 'Clients', icon: Building2 }","{ name: 'Client', icon: Building2 }")
start=s.index("          {activeTab === 'Retailer Data Setup'")
end=s.index('          {/* TAB 2: DATA STREAMS MODULE */}',start)
s=s[:start]+"          {activeTab === 'Client' && <Client />}\n\n"+s[end:]
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/RetailerSetup.jsx';s=p.read_text(encoding='utf-8')
s=s.replace('export default function RetailerSetup() {','export default function RetailerSetup({initialRetailerId=null,onBack}) {')
s=s.replace("if(a.retailers.length){setConfig(a.retailers[0]);loadSample(a.retailers[0].id);}","const selected=a.retailers.find(r=>r.id===initialRetailerId);if(selected){setConfig(selected);loadSample(selected.id);}else if(initialRetailerId){setError('Retailer no longer exists. Return to Client.');}")
s=s.replace('<button disabled={busy||view===\'store\'} className={button} onClick={()=>selectRetailer(\'\')}><Plus size={16}/>New Retailer</button>',"<button disabled={busy} className={button} onClick={()=>{if(!dirty||window.confirm('Discard unsaved setup changes and return to Client?'))onBack?.();}}>Back to Client</button>")
start=s.index('  <div className="flex flex-wrap items-center gap-3"><label')
end=s.index('\n  <div className="flex gap-2 border-b',start)
s=s[:start]+"  <p className=\"text-xs text-slate-400\">Client / Setup · {config.name||'New retailer'} · {dirty?'Unsaved changes':config.id?'Saved configuration':'New configuration'}</p>"+s[end:]
p.write_text(s,encoding='utf-8')
p=root/'script/retailer_setup.py';s=p.read_text(encoding='utf-8')
marker="    @app.route('/api/v1/rule-definitions', methods=['GET','POST'])"
s=s.replace(marker,"""    @app.route('/api/v1/retailers/delete', methods=['POST'])
    def delete_retailers():
        body=request.get_json(silent=True)
        ids=body.get('ids') if isinstance(body,dict) else None
        if not isinstance(ids,list) or not ids or len(ids)>1000 or any(not isinstance(rid,str) or not rid for rid in ids):return error('Select one or more retailers to delete.')
        ids=list(dict.fromkeys(ids));marks=','.join('?' for _ in ids)
        with get_db_connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute(f'SELECT COUNT(*) FROM retailer_configs WHERE id IN ({marks})',ids).fetchone()[0]!=len(ids):return error('A selected retailer no longer exists. Refresh Client.',404)
            if db.execute(f'SELECT id FROM batch_attempts WHERE retailer_id IN ({marks}) LIMIT 1',ids).fetchone():return error('Wait for or cancel running jobs before deleting these retailers.',409)
            db.execute(f'DELETE FROM retailer_samples WHERE retailer_id IN ({marks})',ids)
            db.execute(f'DELETE FROM retailer_configs WHERE id IN ({marks})',ids)
        return jsonify(success=True,deletedIds=ids)

"""+marker)
p.write_text(s,encoding='utf-8')
print('V1.6.A1 prepared')
