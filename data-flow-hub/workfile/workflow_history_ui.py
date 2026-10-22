from pathlib import Path
root=Path(__file__).resolve().parent.parent/'outputs/V1.14.0'
p=root/'frontend-github/src/ConfigurationHistory.jsx';s=p.read_text(encoding='utf-8')
s=s.replace('<h4 className="font-semibold">Ordered Rules', '<h4 className="font-semibold">Output Configuration</h4><p className="text-xs text-slate-400">Primary input: {c.inputFiles?.find(p=>p.id===c.primaryInputId)?.filename||\'Not selected\'} · Analytics columns: {c.analyticsColumns?.join(\', \')||\'None\'}</p><pre className="text-xs whitespace-pre-wrap">{JSON.stringify(c.columnMapping||[],null,2)}</pre><h4 className="font-semibold">Ordered Rules')
s=s.replace('<td className="p-2">{p.filename}</td>', '<td className="p-2">{p.filename}{p.isZipFolder&&<p className="text-slate-400">ZIP: {p.zipFolderName||\'Legacy archive\'}</p>}</td>')
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/WorkflowRules.jsx';s=p.read_text(encoding='utf-8')
s=s.replace('validation findings at this step.</p>}', 'validation findings at this step.</p>}{step.issues.length>0&&<ul className="text-xs text-amber-300 space-y-1">{step.issues.slice(0,100).map((issue,i)=><li key={i}>Row {issue.row} · {issue.field} · {issue.issue}</li>)}</ul>}')
p.write_text(s,encoding='utf-8')
print('Added output configuration history and step validation details.')
