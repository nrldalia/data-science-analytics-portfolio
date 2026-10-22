from pathlib import Path
root=Path(__file__).resolve().parent.parent/'outputs/V1.14.A1/frontend-github/src'
for p in root.glob('*.jsx'):
 s=p.read_text(encoding='utf-8').replace('bg-[#0f172a]','bg-[var(--app-background)]').replace('bg-[#1e293b]','bg-[var(--panel-background)]')
 p.write_text(s,encoding='utf-8')
p=root/'main.jsx';s=p.read_text(encoding='utf-8').replace("import './index.css'","import './index.css'\nimport { applyTheme, preferredTheme } from './theme.js'\n\napplyTheme(preferredTheme())");p.write_text(s,encoding='utf-8')
p=root/'app.jsx';s=p.read_text(encoding='utf-8').replace("import KPIRecords from './KPIRecords';","import { applyTheme, preferredTheme } from './theme.js';\nimport KPIRecords from './KPIRecords';")
s=s.replace('Mail, Edit2, ShieldAlert, Cpu, Check, FileText','Mail, Edit2, ShieldAlert, Cpu, Check, FileText, Sun, Moon')
s=s.replace("  const [activeTab, setActiveTab] = useState('Client');","  const [theme, setTheme] = useState(preferredTheme);\n  const chooseTheme = value => { applyTheme(value, true); setTheme(value); };\n  const [activeTab, setActiveTab] = useState('Client');")
s=s.replace('w-64 bg-[var(--panel-background)]','w-64 bg-[var(--sidebar-background)]')
s=s.replace("isActive ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'","isActive ? 'nav-active' : 'nav-inactive'")
old='<span className="text-xs bg-slate-800 text-cyan-400 px-2.5 py-1 rounded-full border border-slate-700">V1.14.A1</span>'
new='''<div className="flex items-center gap-3 shrink-0"><div className="theme-switch" role="group" aria-label="Colour theme"><button type="button" aria-pressed={theme==='light'} onClick={()=>chooseTheme('light')}><Sun size={14} aria-hidden="true"/>Light</button><button type="button" aria-pressed={theme==='dark'} onClick={()=>chooseTheme('dark')}><Moon size={14} aria-hidden="true"/>Dark</button></div><span className="text-xs bg-slate-900 text-cyan-400 px-2.5 py-1 rounded-full border border-slate-700">V1.14.A1</span></div>'''
assert old in s;s=s.replace(old,new);p.write_text(s,encoding='utf-8')
print('Applied shared light/dark palette and persistent header theme controls.')
