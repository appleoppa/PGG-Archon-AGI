import json
import pickle
import sqlite3
from pathlib import Path
from unittest.mock import patch

import numpy as np

from agent.akashic_consistency import audit_akashic_consistency, repair_akashic_derived_indexes


class _FakeEmbedder:
    max_features = 4

    def transform(self, text: str):
        base = float(len(text) % 10)
        return np.array([base, base + 1, base + 2, base + 3], dtype=np.float32)


class _FakeDense:
    @classmethod
    def embed_batch(cls, texts):
        return np.array([[float(i)] * 512 for i, _ in enumerate(texts)], dtype=np.float32)


def _seed(tmp_path: Path):
    ak = tmp_path / "akashic"
    ak.mkdir()
    index = [
        {"id": "a", "fragment": "alpha", "metadata": {"title": "A", "tags": "one"}, "timestamp": "2026-01-01T00:00:00Z"},
        {"id": "b", "fragment": "beta", "metadata": {"title": "B", "tags": "two"}, "timestamp": "2026-01-02T00:00:00Z"},
    ]
    with (ak / "index.pkl").open("wb") as f:
        pickle.dump(index, f)
    np.save(str(ak / "vectors.npy"), np.zeros((1, 4), dtype=np.float32))
    np.save(str(ak / "dense_vectors.npy"), np.zeros((3, 512), dtype=np.float32))
    (ak / "meta.json").write_text(json.dumps({"count": 99, "created_at": "2026-01-01T00:00:00Z"}))
    db = tmp_path / "state.db"
    conn = sqlite3.connect(str(db))
    try:
        conn.executescript(
            """
            CREATE TABLE akashic_fts_content (
                id TEXT PRIMARY KEY UNIQUE NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT ''
            );
            CREATE VIRTUAL TABLE akashic_fts USING fts5(
                content, title, tags,
                content='akashic_fts_content', content_rowid='rowid'
            );
            """
        )
        conn.execute("INSERT INTO akashic_fts_content (id,title,content,tags) VALUES ('orphan','O','orphan','x')")
        conn.commit()
    finally:
        conn.close()
    return ak, db


def test_audit_reports_repairable_mismatches(tmp_path):
    ak, db = _seed(tmp_path)
    result = audit_akashic_consistency(ak, db)
    assert result["status"] == "REPAIRABLE"
    codes = {i["code"] for i in result["issues"]}
    assert "META_COUNT_MISMATCH" in codes
    assert "VECTORS_ROW_MISMATCH" in codes
    assert "DENSE_ROW_MISMATCH" in codes
    assert "FTS_ORPHAN_IDS" in codes
    assert "FTS_MISSING_PRIMARY_IDS" in codes


def test_repair_rebuilds_derived_indexes_from_primary(tmp_path):
    ak, db = _seed(tmp_path)
    with (
        patch("agent.akashic_consistency._get_embedder", return_value=_FakeEmbedder()),
        patch("agent.akashic_consistency.DenseEmbedder", _FakeDense),
        patch("agent.akashic_consistency.Path.home", return_value=tmp_path),
    ):
        result = repair_akashic_derived_indexes(ak, db)
    assert result["status"] == "PASS"
    assert result["after"]["status"] == "PASS"
    assert result["after"]["counts"]["primary_index"] == 2
    assert result["after"]["counts"]["vectors_rows"] == 2
    assert result["after"]["counts"]["dense_rows"] == 2
    assert result["after"]["counts"]["fts_rows"] == 2
    assert Path(result["backup"]).exists()


def test_stats_report_actual_vector_shape_dimension():
    from agent.akashic_memory import AkashicMemory

    ak = AkashicMemory.__new__(AkashicMemory)
    ak._index = [{"id": "a", "tier": 0, "created_at": 1.0, "last_accessed": 1.0, "access_count": 0}]
    ak._vectors = np.zeros((1, 404), dtype=np.float32)
    ak._dense_vectors = np.zeros((1, 512), dtype=np.float32)
    setattr(ak, "embedder", _FakeEmbedder())
    ak._meta = {"created_at": "x", "last_updated": "y"}
    graph = type("G", (), {"nodes": lambda self: [], "edges": lambda self: []})()
    hybrid = type("H", (), {"_graph": type("GR", (), {"_graph": graph})(), "_fts5": type("F", (), {"count": 1})()})()
    setattr(ak, "_hybrid", hybrid)
    assert ak.get_stats()["vector_dim"] == 404


def test_akashic_default_constructor_respects_hermes_home(tmp_path, monkeypatch):
    from agent.akashic_memory import AkashicMemory, MemoryTier

    profile_home = tmp_path / "profile-home"
    monkeypatch.setenv("HERMES_HOME", str(profile_home))
    monkeypatch.setattr(
        "agent.akashic_memory.DenseEmbedder.embed",
        lambda text: np.ones((512,), dtype=np.float32),
    )

    ak = AkashicMemory()
    fid = ak.store("profile scoped akashic fact", metadata={"source": "test"}, tier=MemoryTier.SEMANTIC)

    assert fid.startswith("ak_")
    assert str(profile_home / "data" / "akashic") == str(ak.home)
    assert (profile_home / "data" / "akashic" / "index.pkl").exists()
    assert (profile_home / "state.db").exists()
    assert not (tmp_path / ".hermes" / "data" / "akashic" / "index.pkl").exists()


def test_consistency_default_paths_respect_hermes_home(tmp_path, monkeypatch):
    from agent.akashic_memory import AkashicMemory

    profile_home = tmp_path / "profile-home-2"
    monkeypatch.setenv("HERMES_HOME", str(profile_home))
    monkeypatch.setattr(
        "agent.akashic_memory.DenseEmbedder.embed",
        lambda text: np.ones((512,), dtype=np.float32),
    )
    AkashicMemory().store("profile consistency fact", metadata={"source": "test"})
    result = audit_akashic_consistency()
    assert result["status"] == "PASS"
    assert result["akashic_home"] == str(profile_home / "data" / "akashic")
    assert result["state_db"] == str(profile_home / "state.db")


def test_tombstone_curated_entry_filters_default_search(tmp_path, monkeypatch):
    from agent.akashic_memory import AkashicMemory, MemoryTier

    profile_home = tmp_path / "profile-home-3"
    monkeypatch.setenv("HERMES_HOME", str(profile_home))
    monkeypatch.setattr(
        "agent.akashic_memory.DenseEmbedder.embed",
        lambda text: np.ones((512,), dtype=np.float32),
    )
    ak = AkashicMemory()
    old = "curated tombstone old unique fact"
    new = "curated tombstone new unique fact"
    old_id = ak.store(old, metadata={"source": "curated_memory_tool", "target": "memory", "action": "add"}, tier=MemoryTier.SEMANTIC)
    new_id = ak.store(new, metadata={"source": "curated_memory_tool", "target": "memory", "action": "replace"}, tier=MemoryTier.SEMANTIC)

    result = ak.tombstone_curated_entry("memory", old, reason="test_replace", replacement_id=new_id)
    assert result["status"] == "tombstoned"
    assert result["ids"] == [old_id]

    assert not any(r["id"] == old_id for r in ak.search(old, n=5))
    inactive = ak.search(old, n=5, include_inactive=True)
    assert any(r["id"] == old_id for r in inactive)
    old_fragment = ak.get_fragment(old_id)
    assert old_fragment is not None
    assert old_fragment["metadata"]["validity_status"] == "superseded"
    assert old_fragment["metadata"]["replacement_id"] == new_id
    assert ak.get_stats()["inactive_count"] == 1


def test_long_lived_instance_reloads_cross_instance_store(tmp_path, monkeypatch):
    from agent.akashic_memory import AkashicMemory

    profile_home = tmp_path / "profile-home-4"
    monkeypatch.setenv("HERMES_HOME", str(profile_home))
    monkeypatch.setattr(
        "agent.akashic_memory.DenseEmbedder.embed",
        lambda text: np.ones((512,), dtype=np.float32),
    )
    old_instance = AkashicMemory()
    writer = AkashicMemory()
    fid = writer.store("cross instance store visible unique fact", metadata={"source": "test"})

    results = old_instance.search("cross instance store visible", n=5)
    assert any(r["id"] == fid for r in results)
    assert old_instance.get_stats()["count"] == 1


def test_long_lived_instance_reloads_cross_instance_tombstone_and_delete(tmp_path, monkeypatch):
    from agent.akashic_memory import AkashicMemory, MemoryTier

    profile_home = tmp_path / "profile-home-5"
    monkeypatch.setenv("HERMES_HOME", str(profile_home))
    monkeypatch.setattr(
        "agent.akashic_memory.DenseEmbedder.embed",
        lambda text: np.ones((512,), dtype=np.float32),
    )
    reader = AkashicMemory()
    writer = AkashicMemory()
    text = "cross instance tombstone visible unique fact"
    fid = writer.store(text, metadata={"source": "curated_memory_tool", "target": "memory", "action": "add"}, tier=MemoryTier.SEMANTIC)
    assert any(r["id"] == fid for r in reader.search(text, n=5))

    writer.tombstone_curated_entry("memory", text, reason="test_cross_instance")
    assert not any(r["id"] == fid for r in reader.search(text, n=5))
    assert any(r["id"] == fid for r in reader.search(text, n=5, include_inactive=True))

    writer.delete(fid)
    assert reader.get_fragment(fid) is None
    assert reader.get_stats()["count"] == 0


def test_multi_writer_threaded_store_preserves_all_fragments(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from agent.akashic_memory import AkashicMemory

    profile_home = tmp_path / "profile-home-6"
    monkeypatch.setenv("HERMES_HOME", str(profile_home))
    monkeypatch.setattr(
        "agent.akashic_memory.DenseEmbedder.embed",
        lambda text: np.ones((512,), dtype=np.float32),
    )

    # Construct instances before concurrent writes so each starts with a stale
    # empty in-memory index.  The write lock must force reload-before-mutate.
    writers = [AkashicMemory() for _ in range(12)]

    def write_one(i):
        return writers[i].store(f"multi writer lock unique fact {i}", metadata={"source": "test", "writer": i})

    with ThreadPoolExecutor(max_workers=6) as ex:
        ids = list(ex.map(write_one, range(len(writers))))

    reader = AkashicMemory()
    stats = reader.get_stats()
    assert stats["count"] == len(writers)
    assert stats["dense_count"] == len(writers)
    assert len(set(ids)) == len(writers)
    all_ids = {entry["id"] for entry in reader.get_all(limit=50)}
    assert set(ids) <= all_ids
    result = audit_akashic_consistency(profile_home / "data" / "akashic", profile_home / "state.db")
    assert result["status"] == "PASS"
    assert result["counts"]["primary_index"] == len(writers)
    assert result["counts"]["vectors_rows"] == len(writers)
    assert result["counts"]["dense_rows"] == len(writers)
    assert result["counts"]["fts_rows"] == len(writers)
