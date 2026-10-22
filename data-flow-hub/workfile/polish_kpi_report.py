from pathlib import Path
import json
root=Path(__file__).resolve().parent.parent
release=root/'outputs/V1.14.A2/frontend-github'
p=release/'src/KPIRecords.jsx';s=p.read_text(encoding='utf-8')
s=s.replace('.map(r=><tr key={r.id}', '.map(r=>{const rowSummary=reportSummary(r.kpi);return <tr key={r.id}')
s=s.replace('</td></tr>)}</tbody></table>{!filtered.length', '</td></tr>;})}</tbody></table>{!filtered.length')
s=s.replace('reportSummary(r.kpi)', 'rowSummary').replace('const rowSummary=rowSummary;', 'const rowSummary=reportSummary(r.kpi);')
s=s.replace("{r.kpi.review?'Manually checked':'Manual check required'}", "{r.status==='Cancelled Job'?'KPI snapshot — job cancelled':r.kpi.review?'Manually checked':'Manual check required'}")
p.write_text(s,encoding='utf-8')
tests=release/'test';tests.mkdir(exist_ok=True)
(tests/'kpiReportSummary.test.js').write_text((root/'work/check_kpi_report.mjs').read_text(encoding='utf-8').replace("'../outputs/V1.14.A2/frontend-github/src/kpiReportSummary.js'", "'../src/kpiReportSummary.js'"),encoding='utf-8')
p=release/'package.json';d=json.loads(p.read_text(encoding='utf-8'));d['scripts']['test:kpi-report']='node test/kpiReportSummary.test.js';p.write_text(json.dumps(d,indent=2),encoding='utf-8')
print('Added reproducible report summary tests and one summary calculation per row.')
