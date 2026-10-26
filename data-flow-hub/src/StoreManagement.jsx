import React, {useEffect, useRef, useState} from 'react';
import {ArrowDown, ArrowUp, CheckCircle2, ChevronLeft, ChevronRight, Download, FileSpreadsheet, Pencil, Plus, RefreshCw, Search, Upload, X} from 'lucide-react';

const API = import.meta.env.VITE_API_URL || '/api/v1';
const input = 'w-full rounded-lg border border-slate-700 bg-slate-950 p-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-400';
const button = 'inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed';
const primary = button + ' bg-cyan-500 text-slate-950 font-semibold hover:bg-cyan-400 border-cyan-500';
const badge = 'rounded-full px-2 py-1 text-xs font-medium';
const PREVIEW_PAGE_SIZE = 25;
const actionLabels = {add: 'Add', update: 'Update', unchanged: 'Unchanged', error: 'Fix required'};

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  let result;
  try { result = await response.json(); }
  catch { throw new Error('The server returned an unexpected response. Please try again.'); }
  if (!response.ok || !result.success) throw new Error(result.error || 'The request could not be completed.');
  return result;
}

export default function StoreManagement({retailer, dirty, busy, onAdd, onEdit, onImported, onBusyChange}) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All');
  const [sort, setSort] = useState('key');
  const [direction, setDirection] = useState('asc');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [listing, setListing] = useState({stores: [], total: 0});
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState('');
  const [reload, setReload] = useState(0);
  const [importOpen, setImportOpen] = useState(false);
  const [mode, setMode] = useState('add');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [previewPage, setPreviewPage] = useState(1);
  const [errorsOnly, setErrorsOnly] = useState(false);
  const [working, setWorking] = useState('');
  const [importError, setImportError] = useState('');
  const [notice, setNotice] = useState('');
  const fileInput = useRef(null);
  const operation = useRef(0);
  const mounted = useRef(true);
  const locked = busy || !!working;
  const importAllowed = !!retailer.id && !dirty && !retailer.archived;

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; operation.current += 1; };
  }, []);

  useEffect(() => {
    setQuery(''); setStatus('All'); setSort('key'); setDirection('asc'); setPage(1);
    setImportOpen(false); setFile(null); setPreview(null); setImportError(''); setNotice('');
    if (fileInput.current) fileInput.current.value = '';
  }, [retailer.id]);

  useEffect(() => {
    // The backend binds each preview to the saved configuration. Never confirm a
    // preview after the user changes the configuration locally.
    if (dirty) setPreview(null);
  }, [dirty]);

  useEffect(() => { setPreview(null); }, [retailer.stores]);

  useEffect(() => {
    const controller = new AbortController();
    if (!retailer.id) {
      setListing({stores: [], total: 0}); setLoading(false); setListError('');
      return () => controller.abort();
    }
    setLoading(true); setListError('');
    const timer = setTimeout(async () => {
      const params = new URLSearchParams({q: query, status, sort, direction, page: String(page), pageSize: String(pageSize)});
      try {
        const data = await request(`/retailers/${retailer.id}/stores?${params}`, {signal: controller.signal});
        if (controller.signal.aborted) return;
        const lastPage = Math.max(1, Math.ceil(data.total / pageSize));
        if (page > lastPage) { setPage(lastPage); return; }
        setListing(data);
      } catch (error) {
        if (!controller.signal.aborted) setListError(error.message);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 200);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [retailer.id, retailer.stores, query, status, sort, direction, page, pageSize, reload]);

  function resetPreview() {
    setPreview(null); setPreviewPage(1); setErrorsOnly(false); setImportError(''); setNotice('');
  }

  async function createPreview() {
    if (!file || !importAllowed || locked) return;
    if (!/\.(csv|xlsx)$/i.test(file.name)) { setImportError('Choose a CSV or Excel (.xlsx) file.'); return; }
    if (file.size > 2 * 1024 * 1024) { setImportError('The store file must be 2 MiB or smaller.'); return; }
    const serial = ++operation.current;
    setWorking('preview'); onBusyChange(true); resetPreview();
    const body = new FormData(); body.append('file', file); body.append('mode', mode);
    try {
      const data = await request(`/retailers/${retailer.id}/stores/import/preview`, {method: 'POST', body});
      if (mounted.current && serial === operation.current) setPreview(data);
    } catch (error) {
      if (mounted.current && serial === operation.current) setImportError(error.message);
    } finally {
      if (mounted.current && serial === operation.current) { setWorking(''); onBusyChange(false); }
    }
  }

  async function confirmImport() {
    if (!preview?.canConfirm || !importAllowed || locked) return;
    const serial = ++operation.current;
    setWorking('confirm'); onBusyChange(true); setImportError('');
    try {
      const result = await request(`/retailers/${retailer.id}/stores/import/confirm`, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({previewId: preview.previewId}),
      });
      if (!mounted.current || serial !== operation.current) return;
      onImported(result.retailer);
      setPreview(null); setFile(null); setImportOpen(false); setPage(1); setReload(value => value + 1);
      if (fileInput.current) fileInput.current.value = '';
      const summary = result.summary || preview.summary;
      setNotice(`Import complete: ${summary.added} added, ${summary.updated} updated, ${summary.unchanged} unchanged. Existing store codes are preserved.`);
    } catch (error) {
      if (mounted.current && serial === operation.current) {
        setImportError(`${error.message} Review the file and generate a new preview before trying again.`);
        setPreview(null);
      }
    } finally {
      if (mounted.current && serial === operation.current) { setWorking(''); onBusyChange(false); }
    }
  }

  function sortBy(field) {
    setPage(1);
    if (sort === field) setDirection(value => value === 'asc' ? 'desc' : 'asc');
    else { setSort(field); setDirection('asc'); }
  }

  const totalPages = Math.max(1, Math.ceil(listing.total / pageSize));
  const previewRows = (preview?.rows || []).filter(row => !errorsOnly || row.errors.length > 0);
  const previewPages = Math.max(1, Math.ceil(previewRows.length / PREVIEW_PAGE_SIZE));
  const shownPreviewPage = Math.min(previewPage, previewPages);
  const selectedPreviewRows = previewRows.slice((shownPreviewPage - 1) * PREVIEW_PAGE_SIZE, shownPreviewPage * PREVIEW_PAGE_SIZE);

  return <section className="rounded-xl border border-slate-700 bg-[var(--panel-background)] p-5 space-y-5" aria-label="Store management">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h3 className="font-semibold text-lg">Store management</h3><p className="text-sm text-slate-400 mt-1">Find and manage stores for {retailer.name || 'this retailer'}, or import a complete store list.</p></div>
      <div className="flex flex-wrap gap-2">
        <button type="button" className={button} disabled={locked || retailer.archived} onClick={() => { setImportOpen(value => !value); setImportError(''); }} aria-expanded={importOpen}><Upload size={16}/>Import stores</button>
        <button type="button" className={primary} disabled={locked || retailer.archived} onClick={onAdd}><Plus size={16}/>Add store</button>
      </div>
    </div>

    {notice && <div role="status" className="flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-200"><CheckCircle2 size={18} className="shrink-0"/>{notice}</div>}

    {importOpen && <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-4 space-y-4" aria-label="Bulk store import">
      <div className="flex items-start justify-between gap-3"><div><h4 className="font-semibold flex items-center gap-2"><FileSpreadsheet size={18}/>Import store list</h4><p className="text-sm text-slate-400 mt-1">Download a template, upload your file, then review every change before saving.</p></div><button type="button" aria-label="Close import" className={button} disabled={locked} onClick={() => setImportOpen(false)}><X size={16}/></button></div>
      <div className="flex flex-wrap gap-2"><a className={button} href={`${API}/store-template?format=csv`} download><Download size={16}/>CSV template</a><a className={button} href={`${API}/store-template?format=xlsx`} download><Download size={16}/>Excel template</a></div>
      <p className="text-xs text-slate-400">Required columns: store_id, store_name. Optional: address, status (Active or Inactive), exception (true or false). Internal store codes are generated automatically. Maximum 1,000 stores per retailer and 2 MiB per file.</p>
      {!importAllowed && <p role="status" className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">{retailer.archived ? 'Restore this retailer before importing stores.' : 'Save Configuration above before importing. Your unsaved retailer changes will be kept.'}</p>}
      <fieldset disabled={!importAllowed || locked} className="grid md:grid-cols-2 gap-4 disabled:opacity-60">
        <label className="space-y-1.5 text-sm"><span className="block text-slate-300">Import mode</span><select aria-label="Import mode" className={input} value={mode} onChange={event => { setMode(event.target.value); resetPreview(); }}><option value="add">Add new stores only</option><option value="upsert">Add new and update matching stores</option></select></label>
        <label className="space-y-1.5 text-sm"><span className="block text-slate-300">Store file (.csv or .xlsx)</span><input ref={fileInput} type="file" accept=".csv,.xlsx" className={input + ' file:mr-3 file:rounded file:border-0 file:bg-slate-800 file:px-2 file:py-1 file:text-slate-100'} onChange={event => { setFile(event.target.files?.[0] || null); resetPreview(); }}/></label>
      </fieldset>
      <p className="text-xs text-slate-400">{mode === 'add' ? 'Existing store IDs are rejected. No stores are deleted or replaced.' : 'Matches use this retailer’s Store ID. Existing identities and internal store codes stay the same. Stores missing from the file stay unchanged.'}</p>
      <button type="button" className={primary} disabled={!file || !importAllowed || locked} onClick={createPreview}><Search size={16}/>{working === 'preview' ? 'Validating file…' : preview ? 'Refresh preview' : 'Validate and preview'}</button>
      {importError && <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-rose-200 text-sm">{importError}</div>}
      {preview && <div className="space-y-4" aria-label="Import preview">
        <p className="text-sm text-slate-300"><strong>{retailer.name}</strong> · {mode === 'add' ? 'Add new stores only' : 'Add new and update matching stores'}. No changes have been saved yet.</p>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2" aria-label="Import summary">{[['total', 'File rows'], ['added', 'To add'], ['updated', 'To update'], ['unchanged', 'Unchanged'], ['errors', 'Rows to fix']].map(([key, label]) => <div key={key} className="rounded-lg border border-slate-700 bg-slate-950/50 px-3 py-2"><div className={`text-xl font-semibold ${key === 'errors' && preview.summary[key] ? 'text-rose-300' : ''}`}>{preview.summary[key]}</div><div className="text-xs text-slate-400">{label}</div></div>)}</div>
        <div className="flex flex-wrap items-center justify-between gap-3"><label className="inline-flex gap-2 items-center text-sm"><input type="checkbox" checked={errorsOnly} onChange={event => { setErrorsOnly(event.target.checked); setPreviewPage(1); }}/>Show rows with errors only</label>{preview.summary.errors > 0 && <a className={button} href={`${API}/retailers/${retailer.id}/stores/import/${preview.previewId}/errors`} download><Download size={16}/>Download error report</a>}</div>
        <div className="overflow-auto max-h-96 rounded-lg border border-slate-700"><table className="w-full text-sm text-left"><caption className="sr-only">Proposed store changes; no records have been saved yet.</caption><thead className="text-slate-400 sticky top-0 bg-slate-950"><tr>{['File row', 'Action', 'Store ID', 'Store name', 'Address', 'Status', 'Exception', 'Validation'].map(label => <th scope="col" key={label} className="p-3 whitespace-nowrap">{label}</th>)}</tr></thead><tbody>{selectedPreviewRows.map(row => <tr key={row.row} className="border-t border-slate-700"><td className="p-3">{row.row}</td><td className="p-3"><span className={badge + (row.errors.length ? ' bg-rose-500/10 text-rose-200' : ' bg-cyan-500/10 text-cyan-200')}>{actionLabels[row.action] || row.action}</span></td><td className="p-3 font-mono text-xs">{row.key}</td><td className="p-3">{row.name}</td><td className="p-3 min-w-48">{row.address || '—'}</td><td className="p-3">{row.status}</td><td className="p-3">{typeof row.exception === 'boolean' ? row.exception ? 'Yes' : 'No' : String(row.exception)}</td><td className="p-3 text-rose-200">{row.errors.join(' · ') || <span className="text-emerald-300">Valid</span>}</td></tr>)}</tbody></table>{!selectedPreviewRows.length && <p className="p-4 text-sm text-slate-400">No rows match this preview filter.</p>}</div>
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm"><span className="text-slate-400">{previewRows.length} preview rows · Page {shownPreviewPage} of {previewPages}</span><div className="flex gap-2"><button type="button" className={button} aria-label="Previous preview page" disabled={shownPreviewPage <= 1 || locked} onClick={() => setPreviewPage(shownPreviewPage - 1)}><ChevronLeft size={16}/></button><button type="button" className={button} aria-label="Next preview page" disabled={shownPreviewPage >= previewPages || locked} onClick={() => setPreviewPage(shownPreviewPage + 1)}><ChevronRight size={16}/></button></div></div>
        <div className="rounded-lg border border-slate-700 p-3 flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-slate-300 max-w-2xl">{preview.canConfirm ? 'Review the proposed changes above. Confirm imports the whole valid file in one transaction. Previews expire after 30 minutes.' : preview.summary.errors ? 'Nothing has been saved. Fix all validation errors, then upload the corrected file and generate another preview.' : 'All stores already match the saved records; there is nothing to import.'}</p><button type="button" className={primary} disabled={!preview.canConfirm || !importAllowed || locked} onClick={confirmImport}><CheckCircle2 size={16}/>{working === 'confirm' ? 'Saving stores…' : 'Confirm import'}</button></div>
      </div>}
    </div>}

    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <label className="sm:col-span-2 space-y-1.5 text-sm"><span className="text-slate-300">Search stores</span><div className="relative"><Search size={16} className="absolute left-3 top-3 text-slate-500"/><input aria-label="Search stores" className={input + ' pl-9'} value={query} onChange={event => { setQuery(event.target.value); setPage(1); }} placeholder="Store ID, name, code or address" type="search"/></div></label>
      <label className="space-y-1.5 text-sm"><span className="text-slate-300">Status</span><select aria-label="Status" className={input} value={status} onChange={event => { setStatus(event.target.value); setPage(1); }}><option value="All">All statuses</option><option>Active</option><option>Inactive</option></select></label>
      <label className="space-y-1.5 text-sm"><span className="text-slate-300">Rows per page</span><select aria-label="Rows per page" className={input} value={pageSize} onChange={event => { setPageSize(Number(event.target.value)); setPage(1); }}>{[25, 50, 100].map(size => <option key={size} value={size}>{size}</option>)}</select></label>
    </div>
    {dirty && retailer.id && <p className="text-xs text-amber-200">The store table shows saved records. Save your retailer changes before importing.</p>}
    {listError ? <div role="alert" className="rounded-lg border border-rose-500/30 p-3 flex flex-wrap items-center justify-between gap-3 text-sm text-rose-200"><span>{listError}</span><button type="button" className={button} onClick={() => setReload(value => value + 1)}><RefreshCw size={16}/>Retry</button></div> : <>
      <div className="overflow-x-auto rounded-lg border border-slate-700" aria-busy={loading}>
        <table className="w-full text-sm text-left"><caption className="sr-only">Stores for {retailer.name || 'this retailer'}</caption><thead className="text-slate-400 bg-slate-950/50"><tr>{[['key', 'Store ID'], ['name', 'Store name'], ['suiteCode', 'SUITE store code'], ['status', 'Status']].map(([field, label]) => <th scope="col" key={field} className="p-3 whitespace-nowrap" aria-sort={sort === field ? direction === 'asc' ? 'ascending' : 'descending' : 'none'}><button type="button" className="inline-flex items-center gap-2 hover:text-slate-100" onClick={() => sortBy(field)}>{label}{sort === field && (direction === 'asc' ? <ArrowUp size={14}/> : <ArrowDown size={14}/>)}</button></th>)}<th scope="col" className="p-3">Exception</th><th scope="col" className="p-3">Edit</th></tr></thead>
          <tbody>{!loading && listing.stores.map(store => <tr key={store.id || store.key} className="border-t border-slate-700 hover:bg-slate-800/30"><td className="p-3 font-mono text-xs">{store.key}</td><td className="p-3"><div>{store.name}</div>{store.address && <div className="text-xs text-slate-500 mt-1 max-w-sm truncate" title={store.address}>{store.address}</div>}</td><td className="p-3 font-mono text-xs">{store.suiteCode || 'Generated on save'}</td><td className="p-3"><span className={badge + (store.status === 'Inactive' ? ' bg-slate-700 text-slate-300' : ' bg-emerald-500/10 text-emerald-300')}>{store.status || 'Active'}</span></td><td className="p-3 text-slate-400">{store.exception ? 'Yes' : 'No'}</td><td className="p-3"><button type="button" className={button} disabled={locked || retailer.archived} title={`Edit ${store.key}`} aria-label={`Edit store ${store.key}`} onClick={() => onEdit(store)}><Pencil size={16}/></button></td></tr>)}</tbody>
        </table>
        {loading && <p role="status" className="p-6 text-sm text-slate-400">Loading stores…</p>}
        {!loading && !listing.stores.length && <div className="p-6 text-sm text-slate-400">{!retailer.id ? 'Save the retailer configuration to start managing its stores.' : query || status !== 'All' ? 'No stores match these filters. Try another search or status.' : 'No stores yet. Add a store or import a store list.'}</div>}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm"><p role="status" className="text-slate-400">{loading ? 'Updating results…' : listing.total ? `Showing ${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, listing.total)} of ${listing.total} stores` : '0 stores'}</p><div className="flex items-center gap-3"><button type="button" className={button} disabled={page <= 1 || loading} onClick={() => setPage(value => value - 1)}><ChevronLeft size={16}/>Previous</button><span className="text-slate-400">Page {page} of {totalPages}</span><button type="button" className={button} disabled={page >= totalPages || loading} onClick={() => setPage(value => value + 1)}>Next<ChevronRight size={16}/></button></div></div>
    </>}
  </section>;
}
