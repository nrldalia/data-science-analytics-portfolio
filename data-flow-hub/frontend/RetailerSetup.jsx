import InputSetup from './InputSetup';
import WorkflowRules from './WorkflowRules';
import ConfigurationHistory from './ConfigurationHistory';
import React, {useEffect, useRef, useState} from 'react';
import {ArrowDown, ArrowUp, Plus, Save, Trash2, Upload, SlidersHorizontal, Building2, Pencil} from 'lucide-react';

const API=import.meta.env.VITE_API_URL || '/api/v1';
const categories=['Cleaning','Transformation','Validation'];
const empty=()=>({name:'',key:'',serviceType:'SM',senderEmail:'',retailerEmail:'',stores:[],pipeline:[],sectionOrder:[...categories]});
const input='w-full rounded-lg border border-slate-700 bg-slate-950 p-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-400';
const button='inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed';
const primary=button+' bg-cyan-500 text-slate-950 font-semibold hover:bg-cyan-400 border-cyan-500';
const card='rounded-xl border border-slate-700 bg-[var(--panel-background)] p-5 space-y-4';
const conditionOperators={all:'All rows',eq:'Equal to',ne:'Not equal to',gt:'Greater than',ge:'Greater than or equal to',lt:'Less than',le:'Less than or equal to',between:'Between (inclusive)',contains:'Text contains',starts:'Text begins with',ends:'Text ends with',blank:'Blank',notblank:'Not blank'};
const operations={Cleaning:{trim:'Trim whitespace',uppercase:'Uppercase text',lowercase:'Lowercase text',replace:'Replace text'},Transformation:{numeric:'Convert to number',date:'Standardise date',rename:'Rename column'},Validation:{required:'Required value',range:'Numeric range',pattern:'Text pattern',unique:'Unique values'}};
async function api(path,options={}) {
 const response=await fetch(`${API}${path}`,options);
 const data=await response.json();
 if(!response.ok || !data.success) throw new Error(data.error || 'Request failed.');
 return data;
}
const json=body=>({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
function Field({label,children}) {return <label className="block space-y-1.5 text-sm text-slate-300"><span>{label}</span>{children}</label>;}
function Rows({title,rows=[]}) {
 const fields=[...new Set(rows.flatMap(r=>Object.keys(r)))];
 return <div className="space-y-2 min-w-0"><h4 className="font-medium text-sm text-slate-200">{title}</h4><div className="overflow-auto max-h-80 rounded-lg border border-slate-700"><table className="w-full text-left text-xs"><thead className="bg-slate-900 sticky top-0"><tr><th className="p-2">#</th>{fields.map(f=><th className="p-2 whitespace-nowrap" key={f}>{f}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i} className="border-t border-slate-700"><td className="p-2 text-slate-500">{i+1}</td>{fields.map(f=><td key={f} className="p-2 whitespace-pre-wrap min-w-24">{String(r[f]??'')}</td>)}</tr>)}</tbody></table>{!rows.length&&<p className="p-3 text-sm text-slate-400">No sample rows.</p>}</div></div>;
}
function Issues({issues=[]}) {
 return issues.length ? <div className="overflow-auto max-h-48"><table className="w-full text-xs text-left"><thead><tr><th className="p-2">Row</th><th className="p-2">Field</th><th className="p-2">Detection</th></tr></thead><tbody>{issues.slice(0,100).map((i,n)=><tr key={n} className="border-t border-slate-700 text-amber-300"><td className="p-2">{i.row}</td><td className="p-2">{i.field}</td><td className="p-2">{i.issue}</td></tr>)}</tbody></table>{issues.length>100&&<p className="text-xs">Showing the first 100 of {issues.length} detections.</p>}</div> : <p className="text-xs text-emerald-300">No issues detected by these rules.</p>;
}
function StepPreview({step}) {
 if(!step) return <p className="text-sm text-slate-400">Upload a sample and complete the rule settings to see this preview.</p>;
 return <div className="space-y-3"><div className="grid grid-cols-1 xl:grid-cols-2 gap-3"><Rows title="Before" rows={step.before}/><Rows title="After" rows={step.after}/></div><Issues issues={step.issues}/></div>;
}
function RuleSettings({rule,onChange,fields}) {
 const update=(key,value)=>onChange({...rule,[key]:value});
 return <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
  <Field label="Field"><input aria-label={`Field for ${rule.name}`} list={`fields-${rule.id}`} className={input} value={rule.field||''} onChange={e=>update('field',e.target.value)}/><datalist id={`fields-${rule.id}`}>{fields.map(f=><option key={f} value={f}/>)}</datalist></Field>
  {rule.operation==='rename'&&<Field label="New column name"><input className={input} value={rule.target||''} onChange={e=>update('target',e.target.value)}/></Field>}
  {rule.operation==='replace'&&<><Field label="Find text"><input className={input} value={rule.find||''} onChange={e=>update('find',e.target.value)}/></Field><Field label="Replace with"><input className={input} value={rule.replacement||''} onChange={e=>update('replacement',e.target.value)}/></Field></>}
  {rule.operation==='date'&&<Field label="Input date format"><input className={input} value={rule.dateFormat||''} placeholder="%d/%m/%Y" onChange={e=>update('dateFormat',e.target.value)}/><span className="text-xs text-slate-400">Example: %d/%m/%Y converts 07/10/2026 to 2026-10-07.</span></Field>}
  {rule.operation==='range'&&<><Field label="Minimum"><input type="number" step="any" className={input} value={rule.min??''} onChange={e=>update('min',e.target.value)}/></Field><Field label="Maximum"><input type="number" step="any" className={input} value={rule.max??''} onChange={e=>update('max',e.target.value)}/></Field></>}
  {rule.operation==='pattern'&&<Field label="Text pattern"><input className={input} value={rule.pattern||''} placeholder="SKU-*" onChange={e=>update('pattern',e.target.value)}/><span className="text-xs text-slate-400">* matches any text; ? matches one character. All other characters match literally.</span></Field>}
 </div>;
}
function ExecutionMessages() {
 return <div className="space-y-3"><Field label="Error 909"><input aria-label="Error 909" readOnly className={input+' text-emerald-300'} value="Successful at Execution"/></Field><Field label="Error 908"><input aria-label="Error 908" readOnly className={input+' text-rose-300'} value="Failure at Execution"/></Field></div>;
}
export default function RetailerSetup({initialRetailerId=null,onBack}) {
 const [retailers,setRetailers]=useState([]),[catalog,setCatalog]=useState([]),[config,setConfig]=useState(empty),[view,setView]=useState('setup');
 const [sampleInputId,setSampleInputId]=useState(''),[sample,setSample]=useState(null),[previewState,setPreviewState]=useState(null),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [busy,setBusy]=useState(false),[previewBusy,setPreviewBusy]=useState(false),[dirty,setDirty]=useState(false);
 const [ruleDraft,setRuleDraft]=useState(null),[draftDefinition,setDraftDefinition]=useState(''),[conditionDraft,setConditionDraft]=useState(null),[conditionEditing,setConditionEditing]=useState(false),[editRule,setEditRule]=useState(null);
 const [storeDraft,setStoreDraft]=useState(null),[historyOpen,setHistoryOpen]=useState(false);
 const sampleRequest=useRef(0);
 const order=config.sectionOrder||categories;
 const pipeline=config.pipeline;
 const hasReferences=pipeline.some(r=>r.operation==='reference');
 const signature=JSON.stringify({id:config.id,sample:sample,inputFileId:sampleInputId,pipeline});
 const preview=previewState?.signature===signature?previewState.data:null;
 const fields=[...new Set([...(sample?.columns||[]),...pipeline.filter(r=>r.operation==='rename').map(r=>r.target).filter(Boolean)])];
 const change=patch=>{setConfig(c=>({...c,...patch}));setDirty(true);setNotice('');};
 const loadSample=async(id)=>{const serial=++sampleRequest.current;setSample(null);setPreviewState(null);setSampleInputId('');if(!id)return;try{const data=await api(`/retailers/${id}/sample`);if(serial===sampleRequest.current)setSample(data.sample);}catch(e){if(serial===sampleRequest.current)setError(e.message);}};
 useEffect(()=>{let alive=true;Promise.all([api('/retailers'),api('/rule-definitions')]).then(([a,b])=>{if(!alive)return;setRetailers(a.retailers);setCatalog(b.rules);const selected=a.retailers.find(r=>r.id===initialRetailerId);if(selected){setConfig(selected);loadSample(selected.id);}else if(initialRetailerId){setError('Retailer no longer exists. Return to Client.');}}).catch(e=>{if(alive)setError(e.message);});return()=>{alive=false;};},[]);
 async function save(next=config) {
  setBusy(true);setError('');
  try {
   const data=await api(config.id?`/retailers/${config.id}`:'/retailers',{...json({...next,pipeline:next.pipeline}),method:config.id?'PUT':'POST'});
   setConfig(data.retailer);setRetailers(list=>[...list.filter(r=>r.id!==data.retailer.id),data.retailer]);setDirty(false);setNotice('Retailer setup and ordered rules saved.');return data.retailer;
  }catch(e){setError(e.message);return null;}finally{setBusy(false);}
 }
 function selectRetailer(id) {
  if(dirty && !window.confirm('Discard unsaved changes and switch retailer?'))return;
  setConfig(retailers.find(r=>r.id===id)||empty());setDirty(false);setError('');setNotice('');setView('setup');setStoreDraft(null);setRuleDraft(null);setEditRule(null);setConditionDraft(null);loadSample(id);
 }
 async function upload(file) {
  if(!file)return;
  if(file.size>=1000000){setError('Sample must be smaller than 1 MB (1,000,000 bytes).');return;}
  let retailer=config;if(!config.id||dirty){retailer=await save();if(!retailer)return;}
  setBusy(true);setError('');
  const data=new FormData();data.append('file',file);
  try{const result=await api(`/retailers/${retailer.id}/sample`,{method:'POST',body:data});setSampleInputId('');setSample(result.sample);setNotice('Sample uploaded. Use Preview in Rules Configure.');}catch(e){setError(e.message);}finally{setBusy(false);}
 }
 function openComponent(category) {
  setDraftDefinition('');setRuleDraft({id:crypto.randomUUID(),category,operation:'',name:'',field:fields[0]||'',description:'',dateFormat:'%d/%m/%Y'});
 }
 function chooseDefinition(id) {
  setDraftDefinition(id);
  if(id==='new'){setRuleDraft(r=>({...r,name:'',operation:Object.keys(operations[r.category])[0]}));return;}
  const def=catalog.find(r=>r.id===id);
  setRuleDraft(r=>def?{...r,...def.defaults,name:def.name,operation:def.operation,description:def.example||'Example: Prepare this field for data processing.'}:{...r,name:'',operation:''});
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
 function updateRule(rule){change({pipeline:config.pipeline.map(r=>r.id===rule.id?rule:r)});}
 function moveRule(rule,direction) {
  const list=[...pipeline], index=list.findIndex(r=>r.id===rule.id), target=index+direction;
  if(target<0||target>=list.length)return;
  [list[index],list[target]]=[list[target],list[index]];change({pipeline:list});
 }
 async function downloadExample() {
  setBusy(true);setError('');
  try {const response=await fetch(`${API}/retailers/${config.id}/example.csv`,json({pipeline,inputFileId:sampleInputId||undefined}));if(!response.ok)throw new Error((await response.json()).error);const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download=`${config.key}_final_example.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){setError(e.message);}finally{setBusy(false);}
 }
 return <div className="space-y-6" data-testid="retailer-setup">
  {historyOpen&&<ConfigurationHistory retailerId={config.id} onClose={()=>setHistoryOpen(false)}/>}
  <div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-2xl font-bold flex items-center gap-2"><Building2 className="text-cyan-400"/>Retailer Data Setup</h2><p className="text-sm text-slate-400 mt-2">Set up retailer details, store records and an ordered data configuration.</p></div><div className="flex gap-2">{config.id&&<button className={button} onClick={()=>setHistoryOpen(true)}>Configuration History</button>}<button disabled={busy} className={button} onClick={()=>{if(!dirty||window.confirm('Discard unsaved setup changes and return to Client?'))onBack?.();}}>Back to Client</button><button disabled={busy||view==='store'||view==='inputs'} className={primary} onClick={()=>save()}><Save size={16}/>{busy?'Working…':'Save Configuration'}</button></div></div>
  <p className="text-xs text-slate-400">Client / Setup · {config.name||'New retailer'} · {dirty?'Unsaved changes':config.id?'Saved configuration':'New configuration'}</p>
  <div className="flex gap-2 border-b border-slate-700 pb-3"><button className={view==='setup'?primary:button} disabled={view==='store'} onClick={()=>setView('setup')}>Retailer Details</button><button className={view==='inputs'?primary:button} disabled={busy||view==='store'} onClick={async()=>{if(!config.id||dirty){const saved=await save();if(!saved)return;}setView('inputs');}}>Input Files</button><button className={view==='rules'?primary:button} disabled={view==='store'} onClick={()=>setView('rules')}><SlidersHorizontal size={16}/>Rules Configure</button></div>
  {error&&<div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-rose-200 text-sm">{error}</div>}
  {notice&&<div role="status" className="text-emerald-300 text-sm">{notice}</div>}
  {view==='inputs'&&config.id&&<InputSetup retailerId={config.id} primaryInputId={config.primaryInputId} hasLinks={config.pipeline.some(r=>r.operation==='join')} onLegacyUpload={upload} legacySample={sample} onUpdated={async()=>{const d=await api('/retailers');setRetailers(d.retailers);setConfig(d.retailers.find(r=>r.id===config.id)||config);setDirty(false);}}/>}
  {view==='setup'&&<>
   <section className={card}><h3 className="font-semibold">Retailer Information</h3><div className="grid md:grid-cols-2 gap-4">
    <Field label="Retailer Name *"><input className={input} required maxLength={120} value={config.name} onChange={e=>change({name:e.target.value})}/></Field>
    <Field label="Retailer Key *"><input className={input} required maxLength={64} placeholder="RETAILER_001" value={config.key} onChange={e=>change({key:e.target.value})}/><span className="text-xs text-slate-400">Unique key using letters, numbers, underscores or hyphens.</span></Field>
    <Field label="Service Type *"><select className={input} value={config.serviceType} onChange={e=>change({serviceType:e.target.value})}><option value="SM">SM — Supermarket</option><option value="HM">HM — Hypermarket</option><option value="MM">MM — Minimarket</option></select></Field>
    <Field label="Sender Email (internal) *"><input type="email" className={input} required value={config.senderEmail} onChange={e=>change({senderEmail:e.target.value})}/></Field>
    <Field label="Retailer Email (optional)"><input type="email" className={input} value={config.retailerEmail} onChange={e=>change({retailerEmail:e.target.value})}/><span className="text-xs text-slate-400">Contact for late data delivery alerts when enabled.</span></Field>
   </div></section>
   <section className={card}><div className="flex items-center justify-between"><h3 className="font-semibold">Store Table Management</h3><button className={button} onClick={()=>{setStoreDraft({index:null,retailerKey:config.key,key:'',name:'',address:'',status:'Active',exception:false});setView('store');}}><Plus size={16}/>Add Store</button></div><div className="overflow-x-auto"><table className="w-full text-sm text-left"><thead className="text-slate-400"><tr>{['Retailer Store ID','Retailer Store Name','SUITE Storecode','Active','Inactive','Edit'].map(h=><th key={h} className="p-3 whitespace-nowrap">{h}</th>)}</tr></thead><tbody>{config.stores.map((store,i)=><tr key={store.id||i} className="border-t border-slate-700"><td className="p-3">{store.key}</td><td className="p-3">{store.name}</td><td className="p-3 font-mono text-xs">{store.suiteCode||'Generated on save'}</td><td className="p-3"><span aria-label={`${store.key} active: ${(store.status||'Active')==='Active'?'yes':'no'}`} className="text-emerald-300">{(store.status||'Active')==='Active'?'●':''}</span></td><td className="p-3"><span aria-label={`${store.key} inactive: ${store.status==='Inactive'?'yes':'no'}`} className="text-slate-400">{store.status==='Inactive'?'●':''}</span></td><td className="p-3"><button className={button} title="Edit store" aria-label={`Edit store ${store.key}`} onClick={()=>{setStoreDraft({status:'Active',exception:false,address:'',...store,index:i,retailerKey:config.key});setView('store');}}><Pencil size={16}/></button></td></tr>)}</tbody></table>{!config.stores.length&&<p className="text-sm text-slate-400 py-4">No stores yet. Add a retailer store.</p>}</div></section>
   <div className="flex justify-end"><button className={primary} disabled={view==='store'} onClick={()=>setView('rules')}><SlidersHorizontal size={16}/>Rules Configure →</button></div>
  </>}
  {view==='store'&&storeDraft&&<section className={card} aria-label="Store edit page"><div className="flex justify-between gap-3"><h2 className="text-xl font-semibold">{storeDraft.index===null?'Add Store':'Edit Store'}</h2><button className={button} disabled={busy} onClick={()=>{setStoreDraft(null);setView('setup');}}>Back to Store Table</button></div><div className="grid grid-cols-1 md:grid-cols-2 gap-5"><Field label="Retailer Name"><input className={input} readOnly value={config.name}/></Field><fieldset className="space-y-3"><legend className="text-sm text-slate-300">Status</legend><div className="flex gap-5">{['Active','Inactive'].map(status=><label key={status} className="flex items-center gap-2 text-sm"><input type="radio" name="store-status" value={status} checked={storeDraft.status===status} onChange={()=>setStoreDraft(d=>({...d,status}))}/>{status}</label>)}</div></fieldset><Field label="Retailer Key"><input className={input} maxLength={64} value={storeDraft.retailerKey} onChange={e=>setStoreDraft(d=>({...d,retailerKey:e.target.value}))}/><span className="text-xs text-slate-400">Shared retailer key: saving updates it for all this retailer's stores.</span></Field><fieldset className="space-y-3"><legend className="text-sm text-slate-300">Exception status</legend><div className="flex gap-5">{[{label:'Yes',value:true},{label:'No',value:false}].map(option=><label key={option.label} className="flex items-center gap-2 text-sm"><input type="radio" name="store-exception" checked={storeDraft.exception===option.value} onChange={()=>setStoreDraft(d=>({...d,exception:option.value}))}/>{option.label}</label>)}</div></fieldset><Field label="Store ID"><input className={input} maxLength={64} value={storeDraft.key} onChange={e=>setStoreDraft(d=>({...d,key:e.target.value}))}/></Field><Field label="SUITE Storecode"><input className={input} readOnly value={storeDraft.suiteCode||''} placeholder="Autogenerated once saved"/></Field><Field label="Store Name"><input className={input} maxLength={120} value={storeDraft.name} onChange={e=>setStoreDraft(d=>({...d,name:e.target.value}))}/></Field><Field label="Store Address"><textarea className={input} rows={3} maxLength={2000} value={storeDraft.address} onChange={e=>setStoreDraft(d=>({...d,address:e.target.value}))}/></Field></div><div className="flex justify-end gap-3"><button className={primary} disabled={busy||!storeDraft.key.trim()||!storeDraft.name.trim()||!storeDraft.retailerKey.trim()} onClick={async()=>{const {index,retailerKey,...store}=storeDraft;const stores=index===null?[...config.stores,store]:config.stores.map((s,i)=>i===index?store:s);const result=await save({...config,key:retailerKey,stores});if(result){setStoreDraft(null);setView('setup');setNotice('Store details saved.');}}}>Save Store</button><button className={button} disabled={busy} onClick={()=>{setStoreDraft(null);setView('setup');}}>Cancel</button></div></section>}
  {view==='rules'&&<WorkflowRules config={config} change={change} catalog={catalog} legacySample={sample}/>}
 </div>;
}
