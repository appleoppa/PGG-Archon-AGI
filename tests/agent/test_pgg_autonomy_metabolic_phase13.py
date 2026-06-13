import json

from agent import pgg_autonomy_default_loop as loop


def test_phase13_balanced_profile_is_high_throughput():
    profile = loop.resolve_metabolic_acceleration("balanced")

    assert profile["acceleration"] == "balanced"
    assert profile["max_batches"] == 5
    assert profile["batch_size"] == 20
    assert profile["daily_cap"] == 100


def test_phase13_execute_requires_explicit_gate(monkeypatch, tmp_path):
    calls = []

    def fake_batch(outdir, *, limit, execute, prefer_rust_mutation=True, **kwargs):
        calls.append({"outdir": str(outdir), "limit": limit, "execute": execute})
        return {
            "schema": "PGGBatchProofMetabolismLoop/v0.3",
            "outdir": str(outdir),
            "limit": limit,
            "execute": execute,
            "mutation_backend": "rust",
            "db_mutation": False,
            "db_path": str(tmp_path / "genes.sqlite3"),
            "backup_path": None,
            "net_gain": {"promoted": 2, "blocked_source_missing": 1, "queue_reduced_estimate": 3},
            "repair_backlog_count": 0,
            "phase4": {"db_mutation": False},
        }

    monkeypatch.setattr(loop, "METABOLIC_NET_GAIN_ROOT", tmp_path)
    result = loop.run_metabolic_evolution_probe(
        "phase13_no_execute",
        execute=True,
        acceleration="balanced",
        run_batch=fake_batch,
        env_execute="0",
    )

    assert result["status"] == "PASS_DRY_RUN_ONLY"
    assert result["requested_execute"] is True
    assert result["execute_allowed"] is False
    assert result["total_batches"] == 5
    assert all(c["execute"] is False for c in calls)


def test_phase13_high_throughput_runs_multiple_batches_until_daily_cap(monkeypatch, tmp_path):
    calls = []

    def fake_batch(outdir, *, limit, execute, prefer_rust_mutation=True, **kwargs):
        calls.append({"outdir": str(outdir), "limit": limit, "execute": execute})
        return {
            "schema": "PGGBatchProofMetabolismLoop/v0.3",
            "outdir": str(outdir),
            "limit": limit,
            "execute": execute,
            "mutation_backend": "rust",
            "db_mutation": bool(execute),
            "db_path": str(tmp_path / "genes.sqlite3"),
            "backup_path": str(tmp_path / f"backup-{len(calls)}.sqlite3") if execute else None,
            "net_gain": {"promoted": 10, "blocked_source_missing": 10, "queue_reduced_estimate": 20},
            "repair_backlog_count": 0,
            "phase4": {"db_mutation": bool(execute)},
        }

    monkeypatch.setattr(loop, "METABOLIC_NET_GAIN_ROOT", tmp_path)
    result = loop.run_metabolic_evolution_probe(
        "phase13_fast",
        execute=True,
        acceleration="balanced",
        run_batch=fake_batch,
        env_execute="1",
    )

    assert result["status"] == "PASS_EXECUTED_BOUNDED"
    assert result["acceleration"] == "balanced"
    assert result["total_batches"] == 5
    assert result["processed_estimate"] == 100
    assert result["aggregate_net_gain"] == {"promoted": 50, "blocked_source_missing": 50, "queue_reduced_estimate": 100}
    assert all(c["execute"] for c in calls)
    assert all(c["limit"] == 20 for c in calls)


def test_phase13_fuse_stops_on_zero_gain_after_two_batches(monkeypatch, tmp_path):
    calls = []

    def fake_batch(outdir, *, limit, execute, prefer_rust_mutation=True, **kwargs):
        calls.append({"outdir": str(outdir), "limit": limit, "execute": execute})
        return {
            "schema": "PGGBatchProofMetabolismLoop/v0.3",
            "outdir": str(outdir),
            "limit": limit,
            "execute": execute,
            "mutation_backend": "rust",
            "db_mutation": False,
            "db_path": str(tmp_path / "genes.sqlite3"),
            "backup_path": None,
            "net_gain": {"promoted": 0, "blocked_source_missing": 0, "queue_reduced_estimate": 0},
            "repair_backlog_count": 3,
            "phase4": {"db_mutation": False},
        }

    monkeypatch.setattr(loop, "METABOLIC_NET_GAIN_ROOT", tmp_path)
    result = loop.run_metabolic_evolution_probe(
        "phase13_fuse",
        execute=True,
        acceleration="balanced",
        run_batch=fake_batch,
        env_execute="1",
    )

    assert result["status"] == "FUSED_NO_NET_GAIN"
    assert result["total_batches"] == 2
    assert result["fuse_triggered"] is True
    assert "zero_net_gain" in result["fuse_reason"]
