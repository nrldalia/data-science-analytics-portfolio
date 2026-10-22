from pathlib import Path
import shutil,sqlite3,json
base=Path('outputs/V1.3.A2');root=Path('outputs/V1.4.0')
shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist','.venv','*.db','*.db-wal','*.db-shm'),dirs_exist_ok=True)
for rel in ['script/app.py','frontend-github/src/app.jsx','Setup_Windows.bat']:
 p=root/rel;s=p.read_text(encoding='utf-8').replace('V1.3.A2','V1.4.0').replace("version='1.3.A2'","version='1.4.0'");p.write_text(s,encoding='utf-8')
p=root/'Start_V1.3.A2.bat';(root/'Start_V1.4.0.bat').write_text(p.read_text().replace('V1.3.A2','V1.4.0'));p.unlink()
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name;d=json.loads(p.read_text());d['version']='1.4.0'
 if '' in d.get('packages',{}):d['packages']['']['version']='1.4.0'
 p.write_text(json.dumps(d,indent=2))
p=Path('outputs/V1.3.A1.bat');p.write_text(p.read_text().replace('V1.3.A2','V1.4.0').replace("'1.3.A2'","'1.4.0'"))
if (base/'script/dataflow.db').exists():
 with sqlite3.connect(base/'script/dataflow.db') as a,sqlite3.connect(root/'script/dataflow.db') as b:a.backup(b)
p=root/'frontend-github/src/RetailerSetup.jsx';s=p.read_text(encoding='utf-8')
s=s.replace("const [component,setComponent]=useState(''),[selectedRule,setSelectedRule]=useState(''),[conditionDraft,setConditionDraft]=useState(null),[editRule,setEditRule]=useState(null);", "const [ruleDraft,setRuleDraft]=useState(null),[draftDefinition,setDraftDefinition]=useState(''),[conditionDraft,setConditionDraft]=useState(null),[conditionEditing,setConditionEditing]=useState(false),[editRule,setEditRule]=useState(null);")
a=s.index(' function addRule(');b=s.index(' function updateRule',a)
s=s[:a]+''' function openComponent(category) {
  setDraftDefinition('');setRuleDraft({id:crypto.randomUUID(),category,operation:'',name:'',field:fields[0]||'',description:'',dateFormat:'%d/%m/%Y'});
 }
 function chooseDefinition(id) {
  setDraftDefinition(id);
  if(id==='new'){setRuleDraft(r=>({...r,name:'',operation:Object.keys(operations[r.category])[0]}));return;}
  const def=catalog.find(r=>r.id===id);
  setRuleDraft(r=>def?{...r,...def.defaults,name:def.name,operation:def.operation}:{...r,name:'',operation:''});
 }
 async function saveRuleDraft() {
  if(!ruleDraft?.description.trim()||!ruleDraft.name.trim()||!ruleDraft.operation)return;
  setError('');
  if(draftDefinition==='new') {
   setBusy(true);
   try {const {category,operation,name,description}=ruleDraft;const data=await api('/rule-definitions',json({category,operation,name,defaults:{description}}));setCatalog(list=>[...list,data.rule]);}
   catch(e){setError(e.message);return;}finally{setBusy(false);}
  }
  change({pipeline:[...pipeline,{...ruleDraft,description:ruleDraft.description.trim()}]});setRuleDraft(null);
 }
'''+s[b:]
a=s.index(' async function createRule()');b=s.index(' async function downloadExample()',a);s=s[:a]+s[b:]
s=s.replace(",[newRule,setNewRule]=useState(null)", '')
s=s.replace("setNewRule(null);loadSample(id);", "setRuleDraft(null);setEditRule(null);setConditionDraft(null);loadSample(id);")
a=s.index("  {view==='rules'&&<section");b=s.index('  <section className={card}><div className="flex flex-wrap justify-between',a)
s=s[:a]+'''  {view==='rules'&&<section className={card}><h3 className="text-xs font-medium text-slate-400">Mandatory components</h3><div className="flex flex-wrap gap-3">{categories.map(category=><button key={category} className={button} onClick={()=>openComponent(category)}>{category}</button>)}</div></section>}
'''+s[b:]
s=s.replace("Field: {rule.field||'Choose in Edit'}", "Field: {rule.field||'Choose in Condition'}")
a=s.index('     <td className="p-3 min-w-72">');b=s.index('     <td className="p-3"><span',a)
s=s[:a]+'''     <td className="p-3 min-w-64"><p className="whitespace-pre-wrap text-slate-200">{rule.description||'Add a description using Edit.'}</p><details className="mt-3"><summary className="cursor-pointer text-cyan-300">Preview this rule</summary><StepPreview step={preview?.steps.find(s=>s.id===rule.id)}/></details></td>
'''+s[b:]
s=s.replace("setConditionDraft({ruleId:rule.id,...(rule.condition||{operator:'all',field:rule.field||'',value:'',value2:''})})", "{setConditionDraft({rule:{...rule},...(rule.condition||{operator:'all',field:rule.field||'',value:'',value2:''})});setConditionEditing(false);}")
s=s.replace('Choose a component and add a rule to create the first row.', 'Choose a component, describe a rule and Save to add a row.')
a=s.index('   {conditionDraft&&');b=s.index('   <section className={card+\' border-cyan-500/40\'}>',a)
s=s[:a]+'''   {ruleDraft&&<div className="fixed inset-0 z-50 bg-slate-950/80 flex items-center justify-center p-4"><section role="dialog" aria-modal="true" aria-label={`${ruleDraft.category} Rules`} className={card+' w-full max-w-xl max-h-[90vh] overflow-y-auto'}><h3 className="font-semibold text-lg">{ruleDraft.category} Rules</h3><Field label="Rule"><select aria-label="Component rule" className={input} value={draftDefinition} onChange={e=>chooseDefinition(e.target.value)}><option value="">Choose a rule…</option>{catalog.filter(r=>r.category===ruleDraft.category).map(r=><option key={r.id} value={r.id}>{r.name}</option>)}<option value="new">＋ Add New Rules…</option></select></Field>{draftDefinition==='new'&&<><Field label="Rule name"><input className={input} maxLength={120} value={ruleDraft.name} onChange={e=>setRuleDraft(r=>({...r,name:e.target.value}))}/></Field><Field label="Operation"><select className={input} value={ruleDraft.operation} onChange={e=>setRuleDraft(r=>({...r,operation:e.target.value}))}>{Object.entries(operations[ruleDraft.category]).map(([key,name])=><option key={key} value={key}>{name}</option>)}</select></Field></>}<Field label="Description"><textarea aria-label="Component description" className={input} rows={4} maxLength={500} placeholder="Explain why this rule is used…" value={ruleDraft.description} onChange={e=>setRuleDraft(r=>({...r,description:e.target.value}))}/></Field><ExecutionMessages/><p className="text-xs text-slate-400">Save adds this rule to the table. Use Condition to set its field and processing settings, then Save Configuration.</p><div className="flex gap-2 justify-end"><button className={primary} disabled={busy||!ruleDraft.description.trim()||!ruleDraft.name.trim()||!ruleDraft.operation} onClick={saveRuleDraft}>Save</button><button className={button} disabled={busy} onClick={()=>setRuleDraft(null)}>Cancel</button></div></section></div>}
   {conditionDraft&&<div className="fixed inset-0 z-50 bg-slate-950/80 flex items-center justify-center p-4"><section role="dialog" aria-modal="true" aria-label="Rule Condition" className={card+' w-full max-w-xl max-h-[90vh] overflow-y-auto'}><div className="flex justify-between gap-3"><h3 className="font-semibold text-lg">Condition · {conditionDraft.rule.name}</h3>{!conditionEditing&&<button className={button} onClick={()=>setConditionEditing(true)}>Edit Condition</button>}</div>{conditionEditing?<><h4 className="text-sm text-cyan-300">Rule settings</h4><RuleSettings rule={conditionDraft.rule} fields={fields} onChange={rule=>setConditionDraft(c=>({...c,rule}))}/><h4 className="text-sm text-cyan-300">Apply to rows</h4><Field label="Condition type"><select className={input} value={conditionDraft.operator} onChange={e=>setConditionDraft(c=>({...c,operator:e.target.value}))}>{Object.entries(conditionOperators).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></Field>{conditionDraft.operator!=='all'&&<><Field label="Condition field"><input className={input} list="condition-fields" value={conditionDraft.field} onChange={e=>setConditionDraft(c=>({...c,field:e.target.value}))}/><datalist id="condition-fields">{fields.map(f=><option key={f} value={f}/>)}</datalist></Field>{!['blank','notblank'].includes(conditionDraft.operator)&&<Field label="Condition value"><input className={input} value={conditionDraft.value||''} onChange={e=>setConditionDraft(c=>({...c,value:e.target.value}))}/></Field>}{conditionDraft.operator==='between'&&<Field label="Upper value"><input className={input} value={conditionDraft.value2||''} onChange={e=>setConditionDraft(c=>({...c,value2:e.target.value}))}/></Field>}</>}</>:<div className="space-y-3 text-sm text-slate-300"><p>Field: {conditionDraft.rule.field||'Not configured'}</p><p>Operation: {operations[conditionDraft.rule.category][conditionDraft.rule.operation]}</p>{['target','find','replacement','dateFormat','min','max','pattern'].filter(k=>conditionDraft.rule[k]!=null&&conditionDraft.rule[k]!==''&&(k!=='dateFormat'||conditionDraft.rule.operation==='date')).map(k=><p key={k}>{k}: {conditionDraft.rule[k]}</p>)}<p>Applies to: {conditionDraft.operator==='all'?'All rows':`${conditionDraft.field} · ${conditionOperators[conditionDraft.operator]} ${conditionDraft.value||''}${conditionDraft.operator==='between'?' and '+conditionDraft.value2:''}`}</p></div>}<div className="flex justify-end gap-2">{conditionEditing&&<button className={primary} disabled={!conditionDraft.rule.field.trim()||(conditionDraft.operator!=='all'&&(!conditionDraft.field.trim()||(!['blank','notblank'].includes(conditionDraft.operator)&&!conditionDraft.value?.trim())||(conditionDraft.operator==='between'&&!conditionDraft.value2?.trim())))} onClick={()=>{const {rule,...condition}=conditionDraft;updateRule({...rule,condition:condition.operator==='all'?null:condition});setConditionDraft(null);}}>Save Condition</button>}<button className={button} onClick={()=>setConditionDraft(null)}>{conditionEditing?'Cancel':'Close'}</button></div></section></div>}
   {editRule&&<div className="fixed inset-0 z-50 bg-slate-950/80 flex items-center justify-center p-4"><section role="dialog" aria-modal="true" aria-label="Edit Description" className={card+' w-full max-w-xl max-h-[90vh] overflow-y-auto'}><h3 className="font-semibold">{editRule.category} · {editRule.name}</h3><Field label="Description"><textarea aria-label="Edit component description" className={input} rows={4} maxLength={500} value={editRule.description||''} onChange={e=>setEditRule(r=>({...r,description:e.target.value}))}/></Field><ExecutionMessages/><div className="flex justify-end gap-2"><button className={primary} disabled={!editRule.description?.trim()} onClick={()=>{updateRule({...editRule,description:editRule.description.trim()});setEditRule(null);}}>Save</button><button className={button} onClick={()=>setEditRule(null)}>Cancel</button></div></section></div>}
'''+s[b:]
s=s.replace('export default function RetailerSetup()', '''function ExecutionMessages() {
 return <div className="space-y-3"><Field label="Error 909"><input aria-label="Error 909" readOnly className={input+' text-emerald-300'} value="Successful at Execution"/></Field><Field label="Error 908"><input aria-label="Error 908" readOnly className={input+' text-rose-300'} value="Failure at Execution"/></Field></div>;
}
export default function RetailerSetup()''')
p.write_text(s,encoding='utf-8')
print('V1.4.0 component popups prepared')
