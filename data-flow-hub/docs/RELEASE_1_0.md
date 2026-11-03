# DataFlow Hub 1.0 release scope

## Release decision

Recommended go-live: **1.0.0, local single-user edition**.
The current build is **1.0.0-rc.1**, pending the Windows acceptance walkthrough below.
This release is for one operator on their own computer with PostgreSQL. It is
not a public website or an authenticated multi-user service.

The objective is: **upload operational data, apply explicit preparation rules,
review quality issues and transformations, and export results with traceable evidence**.

## Included

- Retailer setup, stable store identities/codes, CSV/XLSX bulk store imports,
  previews and confirmation, store search, filters, sorting and pagination.
- Four optional synthetic retailers with 300 stores each.
- CSV, JSON and unencrypted XLSX processing, configured input profiles and rules.
- Preprocessing checks before launch, observed progress and safe reprocessing.
- Captured findings, bounded before/after transformation events, row/store
  reconciliation, exception acknowledgement and deliberate approval.
- Direct processed CSV/JSON/XLSX downloads from completed runs.
- Original source preservation, source hashes, configuration versions,
  per-run history, exception CSV and downloadable evidence ZIP.
- Weekly operational trends using one latest approved result per
  retailer/input profile/business week. Historical store rosters remain frozen;
  missing or unavailable values remain gaps.
- Local Windows PostgreSQL setup, a database health check, one server instance
  per database/schema, interrupted-run recovery, and backup guidance.

Navigation is focused on Client, Data Streams, KPI Records and Settings.
The disconnected legacy quality/AI/email screens are removed from release
navigation. Existing historical standalone-upload records and their legacy API
remain available; this change does not delete records.

## Deliberately deferred

- Agentic/AI processing, model training and automatic business decisions.
- Public hosting, accounts, permissions and multi-user collaboration.
- Broader sales/product analytics, forecasting and anomaly detection.
- Cross-platform saved passwords for encrypted workbooks.
- Delivery SLA/on-time metrics until real deadline snapshots are captured.
- Distributed workers, unattended scheduling and automatic email delivery.
- CI/CD deployment automation and portfolio/LinkedIn presentation polish.

None of these is required to demonstrate the core preparation workflow.

## What review means

A processing acknowledgement records that an operator inspected evidence. It does
not modify a cell, fix an invalid file, register unknown stores or approve a run.
Existing flagged financial KPI checks still require their separate manual review.
Approval is an explicit action and publishes the eligible run for operational trends.
Cancelled runs never contribute a published result.

Changes displayed in processing details are captured rule-attempt events, including
failed/retried attempts; they are not a final-output preview. The report displays
up to 25 changes. Detailed retained evidence is capped at 5,000 events per run,
with availability/truncation notes. The ZIP retains the original uploaded bytes
and the available output; cancelled runs have no published output.

## Windows acceptance walkthrough

1. Back up an existing database before updating; see WINDOWS_SETUP.md.
2. In the cloned repository on feat/dataflow-postgresql, run git pull --ff-only.
3. Ensure the existing PostgreSQL server is running, then run Setup_Windows.bat.
   Keep existing .env credentials private; setup must not overwrite them.
4. Run Start_DataFlow.bat. It opens the browser once the app is healthy.
   Confirm Settings shows version 1.0.0-rc.1 and PostgreSQL.
5. Open a demo retailer and confirm its stores can be searched and edited.
6. Follow sample_data/processing_demo/README.md to configure the numeric rule
   and process one valid weekly file through Data Streams.
7. Open Processing details. Check input/output counts, captured transformations,
   store coverage and findings; download the evidence ZIP and exceptions CSV.
8. Process failed_numeric.csv. Verify it cannot be approved and that the original
   file and captured failure evidence remain downloadable.
9. Review a completed run, approve deliberately, and select its business week in
   KPI Records. Verify the source run and approved coverage. Do not approve a
   failed run merely to populate a chart.
10. Reprocess a completed source. Confirm it has a new run ID, a recorded parent
    and retained history; repeated clicks must not create duplicate active retries.
11. Stop and reopen the app. Confirm completed history remains. An interrupted
    run is recovered as stopped, with original input retained.

After these checks pass on the intended Windows machine, the release can be
designated 1.0.0. Public deployment or merging into main requires explicit approval.

## Operating boundaries

- Keep one server instance open per database/schema. The server lock rejects a
  second instance; ordinary CLI imports no longer cancel active jobs.
- PostgreSQL must run separately. The launcher verifies it but does not install
  a Windows service. If it was started manually, start it again after a reboot.
- The server binds to loopback. Do not expose it publicly or use a multi-worker
  server as this release has no authentication and uses local background workers.
- Keep .env, uploaded business data and backups out of Git. The evidence ZIP
  includes source data and should be treated as private.
- Unencrypted workbooks are the release input path. Positive Windows DPAPI
  password-storage tests cannot be verified on the Linux development machine;
  unsupported-platform rejection remains explicitly tested.
