"""Regression tests for closed stdout/stderr resilience in CLI printing."""

import pytest


class _ClosedStdout:
    def write(self, _data):
        raise ValueError("I/O operation on closed file")

    def flush(self):
        raise ValueError("I/O operation on closed file")


class _BrokenLoop:
    def is_running(self):
        return False

    def call_soon_threadsafe(self, _callback):
        raise ValueError("I/O operation on closed file")


class _RunningAppWithBrokenLoop:
    _is_running = True
    loop = _BrokenLoop()


def test_cprint_swallows_closed_stdout_fallback(monkeypatch):
    import cli as cli_mod

    monkeypatch.setattr(cli_mod, "_pt_print", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("I/O operation on closed file")))
    monkeypatch.setattr(cli_mod.sys, "stdout", _ClosedStdout())

    cli_mod._cprint("must not crash")


def test_cprint_swallows_closed_prompt_toolkit_loop(monkeypatch):
    import cli as cli_mod

    monkeypatch.setattr(cli_mod, "get_app_or_none", lambda: _RunningAppWithBrokenLoop(), raising=False)
    monkeypatch.setattr(cli_mod, "_pt_print", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("I/O operation on closed file")))
    monkeypatch.setattr(cli_mod.sys, "stdout", _ClosedStdout())

    cli_mod._cprint("must not crash")


def test_busy_command_swallows_closed_stdout(monkeypatch):
    import cli as cli_mod

    monkeypatch.setattr(cli_mod.sys, "stdout", _ClosedStdout())
    cli = object.__new__(cli_mod.HermesCLI)
    cli._command_running = False
    cli._command_status = ""
    cli._invalidate = lambda min_interval=0.0: None

    with cli_mod.HermesCLI._busy_command(cli, "Testing"):
        pass
