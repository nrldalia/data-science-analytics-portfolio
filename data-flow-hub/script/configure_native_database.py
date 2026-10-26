"""Configure native local PostgreSQL without changing existing credentials or data."""
import argparse
import getpass
import os
from pathlib import Path
import warnings
from urllib.parse import quote

from dotenv import dotenv_values
import psycopg

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def text_value(value, label):
    if not isinstance(value, str) or not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f"{label} must be nonempty and contain no control characters.")
    return value


def build_url(host, port, database, user, password):
    host = text_value(host, "Host").strip()
    if host not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Use localhost, 127.0.0.1 or ::1 for native local PostgreSQL.")
    text_value(str(port), "Port")
    if isinstance(port, bool):
        raise ValueError("Port must be a whole number from 1 to 65535.")
    try:
        number = int(port)
    except (TypeError, ValueError):
        raise ValueError("Port must be a whole number from 1 to 65535.") from None
    if not 1 <= number <= 65535:
        raise ValueError("Port must be a whole number from 1 to 65535.")
    database = text_value(database, "Database").strip()
    text_value(database, "Database")
    user = text_value(user, "Database role").strip()
    text_value(user, "Database role")
    password = text_value(password, "Password")
    address = f"[{host}]" if host == "::1" else host
    return (f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}"
            f"@{address}:{number}/{quote(database, safe='')}")


def configured_url(path=None):
    path = ENV_FILE if path is None else Path(path)
    url = os.getenv("DATABASE_URL")
    if not url and os.getenv("DATAFLOW_DB"):
        raise ValueError("DATAFLOW_DB selects legacy SQLite. Unset it before using native PostgreSQL.")
    if not url and path.exists():
        url = dotenv_values(path).get("DATABASE_URL")
    if url and not url.startswith(("postgresql://", "postgres://")):
        raise ValueError("DATABASE_URL must configure PostgreSQL.")
    return url


class DatabaseConnectionError(Exception):
    """Connection failure that never carries driver-provided credential details."""


def check_connection(url):
    if not isinstance(url, str) or not url.startswith(("postgresql://", "postgres://")):
        raise ValueError("Configure a PostgreSQL DATABASE_URL first.")
    try:
        with psycopg.connect(url, connect_timeout=5) as connection:
            if connection.execute("SELECT 1").fetchone()[0] != 1:
                raise DatabaseConnectionError()
    except (psycopg.Error, OSError, ValueError, TypeError):
        raise DatabaseConnectionError() from None


def save_url(url, path=None):
    path = ENV_FILE if path is None else Path(path)
    text_value(url, "Connection URL")
    if not url.startswith(("postgresql://", "postgres://")):
        raise ValueError("Only a PostgreSQL connection URL can be saved.")
    # The generated URI percent-encodes user-controlled URI components, so it
    # contains no dotenv interpolation, quote, comment, or line-break characters.
    if any(c in url for c in ("'", "\n", "\r", "$", "#", "\\")):
        raise ValueError("Cannot safely save this generated connection URL.")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        stream.write("# Native local PostgreSQL; private settings, never commit.\n")
        stream.write(f"DATABASE_URL='{url}'\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Only validate existing PostgreSQL settings; never prompt or write.")
    args = parser.parse_args(argv)
    try:
        url = configured_url()
        if url:
            check_connection(url)
            print("PostgreSQL connection verified. Existing settings were kept unchanged.")
            return 0
        if args.check:
            print("No PostgreSQL connection is configured. Run Setup_Windows.bat first.")
            return 1
        if ENV_FILE.exists():
            print("Existing .env has no PostgreSQL DATABASE_URL. Keep a private backup and edit "
                  "that file locally using README.md. Existing .env was not overwritten.")
            return 1
        print("Use the PostgreSQL role and database you created in pgAdmin.")
        print("This checks an existing database; it does not create or modify it.")
        host = input("Host [127.0.0.1]: ").strip() or "127.0.0.1"
        port = input("Port [5432]: ").strip() or "5432"
        database = input("Database [dataflow]: ").strip() or "dataflow"
        user = input("Database role [dataflow]: ").strip() or "dataflow"
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("Database role password (hidden): ")
        url = build_url(host, port, database, user, password)
        check_connection(url)
        save_url(url)
        print("PostgreSQL connection verified. Created private .env without printing credentials.")
        return 0
    except FileExistsError:
        print("A .env file already exists. It was not overwritten; check your settings locally.")
    except (DatabaseConnectionError, psycopg.Error, OSError):
        # Driver errors can include connection strings or credentials. Never echo them.
        print("Could not connect or save settings. Check the PostgreSQL Windows service, port, "
              "existing database, role and password. Existing settings were not changed.")
    except (EOFError, KeyboardInterrupt, getpass.GetPassWarning):
        print("Configuration cancelled or no secure password prompt is available. No settings were overwritten.")
    except ValueError as exc:
        # Only errors constructed in this module are emitted; driver details are above.
        print(str(exc))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
