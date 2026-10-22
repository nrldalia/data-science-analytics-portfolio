from pathlib import Path
root=Path(__file__).resolve().parent.parent/'outputs/V1.14.0'
p=root/'frontend-github/src/RetailerSetup.jsx';s=p.read_text(encoding='utf-8')
s=s.replace("import InputFiles from './InputFiles';","import InputSetup from './InputSetup';\nimport WorkflowRules from './WorkflowRules';")
start=s.index(' useEffect(()=>{\n  if(!config.id');end=s.index(' async function save',start);s=s[:start]+s[end:]
start=s.index("  {view==='inputs'&&config.id&&<InputFiles");end=s.index("\n  {view==='setup'",start)
s=s[:start]+"  {view==='inputs'&&config.id&&<InputSetup retailerId={config.id} primaryInputId={config.primaryInputId} hasLinks={config.pipeline.some(r=>r.operation==='join')} onLegacyUpload={upload} legacySample={sample} onUpdated={async()=>{const d=await api('/retailers');setRetailers(d.retailers);setConfig(d.retailers.find(r=>r.id===config.id)||config);setDirty(false);}}/>}"+s[end:]
start=s.index("  {view==='rules'&&<section");end=s.rindex('\n </div>')
s=s[:start]+"  {view==='rules'&&<WorkflowRules config={config} change={change} catalog={catalog}/>}"+s[end:]
s=s.replace('Sample uploaded. Previews use all sample rows and display up to 25.','Sample uploaded. Use Preview in Rules Configure.')
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/KPIRecords.jsx';s=p.read_text(encoding='utf-8').replace('Configure final Sales, Quantity and Store ID fields and ranges in Client → Input Files.','Add a KPI rule and select final fields and ranges in Client → Rules Configure.').replace('Totals use final rows after all rules.','Totals use final mapped rows after all rules.');p.write_text(s,encoding='utf-8')
print('Updated retailer tabs and single step-through preview.')
