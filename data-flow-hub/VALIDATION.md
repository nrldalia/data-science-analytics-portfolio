# Release validation — 1.0.0-rc.1

Verified in the Linux development environment using Python 3.12, Node.js 24.19.0
and PostgreSQL 17.11. This is a **local single-user release candidate**.

## Automated results

- **203 tests discovered: 201 passed, 2 skipped, 0 failures, 0 errors.**
- The two skipped tests exercise Windows DPAPI password storage. Their original
  encryption assertions remain active on Windows; this Linux run cannot verify them.
- Explicit unsupported-platform tests verify password storage is rejected without
  saving a secret or changing configuration/history. Unencrypted workbooks remain usable.
- The React production build passes.

Coverage includes original upload bytes/hashes, CSV/JSON/XLSX processing/export,
formula-safe spreadsheet exports, store imports, search/filter/pagination,
configuration history, failure evidence, before/after capture, exception
acknowledgement, review fingerprints, retry lineage/duplicate rejection,
reconciliation, approval, retained cancellation audit and interrupted-run recovery.

Operational trend checks cover latest-approved scope selection, profile isolation,
frozen store rosters, inactive/unknown IDs, missing ISO weeks, revisions, weighted
rolling coverage, quality availability, valid duration percentiles, and logical
submission/reprocessing rates.

## Real worker and browser checks

The browser walkthrough uses production spawned workers and a disposable
PostgreSQL schema, without fake execution or application-data changes.

Passed:
- Valid processing and actual row-level failure findings.
- No private invalid-cell values in global job lists.
- Before/after transformation events visible in processing details.
- Explicit acknowledgement without automatic approval.
- Preprocessing handoff for safe reprocessing.
- Direct processed CSV, JSON and XLSX downloads.
- Exceptions CSV and evidence ZIP downloads.
- Approved-only weekly totals with missing-week gaps, revisions and pending results.
- Source-run drill-down and trend CSV export.
- Desktop/mobile rendering without horizontal page overflow.
- Settings showing the actual PostgreSQL engine, version and deployment scope.
- No JavaScript page errors.

The local server session lock rejects a second server for the same database/schema,
and releases on close. A second real server process on a different port was
rejected during the browser check. Ordinary CLI imports do not cancel active jobs.
Restart recovery is explicit and idempotent.

## Data and limits

- Tests and browser runs use isolated schemas; no test approvals were added to the
  development application's business history.
- Existing source SQLite database remains unchanged.
- Four-retailer store fixtures remain 300 stores each. The new eight-week processing
  fixtures are synthetic and require deliberate manual processing/approval.
- Detailed evidence is bounded; reports expose availability/truncation notes.
- Positive Windows encryption, Windows launcher execution, public deployment,
  multi-user access, AI requests and published-cloud restoration were not verified.
- Backup/restore and source migration were verified in earlier setup work; no new
  database restore was required by this release.

## Reproduce

From data-flow-hub with the virtual environment active and PostgreSQL available:

    npm run build
    python script/check_postgres.py --log-dir .artifacts/release-tests

The runner creates and removes an isolated schema for each test module. Do not
point direct mutable test suites at application data. Some legacy migration unit
tests intentionally use in-memory SQLite fixtures.

The final Windows operator walkthrough is in docs/RELEASE_1_0.md. Completing it on
the intended machine is the remaining acceptance step before designating 1.0.0.
