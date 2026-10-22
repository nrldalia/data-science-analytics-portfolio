"""Run backend tests against isolated, disposable PostgreSQL schemas."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import uuid

import psycopg
from psycopg import sql
from database import database_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modules", nargs="*")
    parser.add_argument("--log-dir", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    modules = args.modules or sorted(p.stem for p in root.glob("test_*.py"))
    if any(not re.fullmatch(r"test_[a-z0-9_]+", m) for m in modules):
        parser.error("Use test module names, without paths.")
    url = database_url()
    if not url:
        parser.error("A PostgreSQL DATABASE_URL is required.")
    if args.log_dir:
        args.log_dir.mkdir(parents=True, exist_ok=True)
    failed = []
    with psycopg.connect(url, autocommit=True) as admin:
        for module in modules:
            schema = "dataflow_test_" + uuid.uuid4().hex
            admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            try:
                parts = urlsplit(url)
                query = dict(parse_qsl(parts.query))
                query["options"] = "-csearch_path=" + schema
                test_url = urlunsplit(parts._replace(query=urlencode(query)))
                env = dict(os.environ, DATABASE_URL=test_url)
                run = subprocess.run([sys.executable, "-m", "unittest", module, "-v"],
                                     cwd=root, env=env, text=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     timeout=180)
                if args.log_dir:
                    (args.log_dir / (module + ".log")).write_text(run.stdout)
                counts = re.findall(r"Ran \d+ tests? in .*", run.stdout)
                summary = counts[-1] if counts else "test import/startup failed"
                print(f"{module}: {'PASS' if run.returncode == 0 else 'FAIL'} ({summary})", flush=True)
                if run.returncode:
                    failed.append(module)
                    if not args.log_dir:
                        print(run.stdout)
            finally:
                admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
    return bool(failed)


if __name__ == "__main__":
    sys.exit(main())
