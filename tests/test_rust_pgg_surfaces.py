"""Round9 smoke tests for Rust-native PGG read-only surfaces.

These tests verify importability, JSON contracts, invalid-input boundaries,
ABI symbols, hash registry shape, and a lightweight performance baseline.
They do not claim full AGI, external benchmark success, or legal correctness.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

import hermes_pgg_ecc
import hermes_pgg_overlay
import hermes_pgg_status

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "venv/lib/python3.11/site-packages"
MODULES = {
    "hermes_pgg_status": hermes_pgg_status,
    "hermes_pgg_ecc": hermes_pgg_ecc,
    "hermes_pgg_overlay": hermes_pgg_overlay,
}


def _load_json(text: str) -> dict:
    data = json.loads(text)
    assert isinstance(data, dict)
    return data


def test_rust_surface_versions_and_boundaries() -> None:
    for name, module in MODULES.items():
        version = module.version()
        assert name in version
        assert "read-only" in version


def test_status_surface_contracts() -> None:
    passed = _load_json(hermes_pgg_status.summarize(4, 4))
    assert passed["schema"] == "HermesPGGStatusRust/v1"
    assert passed["status"] == "PASS"
    assert passed["failed_count"] == 0
    assert "not proof" in passed["boundary"]

    watch = _load_json(hermes_pgg_status.summarize(2, 4))
    assert watch["status"] == "WATCH"
    assert watch["failed_count"] == 2


def test_ecc_surface_contracts_and_invalid_json_boundary() -> None:
    clean = _load_json(hermes_pgg_ecc.evaluate("{}"))
    assert clean["schema"] == "HermesPGGEccRust/v1"
    assert clean["status"] == "PASS"
    assert clean["score"] == 100.0

    blocked = _load_json(
        hermes_pgg_ecc.evaluate(
            json.dumps({"hallucination": 1.0, "security": 1.0, "unverified_completion": 1.0})
        )
    )
    assert blocked["status"] == "BLOCKED"
    assert blocked["total_penalty"] == 75.0

    invalid = _load_json(hermes_pgg_ecc.evaluate("not-json"))
    assert invalid["status"] == "PASS"
    assert invalid["total_penalty"] == 0.0


def test_overlay_surface_contracts() -> None:
    inventory = {"summary": {"items": 23, "importable_files": 22, "dirs": 1}}
    report = _load_json(hermes_pgg_overlay.summarize_inventory(json.dumps(inventory)))
    assert report["schema"] == "HermesPGGOverlayRust/v1"
    assert report["status"] == "WATCH"
    assert report["item_count"] == 23
    assert report["importable_files"] == 22
    assert report["dirs"] == 1
    assert "no filesystem mutation" in report["boundary"]


def test_installed_so_hashes_and_pyinit_symbols() -> None:
    for name in MODULES:
        so_path = SITE / f"{name}.abi3.so"
        assert so_path.is_file(), so_path
        digest = hashlib.sha256(so_path.read_bytes()).hexdigest()
        assert len(digest) == 64
        nm = subprocess.run(
            ["nm", "-gU", str(so_path)],
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        assert f"_PyInit_{name}" in nm.stdout


def test_lightweight_performance_baseline() -> None:
    start = time.perf_counter()
    for _ in range(1000):
        hermes_pgg_status.summarize(4, 4)
        hermes_pgg_ecc.evaluate('{"missing_evidence":0.1}')
        hermes_pgg_overlay.summarize_inventory(
            '{"summary":{"items":23,"importable_files":22,"dirs":1}}'
        )
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"3000 Rust surface calls took {elapsed:.4f}s"
