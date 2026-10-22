from pathlib import Path
import shutil,sqlite3,json
base=Path('outputs/V1.4.A2');root=Path('outputs/V1.4.A3')
shutil.copytree(base,root,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist','.venv','*.db','*.db-wal','*.db-shm'),dirs_exist_ok=True)
for rel in ['script/app.py','frontend-github/src/app.jsx','Setup_Windows.bat']:
 p=root/rel;s=p.read_text(encoding='utf-8').replace('V1.4.A2','V1.4.A3').replace("version='1.4.A2'","version='1.4.A3'");p.write_text(s,encoding='utf-8')
p=root/'Start_V1.4.A2.bat';(root/'Start_V1.4.A3.bat').write_text(p.read_text().replace('V1.4.A2','V1.4.A3'));p.unlink()
for name in ['package.json','package-lock.json']:
 p=root/'frontend-github'/name;d=json.loads(p.read_text());d['version']='1.4.3'
 if '' in d.get('packages',{}):d['packages']['']['version']='1.4.3'
 p.write_text(json.dumps(d,indent=2))
p=Path('outputs/V1.3.A1.bat');p.write_text(p.read_text().replace('V1.4.A2','V1.4.A3').replace("'1.4.A2'","'1.4.A3'"))
if (base/'script/dataflow.db').exists():
 with sqlite3.connect(base/'script/dataflow.db') as a,sqlite3.connect(root/'script/dataflow.db') as b:a.backup(b)
shutil.copy('work/reference_catalog.json',root/'script/rule_references.json')
p=root/'frontend-github/src/RetailerSetup.jsx';s=p.read_text(encoding='utf-8')
s=s.replace(' const signature=JSON.stringify', " const hasReferences=pipeline.some(r=>r.operation==='reference');\n const signature=JSON.stringify")
s=s.replace('if(!config.id||!sample){', 'if(!config.id||!sample||hasReferences){setPreviewState(null);')
s=s.replace("{...r,...def.defaults,name:def.name,operation:def.operation}", "{...r,...def.defaults,name:def.name,operation:def.operation,description:def.example||'Example: Prepare this field for data processing.'}")
s=s.replace('<div className="mt-1">{rule.name}</div>', '<div className="mt-1">{rule.name}</div>{rule.operation===\'reference\'&&<span className="block text-xs text-amber-300 mt-2">Reference only</span>}')
s=s.replace('<StepPreview step={preview?.steps.find(s=>s.id===rule.id)}/>', "{rule.operation==='reference'?<p className=\"mt-2 text-xs text-amber-300\">Execution engine not available for this reference.</p>:<StepPreview step={preview?.steps.find(s=>s.id===rule.id)}/>}")
s=s.replace('<ExecutionMessages/><p className="text-xs text-slate-400">Save adds this rule', "<ExecutionMessages/>{ruleDraft.operation==='reference'&&<p className=\"text-sm text-amber-300\">This reference can be saved for planning. Its execution engine is not available.</p>}<p className=\"text-xs text-slate-400\">Save adds this rule")
s=s.replace("{operations[conditionDraft.rule.category][conditionDraft.rule.operation]}", "{operations[conditionDraft.rule.category][conditionDraft.rule.operation]||'Reference only — execution engine unavailable'}")
s=s.replace('<h4 className="text-sm text-cyan-300">Rule settings</h4>', "{conditionDraft.rule.operation==='reference'&&<p className=\"text-sm text-amber-300\">Field and condition settings are saved for planning. This reference cannot execute yet.</p>}<h4 className=\"text-sm text-cyan-300\">Rule settings</h4>")
s=s.replace('Upload a sample and complete the rule settings to preview the final output.', "{hasReferences?'Reference-only selections are saved for planning. Remove them from the execution sequence to preview or run the configured rules.':'Upload a sample and complete the rule settings to preview the final output.'}")
# The preceding replacement sits within paragraph JSX, so braces are deliberate.
p.write_text(s,encoding='utf-8')
print('V1.4.A3 prepared')
