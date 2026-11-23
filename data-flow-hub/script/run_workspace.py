"""Queryable run snapshots, guided filters, and saved reports."""
import json
import math
import re
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from time import monotonic

import database
from flask import Blueprint, jsonify, request

workspace = Blueprint("run_workspace", __name__, url_prefix="/api")
ROW = "__dataflow_row"
FLAG = "__dataflow_flagged"
MISSING = "__dataflow_missing_required"
MAX_ROWS = 1000

SCHEMA = """
CREATE TABLE IF NOT EXISTS workspace_runs (
    run_id TEXT PRIMARY KEY, table_name TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS run_schemas (
    run_id TEXT NOT NULL, table_name TEXT NOT NULL, column_name TEXT NOT NULL,
    source_name TEXT NOT NULL, inferred_type TEXT NOT NULL, null_count INTEGER NOT NULL,
    sample_values_json TEXT NOT NULL, PRIMARY KEY (run_id, column_name)
);
CREATE TABLE IF NOT EXISTS saved_queries (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT,
    sql_text TEXT NOT NULL, default_run_id TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS query_logs (
    id INTEGER PRIMARY KEY, run_id TEXT, mode TEXT NOT NULL, sql_executed TEXT NOT NULL,
    row_count INTEGER NOT NULL, execution_ms REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS workspace_issues (
    run_id TEXT NOT NULL, row_number INTEGER NOT NULL, field TEXT NOT NULL, issue TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS workspace_issues_lookup ON workspace_issues (run_id, field, issue, row_number);
CREATE TABLE IF NOT EXISTS run_issue_reviews (
    run_id TEXT NOT NULL, issue_index INTEGER NOT NULL, status TEXT NOT NULL,
    PRIMARY KEY (run_id, issue_index)
);
"""


def identifier(name):
    return '"' + name.replace('"', '""') + '"'


def missing(value):
    return value is None or isinstance(value, str) and not value.strip()


def numeric(value):
    if type(value) is int:
        return abs(value) <= 10**308
    return type(value) is float and math.isfinite(value)


def valid_date(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def sql_value(value):
    if isinstance(value, (dict, list)) or type(value) is int and not -(2**63) <= value < 2**63:
        return json.dumps(value, ensure_ascii=False)
    return value


def persist_run(conn, rid, rows, issues, rules):
    table = "run_data_" + rid.replace("-", "_")
    source_columns = dict.fromkeys(key for row in rows for key in row)
    names = {ROW, FLAG, MISSING, "rowid", "_rowid_", "oid"}
    columns = []
    for source in source_columns:
        base = source.replace(chr(0), "_") or "column"
        name = base
        suffix = 2
        while name.lower() in names:
            name = f"{base}_{suffix}"
            suffix += 1
        names.add(name.lower())
        columns.append((source, name))

    flagged = {issue["row"] for issue in issues}
    missing_required = {issue["row"] for issue in issues if issue["issue"] == "Missing required value"}
    conn.execute("INSERT INTO workspace_runs VALUES (?, ?)", (rid, table))
    conn.executemany(
        "INSERT INTO workspace_issues VALUES (?,?,?,?)",
        ((rid, issue["row"], issue["field"], issue["issue"]) for issue in issues),
    )
    names_sql = ", ".join(map(identifier, [ROW, FLAG, MISSING] + [name for _, name in columns]))
    conn.execute(f"CREATE TABLE {identifier(table)} ({names_sql})")
    placeholders = ", ".join(["?"] * (3 + len(columns)))
    conn.executemany(
        f"INSERT INTO {identifier(table)} VALUES ({placeholders})",
        ([i, i in flagged, i in missing_required, *(sql_value(row.get(source)) for source, _ in columns)]
         for i, row in enumerate(rows, 1)),
    )
    for source, name in columns:
        values = [row.get(source) for row in rows if not missing(row.get(source))]
        if source in rules.get("dateFields", []) or values and all(map(valid_date, values)):
            kind = "date"
        elif source in rules.get("numericFields", []) or values and all(map(numeric, values)):
            kind = "numeric"
        elif values and all(type(value) is bool for value in values):
            kind = "boolean"
        else:
            kind = "text"
        samples = []
        for value in values:
            encoded = json.dumps(value, ensure_ascii=False)
            if len(encoded) <= 500 and encoded not in samples:
                samples.append(encoded)
                if len(samples) == 5:
                    break
        conn.execute("INSERT INTO run_schemas VALUES (?, ?, ?, ?, ?, ?, ?)", (
            rid, table, name, source, kind, len(rows) - len(values), "[" + ",".join(samples) + "]",
        ))


def ensure_snapshots():
    with database.get_db_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        pending = conn.execute("""
            SELECT p.id, p.output, p.issues, p.rules FROM processing_runs AS p
            LEFT JOIN workspace_runs AS w ON p.id = w.run_id WHERE w.run_id IS NULL
        """)
        for run in pending:
            persist_run(conn, run["id"], json.loads(run["output"]), json.loads(run["issues"]), json.loads(run["rules"]))


def table_for(rid):
    with database.get_db_connection() as conn:
        row = conn.execute("SELECT table_name FROM workspace_runs WHERE run_id = ?", (rid,)).fetchone()
    if row is None:
        ensure_snapshots()
        with database.get_db_connection() as conn:
            row = conn.execute("SELECT table_name FROM workspace_runs WHERE run_id = ?", (rid,)).fetchone()
    if row is None:
        raise WorkspaceError("Run not found.", 404)
    return row[0]


class WorkspaceError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


@workspace.errorhandler(WorkspaceError)
def workspace_error(exc):
    return jsonify(error=str(exc)), exc.status


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise WorkspaceError("Send a JSON object.")
    return data


SQL_TOKENS = re.compile(
    r"""--[^\n]*|/\*.*?\*/|'(?:''|[^'])*'|"(?:""|[^"])*"|`(?:``|[^`])*`|\[[^\]]*\]|[A-Za-z_][A-Za-z_0-9]*|;""",
    re.DOTALL,
)
BLOCKED = set("ALTER ANALYZE ATTACH CREATE DELETE DETACH DROP INSERT PRAGMA REINDEX REPLACE UPDATE VACUUM".split())
FUNCTIONS = set("""
    abs avg cast ceil ceiling char coalesce concat count date datetime dense_rank floor
    format glob group_concat hex ifnull instr julianday lag lead length like lower
    ltrim max min nullif printf rank replace round row_number rtrim strftime substr
    substring sum time total trim typeof unicode unixepoch upper
""".split())


def validate_sql(sql):
    if not isinstance(sql, str) or len(sql) > 20_000 or not re.match(r"\s*(SELECT|WITH)\b", sql, re.I):
        raise WorkspaceError("Enter one SELECT or WITH statement.")
    if any(token.upper() in BLOCKED or token == ";" for token in SQL_TOKENS.findall(sql)):
        raise WorkspaceError("Only a single read-only statement without a semicolon is allowed.")
    return sql


def execute(rid, mode, sql, params=(), limit=MAX_ROWS, log=True):
    with database.get_db_connection() as metadata:
        tables = {r[0] for r in metadata.execute("SELECT table_name FROM workspace_runs")}

    def authorize(action, first, second, schema, trigger):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        allowed_table = first in tables or mode == "guided_filter" and first == "workspace_issues"
        if action == sqlite3.SQLITE_READ and allowed_table and schema in ("main", None):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (second or "").lower() in FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    start = monotonic()
    uri = Path(database.DB_FILE).resolve().as_uri() + "?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=0.5)) as conn:
            conn.execute("PRAGMA query_only=ON")
            conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 2 * 1024 * 1024)
            conn.set_authorizer(authorize)
            conn.set_progress_handler(lambda: monotonic() - start >= 3, 1000)
            result = conn.execute(sql, params)
            columns = [column[0] for column in result.description]
            rows = []
            size = 0
            truncated = False
            for row in result:
                row = tuple(value.hex() if isinstance(value, bytes) else
                            None if isinstance(value, float) and not math.isfinite(value) else value
                            for value in row)
                size += len(json.dumps(row, ensure_ascii=False))
                if len(rows) >= limit or size > 4 * 1024 * 1024:
                    truncated = True
                    break
                rows.append(row)
    except sqlite3.Error as exc:
        if getattr(exc, "sqlite_errorcode", None) == sqlite3.SQLITE_INTERRUPT:
            raise WorkspaceError("Query exceeded the 3-second limit.", 408) from exc
        raise WorkspaceError(f"SQL rejected or invalid: {exc}") from exc
    elapsed = round((monotonic() - start) * 1000, 2)
    if log:
        with database.get_db_connection() as conn:
            conn.execute(
                "INSERT INTO query_logs (run_id,mode,sql_executed,row_count,execution_ms) VALUES (?,?,?,?,?)",
                (rid, mode, sql, len(rows), elapsed),
            )
    return dict(columns=columns, rows=rows, row_count=len(rows), truncated=truncated, execution_ms=elapsed)


@workspace.get("/runs/<rid>/schema")
def schema(rid):
    table = table_for(rid)
    ensure_snapshots()
    with database.get_db_connection() as conn:
        tables = {r["table_name"]: dict(r) | {"columns": []} for r in conn.execute(
            "SELECT w.table_name, w.run_id, p.filename FROM workspace_runs w JOIN processing_runs p ON p.id=w.run_id"
        )}
        for row in conn.execute("SELECT * FROM run_schemas ORDER BY rowid"):
            column = dict(row)
            column["sample_values"] = json.loads(column.pop("sample_values_json"))
            tables[row["table_name"]]["columns"].append(column)
    return jsonify(table_name=table, tables=list(tables.values()), system_columns=[ROW, FLAG, MISSING])


@workspace.post("/runs/<rid>/query")
def query(rid):
    table_for(rid)
    return jsonify(execute(rid, "sql_studio", validate_sql(body().get("sql"))))


OPERATORS = {"eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}


@workspace.post("/runs/<rid>/filter")
def guided_filter(rid):
    table = table_for(rid)
    data = body()
    filters = data.get("filters", [])
    logic = data.get("logic", "AND")
    limit = data.get("limit", 500)
    if not isinstance(filters, list) or len(filters) > 30 or logic not in ("AND", "OR"):
        raise WorkspaceError("Supply up to 30 filters and choose AND or OR.")
    if type(limit) is not int or not 1 <= limit <= MAX_ROWS:
        raise WorkspaceError("Limit must be an integer between 1 and 1000.")
    with database.get_db_connection() as conn:
        allowed = {r[0]: r[1] for r in conn.execute(
            "SELECT column_name,inferred_type FROM run_schemas WHERE run_id = ?", (rid,)
        )}
    clauses, params = [], []
    for item in filters:
        if not isinstance(item, dict):
            raise WorkspaceError("Each filter must be an object.")
        column, operator, value = item.get("column"), item.get("operator"), item.get("value")
        if not isinstance(column, str) or column not in allowed or not isinstance(operator, str):
            raise WorkspaceError("Select a valid column and operator.")
        field = identifier(column)
        if operator == "missing":
            clauses.append(f"({field} IS NULL OR trim(CAST({field} AS TEXT)) = '')")
            continue
        if operator == "contains" and isinstance(value, str):
            clauses.append(f"instr(lower(CAST({field} AS TEXT)), lower(?)) > 0")
        elif operator in OPERATORS and type(value) in (str, int, float, bool):
            if allowed[column] == "numeric":
                try:
                    value = float(value)
                    if not math.isfinite(value):
                        raise ValueError()
                except (ValueError, OverflowError) as exc:
                    raise WorkspaceError("Enter a finite numeric value.") from exc
                clauses.append(f"(typeof({field}) IN ('integer', 'real') AND {field} {OPERATORS[operator]} ?)")
            else:
                clauses.append(f"{field} {OPERATORS[operator]} ?")
        else:
            raise WorkspaceError("Select a valid operator and value.")
        params.append(sql_value(value))
    conditions = ["(" + f" {logic} ".join(clauses) + ")"] if clauses else []
    issue = data.get("issue")
    if issue is not None:
        if not isinstance(issue, dict) or not all(isinstance(issue.get(key), str) for key in ("field", "reason")):
            raise WorkspaceError("Choose a valid issue.")
        conditions.append(f"{ROW} IN (SELECT row_number FROM workspace_issues WHERE run_id = ? AND field = ? AND issue = ?)")
        params.extend((rid, issue["field"], issue["reason"]))
    preset = data.get("preset")
    if preset == "flagged":
        conditions.append(f"{FLAG} = 1")
    elif preset == "missing_required":
        conditions.append(f"{MISSING} = 1")
    elif preset not in (None, ""):
        raise WorkspaceError("Unknown filter preset.")
    sql = f"SELECT * FROM {identifier(table)}"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {ROW}"
    return jsonify(execute(rid, "guided_filter", sql, params, limit) | {"sql": sql, "parameters": params})


@workspace.route("/saved-queries", methods=["GET", "POST"])
def reports():
    if request.method == "GET":
        with database.get_db_connection() as conn:
            records = conn.execute("SELECT * FROM saved_queries ORDER BY id DESC")
            return jsonify(reports=[dict(record) for record in records])
    data = body()
    name, description, rid = data.get("name"), data.get("description", ""), data.get("default_run_id")
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        raise WorkspaceError("Enter a report name up to 120 characters.")
    if not isinstance(description, str) or len(description) > 1000 or not isinstance(rid, str):
        raise WorkspaceError("Supply a run and a description up to 1000 characters.")
    table_for(rid)
    sql = validate_sql(data.get("sql"))
    execute(rid, "saved_report", sql, limit=1, log=False)
    with database.get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO saved_queries (name,description,sql_text,default_run_id) VALUES (?,?,?,?)",
            (name.strip(), description.strip(), sql, rid),
        )
        return jsonify(id=cursor.lastrowid), 201


@workspace.route("/saved-queries/<int:report_id>", methods=["DELETE", "POST"])
def saved_report(report_id):
    with database.get_db_connection() as conn:
        report = conn.execute("SELECT * FROM saved_queries WHERE id = ?", (report_id,)).fetchone()
        if report is None:
            raise WorkspaceError("Report not found.", 404)
        if request.method == "DELETE":
            conn.execute("DELETE FROM saved_queries WHERE id = ?", (report_id,))
            return "", 204
    rid = report["default_run_id"]
    table_for(rid)
    return jsonify(execute(rid, "saved_report", validate_sql(report["sql_text"])))


@workspace.put("/runs/<rid>/issues/<int:index>")
def review(rid, index):
    status = body().get("status")
    if status not in ("open", "reviewed", "resolved"):
        raise WorkspaceError("Select a valid review status.")
    with database.get_db_connection() as conn:
        row = conn.execute("SELECT issues FROM processing_runs WHERE id = ?", (rid,)).fetchone()
        if row is None or index >= len(json.loads(row[0])):
            raise WorkspaceError("Issue not found.", 404)
        conn.execute("""
            INSERT INTO run_issue_reviews VALUES (?,?,?)
            ON CONFLICT(run_id,issue_index) DO UPDATE SET status = excluded.status
        """, (rid, index, status))
    return jsonify(status=status)


@workspace.get("/runs/<rid>/issue-reviews")
def issue_reviews(rid):
    with database.get_db_connection() as conn:
        if conn.execute("SELECT 1 FROM processing_runs WHERE id=?", (rid,)).fetchone() is None:
            raise WorkspaceError("Run not found.", 404)
        reviews = dict(conn.execute("SELECT issue_index,status FROM run_issue_reviews WHERE run_id=?", (rid,)))
    return jsonify(issue_reviews=reviews)
