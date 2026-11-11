
import time
import turso_serverless

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
    if not C.TURSO_DATABASE_URL or not C.TURSO_AUTH_TOKEN:
        raise RuntimeError("Turso credentials are not configured")

    return turso_serverless.connect(
        C.TURSO_DATABASE_URL,
        auth_token=C.TURSO_AUTH_TOKEN
    )


def _dict_rows(cursor):
    """Convert Turso tuple rows into dictionaries."""
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def init():
    conn = _c()

    try:
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

        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(tickets)"
            ).fetchall()
        }

        if "updated" not in columns:
            conn.execute(
                "ALTER TABLE tickets ADD COLUMN updated REAL"
            )

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

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def add(source, ref, text, res, sources):
    now = time.time()
    status = "needs_review" if res["needs_human"] else "new"

    conn = _c()

    try:
        cursor = conn.execute("""
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
            ",".join(sources)
        ))

        ticket_id = cursor.lastrowid
        conn.commit()

        return int(ticket_id)

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get(tid):
    conn = _c()

    try:
        cursor = conn.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (tid,)
        )

        rows = _dict_rows(cursor)
        return rows[0] if rows else None

    finally:
        conn.close()


def list_(status=None, limit=50):
    limit = max(1, min(int(limit), 500))

    query = "SELECT * FROM tickets"
    args = []

    if status:
        query += " WHERE status = ?"
        args.append(status)

    query += f" ORDER BY {_ORDER} LIMIT ?"
    args.append(limit)

    conn = _c()

    try:
        cursor = conn.execute(query, args)
        return _dict_rows(cursor)

    finally:
        conn.close()


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

    conn = _c()

    try:
        cursor = conn.execute(
            f"UPDATE tickets SET {assignments} WHERE id = ?",
            values
        )

        changed = cursor.rowcount > 0
        conn.commit()

        return changed

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def seen(ref):
    if not ref:
        return False

    conn = _c()

    try:
        cursor = conn.execute(
            "SELECT 1 FROM tickets WHERE ref = ? LIMIT 1",
            (ref,)
        )

        return cursor.fetchone() is not None

    finally:
        conn.close()
