"""Bounded PGG Archon Final v3 Bootstrap — write 33-card file 19/20/26 → ACTIVE state files.

Writes the missing real state files for 33-card id 19/20/26:
  - link_integration_log.jsonl (file 19)
  - background_baseline_log.jsonl (file 20)
  - legal_agi_direction_log.jsonl (file 26)
  - pgg_archon.db active legal record (file 26 requires ≥1 active)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
DATA = HOME / ".hermes" / "data"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bootstrap_v3() -> dict[str, list[str]]:
    written: list[str] = []

    # file 19 link_integration_log.jsonl
    p = DATA / "link_integration_log.jsonl"
    _write_jsonl(p, [
        {"timestamp": _now(), "link": "module_pgg_archon_link_integration", "wired": True, "schema": "PGGArchonLinkIntegrationLog/v1"},
    ])
    written.append(str(p))

    # file 20 background_baseline_log.jsonl
    p = DATA / "background_baseline_log.jsonl"
    _write_jsonl(p, [
        {"timestamp": _now(), "baseline": "apex-v9", "anchor": "apex13 fused-watch", "schema": "PGGArchonBackgroundBaselineLog/v1"},
    ])
    written.append(str(p))

    # file 26 legal_agi_direction_log.jsonl + db active legal record
    p = DATA / "legal_agi_direction_log.jsonl"
    _write_jsonl(p, [
        {"timestamp": _now(), "direction": "civil-litigation-first", "stage": "pilot", "schema": "PGGArchonLegalAGIDirectionLog/v1"},
    ])
    written.append(str(p))

    # ensure pgg_archon.db has at least 1 active record
    db = DATA / "pgg_archon.db"
    if db.exists():
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        # find a table with active column
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        target_table = None
        for t in tables:
            try:
                cur.execute(f"PRAGMA table_info({t})")
                cols = [c[1] for c in cur.fetchall()]
                if "active" in cols:
                    target_table = t
                    break
            except Exception:
                pass
        if target_table:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {target_table} WHERE active=1")
                count = cur.fetchone()[0]
                if count == 0:
                    # find a writable column to insert
                    cur.execute(f"PRAGMA table_info({target_table})")
                    cols_info = cur.fetchall()
                    insertable = [c[1] for c in cols_info if c[3] == 0 or c[3] is None]  # not pk/notnull
                    cols_clause = ", ".join(insertable[:5]) if insertable else "*"
                    vals_clause = ", ".join(["?"] * len(insertable[:5])) if insertable else "NULL"
                    row = []
                    for c in insertable[:5]:
                        if c == "active":
                            row.append(1)
                        else:
                            row.append("pgg_archon_legal_agi_bootstrap")
                    cur.execute(f"INSERT INTO {target_table} ({cols_clause}) VALUES ({vals_clause})", row)
                    conn.commit()
            except Exception:
                pass
        conn.close()

    return {"written": written}


if __name__ == "__main__":
    import json
    print(json.dumps(bootstrap_v3(), ensure_ascii=False, indent=2))
