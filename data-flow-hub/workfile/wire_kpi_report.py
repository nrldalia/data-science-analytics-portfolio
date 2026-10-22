from pathlib import Path
p=Path(__file__).resolve().parent.parent/'outputs/V1.14.A2/frontend-github/src/KPIRecords.jsx'
s=p.read_text(encoding='utf-8')
s="import {reportSummary} from './kpiReportSummary.js';\n"+s
s=s.replace(" const k=chosen?.kpi;"," const k=chosen?.kpi;\n const summary=reportSummary(k);")
s=s.replace('Store % shows the mean store change; every individual store is checked.','Worst Store % shows the largest absolute individual store change, retaining its increase/decrease sign. Flagged counts include stores with unavailable percentages; every individual store is checked.')
s=s.replace("'Store %','Retailer %','Count %','filename'","'Worst Store %','Retailer %','Count %','Review Reason','filename'")
old="<td className={`p-3 ${r.kpi?.stores.some(s=>s.flagged)?'text-amber-300':''}`}>{percent(r.kpi?.storePercent)}</td>"
new="""<td className={`p-3 ${reportSummary(r.kpi).flaggedStores?'text-amber-300':''}`}><span className="font-medium">{percent(reportSummary(r.kpi).worstStore?.percent)}</span>{r.kpi&&<><p className="mt-1 text-slate-400">{reportSummary(r.kpi).worstStore?`Store ${reportSummary(r.kpi).worstStore.storeId}`:'No comparable store percentage'}</p><p className="mt-1">{reportSummary(r.kpi).flaggedStores} / {reportSummary(r.kpi).totalStores} stores flagged</p>{reportSummary(r.kpi).unavailableStores>0&&<p className="mt-1 text-amber-300">{reportSummary(r.kpi).unavailableStores} store % unavailable</p>}</>}</td>"""
assert old in s;s=s.replace(old,new)
needle='<td className="p-3 min-w-52">{r.filename}'
new="""<td className="p-3 min-w-40">{reportSummary(r.kpi).reasons.length?<><div className="flex flex-wrap gap-1">{reportSummary(r.kpi).reasons.map(reason=><span key={reason} className="rounded border border-amber-700 px-2 py-1 text-amber-300">{reason}</span>)}</div><p className="mt-2 text-slate-400">{r.kpi.review?'Manually checked':'Manual check required'}</p></>:<span className="text-slate-400">{r.kpi?'None — within range':'Not captured'}</span>}</td><td className="p-3 min-w-52">{r.filename}"""
assert needle in s;s=s.replace(needle,new)
needle='<p className="text-sm">Allowed ranges:'
new="""<div className="rounded border border-slate-600 p-3 space-y-2"><p className="text-sm">Worst store change: <strong>{percent(summary.worstStore?.percent)}</strong>{summary.worstStore?` · Store ${summary.worstStore.storeId}`:''} · {summary.flaggedStores} / {summary.totalStores} stores flagged{summary.unavailableStores?` · ${summary.unavailableStores} store % unavailable`:''}</p><p className={summary.reasons.length?'text-sm text-amber-300':'text-sm text-emerald-300'}>Review reason: {summary.reasons.join(' · ')||'None — within range'}</p></div><p className="text-sm">Allowed ranges:"""
assert needle in s;s=s.replace(needle,new)
p.write_text(s,encoding='utf-8')
print('Added worst-store display, flagged counts and saved-result review reasons.')
