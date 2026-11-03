# Priority 4 operational processing demo

These are **synthetic development fixtures**, not actual retailer transactions or
financial performance evidence. The sales and quantity values are deliberately
invented so a numeric rule can process the files. This package demonstrates
processing, store reconciliation and operational history; it does not establish
sales growth, profitability, on-time delivery or service-level compliance.

## Prerequisite

Load the four-retailer store demo using the instructions in
[the store-import guide](../store_import/README.md). Use **Aurora Demo Grocer**,
retailer key `DEMO_AURORA`. The expected results below assume its original
300-store roster: **285 Active and 15 Inactive**.

Do not reset or replace edited application records to reproduce these examples.
If Aurora's actual roster differs, the app should use the roster it captures at
launch, and its reconciliation can legitimately differ from this fixture manifest.

## Files and expected reconciliation

All CSV files use three columns: `store_id`, `sales`, `quantity`.
Store IDs come from the existing Aurora store-import fixture. Clean weekly files
contain one row per received expected active store and no unknown/inactive IDs.

| File | Select business week | Rows / expected active stores received | Missing active stores | Coverage |
| --- | --- | ---: | ---: | ---: |
| `aurora_2026-W37.csv` | `2026-W37` | 285 / 285 | 0 | 100.00% |
| `aurora_2026-W38.csv` | `2026-W38` | 285 / 285 | 0 | 100.00% |
| `aurora_2026-W39.csv` | `2026-W39` | 280 / 285 | 5 | 98.25% |
| `aurora_2026-W40.csv` | `2026-W40` | 285 / 285 | 0 | 100.00% |
| `aurora_2026-W41.csv` | `2026-W41` | 275 / 285 | 10 | 96.49% |
| `aurora_2026-W42.csv` | `2026-W42` | 285 / 285 | 0 | 100.00% |
| `aurora_2026-W43.csv` | `2026-W43` | 270 / 285 | 15 | 94.74% |
| `aurora_2026-W44.csv` | `2026-W44` | 280 / 285 | 5 | 98.25% |

`manifest.json` documents exact missing IDs and fixture expectations. A reporting
week is separate from the actual upload/processing time. Selecting an older week
does not make the file arrive on time for that week.

## Configure one simple processing rule

1. Open **Client → Edit Aurora Demo Grocer → Rules Configure**.
2. Add a **Transformation** component/rule with:
   - Name: **Convert sales to number**
   - Operation: **Convert to number** (`numeric`)
   - Field: `sales`
   - Description: **Validate and convert synthetic sales without inventing missing amounts.**
3. Apply/save the rule, then **Save Configuration**.
4. Keep any unrelated rules and mappings intact. Additional rules that reference
   other columns may intentionally reject this small fixture; use a deliberately
   configured test retailer/profile if the existing setup needs other fields.

The complete machine-readable suggested rule is included in `manifest.json`.
No join or sales-KPI rule is required for the initial operational walkthrough.

## Process and deliberately approve a weekly file

1. Open **Data Streams → New Batch Job**.
2. Select **Aurora Demo Grocer**.
3. Enter the business ISO week matching the file name, for example `2026-W37`.
4. Select **Legacy CSV / Excel / JSON defaults** for this simple CSV walkthrough.
   If you use a saved input profile instead, configure it for comma-separated CSV,
   UTF-8, header row 1 and these three columns, and keep the same profile scope
   when comparing weeks. Do not mix unrelated input profiles into one trend.
5. Select the matching weekly CSV. Enter `store_id` as the Store ID field override.
6. Click **Check Preprocessing**. Review its errors and warnings.
7. If ready, click **Start Job**. Observe the actual stage, rule attempts and final
   state; do not close the app while it is processing.
8. Open the run's report/evidence and review the received rows, expected-store
   coverage, missing stores, rule outcomes and configuration version.
9. **Only after your review**, use the app's explicit review/approval controls.
   Approval is a product decision, not something these files or generator perform.
10. Repeat for the other weeks as desired, then open **KPI Records** and its weekly
    operational trends. A week with no approved result should remain a gap or
    provisional result, not a zero. Repeated attempts for one scope/week must not
    inflate the published trend.

A normal completion and publication are separate. Existing per-run sales KPI
checks, if added separately, retain their own baselines and review requirements.
The operational trend should clearly identify its approved source run.

## Failed numeric example

Use `failed_numeric.csv` with business week `2026-W44` and the same numeric rule.
There are ten input rows and **three invalid sales cells**, on CSV lines
**3, 6 and 10** (data rows 2, 5 and 9). The expected active-store coverage is
10 / 285 if the input mapping has been captured, but numeric processing must fail.

- Inspect the failure/exception evidence and bounded retry results.
- A review note does not correct the source or turn a cancelled job into an
  approvable result.
- For a successful retry demonstration, make a separate corrected copy with values
  you explicitly choose for the synthetic exercise, rerun preprocessing, and
  submit it as a new run. Keep the original failed fixture and run intact.
- Reprocessing the unchanged invalid source with the unchanged numeric rule is
  expected to fail again; a retry must not fabricate replacement values.

## Unknown and inactive store example

Use `unknown_store.csv`, business week `2026-W44`, and `store_id` override.
Its 277 rows comprise:

- 275 expected active Aurora stores.
- One known inactive store, `DEMO_AURORA-020`.
- One fictional unknown store, `DEMO_AURORA-UNKNOWN`.

Numeric conversion can pass, but reconciliation should show **ten missing active
stores and one unknown store**. Coverage is **275 / 285 = 96.49%**, not 277 / 285.
Review the unknown/inactive findings deliberately. Do not register the synthetic
unknown store merely to clear a warning; doing so changes the roster for future
runs and this fixture's expected results. New-store registration and job approval
remain separate actions.

If a clean W44 result has already been approved, this example is another attempt
in that scope/week. Do not approve it unless you intentionally want that revision
used by the publication policy. Previous attempts and their evidence remain.

## Reproduce the fixtures

From `data-flow-hub`, with the project's Python environment:

```sh
.venv/bin/python script/generate_processing_demo.py
```

On Windows:

```bat
.venv\Scripts\python.exe script\generate_processing_demo.py
```

The generator reads the existing Aurora store fixture and writes only its own
known fixture filenames. It never connects to a database, launches jobs, approves
results or changes store records. Identical reruns are safe, including equivalent
Windows CRLF checkouts. Modified output files and symlink destinations are refused;
use a new output folder inside `data-flow-hub` to preserve your changes.

For this fixed demo, set KPI Records ending week to **2026-W44** and show **8 weeks**.
The application's default is the current business week; later weeks without an
approved demo run correctly appear as missing rather than zero.
