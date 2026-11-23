import hashlib
import io
import json
import zipfile

import pytest

from test_app import module
from database import get_db_connection


@pytest.fixture
def client():
    return module.app.test_client()


def process(client, records, rules=None):
    response = client.post("/api/process", data={
        "file": (io.BytesIO(json.dumps(records).encode()), "sales.json"),
        "rules": json.dumps(rules or {}),
    })
    assert response.status_code == 200, response.json
    return response.json


def workspace(client, run_id, suffix, payload=None):
    path = f"/api/runs/{run_id}/{suffix}"
    return client.get(path) if payload is None else client.post(path, json=payload)


def test_cleaning_snapshot_and_audit(client):
    rows = [{"name": " A ", "amount": "12", "date": "31/01/2024", "required": ""},
            {"name": "B", "amount": "bad", "date": "invalid", "required": "set"}]
    rules = {"numericFields": ["amount"], "dateFields": ["date"],
             "dateFormat": "%d/%m/%Y", "requiredFields": ["required"]}
    run = process(client, rows, rules)
    rid = run["runId"]
    assert run["cleanedSample"][0] == {"name": "A", "amount": 12, "date": "2024-01-31", "required": ""}
    assert run["cleanedSample"][1] == rows[1]
    assert run["issueRows"] == 2
    schema = workspace(client, rid, "schema").json
    active = next(table for table in schema["tables"] if table["run_id"] == rid)
    assert [column["inferred_type"] for column in active["columns"]] == ["text", "numeric", "date", "text"]
    assert client.put(f"/api/runs/{rid}/issues/0", json={"status": "resolved"}).status_code == 200
    with zipfile.ZipFile(io.BytesIO(client.get(f"/api/v1/runs/{rid}/audit").data)) as archive:
        source = archive.read("original.json")
        assert json.loads(source) == rows
        assert json.loads(archive.read("metadata.json"))["source_hash"] == hashlib.sha256(source).hexdigest()
        assert json.loads(archive.read("issue_reviews.json")) == {"0": "resolved"}
    for kind in ("csv", "json", "xlsx"):
        assert client.post("/api/v1/export", json={"runId": rid, "fileType": kind}).status_code == 200


def test_query_security_joins_logs_and_limits(client):
    first = process(client, [{"account": 1, "value": 8}] * 1001, {"flagDuplicates": False})["runId"]
    second = process(client, [{"account": 1, "label": "priority; SELECT"}])["runId"]
    tables = {table["run_id"]: table["table_name"] for table in workspace(client, second, "schema").json["tables"]}
    query = f'''WITH matched AS (
        SELECT b.label FROM "{tables[first]}" AS a JOIN "{tables[second]}" AS b USING (account)
        WHERE b.label = 'priority; SELECT'
    ) SELECT * FROM matched'''
    result = workspace(client, second, "query", {"sql": query})
    assert result.status_code == 200, result.json
    assert result.json["rows"][0] == ["priority; SELECT"]
    assert result.json["row_count"] == 1000 and result.json["truncated"]
    for statement in ("SELECT 1; SELECT 2", "PRAGMA table_info(processing_runs)",
                      "SELECT * FROM processing_runs", "SELECT * FROM sqlite_master",
                      "WITH c AS (SELECT 1) DELETE FROM processing_runs",
                      "SELECT load_extension('x')", "SELECT * FROM workspace_issues"):
        assert workspace(client, second, "query", {"sql": statement}).status_code == 400
    with get_db_connection() as conn:
        log = conn.execute("SELECT mode,row_count FROM query_logs WHERE run_id=?", (second,)).fetchone()
        assert tuple(log) == ("sql_studio", 1000)


def test_query_timeout(client, monkeypatch):
    import run_workspace
    rid = process(client, [{"value": i} for i in range(100)])["runId"]
    table = workspace(client, rid, "schema").json["table_name"]
    times = iter([0.0, 3.1])
    monkeypatch.setattr(run_workspace, "monotonic", lambda: next(times, 3.1))
    sql = f'SELECT count(*) FROM "{table}" a CROSS JOIN "{table}" b CROSS JOIN "{table}" c'
    assert workspace(client, rid, "query", {"sql": sql}).status_code == 408


def test_guided_filters_and_saved_reports(client):
    rows = [{"code": "one", "val": "12"}, {"code": "", "val": "bad"}, {"code": "two", "val": "4"}]
    rid = process(client, rows, {"numericFields": ["val"], "requiredFields": ["code"]})["runId"]
    schema = workspace(client, rid, "schema").json
    result = workspace(client, rid, "filter", {"filters": [{"column": "val", "operator": "gt", "value": "5"}]})
    assert result.json["row_count"] == 1
    assert "?" in result.json["sql"] and result.json["parameters"] == [5]
    assert workspace(client, rid, "filter", {"preset": "missing_required"}).json["row_count"] == 1
    assert workspace(client, rid, "filter", {"issue": {"field": "val", "reason": "Invalid numeric; original retained"}}).json["row_count"] == 1
    injection = {"column": "code", "operator": "eq", "value": "' OR 1=1 --"}
    assert workspace(client, rid, "filter", {"filters": [injection]}).json["rows"] == []
    assert workspace(client, rid, "filter", {"filters": [injection | {"column": "bad name"}]}).status_code == 400
    report = client.post("/api/saved-queries", json={
        "name": "Count", "sql": f'SELECT count(*) FROM "{schema["table_name"]}"', "default_run_id": rid,
    })
    assert report.status_code == 201, report.json
    report_id = report.json["id"]
    assert report_id in [item["id"] for item in client.get("/api/saved-queries").json["reports"]]
    assert client.post(f"/api/saved-queries/{report_id}").json["rows"] == [[3]]
    assert client.delete(f"/api/saved-queries/{report_id}").status_code == 204


def test_insights_drift_review_and_gemini_consent(client, monkeypatch):
    import run_insights
    previous = process(client, [{"value": "5", "old": True}], {"numericFields": ["value"]})
    run = process(client, [{"value": "6", "segment": "X"}, {"value": "8", "segment": "Y"},
                           {"value": "8", "segment": "Y"}, {"value": "bad", "segment": "X"}],
                  {"numericFields": ["value"]})
    rid = run["runId"]
    monkeypatch.setenv("DATAFLOW_AI_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "configured")
    requests = []

    def narrative(key, model, prompt, aggregate):
        requests.append(aggregate)
        return {"summary": "Summary of the run."}

    monkeypatch.setattr(run_insights, "suggest", narrative)
    assert client.put(f"/api/runs/{rid}/issues/0", json={"status": "reviewed"}).status_code == 200
    info = workspace(client, rid, "insights").json
    assert not requests and "ai_summary" not in info
    health = info["processing_health"]
    assert health["flagged_count"] == 3 and health["duplicate_groups"] == 1
    assert health["resolution"] == {"open": 2, "reviewed": 1, "resolved": 0}
    assert health["drift"]["previous_run_id"] == previous["runId"]
    assert health["drift"]["row_delta"] == 3
    assert health["drift"]["added_columns"] == ["segment"] and health["drift"]["removed_columns"] == ["old"]
    assert health["drift"]["rate_changes"] == [{"column": "value", "missing_rate_delta": 0, "invalid_rate_delta": 0.25}]
    profile = next(item for item in info["column_profiles"] if item["column"] == "value")
    assert profile["mean"] == pytest.approx(22 / 3)
    groups = info["segment_breakdowns"][0]["groups"]
    assert next(group for group in groups if group["value"] == "Y")["metrics"]["value"] == {"sum": 16, "mean": 8}
    assert workspace(client, rid, "insights?narrative=true").json["ai_summary"] == "Summary of the run."
    assert len(requests) == 1 and "segment" not in json.dumps(requests)


def test_legacy_run_materialization_and_column_collisions(client):
    rid = "RUN-legacy-1"
    rows = [{"select": 1, "Name": "A", "name": "B", "__dataflow_row": "original", "": "blank header"}]
    with get_db_connection() as conn:
        conn.execute("INSERT INTO processing_runs VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            rid, "2025-01-01T00:00:00+00:00", "legacy.json", "json", 1,
            "Completed", "", "{}", json.dumps(rows), json.dumps(rows), "[]",
        ))
    data = workspace(client, rid, "schema").json
    table = next(table for table in data["tables"] if table["run_id"] == rid)
    cols = {column["source_name"]: column["column_name"] for column in table["columns"]}
    assert len(set(name.lower() for name in cols.values())) == len(cols)
    sql = f'SELECT "select", "{cols["name"]}", "{cols["__dataflow_row"]}" FROM "{table["table_name"]}"'
    assert workspace(client, rid, "query", {"sql": sql}).json["rows"] == [[1, "B", "original"]]
