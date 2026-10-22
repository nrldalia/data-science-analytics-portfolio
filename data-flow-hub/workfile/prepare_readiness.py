from release_tools import clone
root=clone('V1.11.0','V1.11.A1','1.11.1')
p=root/'script/retailer_setup.py';s=p.read_text(encoding='utf-8')
s=s.replace("            return jsonify(success=True,retailers=rows)","            from processing_readiness import readiness\n            with get_db_connection() as db:\n                for row in rows:row['processingReadiness']=readiness(db,row['id'],row)\n            return jsonify(success=True,retailers=rows)",1)
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/Client.jsx';s=p.read_text(encoding='utf-8');a=s.index('function setupStatus');b=s.index('export default',a);s=s[:a]+"function setupStatus(r){return r.processingReadiness?.status||'Not checked';}\n"+s[b:]
s=s.replace("setupStatus(r)==='Ready'", "setupStatus(r)==='Ready for preprocessing'")
s=s.replace('title="Ready requires retailer details, at least one store and executable rules in all three components."', 'title="Readiness uses saved configuration and sample schema. Check the actual uploaded batch before starting."')
s=s.replace('{setupStatus(r)}</span>', '''{setupStatus(r)}</span>{r.processingReadiness&&<details className="mt-2 text-xs text-slate-400 max-w-md"><summary className="cursor-pointer text-cyan-300">Readiness Details</summary><p className="mt-2">{r.processingReadiness.note}</p><ul className="space-y-1 mt-2">{r.processingReadiness.issues.map((issue,i)=><li className="text-rose-300" key={i}>{issue.sequence?`Rule ${issue.sequence}: `:''}{issue.message}</li>)}{r.processingReadiness.warnings.map((warning,i)=><li className="text-amber-300" key={i}>{warning}</li>)}</ul></details>}''')
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/BatchLogs.jsx';s=p.read_text(encoding='utf-8').replace('{r.name} · {r.key}</option>',"{r.name} · {r.key} · {r.processingReadiness?.status||'Not checked'}</option>");p.write_text(s,encoding='utf-8')
print('V1.11.A1 prepared')
