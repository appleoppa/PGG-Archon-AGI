import json
from pathlib import Path

from agent.pgg_batch_proof_metabolism_loop import run_batch_metabolism_loop


def test_run_batch_metabolism_loop_stops_before_execute_when_dry_run(tmp_path):
    calls = []

    def fake_runner(cmd, timeout=300):
        calls.append(cmd)
        if "pgg-promotion-authority-matrix" in cmd[0]:
            return {"exit_code": 0, "output": json.dumps({"ok": True, "rundir": str(tmp_path / "phase2"), "total_queue": 3})}
        if "pgg-proof-packet-completion" in cmd[0]:
            outdir = Path(cmd[cmd.index("--outdir") + 1])
            outdir.mkdir(parents=True, exist_ok=True)
            (outdir / "completion_results.json").write_text("[]", encoding="utf-8")
            (outdir / "controlled_promotion_proposal.json").write_text("[]", encoding="utf-8")
            return {"exit_code": 0, "output": json.dumps({"completed_count": 3, "controlled_promotion_proposal_count": 1, "verdict_counts": {"PASS_CONTROLLED_PROMOTION_PROPOSAL": 1}})}
        if "pgg-controlled-genedb-mutation" in cmd[0]:
            assert "--execute" not in cmd
            return {"exit_code": 0, "output": json.dumps({"db_mutation": False, "promoted_count": 1, "source_missing_marked_count": 0})}
        raise AssertionError(cmd)

    result = run_batch_metabolism_loop(tmp_path / "run", limit=3, execute=False, runner=fake_runner)

    assert result["schema"] == "PGGBatchProofMetabolismLoop/v0.1"
    assert result["db_mutation"] is False
    assert result["net_gain"]["promoted"] == 1
    assert len(calls) == 3


def test_run_batch_metabolism_loop_executes_mutation_when_enabled(tmp_path):
    mutation_cmds = []

    def fake_runner(cmd, timeout=300):
        if "pgg-promotion-authority-matrix" in cmd[0]:
            return {"exit_code": 0, "output": json.dumps({"ok": True, "rundir": str(tmp_path / "phase2"), "total_queue": 10})}
        if "pgg-proof-packet-completion" in cmd[0]:
            return {"exit_code": 0, "output": json.dumps({"completed_count": 10, "controlled_promotion_proposal_count": 2, "verdict_counts": {"PASS_CONTROLLED_PROMOTION_PROPOSAL": 2, "BLOCKED_SOURCE_MISSING": 8}})}
        if "pgg-controlled-genedb-mutation" in cmd[0]:
            mutation_cmds.append(cmd)
            assert "--execute" in cmd
            return {"exit_code": 0, "output": json.dumps({"db_mutation": True, "promoted_count": 2, "source_missing_marked_count": 8})}
        raise AssertionError(cmd)

    result = run_batch_metabolism_loop(tmp_path / "run", limit=10, execute=True, runner=fake_runner)

    assert result["db_mutation"] is True
    assert result["net_gain"] == {"promoted": 2, "blocked_source_missing": 8, "queue_reduced_estimate": 10}
    assert mutation_cmds
