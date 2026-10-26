# Unreleased

- Fix demo fingerprint verification for Windows CRLF checkouts while retaining content verification and changed-file protection.

- Support native PostgreSQL on Windows without Docker Desktop; add connection setup and a step-by-step pgAdmin guide.

- Add preview/confirm CSV and XLSX store imports with templates, validation reports, and identity-preserving updates.
- Add searchable, sortable, filtered, paginated retailer store management.
- Add four reproducible synthetic retailer datasets with 300 stores each and an opt-in additive demo loader.

- Use local PostgreSQL through Docker Compose for normal development.
- Add verified, read-only SQLite import with destination protection.
- Preserve generated IDs, store codes, audit evidence and processing history.
- Add isolated PostgreSQL test runner, backup guidance and private local setup.
- Make input-file scope configurable so startup works outside a Codex directory.

# Improved original v1.0

Restored the original React + Vite + Tailwind / Flask + Pandas / SQLite stack and navigation. Improved the existing code rather than replacing the interface with a different framework. Reworked sample-only AI cleaning into full deterministic processing with optional Gemini assistance. Added explicit cleaning configuration, source-preserving previews, run-specific audits, full exports, saved history, persistent edits, genuine metrics, visible connectivity failures, Excel support and corrected setup instructions.

Future passes can add client column mappings, reusable rule templates and the broader FlowTrade modules after review. No GitHub changes, commits or tags were published by this task.
