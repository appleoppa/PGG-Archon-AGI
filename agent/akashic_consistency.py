"""Read-only/repair gate for Akashic derived index consistency.

`index.pkl` is the primary fragment ledger.  vectors.npy, dense_vectors.npy,
meta.json, and SQLite FTS5 rows are derived indexes that can be audited and,
when explicitly requested, rebuilt from the primary ledger.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pickle
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from hermes_constants import get_hermes_home
from agent.akashic_memory import DenseEmbedder, get_akashic_home, get_akashic_state_db_path, _get_embedder


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _load_index(akashic_home: Path) -> List[Dict[str, Any]]:
    path = akashic_home / "index.pkl"
    if not path.exists():
        return []
    with path.open("rb") as f:
        data = pickle.load(f)
    return data if isinstance(data, list) else []


def _npy_rows(path: Path) -> Optional[int]:
    if not path.exists():
        return None
    try:
        arr = np.load(str(path), allow_pickle=False)
        return int(arr.shape[0]) if getattr(arr, "ndim", 0) >= 1 else 0
    except Exception:
        return None


def _meta_count(path: Path) -> Optional[int]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return int(data.get("count", 0))
    except Exception:
        return None
    return None


def _ensure_fts(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS akashic_fts_content (
                id TEXT PRIMARY KEY UNIQUE NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT ''
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS akashic_fts USING fts5(
                content, title, tags,
                content='akashic_fts_content', content_rowid='rowid'
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _fts_ids(db_path: Path) -> List[str]:
    if not db_path.exists():
        return []
    _ensure_fts(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("SELECT id FROM akashic_fts_content ORDER BY id").fetchall()
        return [str(r[0]) for r in rows]
    finally:
        conn.close()


def audit_akashic_consistency(akashic_home: Path | None = None, state_db_path: Path | None = None) -> Dict[str, Any]:
    ak_home = Path(akashic_home or get_akashic_home())
    db_path = Path(state_db_path or get_akashic_state_db_path())
    issues: List[Dict[str, Any]] = []
    try:
        index = _load_index(ak_home)
        primary_count = len(index)
        primary_ids = {str(i.get("id")) for i in index if i.get("id")}
        counts = {
            "primary_index": primary_count,
            "meta_count": _meta_count(ak_home / "meta.json"),
            "vectors_rows": _npy_rows(ak_home / "vectors.npy"),
            "dense_rows": _npy_rows(ak_home / "dense_vectors.npy"),
            "fts_rows": None,
        }
        fts = set(_fts_ids(db_path))
        counts["fts_rows"] = len(fts)

        if counts["meta_count"] != primary_count:
            issues.append({"code": "META_COUNT_MISMATCH", "expected": primary_count, "actual": counts["meta_count"]})
        if counts["vectors_rows"] != primary_count:
            issues.append({"code": "VECTORS_ROW_MISMATCH", "expected": primary_count, "actual": counts["vectors_rows"]})
        if counts["dense_rows"] != primary_count:
            issues.append({"code": "DENSE_ROW_MISMATCH", "expected": primary_count, "actual": counts["dense_rows"]})
        missing = sorted(primary_ids - fts)
        orphan = sorted(fts - primary_ids)
        if missing:
            issues.append({"code": "FTS_MISSING_PRIMARY_IDS", "count": len(missing), "ids_sample": missing[:20]})
        if orphan:
            issues.append({"code": "FTS_ORPHAN_IDS", "count": len(orphan), "ids_sample": orphan[:20]})
        status = "PASS" if not issues else "REPAIRABLE"
        return {
            "schema": "PGGAkashicConsistency/v1",
            "generated_at": _now(),
            "status": status,
            "akashic_home": str(ak_home),
            "state_db": str(db_path),
            "counts": counts,
            "issues": issues,
            "read_only": True,
        }
    except Exception as e:
        return {
            "schema": "PGGAkashicConsistency/v1",
            "generated_at": _now(),
            "status": "ERROR",
            "akashic_home": str(ak_home),
            "state_db": str(db_path),
            "error": f"{type(e).__name__}: {str(e)[:240]}",
            "read_only": True,
        }


def _backup(ak_home: Path, db_path: Path) -> Path:
    backup_root = get_hermes_home() / "workspace" / "pgg-archon-governance" / "akashic-consistency-backups"
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = backup_root / f"backup-{stamp}"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ["index.pkl", "vectors.npy", "dense_vectors.npy", "meta.json"]:
        p = ak_home / name
        if p.exists():
            shutil.copy2(p, dest / name)
    if db_path.exists():
        shutil.copy2(db_path, dest / "state.db")
    return dest


def _entry_text(entry: Dict[str, Any]) -> str:
    return str(entry.get("fragment") or entry.get("content") or entry.get("text") or "")


def _entry_title_tags(entry: Dict[str, Any]) -> tuple[str, str]:
    raw_md = entry.get("metadata")
    md: Dict[str, Any] = raw_md if isinstance(raw_md, dict) else {}
    title = str(entry.get("title") or md.get("title") or "")
    tags = entry.get("tags") or md.get("tags") or ""
    if isinstance(tags, (list, tuple)):
        tags = ",".join(str(x) for x in tags)
    return title, str(tags)


def repair_akashic_derived_indexes(akashic_home: Path | None = None, state_db_path: Path | None = None) -> Dict[str, Any]:
    ak_home = Path(akashic_home or get_akashic_home())
    db_path = Path(state_db_path or get_akashic_state_db_path())
    before = audit_akashic_consistency(ak_home, db_path)
    index = _load_index(ak_home)
    backup = _backup(ak_home, db_path)

    texts = [_entry_text(e) for e in index]
    embedder = _get_embedder(ak_home)
    vectors = np.array([embedder.transform(t) for t in texts], dtype=np.float32) if texts else np.zeros((0, getattr(embedder, "max_features", 0)), dtype=np.float32)
    dense = np.array(DenseEmbedder.embed_batch(texts), dtype=np.float32) if texts else np.zeros((0, 512), dtype=np.float32)

    ak_home.mkdir(parents=True, exist_ok=True)
    np.save(str(ak_home / "vectors.npy"), vectors)
    np.save(str(ak_home / "dense_vectors.npy"), dense)
    meta_path = ak_home / "meta.json"
    old_meta: Dict[str, Any] = {}
    if meta_path.exists():
        try:
            old_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            old_meta = {}
    old_meta.update({"count": len(index), "last_repaired_at": _now()})
    old_meta.setdefault("created_at", _now())
    meta_path.write_text(json.dumps(old_meta, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    _ensure_fts(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("DELETE FROM akashic_fts_content")
        for e in index:
            fid = str(e.get("id") or "")
            if not fid:
                continue
            title, tags = _entry_title_tags(e)
            conn.execute(
                "INSERT OR REPLACE INTO akashic_fts_content (id,title,content,tags) VALUES (?,?,?,?)",
                (fid, title, _entry_text(e), tags),
            )
        conn.commit()
    finally:
        conn.close()

    after = audit_akashic_consistency(ak_home, db_path)
    return {
        "schema": "PGGAkashicConsistencyRepair/v1",
        "generated_at": _now(),
        "status": "PASS" if after.get("status") == "PASS" else "WATCH_REPAIR_INCOMPLETE",
        "backup": str(backup),
        "before": before,
        "after": after,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--apply-repair", action="store_true")
    args = ap.parse_args()
    result = repair_akashic_derived_indexes() if args.apply_repair else audit_akashic_consistency()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"Akashic consistency: {result.get('status')} counts={result.get('counts')}")
        if result.get("issues"):
            print("issues:", ", ".join(i.get("code", "UNKNOWN") for i in result["issues"]))
    return 0 if result.get("status") in {"PASS", "REPAIRABLE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
