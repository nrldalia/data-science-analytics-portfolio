from pathlib import Path
import shutil,re,json
root=Path('outputs/DataFlow_V1.1.0')
src=next(Path('work/baseline').rglob('app.py')).parent.parent
shutil.copytree(src,root,ignore=shutil.ignore_patterns('node_modules','.venv','__pycache__'),dirs_exist_ok=True)
p=root/'script/app.py';s=p.read_text(encoding='utf-8-sig')
s=s.replace('from ai_assistant import suggest','')
s=s.replace("version='1.0.0-improved'","version='1.1.0'")
s=s.replace('records[:5]','records[:25]').replace('output[:5]','output[:25]').replace("json.loads(r['output'])[:5]","json.loads(r['output'])[:25]")
s=s.replace(" body=request.get_json(silent=True) or {}\n if not body.get('consent')", " if os.getenv('DATAFLOW_AI_ENABLED','').lower() != 'true': return error('Analysis is dormant.',403)\n from ai_assistant import suggest\n body=request.get_json(silent=True) or {}\n if not body.get('consent')")
extra='''
def cleaning_log(rid):
 with get_db_connection() as c:
  run=c.execute('SELECT * FROM processing_runs WHERE id=?',(rid,)).fetchone()
  ev=c.execute('SELECT trace FROM run_evidence WHERE run_id=?',(rid,)).fetchone()
 if not run: return None,[]
 rows=[{'row':t['row'],'field':t['field'],'status':'Changed','before':t['before'],'after':t['after'],'action':t['action']} for t in json.loads(ev['trace'] if ev else '[]')]
 output=json.loads(run['output'])
 rows += [{'row':i['row'],'field':i['field'],'status':'Review','before':output[i['row']-1].get(i['field'],''),'after':output[i['row']-1].get(i['field'],''),'action':i['issue']} for i in json.loads(run['issues'])]
 return run,sorted(rows,key=lambda r:r['row'])
@app.route('/api/v1/runs/<rid>/log')
def log_export(rid):
 import csv
 run,rows=cleaning_log(rid)
 if run is None: return error('Run not found.',404)
 b=io.StringIO();writer=csv.DictWriter(b,fieldnames=['row','field','status','before','after','action']);writer.writeheader();writer.writerows(rows)
 return send_file(io.BytesIO(b.getvalue().encode('utf-8-sig')),mimetype='text/csv',as_attachment=True,download_name=rid+'_cleaning_log.csv')
@app.route('/api/v1/runs/<rid>/print')
def print_log(rid):
 from html import escape
 run,rows=cleaning_log(rid)
 if run is None: return error('Run not found.',404)
 body=''.join('<tr>'+''.join('<td>'+escape(str(r[k]))+'</td>' for k in ['row','field','status','before','after','action'])+'</tr>' for r in rows)
 return '<!doctype html><html><head><title>Cleaning log</title><style>body{font:12px Arial}table{border-collapse:collapse;width:100%}td,th{border:1px solid #aaa;padding:6px;overflow-wrap:anywhere}thead{display:table-header-group}@media print{button{display:none}}</style></head><body><button onclick="window.print()">Print / Save as PDF</button><h1>DataFlow V1.1.0 cleaning log</h1><p>'+escape(run['filename'])+' | '+escape(rid)+' | '+str(len(rows))+' entries</p><table><thead><tr><th>Row</th><th>Field</th><th>Status</th><th>Before</th><th>After</th><th>Action / detection</th></tr></thead><tbody>'+body+'</tbody></table></body></html>'
'''
s=s.replace("if __name__=='__main__':",extra+"\nif __name__=='__main__':")
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/app.jsx';s=p.read_text(encoding='utf-8-sig')
s=s.replace('v1.0.0','V1.1.0').replace('AI Insights','Processing Insights').replace('2. AI Processing Engine','2. Automation & Parsing').replace('Applies deterministic Pandas/Python rules to every row. Optional Gemini assistance explains issues for operator review.','Applies deterministic parsing, cleaning and detection rules to every row.')
s=re.sub(r'\s*\{ title: "AI assistance"[^\n]*','',s)
s=re.sub(r'<div className="space-y-2">\s*<label[^>]*>AI Model Pipeline</label>.*?</div>','',s,flags=re.S)
a=s.index('                <details><summary>Unresolved issues');b=s.index('\n              </div>}',a);s=s[:a]+s[b:]
a=s.index('                  <div className="grid grid-cols-2 gap-4">',s.index('MODAL 3:'));b=s.index('\n                </>',a)
s=s[:a]+'''                  <CleaningLog result={cleanResult} />
                  <DataPreview title="Original data (up to 25 rows)" rows={cleanResult.rawSample} />
                  <DataPreview title="Cleaned data (up to 25 rows)" rows={cleanResult.cleanedSample} />'''+s[b:]
s += '''
function DataPreview({title,rows=[]}) {
 const cols=[...new Set(rows.flatMap(r=>Object.keys(r)))];
 return <section><h3 className="font-bold mb-2">{title}</h3><div className="overflow-auto max-h-80"><table className="w-full text-xs text-left"><thead><tr>{cols.map(c=><th className="p-2 border border-slate-700" key={c}>{c}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i}>{cols.map(c=><td className="p-2 border border-slate-700" key={c}>{String(r[c]??'')}</td>)}</tr>)}</tbody></table></div></section>;
}
function CleaningLog({result}) {
 const [page,setPage]=useState(0);
 useEffect(()=>setPage(0),[result.runId]);
 const rows=[...(result.transformationTrace||[]).map(t=>({...t,status:'Changed'})),...(result.issues||[]).map(i=>({...i,status:'Review',action:i.issue}))].sort((a,b)=>a.row-b.row);
 const pages=Math.max(1,Math.ceil(rows.length/25));
 return <section className="space-y-3"><h3 className="font-bold">Cleaning log</h3><div className="flex gap-4"><a className="text-cyan-300 underline" href={`${API}/runs/${result.runId}/log`}>Export full log CSV</a><a className="text-cyan-300 underline" target="_blank" rel="noreferrer" href={`${API}/runs/${result.runId}/print`}>Print full log</a></div><div className="overflow-auto"><table className="w-full text-xs text-left"><thead><tr>{['Row','Field','Status','Before','After','Action / detection'].map(c=><th key={c} className="p-2 border border-slate-700">{c}</th>)}</tr></thead><tbody>{rows.slice(page*25,page*25+25).map((r,i)=><tr key={i}>{[r.row,r.field,r.status,r.before??'',r.after??'',r.action].map((v,j)=><td key={j} className="p-2 border border-slate-700">{String(v)}</td>)}</tr>)}</tbody></table>{!rows.length&&<p className="p-3">No changes or issues detected.</p>}</div><div className="flex items-center gap-4"><button disabled={page===0} onClick={()=>setPage(p=>p-1)} className="disabled:opacity-40">Previous</button><span>Entries {rows.length?page*25+1:0}–{Math.min(rows.length,page*25+25)} of {rows.length} · 25 per page</span><button disabled={page>=pages-1} onClick={()=>setPage(p=>p+1)} className="disabled:opacity-40">Next</button></div></section>;
}
'''
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/package.json';data=json.loads(p.read_text());data['version']='1.1.0';p.write_text(json.dumps(data,indent=2))
(root/'CHANGELOG_V1.1.0.md').write_text('V1.1.0: 25-entry cleaning log, full CSV and print log, table previews, dormant backend analysis. Built locally from improved v1.0. Existing database preserved.\n')
print(root.resolve())
