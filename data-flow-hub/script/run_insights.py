"""Deterministic profiling of preserved processed rows."""
import json
import os
from collections import Counter, defaultdict
from statistics import mean

import pandas as pd
from flask import jsonify, request

from ai_assistant import suggest
from database import get_db_connection
from run_workspace import WorkspaceError, missing, numeric, table_for, valid_date, workspace


def ratio(count, total):
    return round(count / total, 6) if total else 0


def classify(issues):
    return Counter((item["field"], item["issue"]) for item in issues)


def measure(rows, issues):
    columns = dict.fromkeys(key for row in rows for key in row)
    completeness = {
        column: ratio(sum(not missing(row.get(column)) for row in rows), len(rows))
        for column in columns
    }
    invalid = Counter(item["field"] for item in issues if item["issue"].startswith("Invalid "))
    return completeness, {column: ratio(invalid[column], len(rows)) for column in columns}


def profiles_for(rows, schema):
    profiles, dimensions, metrics = [], [], []
    for column in schema:
        name, kind = column["source_name"], column["inferred_type"]
        values = [row.get(name) for row in rows if not missing(row.get(name))]
        profile = {
            "column": name, "type": kind,
            "missing_count": len(rows) - len(values),
        }
        if kind == "numeric":
            series = pd.Series([value for value in values if numeric(value)], dtype="float64")
            if not series.empty:
                q1, q3 = series.quantile([0.25, 0.75])
                spread = q3 - q1
                lower, upper = q1 - 1.5 * spread, q3 + 1.5 * spread
                std = series.std(ddof=0)
                profile.update(
                    min=series.min(), max=series.max(), mean=series.mean(), median=series.median(),
                    iqr_outliers=int(((series < lower) | (series > upper)).sum()),
                    iqr_lower=lower, iqr_upper=upper,
                    z_score_outliers=int(((series - series.mean()).abs() > 3 * std).sum()) if std else 0,
                )
                profile = {key: None if pd.isna(value) or value in (float("inf"), float("-inf")) else value
                           for key, value in profile.items()}
                metrics.append(name)
        elif kind == "date":
            dates = [value for value in values if valid_date(value)]
            profile.update(min=min(dates, default=None), max=max(dates, default=None))
        else:
            counts = Counter(label(value) for value in values)
            profile.update(cardinality=len(counts), top_values=counts.most_common(10))
            if 1 < len(counts) <= 100 or counts and name.lower().endswith("_id"):
                dimensions.append(name)
        profiles.append(profile)
    return profiles, dimensions, metrics


def label(value):
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)


def segments_for(rows, dimensions, metrics):
    segments = []
    for dimension in dimensions[:5]:
        counts = Counter(label(row[dimension]) for row in rows if not missing(row.get(dimension)))
        groups = {value: defaultdict(list) for value, _ in counts.most_common(10)}
        for row in rows:
            if missing(row.get(dimension)):
                continue
            group = groups.get(label(row[dimension]))
            if group is not None:
                for metric in metrics[:5]:
                    if numeric(row.get(metric)):
                        group[metric].append(row[metric])
        segments.append({"column": dimension, "groups": [
            {"value": value, "count": counts[value], "metrics": {
                metric: {"sum": sum(numbers), "mean": mean(numbers)}
                for metric, numbers in group.items()
                if abs(sum(numbers)) < float("inf") and abs(mean(numbers)) < float("inf")
            }}
            for value, group in groups.items()
        ]})
    return segments


def compare(run, previous, completeness, invalid):
    if previous is None:
        return None
    prior_rows = json.loads(previous["output"])
    prior_completeness, prior_invalid = measure(prior_rows, json.loads(previous["issues"]))
    shared = sorted(completeness.keys() & prior_completeness.keys())
    return {
        "previous_run_id": previous["id"], "previous_filename": previous["filename"],
        "row_delta": run["input_rows"] - previous["input_rows"],
        "added_columns": sorted(completeness.keys() - prior_completeness.keys()),
        "removed_columns": sorted(prior_completeness.keys() - completeness.keys()),
        "rate_changes": [
            {"column": column, "missing_rate_delta": round(prior_completeness[column] - completeness[column], 6),
             "invalid_rate_delta": round(invalid[column] - prior_invalid[column], 6)}
            for column in shared
        ],
    }


@workspace.get("/runs/<rid>/insights")
def insights(rid):
    table_for(rid)
    with get_db_connection() as conn:
        run = conn.execute("SELECT * FROM processing_runs WHERE id=?", (rid,)).fetchone()
        previous = conn.execute("""
            SELECT * FROM processing_runs WHERE created_at < ? OR (created_at = ? AND id < ?)
            ORDER BY created_at DESC, id DESC LIMIT 1
        """, (run["created_at"], run["created_at"], rid)).fetchone()
        schema = conn.execute("SELECT * FROM run_schemas WHERE run_id=? ORDER BY rowid", (rid,)).fetchall()
        reviews = dict(conn.execute("SELECT issue_index,status FROM run_issue_reviews WHERE run_id=?", (rid,)))
    rows, issues = json.loads(run["output"]), json.loads(run["issues"])
    completeness, invalid = measure(rows, issues)
    breakdown = classify(issues)
    flagged = len({item["row"] for item in issues})
    duplicates = breakdown["record", "Duplicate record; retained"]
    collision_groups = Counter(
        json.dumps(rows[item["row"] - 1], sort_keys=True)
        for item in issues if item["issue"].startswith("Duplicate record")
    )
    statuses = Counter(reviews.get(index, "open") for index in range(len(issues)))
    profiles, dimensions, metrics = profiles_for(rows, schema)
    drift = compare(run, previous, completeness, invalid)
    health = {
        "total_rows": len(rows), "flagged_count": flagged, "flagged_rate": ratio(flagged, len(rows)),
        "duplicate_rows": duplicates, "duplicate_groups": len(collision_groups),
        "issue_breakdown": [{"column": c, "issue": issue, "count": count}
                            for (c, issue), count in breakdown.most_common()],
        "completeness_rates": completeness, "invalid_rates": invalid, "drift": drift,
        "resolution": {key: statuses[key] for key in ("open", "reviewed", "resolved")},
        "readiness": "Ready for export" if statuses["resolved"] == len(issues) else "Review required",
    }
    actions = []
    for (column, issue), count in breakdown.most_common(10):
        if issue.startswith("Invalid date"):
            message = f"Check the input date format for {column} ({count} issues)."
        elif issue.startswith("Invalid numeric"):
            message = f"Check numeric separators and units in {column} ({count} issues)."
        elif issue == "Missing required value":
            message = f"Review {count} missing required values in {column}."
        else:
            message = f"Review {count} rows that share a processed record."
        actions.append({"message": message, "issue": {"field": column, "reason": issue}})
    if drift:
        for change in sorted(drift["rate_changes"], key=lambda item: max(item["missing_rate_delta"], item["invalid_rate_delta"]), reverse=True)[:3]:
            if max(change["missing_rate_delta"], change["invalid_rate_delta"]) >= 0.05:
                actions.append({
                    "message": f"Investigate the rise in missing or invalid values in {change['column']}.",
                    "missing_column": change["column"] if change["missing_rate_delta"] >= change["invalid_rate_delta"] else None,
                    "preset": "flagged" if change["invalid_rate_delta"] > change["missing_rate_delta"] else "",
                })
    if not actions:
        actions.append({"message": "No cleaning issues were flagged. The processed dataset is ready for export."})
    result = {
        "processing_health": health, "column_profiles": profiles,
        "segment_breakdowns": segments_for(rows, dimensions, metrics),
        "recommended_actions": actions, "issue_reviews": reviews,
        "ai_available": bool(os.getenv("GEMINI_API_KEY")) and os.getenv("DATAFLOW_AI_ENABLED", "").lower() == "true",
    }
    if request.args.get("narrative") == "true":
        if not result["ai_available"]:
            raise WorkspaceError("Gemini narrative is unavailable.", 503)
        # Send aggregate metrics without filenames, field names, examples, or source rows.
        aggregate = {
            "rows": len(rows), "flagged_rows": flagged, "duplicates": duplicates,
            "resolution": health["resolution"], "readiness": health["readiness"],
            "row_delta": drift["row_delta"] if drift else None,
        }
        try:
            narrative = suggest(
                os.environ["GEMINI_API_KEY"], os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                'Summarize these aggregate metrics in 2–4 sentences. Return {"summary":"..."}.', aggregate,
            ).get("summary")
            if not isinstance(narrative, str) or not narrative.strip():
                raise ValueError("Missing summary")
            result["ai_summary"] = narrative
        except Exception:
            raise WorkspaceError("Gemini could not generate a narrative.", 503) from None
    return jsonify(result)
