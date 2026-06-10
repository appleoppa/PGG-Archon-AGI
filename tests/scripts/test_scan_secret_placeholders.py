from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "scan_secret_placeholders.py"


def load_scanner():
    spec = importlib.util.spec_from_file_location("scan_secret_placeholders_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scanner_flags_openrouter_and_google_without_printing_values(tmp_path, capsys, monkeypatch):
    scanner = load_scanner()
    secret_dir = tmp_path / "evals" / "terminal-bench-2"
    secret_dir.mkdir(parents=True)
    google_key = "AI" + "za" + "A" * 35
    openrouter_key = "sk-or-v1-" + "B" * 32
    (secret_dir / "evaluate_config.yaml").write_text(
        f"google: {google_key}\nopenrouter: {openrouter_key}\n", encoding="utf-8"
    )

    monkeypatch.setattr(scanner, "ROOT", tmp_path)
    code = scanner.main()
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert code == 1
    assert payload["finding_count"] == 2
    assert {item["type"] for item in payload["findings"]} == {"google_api_key", "openrouter_api_key"}
    assert google_key not in out
    assert openrouter_key not in out
    assert all("sha256_12" in item for item in payload["findings"])


def test_scanner_skips_intentional_test_fixtures(tmp_path, capsys, monkeypatch):
    scanner = load_scanner()
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    fake_key = "sk-or-v1-" + "C" * 32
    (test_dir / "fixture.py").write_text(f"TOKEN = {fake_key!r}\n", encoding="utf-8")

    monkeypatch.setattr(scanner, "ROOT", tmp_path)
    code = scanner.main()
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload == {"finding_count": 0, "findings": []}
