from pathlib import Path

from agent.apex_sequence_loop_runner import run_apex_triple_sequence_loops


def test_apex_triple_sequence_runner_runs_three_by_five(tmp_path):
    report = run_apex_triple_sequence_loops(write_report=True, report_dir=tmp_path)
    assert report["schema"] == "ApexTripleSequenceLoopReport/v1"
    assert report["sequence_count"] == 3
    assert report["iterations_per_sequence"] == 5
    assert report["run_count"] == 15
    assert report["bottlenecks"]
    assert Path(report["report_path"]).exists()
    assert report["agi_completion_claim"] is False


def test_apex_triple_sequence_runner_accepts_custom_base():
    base = {"Tok": 0.1, "Clw": 0.1, "Agt": 0.1, "Pan": 0.1, "Prm": 0.1, "Soul": 0.1, "Run": 0.1, "Net": 0.1, "Err": 0.1, "Mem": 0.1, "Res": 0.1, "Log": 0.1}
    report = run_apex_triple_sequence_loops(base, iterations_per_sequence=2, pressure_rebounds={"Err": 0.0})
    assert report["run_count"] == 6
    assert all("evm_value" in run for run in report["runs"])
