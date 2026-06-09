from __future__ import annotations

import json

from agent import pgg_guarded_production_enable_gate as gate


def test_http_json_omits_session_token_when_env_absent(monkeypatch):
    captured = {}

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(req, timeout=20):
        captured["headers"] = dict(req.header_items())
        return DummyResponse()

    monkeypatch.setattr(gate, "TOKEN", "")
    monkeypatch.setattr(gate.urllib.request, "urlopen", fake_urlopen)

    ok, data = gate._http_json("/probe")

    assert ok is True
    assert data == {"ok": True}
    normalized = {k.lower(): v for k, v in captured["headers"].items()}
    assert "x-hermes-session-token" not in normalized
    assert normalized["content-type"] == "application/json"


def test_default_loopback_token_is_only_sent_to_loopback(monkeypatch):
    captured = {}

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(req, timeout=20):
        captured["headers"] = dict(req.header_items())
        return DummyResponse()

    monkeypatch.setattr(gate, "TOKEN", gate.LOCAL_LOOPBACK_DASHBOARD_TOKEN)
    monkeypatch.setattr(gate, "API", "https://example.invalid")
    monkeypatch.setattr(gate.urllib.request, "urlopen", fake_urlopen)

    ok, data = gate._http_json("/probe")

    assert ok is True
    assert data == {"ok": True}
    normalized = {k.lower(): v for k, v in captured["headers"].items()}
    assert "x-hermes-session-token" not in normalized


def test_default_loopback_token_is_sent_to_loopback(monkeypatch):
    captured = {}

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(req, timeout=20):
        captured["headers"] = dict(req.header_items())
        return DummyResponse()

    monkeypatch.setattr(gate, "TOKEN", gate.LOCAL_LOOPBACK_DASHBOARD_TOKEN)
    monkeypatch.setattr(gate, "API", "http://127.0.0.1:9197")
    monkeypatch.setattr(gate.urllib.request, "urlopen", fake_urlopen)

    ok, data = gate._http_json("/probe")

    assert ok is True
    assert data == {"ok": True}
    normalized = {k.lower(): v for k, v in captured["headers"].items()}
    assert normalized["x-hermes-session-token"] == gate.LOCAL_LOOPBACK_DASHBOARD_TOKEN


def test_http_json_includes_session_token_when_env_present(monkeypatch):
    captured = {}

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(req, timeout=20):
        captured["headers"] = dict(req.header_items())
        return DummyResponse()

    monkeypatch.setattr(gate, "TOKEN", "test-token")
    monkeypatch.setattr(gate.urllib.request, "urlopen", fake_urlopen)

    ok, data = gate._http_json("/probe")

    assert ok is True
    assert data == {"ok": True}
    normalized = {k.lower(): v for k, v in captured["headers"].items()}
    assert normalized["x-hermes-session-token"] == "test-token"


def test_main_updates_latest_snapshot_atomically(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(gate, "HOME", tmp_path)
    monkeypatch.setattr(
        gate,
        "_http_json",
        lambda path, method="GET", payload=None, timeout=20: (
            True,
            {
                "selected_provider": "gpt",
                "production_answer_chain_replaced": "guarded_strict_exact_general",
                "credential_integration": "ENABLED_WITH_EXISTING_AUTH_JSON_POOL",
                "oauth_integration": "WATCH_NO_ACTIVE_OAUTH_CREDENTIAL",
                "account_pool_integration": "ENABLED_WITH_EXISTING_AUTH_JSON_POOL",
                "scheduler_security_core_mutated": False,
                "production_runtime_status": {
                    "status": "PASS_GUARDED_STRICT_EXACT_GENERAL_ENABLED_WITH_OAUTH_WATCH",
                    "allowed_scope": "exact/general guarded production lane",
                    "denied_scope": [
                        "chinese_legal",
                        "audit_judge",
                        "agi_architecture_coding",
                        "scheduler_security_mutation",
                    ],
                    "auth_summary_no_secrets": {
                        "credential_pool_entry_count": 3,
                        "oauth_active_count": 0,
                    },
                },
            },
        ),
    )

    assert gate.main(["--json"]) == 0
    printed = json.loads(capsys.readouterr().out)
    latest = tmp_path / "data/pgg_guarded_production_enable_gate_latest.json"
    ledger = tmp_path / "data/pgg_guarded_production_enable_gate_ledger.jsonl"

    assert latest.exists()
    assert ledger.exists()
    assert json.loads(latest.read_text(encoding="utf-8")) == printed
    assert json.loads(ledger.read_text(encoding="utf-8").strip()) == printed
    assert printed["status"] == "PASS_GUARDED_STRICT_EXACT_GENERAL_PRODUCTION_ACTIVE"
