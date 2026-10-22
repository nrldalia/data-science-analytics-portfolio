from pathlib import Path
p=Path(__file__).resolve().parent.parent/'outputs/V1.14.0/frontend-github/src/WorkflowRules.jsx'
s=p.read_text(encoding='utf-8')
before=' function mappingAdd(source)'
handler=''' async function exportExample(){setBusy(true);setError('');try{const r=await fetch(`${API}/retailers/${config.id}/example.csv`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pipeline:config.pipeline,inputFileId:primary||undefined,workflow:{columnMapping:config.columnMapping||[],analyticsColumns:config.analyticsColumns||[],primaryInputId:primary}})});if(!r.ok)throw Error((await r.json()).error);const url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download=`${config.key}_final_example.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){setError(e.message);}finally{setBusy(false);}}
'''
s=s.replace(before,handler+before).replace('<span className="text-xs text-slate-400">Showing up to 25 rows', '<button className={button} disabled={busy} onClick={exportExample}>Export Final Example CSV</button><span className="text-xs text-slate-400">Showing up to 25 rows')
p.write_text(s,encoding='utf-8');print('Retained final sample export in the single preview dialog.')
