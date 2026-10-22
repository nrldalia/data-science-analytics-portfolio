"""PostgreSQL-only regression checks; use check_postgres.py for isolated schemas."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import uuid

from psycopg import sql
import test_app as fixtures
from database import database_url, get_db_connection, IntegrityError


@unittest.skipUnless(database_url(), "Run with check_postgres.py and PostgreSQL.")
class PostgresStorageTests(unittest.TestCase):
    def test_parameter_literals_and_binary_returning_id(self):
        with get_db_connection() as db:
            row = db.execute("SELECT '?' AS literal, ? AS bound, '100%' AS percent", ("safe value",)).fetchone()
            self.assertEqual(row["literal"], "?")
            self.assertEqual(row["bound"], "safe value")
            self.assertEqual(row["percent"], "100%")
            identity = db.execute(
                "INSERT INTO raw_data_payloads(store_id,raw_json_payload,missing_fields_count) VALUES(?,?,?) RETURNING id",
                ("ST-101", "[]", 0)).fetchone()[0]
            self.assertIsInstance(identity, int)
            db.execute("INSERT INTO run_evidence VALUES(?,?,?,?)", ("PG-BINARY", identity, b"\x00\xff", "[]"))
        with get_db_connection() as db:
            self.assertEqual(db.execute("SELECT source FROM run_evidence WHERE run_id=?", ("PG-BINARY",)).fetchone()[0], b"\x00\xff")

    def test_exception_rolls_back_the_transaction(self):
        with self.assertRaises(IntegrityError):
            with get_db_connection() as db:
                db.execute("INSERT INTO stores(id,store_name) VALUES(?,?)", ("PG-ROLLBACK", "Temporary"))
                db.execute("INSERT INTO stores(id,store_name) VALUES(?,?)", ("PG-ROLLBACK", "Duplicate"))
        with get_db_connection() as db:
            self.assertIsNone(db.execute("SELECT id FROM stores WHERE id=?", ("PG-ROLLBACK",)).fetchone())

    def test_sqlite_import_preserves_content_and_refuses_overwrite(self):
        source = Path(__file__).resolve().parent / "dataflow.db"
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        schema = "dataflow_import_test_" + uuid.uuid4().hex
        parts = urlsplit(database_url())
        query = dict(parse_qsl(parts.query))
        query["options"] = "-csearch_path=" + schema
        url = urlunsplit(parts._replace(query=urlencode(query)))
        with get_db_connection() as admin:
            admin.connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            env = dict(os.environ, DATABASE_URL=url)
            command = [sys.executable, str(source.parent / "migrate_sqlite.py"), str(source)]
            first = subprocess.run(command, env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertIn("Source unchanged", first.stdout)
            with patch.dict(os.environ, {"DATABASE_URL": url}), get_db_connection() as db:
                before = db.execute("SELECT COUNT(*) FROM raw_data_payloads").fetchone()[0]
                self.assertEqual(db.execute("SELECT COUNT(*) FROM sqlite_import_receipts").fetchone()[0], 1)
            second = subprocess.run(command, env=env, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("Destination must be empty", second.stderr)
            with patch.dict(os.environ, {"DATABASE_URL": url}), get_db_connection() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM raw_data_payloads").fetchone()[0], before)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest)
        finally:
            with get_db_connection() as admin:
                admin.connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    unittest.main()
