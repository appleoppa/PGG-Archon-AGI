from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.pgg_archon_benchmark_corpus import list_benchmarks, load_benchmark
from agent.pgg_archon_benchmark_harness import (
    BenchReport,
    ItemVerdict,
    run_bench,
)


def test_corpus_benchmarks_present() -> None:
    names = list_benchmarks()
    assert set(names) == {"mmlu", "gsm8k", "bigbench"}


def test_corpus_each_benchmark_has_five_items() -> None:
    for name in list_benchmarks():
        items = load_benchmark(name)
        assert len(items) == 5
        for it in items:
            assert it.question and it.answer


def test_bench_report_accuracy() -> None:
    items = [
        ItemVerdict("mmlu", "a", "q", "4", "4", True, 200, 1),
        ItemVerdict("mmlu", "b", "q", "Paris", "Paris", True, 200, 5),
        ItemVerdict("mmlu", "c", "q", "water", "H2O", False, 200, 3),
    ]
    rep = BenchReport(provider="x", model="y", started_at="t0", finished_at="t1", items=items)
    assert rep.accuracy() == pytest.approx(2 / 3)


def test_bench_report_to_dict_includes_boundary() -> None:
    rep = BenchReport(provider="x", model="y", started_at="t0", finished_at="t1")
    d = rep.to_dict()
    assert d["schema"] == "PGGArchonBenchReport/v1"
    assert "boundary" in d
