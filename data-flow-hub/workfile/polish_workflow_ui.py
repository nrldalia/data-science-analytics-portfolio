from pathlib import Path
root=Path(__file__).resolve().parent.parent/'outputs/V1.14.0'
p=root/'frontend-github/src/WorkflowRules.jsx';s=p.read_text(encoding='utf-8')
s=s.replace('config,change,catalog})','config,change,catalog,legacySample})')
s=s.replace("let current=[...(datasets[primary]||[])],linked=false","let current=[...(datasets[primary]||legacySample?.columns||[])],linked=false")
s=s.replace('busy||!config.id||!primary','busy||!config.id||(profiles.length>0&&!primary)')
s=s.replace('setEditing(true);setDescriptionOnly','setCustom(false);setEditing(true);setDescriptionOnly')
s=s.replace("{select('Primary Input / Preview Sample',primary", "{profiles.length>0&&select('Primary Input / Preview Sample',primary")
start=s.index(" {!descriptionOnly&&!['join','kpi']")
end=s.index('\n <label className="block text-sm">Description',start)
s=s[:start]+''' {error&&<p role="alert" className="text-rose-300">{error}</p>}
 {!descriptionOnly&&!['join','kpi'].includes(draft.operation)&&select('Rule Reference',custom?'new':[...catalog,...extraCatalog].find(c=>c.name===draft.name&&c.category===draft.category)?.id||'',id=>{if(id==='new'){setCustom(true);update({name:'',operation:draft.category==='Cleaning'?'trim':draft.category==='Transformation'?'numeric':'required',description:''});return;}setCustom(false);const def=[...catalog,...extraCatalog].find(c=>c.id===id);if(def)update({...def.defaults,operation:def.operation,name:def.name,field:draft.field||fields[0]||'',description:def.example||'Example: Prepare values for processing.'});},[...[...catalog,...extraCatalog].filter(c=>c.category===draft.category).map(c=>({value:c.id,label:c.name})),{value:'new',label:'＋ Add New Rules'}])}
 {custom&&<><label className="text-sm block">Rule Name<input className={input} maxLength={120} value={draft.name} onChange={e=>update({name:e.target.value})}/></label>{select('Operation',draft.operation,v=>update({operation:v}),draft.category==='Cleaning'?['trim','uppercase','lowercase','replace']:draft.category==='Transformation'?['numeric','date','rename']:['required','range','pattern','unique'])}</>}
'''+s[end:]
s=s.replace("draft.leftInputId==='current'?joined:colsFor(draft.leftInputId)","draft.leftInputId==='current'?prior.current:prior.datasets[draft.leftInputId]||[]")
s=s.replace('colsFor(draft.rightInputId))','prior.datasets[draft.rightInputId]||[]))')
p.write_text(s,encoding='utf-8')
p=root/'frontend-github/src/RetailerSetup.jsx';s=p.read_text(encoding='utf-8').replace('config={config} change={change} catalog={catalog}','config={config} change={change} catalog={catalog} legacySample={sample}');p.write_text(s,encoding='utf-8')
p=root/'script/retailer_setup.py';s=p.read_text(encoding='utf-8').replace('if input_file_id and settings is not None:','if settings is not None:').replace('return walkthrough(sample_state(db,rid,config,input_file_id),config)',"if input_file_id:state=sample_state(db,rid,config,input_file_id)\n                else:\n                    legacy=db.execute('SELECT records FROM retailer_samples WHERE retailer_id=?',(rid,)).fetchone()\n                    if not legacy:raise ValueError('Upload a sample in Input Files first.')\n                    state={'datasets':{},'primary':None,'current':json.loads(legacy['records']),'linked':False}\n                return walkthrough(state,config)");p.write_text(s,encoding='utf-8')
print('Preserved custom rules, sequenced field choices and legacy sample walkthroughs.')
