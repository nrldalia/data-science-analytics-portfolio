import { useEffect, useRef, useState } from 'react';

export const API = import.meta.env.VITE_API_URL || '/api/v1';
const ROOT = API.replace(/\/v1\/?$/, '').replace(/\/$/, '');
const TABS = ['Quality Review', 'Guided Explorer', 'SQL Studio', 'Insights', 'Audit & Export'];
const button = 'rounded border border-slate-600 px-3 py-1.5 hover:border-cyan-500 disabled:opacity-50';
const input = 'rounded border border-slate-600 bg-[var(--panel-background)] px-2 py-1.5';
const sqlName = name => '"' + name.replaceAll('"', '""') + '"';
const percent = rate => `${(rate * 100).toFixed(1)}%`;
const show = value => value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value);
const operators = {
  eq: 'Equals', ne: 'Does not equal', gt: 'Greater than', gte: 'At least',
  lt: 'Less than', lte: 'At most', contains: 'Contains', missing: 'Is missing',
};

async function api(path, method = 'GET', data, signal) {
  const response = await fetch(ROOT + path, {
    method, signal,
    ...(data === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  });
  if (response.status === 204) return null;
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed.');
  return result;
}

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function csvCell(value) {
  const text = show(value);
  const safe = typeof value === 'string' && /^[\s]*[=+@-]|^[\t\r\n]/.test(text) ? "'" + text : text;
  return '"' + safe.replaceAll('"', '""') + '"';
}

function DataTable({ columns, rows }) {
  return <div className="overflow-auto max-h-80 rounded border border-slate-700">
    <table className="w-full text-left text-xs">
      <thead><tr>{columns.map((column, i) => <th key={i} className="px-2 py-1.5">{column}</th>)}</tr></thead>
      <tbody>{rows.map((row, i) => <tr key={i} className="border-t border-slate-700">
        {row.map((value, j) => <td key={j} className="px-2 py-1.5 break-all">{show(value)}</td>)}
      </tr>)}</tbody>
    </table>
    {!rows.length && <p className="p-2">No matching rows.</p>}
  </div>;
}

function QueryResult({ result, name }) {
  if (!result) return null;
  const { columns, rows, execution_ms, truncated } = result;
  const exportQuery = format => {
    const content = format === 'csv'
      ? [columns, ...rows].map(row => row.map(csvCell).join(',')).join('\r\n')
      : JSON.stringify({ columns, rows }, null, 2);
    download(new Blob([content], { type: format === 'csv' ? 'text/csv' : 'application/json' }), `${name}.${format}`);
  };
  return <section className="space-y-2" aria-label="Query results">
    <div className="flex flex-wrap items-center gap-2">
      <p aria-live="polite">{rows.length} rows shown · {execution_ms} ms{truncated && ' · Preview truncated'}</p>
      <button className={button} onClick={() => exportQuery('csv')}>Export result CSV</button>
      <button className={button} onClick={() => exportQuery('json')}>Export result JSON</button>
    </div>
    <DataTable columns={columns} rows={rows} />
  </section>;
}

export default function RunWorkspace({ run, quality, onExport }) {
  const path = '/runs/' + encodeURIComponent(run.runId);
  const [tab, setTab] = useState(TABS[0]);
  const [schema, setSchema] = useState(null);
  const [reports, setReports] = useState([]);
  const [filters, setFilters] = useState([]);
  const [logic, setLogic] = useState('AND');
  const [preset, setPreset] = useState('');
  const [issue, setIssue] = useState(null);
  const [generated, setGenerated] = useState(false);
  const [guidedResult, setGuidedResult] = useState(null);
  const [sqlResult, setSqlResult] = useState(null);
  const [sql, setSql] = useState('');
  const [reportOpen, setReportOpen] = useState(false);
  const [insights, setInsights] = useState(null);
  const [reviews, setReviews] = useState({});
  const [issuePage, setIssuePage] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const editor = useRef(null);
  const reportDialog = useRef(null);

  useEffect(() => {
    if (reportOpen && reportDialog.current && !reportDialog.current.open) {
      reportDialog.current.showModal();
    }
  }, [reportOpen, tab]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api(path + '/schema', 'GET', undefined, controller.signal),
      api('/saved-queries', 'GET', undefined, controller.signal),
      api(path + '/issue-reviews', 'GET', undefined, controller.signal),
    ]).then(([schemaData, reportData, reviewData]) => {
      if (controller.signal.aborted) return;
      setSchema(schemaData);
      setSql(`SELECT * FROM ${sqlName(schemaData.table_name)}`);
      setReports(reportData.reports);
      setReviews(reviewData.issue_reviews);
    }).catch(exc => { if (!controller.signal.aborted) setError(exc.message); });
    return () => controller.abort();
  }, [path]);

  useEffect(() => {
    if (tab !== 'Insights' || insights) return;
    const controller = new AbortController();
    api(path + '/insights', 'GET', undefined, controller.signal)
      .then(data => { if (!controller.signal.aborted) setInsights(data); })
      .catch(exc => { if (!controller.signal.aborted) setError(exc.message); });
    return () => controller.abort();
  }, [insights, path, tab]);

  async function perform(action) {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      await action();
    } catch (exc) {
      setError(exc.message);
    } finally {
      setBusy(false);
    }
  }

  const columns = schema?.tables.find(table => table.table_name === schema.table_name)?.columns || [];
  const runFilter = (nextPreset = preset, selected = filters, nextIssue = issue, match = logic) => perform(async () => {
    setPreset(nextPreset);
    setIssue(nextIssue);
    setGuidedResult(await api(path + '/filter', 'POST', {
      filters: selected.map(({ column, operator, value }) => ({ column, operator, value })),
      logic: match, preset: nextPreset, issue: nextIssue, limit: 500,
    }));
  });
  const runSql = () => perform(async () => setSqlResult(await api(path + '/query', 'POST', { sql })));
  const loadReports = async () => setReports((await api('/saved-queries')).reports);
  function insert(text) {
    const { selectionStart, selectionEnd } = editor.current;
    setSql(value => value.slice(0, selectionStart) + text + value.slice(selectionEnd));
    requestAnimationFrame(() => {
      editor.current?.focus();
      editor.current?.setSelectionRange(selectionStart + text.length, selectionStart + text.length);
    });
  }

  return <section className="space-y-4 text-sm" aria-label="Run workspace">
    <p className="font-medium">{run.filename} · {run.outputRows} rows · {run.changedCells} changed cells · {run.issueRows} flagged rows</p>
    <nav aria-label="Run workspace views" className="flex flex-wrap gap-2">
      {TABS.map(name => <button key={name} className={button} aria-pressed={name === tab}
        onClick={() => { setError(''); setTab(name); }}>{name}</button>)}
    </nav>
    {error && !reportOpen && <p role="alert" className="text-rose-400">{error}</p>}
    {tab === 'Quality Review' && <>
      {quality}
      {!!run.issues.length && <section className="space-y-2">
        <h4 className="font-semibold">Flagged issues</h4>
        {run.issues.slice(issuePage * 25, issuePage * 25 + 25).map((issue, offset) => {
          const index = issuePage * 25 + offset;
          return <label key={index} className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700 py-1">
            <span>Row {issue.row} · {issue.field} · {issue.issue}</span>
            <select className={input} disabled={busy} value={reviews[index] || 'open'} onChange={event => {
              const status = event.target.value;
              perform(async () => {
                await api(path + '/issues/' + index, 'PUT', { status });
                setReviews(previous => ({ ...previous, [index]: status }));
                setInsights(null);
              });
            }}>
              <option value="open">Open</option><option value="reviewed">Reviewed</option><option value="resolved">Resolved</option>
            </select>
          </label>;
        })}
        <button className={button} disabled={!issuePage} onClick={() => setIssuePage(issuePage - 1)}>Previous issues</button>
        <button className={button} disabled={(issuePage + 1) * 25 >= run.issues.length} onClick={() => setIssuePage(issuePage + 1)}>Next issues</button>
      </section>}
    </>}
    {tab === 'Guided Explorer' && <>
      <form className="space-y-2" onSubmit={event => { event.preventDefault(); runFilter(); }}>
        <div className="flex flex-wrap gap-2">
          {[['', 'All rows'], ['flagged', 'Flagged Rows Only'], ['missing_required', 'Missing Required Fields']].map(([value, label]) =>
            <button type="button" key={value} className={button} aria-pressed={preset === value}
              disabled={busy || !schema} onClick={() => runFilter(value, filters, null)}>{label}</button>)}
          <label>Match <select className={input} value={logic} onChange={event => setLogic(event.target.value)}>
            <option value="AND">All filters</option><option value="OR">Any filter</option>
          </select></label>
          <button className={button} type="button" disabled={!columns.length || filters.length >= 30} onClick={() =>
            setFilters([...filters, { column: columns[0].column_name, operator: 'eq', value: '', key: crypto.randomUUID() }])}>Add filter</button>
        </div>
        {filters.map((filter, i) => {
          const update = (field, value) => setFilters(filters.map((item, j) => j === i ? { ...item, [field]: value } : item));
          return <div className="flex flex-wrap gap-2" key={filter.key}>
            <select aria-label={`Filter ${i + 1} column`} className={input} value={filter.column} onChange={event => update('column', event.target.value)}>
              {columns.map(column => <option key={column.column_name} value={column.column_name}>{column.source_name || '(empty header)'}</option>)}
            </select>
            <select aria-label={`Filter ${i + 1} operator`} className={input} value={filter.operator} onChange={event => update('operator', event.target.value)}>
              {Object.entries(operators).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
            {filter.operator !== 'missing' && (columns.find(column => column.column_name === filter.column)?.inferred_type === 'boolean' && filter.operator !== 'contains'
              ? <select aria-label={`Filter ${i + 1} value`} className={input} value={String(filter.value)} onChange={event => update('value', event.target.value === '' ? '' : event.target.value === 'true')}>
                <option value="">Choose a value</option><option value="true">True</option><option value="false">False</option>
              </select>
              : <input aria-label={`Filter ${i + 1} value`} className={input} value={show(filter.value)} onChange={event => update('value', event.target.value)} />)}
            <button className={button} type="button" onClick={() => setFilters(filters.filter((_, j) => j !== i))}>Remove filter</button>
          </div>;
        })}
        {issue && <p>{issue.field} · {issue.reason} <button type="button" className={button} onClick={() => setIssue(null)}>Clear issue filter</button></p>}
        <button className={button} disabled={busy || !schema}>Apply filters</button>
      </form>
      <section className="space-y-2">
        <h4 className="font-semibold">Saved reports</h4>
        {!reports.length && <p>Use SQL Studio to save a reusable report.</p>}
        {reports.map(report => <div key={report.id} className="flex flex-wrap items-center gap-2">
          <button title={report.description} className={button} disabled={busy} onClick={() => perform(async () =>
            setGuidedResult(await api('/saved-queries/' + report.id, 'POST')))}>{report.name}</button>
          <span className="text-xs">{report.default_run_id}</span>
          <button aria-label={`Delete report ${report.name}`} className={button} disabled={busy} onClick={() => {
            if (window.confirm(`Delete “${report.name}”?`)) perform(async () => {
              await api('/saved-queries/' + report.id, 'DELETE');
              await loadReports();
            });
          }}>Delete</button>
        </div>)}
      </section>
      {guidedResult?.sql && <div>
        <label><input type="checkbox" checked={generated} onChange={event => setGenerated(event.target.checked)} /> Show Generated SQL</label>
        {generated && <pre className="overflow-auto whitespace-pre-wrap">{guidedResult.sql}{'\n'}Parameters {JSON.stringify(guidedResult.parameters)}</pre>}
      </div>}
      <QueryResult result={guidedResult} name={run.runId + '-guided'} />
    </>}
    {tab === 'SQL Studio' && <>
      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <aside aria-label="Run schemas" className="space-y-2 max-h-60 overflow-auto">
          {schema?.tables.map(table => <details key={table.table_name} open={table.run_id === run.runId || undefined}>
            <summary className="break-all">{table.filename}</summary>
            <button className={button + ' break-all'} onClick={() => insert(sqlName(table.table_name))}>{table.table_name}</button>
            <ul>{table.columns.map(column => <li key={column.column_name}>
              <button className="text-left underline break-all" onClick={() => insert(sqlName(column.column_name))}>{column.column_name}</button>
              <span className="block text-xs break-all">{column.inferred_type} · {column.sample_values.map(show).join(', ') || 'No samples'}</span>
            </li>)}</ul>
          </details>)}
        </aside>
        <label className="block">Read-only SQL
          <textarea ref={editor} className={input + ' block w-full min-h-40 font-mono'} value={sql}
            onChange={event => setSql(event.target.value)} onKeyDown={event => {
              if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
                event.preventDefault();
                runSql();
              }
            }} />
        </label>
      </div>
      <div className="flex flex-wrap gap-2">
        <button className={button} disabled={busy || !sql.trim()} onClick={runSql}>Run SQL</button>
        <button className={button} disabled={busy || !sql.trim()} onClick={() => { setError(''); setReportOpen(true); }}>Save as Report</button>
      </div>
      {reportOpen && <dialog ref={reportDialog} onClose={() => setReportOpen(false)} aria-labelledby="report-title"
        className="m-auto w-full max-w-md rounded-xl border border-slate-600 bg-[var(--panel-background)] p-5 text-inherit backdrop:bg-slate-950/80">
        <form className="space-y-3" onSubmit={event => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        perform(async () => {
          await api('/saved-queries', 'POST', { name: data.get('name'), description: data.get('description'), sql, default_run_id: run.runId });
          await loadReports();
          reportDialog.current?.close();
        });
      }}>
        <h4 id="report-title" className="font-semibold">Save as Report</h4>
        {error && <p role="alert" className="text-rose-400">{error}</p>}
        <label className="block">Report name <input className={input + ' block w-full'} name="name" required maxLength={120} /></label>
        <label className="block">Description <input className={input + ' block w-full'} name="description" maxLength={1000} /></label>
        <div className="flex gap-2">
          <button className={button} disabled={busy}>Save</button>
          <button className={button} type="button" onClick={() => reportDialog.current?.close()}>Cancel</button>
        </div>
      </form></dialog>}
      <QueryResult result={sqlResult} name={run.runId + '-sql'} />
    </>}
    {tab === 'Insights' && (insights ? <Insights data={insights} busy={busy} inspect={action => {
      const column = columns.find(item => item.source_name === (action.missing_column ?? action.outlier_column));
      const conditions = action.outlier_column == null
        ? [['missing', '']]
        : [['lt', action.iqr_lower], ['gt', action.iqr_upper]];
      const selected = column ? conditions.map(([operator, value]) =>
        ({ column: column.column_name, operator, value, key: crypto.randomUUID() })) : [];
      const match = selected.length > 1 ? 'OR' : 'AND';
      setFilters(selected);
      setLogic(match);
      setTab('Guided Explorer');
      runFilter(action.preset || '', selected, action.issue || null, match);
    }} narrative={() => perform(async () => setInsights(await api(path + '/insights?narrative=true')))} /> : !error && <p role="status">Loading insights…</p>)}
    {tab === 'Audit & Export' && <div className="flex flex-wrap gap-2">
      {['csv', 'json', 'xlsx'].map(format => <button key={format} className={button} disabled={busy}
        onClick={() => perform(() => onExport(format))}>Download {format.toUpperCase()}</button>)}
      <a className={button} href={`${API}/runs/${run.runId}/audit`}>Download audit ZIP</a>
    </div>}
  </section>;
}

function Insights({ data, busy, inspect, narrative }) {
  const health = data.processing_health;
  const drift = health.drift;
  return <div className="space-y-4">
    <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {[['Processed rows', health.total_rows], ['Flagged rate', percent(health.flagged_rate)],
        ['Row change', drift?.row_delta ?? 'First run'], ['Readiness', health.readiness]].map(([label, value]) =>
        <div key={label} className="rounded border border-slate-700 p-2"><dt>{label}</dt><dd className="text-lg font-semibold">{value}</dd></div>)}
    </dl>
    <section className="space-y-2">
      <h4 className="font-semibold">Processing & Drift Insights</h4>
      <p>{health.duplicate_rows} duplicate rows across {health.duplicate_groups} groups · {health.resolution.open} open · {health.resolution.reviewed} reviewed · {health.resolution.resolved} resolved</p>
      <DataTable columns={['Column', 'Complete', 'Invalid rate', 'Missing change', 'Invalid change']}
        rows={Object.entries(health.completeness_rates).map(([column, rate]) => {
          const change = drift?.rate_changes.find(item => item.column === column);
          return [column, percent(rate), percent(health.invalid_rates[column]),
            change ? percent(change.missing_rate_delta) : '', change ? percent(change.invalid_rate_delta) : ''];
        })} />
      {drift && <p>Compared with {drift.previous_filename} ({drift.previous_run_id}) · Added {drift.added_columns.join(', ') || 'none'} · Removed {drift.removed_columns.join(', ') || 'none'}</p>}
      {!!health.issue_breakdown.length && <DataTable columns={['Column', 'Issue', 'Count']}
        rows={health.issue_breakdown.map(item => [item.column, item.issue, item.count])} />}
    </section>
    <section className="space-y-2">
      <h4 className="font-semibold">Dataset Profiles & Segment Breakdowns</h4>
      {data.column_profiles.map(({ column, type, top_values, iqr_lower, iqr_upper, ...stats }) => <details key={column}>
        <summary>{column} · {type}</summary>
        <dl className="grid grid-cols-2 gap-1">{Object.entries(stats).map(([name, value]) =>
          <div key={name}><dt className="inline">{name.replaceAll('_', ' ')} </dt><dd className="inline font-medium">{value ?? '—'}</dd></div>)}</dl>
        {!!stats.iqr_outliers && iqr_lower != null && iqr_upper != null && <button className={button} disabled={busy}
          onClick={() => inspect({ outlier_column: column, iqr_lower, iqr_upper })}>Inspect IQR outliers</button>}
        {!!top_values?.length && <DataTable columns={['Value', 'Count']} rows={top_values} />}
      </details>)}
      {data.segment_breakdowns.map(segment => <details key={segment.column}>
        <summary>Groups by {segment.column}</summary>
        <DataTable columns={['Group', 'Rows', 'Numeric summaries']}
          rows={segment.groups.map(group => [group.value, group.count,
            Object.entries(group.metrics).map(([metric, summary]) => `${metric} sum ${summary.sum}, mean ${summary.mean}`).join(' · ')])} />
      </details>)}
    </section>
    <section className="space-y-2">
      <h4 className="font-semibold">Recommended Actions</h4>
      {data.recommended_actions.map((action, i) => <div key={i} className="flex flex-wrap items-center gap-2">
        <span>{action.message}</span>
        {(action.preset || action.missing_column || action.issue) && <button className={button} disabled={busy} onClick={() => inspect(action)}>Inspect rows</button>}
      </div>)}
      {data.ai_available && <button className={button} disabled={busy} onClick={narrative}>Send aggregate metrics to Gemini for a summary</button>}
      {data.ai_summary && <p>{data.ai_summary}</p>}
    </section>
  </div>;
}
