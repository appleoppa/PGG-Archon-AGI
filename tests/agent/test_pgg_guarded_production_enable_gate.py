from __future__ import annotations

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
