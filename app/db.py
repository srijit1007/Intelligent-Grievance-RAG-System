import os, sqlite3, time
from . import config as C

_ORDER = "CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, id"


def _c():
    os.makedirs(os.path.dirname(C.DB_PATH) or ".", exist_ok=True)
    c = sqlite3.connect(C.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _c() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS tickets(
            id INTEGER PRIMARY KEY, created REAL, source TEXT, ref TEXT, text TEXT,
            category TEXT, priority TEXT, confidence REAL, reply TEXT, status TEXT, sources TEXT)""")


def add(source, ref, text, res, sources):
    status = "needs_review" if res["needs_human"] else "new"
    with _c() as c:
        cur = c.execute("INSERT INTO tickets(created,source,ref,text,category,priority,confidence,reply,status,sources)"
                        " VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (time.time(), source, ref, text, res["category"], res["priority"],
                         res["confidence"], res["reply"], status, ",".join(sources)))
        return cur.lastrowid


def get(tid):
    with _c() as c:
        r = c.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
    return dict(r) if r else None


def list_(status=None, limit=50):
    q, a = "SELECT * FROM tickets", []
    if status:
        q, a = q + " WHERE status=?", [status]
    with _c() as c:
        return [dict(r) for r in c.execute(f"{q} ORDER BY {_ORDER} LIMIT ?", a + [limit])]


def update(tid, **f):
    with _c() as c:
        c.execute(f"UPDATE tickets SET {','.join(k + '=?' for k in f)} WHERE id=?", [*f.values(), tid])


def seen(ref):
    with _c() as c:
        return c.execute("SELECT 1 FROM tickets WHERE ref=?", (ref,)).fetchone() is not None
