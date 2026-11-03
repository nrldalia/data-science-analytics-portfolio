import {applyTheme, preferredTheme} from './theme.js';
import KPIRecords from './KPIRecords';
import BatchLogs from './BatchLogs';
import Client from './Client';
import React, {useEffect, useState} from 'react';
import {version as RELEASE} from '../package.json';
import {Building2, Database, BarChart3, Settings, Upload, X, Sun, Moon, Menu, RefreshCw} from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '/api/v1';
const modules = [
  {name: 'Client', icon: Building2},
  {name: 'Data Streams', icon: Database},
  {name: 'KPI Records', icon: BarChart3},
  {name: 'Settings', icon: Settings},
];

export default function App() {
  const [theme, setTheme] = useState(preferredTheme);
  const [activeTab, setActiveTab] = useState('Client');
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false);
  const [batchFile, setBatchFile] = useState(null);
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState('');
  const [checking, setChecking] = useState(false);
  const [healthReload, setHealthReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setChecking(true);
    setHealthError('');
    fetch(`${API}/health`, {signal: controller.signal})
      .then(async response => {
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error('The application service is unavailable.');
        if (!controller.signal.aborted) setHealth(data);
      })
      .catch(error => {
        if (!controller.signal.aborted) {
          setHealth(null);
          setHealthError('The application service could not be reached. Check PostgreSQL and the app terminal, then retry.');
        }
      })
      .finally(() => {if (!controller.signal.aborted) setChecking(false);});
    return () => controller.abort();
  }, [healthReload]);

  const chooseTheme = value => {applyTheme(value, true); setTheme(value);};
  const chooseModule = name => {setActiveTab(name); setMobileNavigationOpen(false);};
  const handleFileUpload = event => {
    const file = event.target.files?.[0];
    if (!file) return;
    setBatchFile(file);
    chooseModule('Data Streams');
    event.target.value = '';
  };
  const database = health?.database === 'postgresql' ? 'PostgreSQL' : health?.database === 'sqlite' ? 'SQLite (legacy mode)' : 'Not verified';

  return <div className="flex flex-col md:flex-row h-dvh bg-[var(--app-background)] text-slate-100 font-sans overflow-hidden">
    <aside className="w-full md:w-64 bg-[var(--sidebar-background)] border-b md:border-b-0 md:border-r border-slate-700/50 flex flex-col justify-between p-3 md:p-4 shrink-0">
      <div>
        <div className="flex items-center justify-between gap-2 md:mb-8 px-2">
          <div className="flex items-center gap-2"><Database className="text-cyan-400 w-6 h-6"/><span className="font-bold text-lg tracking-wide text-cyan-400">DataFlow Hub</span></div>
          <button type="button" className="md:hidden inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm" aria-controls="module-navigation" aria-expanded={mobileNavigationOpen} onClick={() => setMobileNavigationOpen(open => !open)}>{mobileNavigationOpen ? <X size={18}/> : <Menu size={18}/>}<span>Menu</span></button>
        </div>
        <div className="hidden md:block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 px-2">Modules</div>
        <nav id="module-navigation" aria-label="Application modules" className={`${mobileNavigationOpen ? 'grid' : 'hidden'} grid-cols-2 gap-1 mt-3 md:mt-0 md:block md:space-y-1`}>
          {modules.map(item => {
            const Icon = item.icon;
            return <button type="button" key={item.name} onClick={() => chooseModule(item.name)} aria-current={activeTab === item.name ? 'page' : undefined} className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${activeTab === item.name ? 'nav-active' : 'nav-inactive'}`}><Icon className="w-4 h-4"/>{item.name}</button>;
          })}
        </nav>
      </div>
      <div className={`${mobileNavigationOpen ? 'block' : 'hidden'} md:block p-3 mt-3 md:mt-0 bg-slate-800/50 rounded-lg border border-slate-700/50`}>
        <label className="flex items-center justify-center gap-2 cursor-pointer bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold py-2 px-4 rounded-md text-xs transition-colors"><Upload className="w-4 h-4"/>Upload Data File<input aria-label="Upload data file" type="file" accept=".csv,.json,.xlsx,.tsv,.txt,.zip" onChange={handleFileUpload} className="sr-only"/></label>
        <p className="text-xs text-slate-400 mt-3">Upload → configure → process → review → export</p>
      </div>
    </aside>
    <main className="flex-1 min-w-0 min-h-0 flex flex-col overflow-y-auto">
      <header className="min-h-16 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 px-4 py-3 md:px-8 bg-[var(--app-background)] shrink-0">
        <div><h1 className="text-sm sm:text-lg xl:text-xl font-bold text-slate-100">DataFlow Hub — Data preparation & review</h1><p className="text-xs text-slate-400 mt-1">Local single-user release candidate</p></div>
        <div className="flex items-center gap-3 shrink-0"><div className="theme-switch" role="group" aria-label="Colour theme"><button type="button" aria-pressed={theme === 'light'} onClick={() => chooseTheme('light')}><Sun size={14} aria-hidden="true"/>Light</button><button type="button" aria-pressed={theme === 'dark'} onClick={() => chooseTheme('dark')}><Moon size={14} aria-hidden="true"/>Dark</button></div><span className="text-xs bg-slate-900 text-cyan-400 px-2.5 py-1 rounded-full border border-slate-700">{RELEASE}</span></div>
      </header>
      <div className="min-w-0 p-3 sm:p-5 lg:p-8 space-y-6 flex-1">
        {healthError && <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300"><p>{healthError}</p><button type="button" className="mt-2 inline-flex items-center gap-2 rounded border border-slate-600 px-3 py-1.5" disabled={checking} onClick={() => setHealthReload(value => value + 1)}><RefreshCw size={14}/>{checking ? 'Checking…' : 'Retry connection'}</button></div>}
        {activeTab === 'Client' && <Client/>}
        {activeTab === 'Data Streams' && <BatchLogs incomingFile={batchFile} onFileAccepted={() => setBatchFile(null)}/>}
        {activeTab === 'KPI Records' && <KPIRecords/>}
        {activeTab === 'Settings' && <section aria-label="Application settings" className="space-y-5 max-w-2xl">
          <h2 className="text-2xl font-bold">Application settings</h2>
          <p className="text-sm text-slate-400">Prepare data locally with explicit rules, review the findings, and export the result and supporting evidence.</p>
          <dl className="rounded-xl border border-slate-700 bg-[var(--panel-background)] p-5 space-y-4 text-sm">
            <div><dt className="font-semibold">Release</dt><dd className="mt-1 text-slate-400">{RELEASE} · Local single-user release candidate</dd></div>
            <div><dt className="font-semibold">Backend version</dt><dd className="mt-1 text-slate-400">{health?.version || 'Not verified'}</dd></div>
            <div><dt className="font-semibold">Database engine</dt><dd className="mt-1 text-slate-400">{database}</dd></div>
            <div><dt className="font-semibold">Connection</dt><dd className="mt-1 text-slate-400">{checking ? 'Checking…' : health ? 'Application service responding' : 'Unavailable'}</dd></div>
            <div><dt className="font-semibold">API endpoint</dt><dd className="mt-1 text-slate-400 font-mono break-all">{API}</dd></div>
          </dl>
          <p className="text-sm text-slate-400">AI assistance, public hosting, and multi-user access are outside this release. No model credentials are required for the core workflow.</p>
          <button type="button" disabled={checking} onClick={() => setHealthReload(value => value + 1)} className="inline-flex items-center gap-2 rounded-lg border border-slate-600 px-3 py-2 text-sm disabled:opacity-40"><RefreshCw size={14}/>{checking ? 'Checking…' : 'Check connection'}</button>
        </section>}
      </div>
    </main>
  </div>;
}
