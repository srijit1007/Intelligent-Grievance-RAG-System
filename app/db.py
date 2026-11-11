
import os
import sqlite3
import time

from . import config as C


_ORDER = """
CASE priority
    WHEN 'critical' THEN 0
    WHEN 'high' THEN 1
    WHEN 'medium' THEN 2
    ELSE 3
END, id
"""

ALLOWED_UPDATE_FIELDS = {
    "category",
    "priority",
    "confidence",
    "reply",
    "status",
}


def _c():
    db_dir = os.path.dirname(C.DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(
        C.DB_PATH,
        timeout=30,
    )

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")

    return conn


def init():
    with _c() as conn:
        conn.execute("""
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

        # Add updated column to older databases if necessary.
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(tickets)")
        }

        if "updated" not in columns:
            conn.execute("ALTER TABLE tickets ADD COLUMN updated REAL")

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tickets_status
            ON tickets(status)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tickets_created
            ON tickets(created)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tickets_ref
            ON tickets(ref)
        """)


def add(source, ref, text, res, sources):
    now = time.time()

    status = "needs_review" if res["needs_human"] else "new"

    with _c() as conn:
        cur = conn.execute("""
            INSERT INTO tickets (
                created, updated, source, ref, text,
                category, priority, confidence, reply,
                status, sources
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            now,
            source,
            ref,
            text,
            res["category"],
            res["priority"],
            res["confidence"],
            res["reply"],
            status,
            ",".join(sources),
        ))

        return cur.lastrowid


def get(tid):
    with _c() as conn:
        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (tid,)
        ).fetchone()

    return dict(row) if row else None


def list_(status=None, limit=50):
    limit = max(1, min(int(limit), 500))

    query = "SELECT * FROM tickets"
    args = []

    if status:
        query += " WHERE status = ?"
        args.append(status)

    query += f" ORDER BY {_ORDER} LIMIT ?"
    args.append(limit)

    with _c() as conn:
        rows = conn.execute(query, args).fetchall()

    return [dict(row) for row in rows]


def update(tid, **fields):
    if not fields:
        return False

    invalid = set(fields) - ALLOWED_UPDATE_FIELDS

    if invalid:
        raise ValueError(
            f"Invalid ticket fields: {', '.join(sorted(invalid))}"
        )

    fields["updated"] = time.time()

    assignments = ", ".join(
        f"{key} = ?" for key in fields
    )

    values = list(fields.values()) + [tid]

    with _c() as conn:
        cur = conn.execute(
            f"UPDATE tickets SET {assignments} WHERE id = ?",
            values,
        )

        return cur.rowcount > 0


def seen(ref):
    if not ref:
        return False

    with _c() as conn:
        row = conn.execute(
            "SELECT 1 FROM tickets WHERE ref = ? LIMIT 1",
            (ref,)
        ).fetchone()

    return row is not None
