import hashlib, pathlib
import chromadb
from . import config as C

_col = None


def col():
    global _col
    if _col is None:
        _col = chromadb.PersistentClient(C.CHROMA_DIR).get_or_create_collection("knowledge_base")
    return _col


def ingest() -> int:
    """Idempotent: one chunk per paragraph of every .md/.txt file in KB_DIR."""
    ids, docs, metas = [], [], []
    for f in sorted(pathlib.Path(C.KB_DIR).glob("*.*")):
        if f.suffix not in (".md", ".txt"):
            continue
        for p in f.read_text(encoding="utf-8").split("\n\n"):
            if p.strip():
                ids.append(hashlib.sha1(p.encode()).hexdigest())
                docs.append(p.strip())
                metas.append({"source": f.name})
    if docs:
        col().upsert(ids=ids, documents=docs, metadatas=metas)
    return len(docs)


def retrieve(text, k=3):
    n = col().count()
    if not n:
        return []
    r = col().query(query_texts=[text], n_results=min(k, n))
    return [(d, dist, m["source"]) for d, dist, m in zip(r["documents"][0], r["distances"][0], r["metadatas"][0])]
