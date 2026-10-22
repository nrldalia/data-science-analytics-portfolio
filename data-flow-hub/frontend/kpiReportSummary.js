// Read saved results only: this summary does not recalculate or change a job.
export function reportSummary(kpi) {
  if (!kpi) return { worstStore: null, flaggedStores: 0, unavailableStores: 0, totalStores: 0, reasons: [] };
  const stores = kpi.stores || [];
  const available = stores.filter(s => typeof s.percent === 'number' && Number.isFinite(s.percent));
  const worstStore = available.reduce((worst, store) => !worst || Math.abs(store.percent) > Math.abs(worst.percent) ? store : worst, null);
  const reasons = [];
  const add = value => { if (!reasons.includes(value)) reasons.push(value); };
  if (kpi.flagged) {
    for (const flag of kpi.flags || []) {
      if (/^One or more stores /i.test(flag)) add('Store sales');
      else if (/^Retailer sales /i.test(flag)) add('Retailer sales');
      else if (/^(Rows Count|Row-count percentage) /i.test(flag)) add('Row count');
      else if (/^No eligible previous-week baseline/i.test(flag)) add('Insufficient history');
      else if (/^(Select Sales, Quantity|\d+ rows have missing or invalid KPI fields|KPI totals exceed)/i.test(flag)) add('KPI fields');
      else add('Other KPI check');
    }
    if (!reasons.length) add('Other KPI check');
  }
  return {
    worstStore,
    flaggedStores: stores.filter(s => s.flagged).length,
    unavailableStores: stores.filter(s => typeof s.percent !== 'number' || !Number.isFinite(s.percent)).length,
    totalStores: stores.length,
    reasons,
  };
}
