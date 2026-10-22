"""Copy a read-only SQLite snapshot into an empty PostgreSQL application schema."""
import argparse
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import quote

from psycopg import sql
from database import get_db_connection, is_postgres, begin_write

ORDERED_TABLES = ("retailer_configs", "batch_jobs", "batch_attempts")


def fingerprint(rows, columns):
    def value(v):
        if isinstance(v, (bytes, memoryview)):
            return {"bytes": bytes(v).hex()}
        if isinstance(v, (datetime, date)):
            return str(v)
        return v
    encoded = [json.dumps([value(row[c]) for c in columns], ensure_ascii=False,
                          separators=(",", ":")) for row in rows]
    return hashlib.sha256("\n".join(sorted(encoded)).encode()).hexdigest()


def migrate(source):
    source = Path(source).resolve(strict=True)
    with get_db_connection() as destination:
        if not is_postgres(destination):
            raise ValueError("Migration requires a PostgreSQL DATABASE_URL.")
    os.environ["DATAFLOW_SEED_DEMO"] = "0"
    with sqlite3.connect(f"file:{quote(str(source))}?mode=ro", uri=True) as legacy:
        legacy.row_factory = sqlite3.Row
        legacy.execute("BEGIN")
        if legacy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity check failed; no data was copied.")
        if legacy.execute("PRAGMA foreign_key_check").fetchone():
            raise RuntimeError("SQLite foreign key check failed; no data was copied.")
        tables = [r[0] for r in legacy.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        if not {"stores", "raw_data_payloads"}.issubset(tables):
            raise ValueError("Source is not a DataFlow SQLite database.")
        import app
        with get_db_connection() as target:
            if not is_postgres(target):
                raise ValueError("Migration requires a PostgreSQL DATABASE_URL.")
            begin_write(target)
            columns = {}
            for row in target.execute(
                "SELECT table_name,column_name FROM information_schema.columns "
                "WHERE table_schema=current_schema() ORDER BY ordinal_position"):
                columns.setdefault(row["table_name"], []).append(row["column_name"])
            unknown = set(tables) - columns.keys()
            if unknown:
                raise ValueError("Unsupported source tables: " + ", ".join(sorted(unknown)))
            for table in columns:
                if table == "schema_migrations":
                    continue
                count = target.connection.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(
                    sql.Identifier(table))).fetchone()[0]
                if table == "store_code_sequence" and count == 1:
                    row = target.execute("SELECT id,last_value FROM store_code_sequence").fetchone()
                    if row["id"] == 1 and row["last_value"] == 0:
                        continue
                if count:
                    raise ValueError("Destination must be empty; found data in " + table)
            target.execute("DELETE FROM store_code_sequence")
            first = ["stores", "raw_data_payloads", "transformation_traces", "ai_generated_emails"]
            tables = [t for t in first if t in tables] + sorted(set(tables) - set(first))
            report = {}
            for table in tables:
                ident = '"' + table.replace('"', '""') + '"'
                source_columns = [r["name"] for r in legacy.execute(f"PRAGMA table_info({ident})")]
                if not set(source_columns).issubset(columns[table]):
                    raise ValueError("Unsupported source columns in " + table)
                selected = source_columns + (["rowid"] if table in ORDERED_TABLES else [])
                selection = ",".join('"' + c.replace('"', '""') + '"' for c in selected)
                rows = legacy.execute(f"SELECT {selection} FROM {ident}").fetchall()
                if rows:
                    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                        sql.Identifier(table),
                        sql.SQL(",").join(map(sql.Identifier, selected)),
                        sql.SQL(",").join(sql.Placeholder() for _ in selected))
                    with target.connection.cursor() as cursor:
                        cursor.executemany(statement, [tuple(r[c] for c in selected) for r in rows])
                copied = target.connection.execute(sql.SQL("SELECT {} FROM {}").format(
                    sql.SQL(",").join(map(sql.Identifier, selected)), sql.Identifier(table))).fetchall()
                if len(rows) != len(copied) or fingerprint(rows, selected) != fingerprint(copied, selected):
                    raise RuntimeError("Verification failed for " + table + "; transaction rolled back.")
                report[table] = len(rows)
            for table, fields in columns.items():
                for column in ("id", "rowid"):
                    if column not in fields:
                        continue
                    sequence = target.execute("SELECT pg_get_serial_sequence(?,?)", (table, column)).fetchone()[0]
                    if sequence:
                        maximum = target.connection.execute(sql.SQL("SELECT MAX({}) FROM {}").format(
                            sql.Identifier(column), sql.Identifier(table))).fetchone()[0]
                        if maximum is not None:
                            target.execute("SELECT setval(?, ?, true)", (sequence, maximum))
            target.execute("CREATE TABLE IF NOT EXISTS sqlite_import_receipts(source_sha256 TEXT PRIMARY KEY, imported_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, table_counts TEXT NOT NULL)")
            target.execute("INSERT INTO sqlite_import_receipts(source_sha256,table_counts) VALUES(?,?)",
                           (hashlib.sha256(source.read_bytes()).hexdigest(), json.dumps(report)))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    report = migrate(parser.parse_args().source)
    print(f"Verified {sum(report.values())} rows across {len(report)} tables. Source unchanged.")
    for name, count in sorted(report.items()):
        print(f"  {name}: {count}")
