"""Create private local development settings without overwriting existing files."""
import os
from pathlib import Path
import secrets

root = Path(__file__).resolve().parent.parent
path = root / ".env"
if path.exists():
    print("Keeping existing .env. Start PostgreSQL with docker compose up -d --wait.")
else:
    password = secrets.token_urlsafe(32)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(f"POSTGRES_PASSWORD={password}\nDATAFLOW_POSTGRES_PORT=55432\n"
                     f"DATABASE_URL=postgresql://dataflow:{password}@127.0.0.1:55432/dataflow\n")
    print("Created private .env. Start PostgreSQL with docker compose up -d --wait.")
