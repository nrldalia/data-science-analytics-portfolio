# DataFlow Hub 2.0

### Turning messy operational data into clear, traceable workflows.

DataFlow Hub is a data processing and quality review application designed to help users prepare operational datasets with greater consistency and visibility.

Built with **Python, Flask, Pandas, SQLite, and React**, it brings file uploads, configurable cleaning rules, quality checks, and processing history into one interface.

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

SQLite stores processing information locally so users can return to previous work after restarting the application.

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

**Upload → Configure Rules → Process → Review → Explore → Export**

1. In **Quality Analytics**, select **Process a dataset** and choose a CSV, JSON, or Excel file up to 50 MB.
2. **Configure** the fields and preparation rules.
3. **Process** the full dataset.
4. **Review** previews, changes, and unresolved issues.
5. **Explore** the same run in Guided Explorer, SQL Studio, or Insights.
6. **Export** processed data and audit evidence. Select any saved run in Quality Analytics to reopen its workspace.

### Run workspace

| View | Use it to |
| :--- | :--- |
| Quality Review | Compare original and processed previews, inspect the cleaning log, and mark issues open, reviewed, or resolved. Review statuses record decisions without editing the snapshot. |
| Guided Explorer | Apply column filters with AND or OR, inspect flagged or missing-required rows, and run saved reports. The SQL preview shows placeholders and bound values. |
| SQL Studio | Insert table and column names from the schema sidebar, query or join processed runs, and run SQL with Ctrl/Command + Enter. Save a query as a guided report and export results as CSV or JSON. |
| Insights | Review completeness, invalid values, duplicates, and resolution coverage. Compare against the immediately preceding run, inspect column profiles and group summaries, and open affected rows from recommended actions. |
| Audit & Export | Download complete CSV, JSON, or XLSX output, or a ZIP with source, processed rows, rules, transformations, issues, review statuses, metadata, and the source hash. |

The **Data Streams** workspace continues to handle retailer batch jobs and its existing review and approval workflow.

### Architecture and API

Flask runs the cleaning rules and commits the processing record, audit evidence, and queryable SQLite snapshot in one transaction. Previously saved single-file runs are materialized from their stored processed rows when the workspace needs them. The API exposes the canonical names of the snapshot and columns, including disambiguated names when source headers collide. The reserved columns `__dataflow_row`, `__dataflow_flagged` and `__dataflow_missing_required` record row numbers and issue flags.

SQL Studio and saved reports execute against a read-only SQLite connection with an authorizer restricted to processed run tables and supported functions. Queries accept a single SELECT or WITH statement, have a 3-second execution budget, and preview up to 1,000 rows or 4 MiB. Guided Explorer binds filter values as parameters. SQLite records execution mode, statement, returned row count, and elapsed time in `query_logs`. Saved reports reference their original run and SQL statement.

| Method and path | Description |
| :--- | :--- |
| `POST /api/process` | Multipart upload with `file` and optional JSON `rules` |
| `GET /api/runs/<run_id>/schema` | Active run table and available join schemas |
| `POST /api/runs/<run_id>/query` | Run a read-only statement in `{"sql":"…"}` |
| `POST /api/runs/<run_id>/filter` | Apply `filters`, `logic`, an optional `preset`, and `limit` |
| `GET, POST /api/saved-queries` | List or save reusable reports |
| `POST, DELETE /api/saved-queries/<id>` | Run or remove a saved report |
| `GET /api/runs/<run_id>/insights` | Processing health, profiles, segments, and recommendations |
| `GET /api/runs/<run_id>/issue-reviews` | Read current issue-review statuses |
| `PUT /api/runs/<run_id>/issues/<index>` | Record a review status by zero-based issue index |

The existing `/api/v1` upload, history, export, and audit routes remain available. Set `DATAFLOW_DB` to use a separate SQLite file. Configured file reads and monitoring stay inside the enclosing Codex folder when present, or the DataFlow Hub folder in a standard GitHub checkout.

To enable the optional Insights narrative, set `DATAFLOW_AI_ENABLED=true` and `GEMINI_API_KEY`. The request runs only when a user selects the Gemini button or explicitly adds `?narrative=true` to the Insights request. It sends aggregate metrics and keeps deterministic results available independently.

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
| Storage | SQLite |
| Optional AI assistance | Gemini API |

## 🚀 Getting Started

### Requirements

- Python 3.11 or 3.12
- Node.js 20.19+ or 22.12+
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
.venv/bin/python script/app.py
```

Open **http://localhost:5000**.

### Try the Sample Dataset

Save the following as `retail.csv`, upload it in **Quality Analytics**, and configure the rules below.

```csv
store_id,sales,quantity,date
KL01,120.5,3,30/10/2026
KL02,bad,2,31/10/2026
KL03,,1,01/11/2026
KL03,,1,01/11/2026
```

| Setting | Value |
| :--- | :--- |
| Numeric fields | `sales, quantity` |
| Required fields | `store_id, sales` |
| Date field | `date` |
| Input date format | `%d/%m/%Y` |
| Trim whitespace | Enabled |

Run processing, inspect the reported changes and issues, then download the output and audit evidence.

### Run the backend tests

After building the frontend, install pytest in the same Python environment and run the API and workspace regression tests.

```sh
python -m pip install pytest
python -m pytest -q script/test_app.py script/test_run_workspace.py
```

## 📌 Scope and Limitations

DataFlow Hub is a **local portfolio application** demonstrating data preparation, quality review, and workflow design.

- It does not include authentication or multi-user access controls.
- Processing runs in memory, with a 50 MB upload limit.
- Numeric conversion expects plain numeric values; currency symbols are not automatically removed.
- Duplicate checks compare complete processed records.
- Uploaded files are not automatically mapped to individual client stores.
- Audit records provide traceability but are not tamper-proof.
- Optional AI assistance requires your own API credentials and connectivity.

The local database is created at `script/dataflow.db`. Stop the application before copying this file for backup. Keep credentials in environment variables and exclude private operational data from the repository.

