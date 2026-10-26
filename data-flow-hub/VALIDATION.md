# Validation

Validated on Linux with Python 3.12, Node.js 24.19.0 and local PostgreSQL 17.11.

- React production build passes.
- PostgreSQL backend run: 153 tests executed, 151 passed, 2 failed.
- The two failures are existing spreadsheet password tests:
  - `test_sheet_secret_is_encrypted_and_not_in_history`
  - `test_password_yes_requires_secret_and_no_hides_and_clears`
  Their implementation explicitly requires Windows user encryption.
- Passing coverage includes uploads, CSV/Excel exports, audit evidence, batch
  processing and history, cancellation/reprocessing, configuration versions,
  KPI metrics, store management, and concurrent store-code allocation.
- New PostgreSQL regression tests verify parameter handling, binary storage,
  generated IDs, transaction rollback, verified SQLite import, source preservation,
  and refusal to overwrite a populated destination.
- Imported 42 rows across 20 existing SQLite tables. Counts and content
  fingerprints matched before commit; the source SQLite file remains unchanged.
- Imported history survives PostgreSQL stop/start.
- Live HTTP checks pass for health, stores, run history, and the built React page.
- A private local backup was restored into a separate disposable database;
  imported history, the import receipt, and the store API were verified.

Run `npm run test:postgres` with the Python virtual environment active.
The runner isolates each module in a temporary PostgreSQL schema. Some legacy
migration unit tests intentionally exercise in-memory SQLite fixtures.

## Bulk store import and store management

- Ten backend regression tests pass for CSV/XLSX templates and imports,
  validation, preview expiry/staleness/replay, atomic rollback, identity/code
  preservation, history, search, filtering, sorting, and pagination.
- Seven independent acceptance tests pass, including four retailers with
  exactly 300 stores each (1,200 distinct internal IDs/codes), update preservation,
  invalid-row blocking, cross-retailer isolation, leading-zero IDs, and loader
  idempotence/conflict preflight.
- Chromium browser checks exercise template download, a 300-store preview and
  confirmation, pagination, editing the correct store from page 2, status
  filtering, search/empty state, invalid-import blocking, error-report download,
  and mobile rendering. No JavaScript page errors were reported.
- Upload review checks cover formula-safe error CSV output, bounded CSV/XLSX
  parsing, compressed/expanded/member/worksheet-dimension limits and XLSX formula rejection.
- Four synthetic demo retailers were loaded additively in the local development
  database, with 300 stores each. Repeating the loader changed no records.

Live AI calls, Windows launchers, production deployment and restoration in a newly
published cloud task were not tested.

## Native Windows database setup

- Seven focused configuration tests pass: credential encoding and dotenv roundtrip,
  preservation of existing files, no-prompt checking, connection failure without
  credential disclosure or file creation, validated setup/reuse, local host/port
  validation, and environment-variable precedence.
- The connection helper's noninteractive check passed against the running local
  PostgreSQL server using only SELECT 1. This is protocol-level validation on Linux,
  not proof that a native Windows PostgreSQL service has been installed or tested.
- Windows launchers no longer invoke Docker and use the native connection helper.
  Windows batch execution and the pgAdmin installation steps remain untested here.

## Windows demo fixture line endings

Three regression tests pass for equivalent CRLF checkouts, rejection of edited
content with either line ending, and non-overwriting generator reruns. The
manifest remains the authoritative LF fingerprint; no checksums were replaced.
