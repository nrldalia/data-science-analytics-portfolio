from pathlib import Path
root=Path('outputs/V1.11.0')
p=root/'frontend-github/src/Client.jsx';s=p.read_text(encoding='utf-8')
s=s.replace(" if(r.pipeline", " if(r.archived)return 'Archived';\n if(r.pipeline",1)
s=s.replace("[notice,setNotice]=useState('');", "[notice,setNotice]=useState(''),[archived,setArchived]=useState(false);")
s=s.replace(' const allBox=useRef(null);', ' const allBox=useRef(null);\n const visible=retailers.filter(r=>!!r.archived===archived);')
s=s.replace('selected.length<retailers.length','selected.length<visible.length').replace('[selected,retailers,editing]','[selected,retailers,editing,archived]')
start=s.index(' if(editing!==undefined)')
s=s[:start]+''' async function archiveAction(){
  const type=archived?'restore':'archive';
  if(!selected.length||!window.confirm(`${archived?'Restore':'Archive'} ${selected.length} retailer(s)? Setup, samples and batch history are retained.`))return;
  setBusy(true);setError('');setNotice('');
  try{const response=await fetch(`${API}/retailers/${type}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids:selected})});const data=await response.json();if(!response.ok||!data.success)throw new Error(data.error||'Action failed.');await refresh();setNotice(`${data.changedIds.length} retailer(s) ${archived?'restored':'archived'}.`);}catch(e){setError(e.message);}finally{setBusy(false);}
 }
'''+s[start:]
s=s.replace('Select Edit to open retailer Setup.','Archive retains setup and history. Restore before editing or processing.')
s=s.replace('<div className="flex gap-2"><button', '<div className="flex gap-2"><button className={button} disabled={busy||!selected.length} onClick={archiveAction}>{archived?\'Restore\':\'Archive\'}{selected.length?` (${selected.length})`:\'\'}</button><button',1)
s=s.replace('{error&&<p role="alert"', '<label className="flex gap-2 text-sm"><input type="checkbox" checked={archived} disabled={busy} onChange={e=>{setArchived(e.target.checked);setSelected([]);}}/>Show Archived Retailers</label>{error&&<p role="alert"',1)
s=s.replace('!retailers.length','!visible.length').replace('retailers.length>0','visible.length>0').replace('selected.length===retailers.length','selected.length===visible.length').replace('retailers.map(r=>','visible.map(r=>')
s=s.replace('disabled={busy} title="Edit retailer setup"','disabled={busy||r.archived} title={r.archived?\'Restore before editing\':\'Edit retailer setup\'}')
s=s.replace('No retailers. Add a retailer to begin setup.','No retailers in this view.')
p.write_text(s,encoding='utf-8')
p=root/'script/preprocessing.py';s=p.read_text(encoding='utf-8')
s=s.replace("        with get_db_connection() as db:row=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(request.form.get('retailerId',''),)).fetchone()", "        rid=request.form.get('retailerId','')\n        with get_db_connection() as db:\n            row=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(rid,)).fetchone()\n            config=json.loads(row['payload']) if row else None\n            if config is not None and archive_state(db,rid)['archived']:config['archived']=True")
s=s.replace("preprocessing_report(json.loads(row['payload']) if row else None,file.read()", "preprocessing_report(config,file.read()")
s=s.replace("            row=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(job['retailer_id'],)).fetchone()", "            row=db.execute('SELECT payload FROM retailer_configs WHERE id=?',(job['retailer_id'],)).fetchone()\n            config=json.loads(row['payload']) if row else None\n            if config is not None and archive_state(db,job['retailer_id'])['archived']:config['archived']=True")
s=s.replace("preprocessing_report(json.loads(row['payload']) if row else None,job['source']", "preprocessing_report(config,job['source']")
p.write_text(s,encoding='utf-8')
