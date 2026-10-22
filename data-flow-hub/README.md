# DataFlow Hub

### Turning messy operational data into clear, traceable workflows.

DataFlow Hub is a data processing and quality review application designed to help users prepare operational datasets with greater consistency and visibility.

Built with **Python, Flask, Pandas, PostgreSQL, and React**, it brings file uploads, configurable cleaning rules, quality checks, and processing history into one interface.

## 🌍 Vision

To make reliable data preparation accessible, understandable, and traceable; so people can spend more time using their data and less time correcting it.

## 🎯 Mission

To simplify repetitive data preparation through explicit processing rules, visible quality checks, and preserved evidence of each run.

DataFlow Hub aims to give users control over how their data is processed and a clear understanding of what changed, what remains unresolved, and what needs further review.

## 💡 Purpose

Operational datasets often arrive with inconsistent formatting, missing fields, duplicate records, and invalid values. Handling these issues manually can be repetitive and makes it difficult to explain how a final dataset was produced.

DataFlow Hub provides a structured workflow to:

- Consolidate common preparation tasks in one application.
- Apply consistent rules across an uploaded dataset.
- Identify quality issues without silently discarding records.
- Compare original data with processed results.
- Preserve processing history and supporting evidence.
- Produce downloadable datasets for further analysis.

## 🔍 What DataFlow Hub Does

### Configurable Data Preparation

Upload **CSV, JSON, or Excel (`.xlsx`)** files and choose the rules to apply before processing.

Available rules include:

- Trimming leading and trailing whitespace.
- Converting specified fields to numeric values.
- Standardising dates using an explicit input format.
- Checking required fields for missing values.
- Flagging duplicate records.

Excel imports use the first worksheet.

### Visible Quality Checks

Review original and processed previews alongside reported issues and transformation details.

Invalid numeric and date values are flagged for review rather than replaced with invented values. Duplicate records are retained and identified, allowing users to decide how to handle them.

### Processing History

Reopen saved processing runs to review their results, rules, issues, and transformation records.

PostgreSQL stores processing information locally so users can return to previous work after restarting the application.

### Full-Dataset Exports and Audit Evidence

Download processed data in CSV, JSON, or Excel format.

Each saved run also supports an audit ZIP containing:

- The original uploaded file.
- The processed output.
- The applied rules.
- Recorded transformations.
- Reported quality issues.
- Run metadata and a source-file hash.

### Optional AI Assistance

With explicit consent, users can share a limited sample with an optional Gemini integration to receive explanations and suggested rules.

AI supports interpretation; it does not automatically modify records. Core processing works independently of AI availability.

## 🔄 Workflow

**Upload → Configure Rules → Process → Review → Export**

1. **Upload** a supported dataset.
2. **Configure** the fields and preparation rules.
3. **Process** the full dataset.
4. **Review** previews, changes, and unresolved issues.
5. **Export** the processed data and supporting evidence.

## 📊 Intended Outcomes

DataFlow Hub is designed to support:

| Outcome | How the application supports it |
| :--- | :--- |
| More consistent data preparation | Applies configured rules across every record in a run. |
| Less repetitive manual work | Combines common cleaning and validation steps into one workflow. |
| Clearer quality review | Makes missing values, invalid values, and duplicates visible. |
| Greater traceability | Preserves source files, rules, transformations, and outputs. |
| Easier handover | Provides downloadable results and evidence for further review. |

These are intended benefits of the workflow, rather than measured claims of time savings or business impact. Processed data may still contain flagged issues requiring human judgment.

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| Frontend | React, Vite, Tailwind CSS |
| Backend | Python, Flask |
| Data processing | Pandas |
| Storage | PostgreSQL |
| Optional AI assistance | Gemini API |

## 🚀 Getting Started

### Requirements

- Python 3.11 or 3.12
- Node.js 20.19+ or 22.12+
- Docker with Compose v2 for local PostgreSQL
- Internet access for the initial dependency installation

Run the following steps from the **DataFlow Hub project folder**.

### Windows

1. Run `Setup_Windows.bat` to install dependencies and build the frontend.
2. Run `Start_DataFlow.bat`.
3. Open **http://localhost:5000** in your browser.
4. Keep the terminal open while using the application.

### Linux / macOS

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r script/requirements.txt
npm ci
npm run build
.venv/bin/python script/dev_database.py
docker compose up -d --wait
.venv/bin/python script/app.py
```

Local input files are restricted to the DataFlow Hub project directory by default.
Existing installations inside a folder named `Codex` retain that folder as their
input boundary. To use another existing directory, set `DATAFLOW_INPUT_ROOT` to
its absolute path before starting the backend, for example:

```sh
export DATAFLOW_INPUT_ROOT=/absolute/path/to/incoming
.venv/bin/python script/app.py
```

Paths and symlinks that resolve outside this boundary are rejected.

Open **http://localhost:5000**.

### Try the Sample Dataset

Upload [`sample_data/retail.csv`](./sample_data/retail.csv) and configure:

| Setting | Value |
| :--- | :--- |
| Numeric fields | `sales, quantity` |
| Required fields | `store_id, sales` |
| Date field | `date` |
| Input date format | `%d/%m/%Y` |
| Trim whitespace | Enabled |

Run processing, inspect the reported changes and issues, then download the output and audit evidence.

## 📌 Scope and Limitations

DataFlow Hub is a **local portfolio application** demonstrating data preparation, quality review, and workflow design.

- It does not include authentication or multi-user access controls.
- Processing runs in memory, with a 50 MB upload limit.
- Numeric conversion expects plain numeric values; currency symbols are not automatically removed.
- Duplicate checks compare complete processed records.
- Uploaded files are not automatically mapped to individual client stores.
- Audit records provide traceability but are not tamper-proof.
- Optional AI assistance requires your own API credentials and connectivity.

PostgreSQL runs locally through Docker Compose, bound to `127.0.0.1:55432`.
Its data is retained in the `dataflow-postgres` Docker volume. Normal
`docker compose down` preserves data; `docker compose down -v` deletes it.

`script/dev_database.py` creates a private, ignored `.env` with a random local
password and `DATABASE_URL`; existing settings are never overwritten. Use
`.env.example` as a template if configuring PostgreSQL yourself. Keep credentials
and private operational data out of Git. A new empty database starts with demo
stores; set `DATAFLOW_SEED_DEMO=0` to disable that seed.

### Transfer the existing SQLite database

Before the first app launch, with dependencies installed and PostgreSQL running:

```sh
.venv/bin/python script/migrate_sqlite.py script/dataflow.db
```

The importer opens SQLite read-only, checks its integrity, and requires an empty
PostgreSQL destination. It copies records in one transaction, verifies row counts
and content fingerprints, preserves store codes and receipt order, and advances
generated ID sequences. It refuses to overwrite a populated destination.
The source file remains available for rollback. Review the local source before
importing; it may contain saved application records. Older incompatible schemas
are rejected rather than partially imported.

PostgreSQL schema migrations are recorded in `schema_migrations`; component
initializers retain the existing application schema and history upgrade behavior.
An explicitly set `DATAFLOW_DB` without `DATABASE_URL` retains SQLite access for
legacy tests and migration work. Normal development uses PostgreSQL.

### Validate and back up

Activate the virtual environment, then run:

```sh
npm run build
npm run test:postgres
```

The PostgreSQL runner creates a disposable schema for each test module and removes
it afterward. It never runs those tests against your application tables.
The local database user needs permission to create schemas for these checks.
The existing `npm run test:backend` command remains a quick eight-test legacy check.

Password storage for encrypted Excel files currently requires Windows user
encryption; its two existing tests fail on Linux. Do not use the Linux demo for
saved spreadsheet passwords.

For a database backup:

```sh
mkdir -p backups
docker compose exec -T postgres pg_dump -U dataflow -d dataflow -Fc > backups/dataflow.dump
```

Keep backups private. Local Compose is a development setup; production deployment,
authentication and managed database configuration require separate work.

