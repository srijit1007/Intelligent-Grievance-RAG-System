
import os
import sqlite3
from dotenv import load_dotenv
import turso_serverless

load_dotenv()

# Connect to local SQLite database
local = sqlite3.connect("data/tickets.db")
local.row_factory = sqlite3.Row

# Connect to Turso
url = os.getenv("TURSO_DATABASE_URL")
token = os.getenv("TURSO_AUTH_TOKEN")

if not url or not token:
    raise RuntimeError("Turso credentials missing from .env")

remote = turso_serverless.connect(
    url,
    auth_token=token
)

try:
    # Create the same ticket table in Turso
    remote.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created REAL NOT NULL,
            updated REAL,
            source TEXT,
            ref TEXT,
            text TEXT,
            category TEXT,
            priority TEXT,
            confidence REAL,
            reply TEXT,
            status TEXT,
            sources TEXT
        )
    """)

    rows = local.execute(
        "SELECT * FROM tickets ORDER BY id"
    ).fetchall()

    columns = [
        "id", "created", "updated", "source", "ref", "text",
        "category", "priority", "confidence", "reply",
        "status", "sources"
    ]

    placeholders = ", ".join(["?"] * len(columns))
    column_names = ", ".join(columns)

    remote.execute("BEGIN")

    try:
        for row in rows:
            values = [row[col] if col in row.keys() else None for col in columns]

            remote.execute(
                f"INSERT OR IGNORE INTO tickets ({column_names}) "
                f"VALUES ({placeholders})",
                values
            )

        remote.commit()

    except Exception:
        remote.rollback()
        raise

    result = remote.execute(
        "SELECT COUNT(*) FROM tickets"
    ).fetchone()

    print("Migration completed!")
    print("Local SQLite tickets:", len(rows))
    print("Total Turso tickets:", result[0])

finally:
    remote.close()
    local.close()
