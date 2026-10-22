# Validation

Validated on Linux with Python 3.12, Node.js 24.19.0 and local PostgreSQL 17.11.

- React production build passes.
- PostgreSQL backend run: 136 tests executed, 134 passed, 2 failed.
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

Live AI calls, Windows launchers, browser interaction, production deployment and
restoration in a newly published cloud task were not tested.
