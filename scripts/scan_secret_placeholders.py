#!/usr/bin/env python3
"""Repository secret-like placeholder scanner.

Metadata-only: prints type/path/line/hash, never prints matched secret values.
Intended for docs/examples/tests hardening, not a replacement for provider secret validation.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', '.mypy_cache', '.pytest_cache', 'dist', 'build', '__pycache__'}
SKIP_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.zip', '.gz', '.tgz', '.mp4', '.mov', '.sqlite', '.db', '.pack', '.idx', '.pyc'}
PATTERNS: list[tuple[str, re.Pattern[bytes]]] = [
    ('github_token', re.compile(rb'gh[pousr]_[A-Za-z0-9_]{20,}')),
    ('openai_key', re.compile(rb'sk-[A-Za-z0-9]{20,}')),
    ('anthropic_key', re.compile(rb'sk-ant-[A-Za-z0-9_-]{20,}')),
    ('aws_access_key', re.compile(rb'AKIA[0-9A-Z]{16}')),
    ('google_api_key', re.compile(rb'AIza[0-9A-Za-z_-]{35}')),
    ('telegram_bot_token', re.compile(rb'\b\d{6,10}:[A-Za-z0-9_-]{25,}\b')),
    ('slack_token', re.compile(rb'xox[baprs]-[A-Za-z0-9-]{20,}')),
    ('private_key_block', re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----')),
]
ALLOW_CONTEXT = (b'EXAMPLE', b'FAKE', b'DUMMY', b'MOCK', b'PLACEHOLDER', b'TEST', b'<', b'REDACTED')

SCANNED_PREFIXES = (
    Path('.env.example'),
    Path('hermes_cli'),
    Path('website'),
    Path('skills'),
)
ALLOWLIST_PREFIXES = (
    Path('tests'),
    Path('external'),
)

def in_prefix(path: Path, prefixes: tuple[Path, ...]) -> bool:
    return any(path == prefix or path.is_relative_to(prefix) for prefix in prefixes)

def should_skip(path: Path) -> bool:
    if path.suffix.lower() in SKIP_EXT:
        return True
    if any(part in SKIP_DIRS for part in path.parts):
        return True
    # Default fail gate targets docs/examples/skills and CLI user-facing examples.
    # Tests/external fixtures intentionally contain fake secret shapes for redaction tests.
    return not in_prefix(path, SCANNED_PREFIXES)

def is_allowed_context(data: bytes, start: int, end: int, typ: str) -> bool:
    window = data[max(0, start - 120): min(len(data), end + 120)].upper()
    if any(marker in window for marker in ALLOW_CONTEXT):
        # AWS official EXAMPLE keys are safe fixtures but should still avoid real-looking docs when possible.
        return typ in {'aws_access_key', 'private_key_block'}
    return False

def main() -> int:
    findings = []
    for path in ROOT.rglob('*'):
        if not path.is_file() or should_skip(path.relative_to(ROOT)):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b'\x00' in data[:4096]:
            continue
        for typ, rgx in PATTERNS:
            for m in rgx.finditer(data):
                if is_allowed_context(data, m.start(), m.end(), typ):
                    continue
                findings.append({
                    'type': typ,
                    'path': str(path.relative_to(ROOT)),
                    'line': data[:m.start()].count(b'\n') + 1,
                    'sha256_12': hashlib.sha256(m.group(0)).hexdigest()[:12],
                    'length': len(m.group(0)),
                })
    print(json.dumps({'finding_count': len(findings), 'findings': findings}, ensure_ascii=False, indent=2))
    return 1 if findings else 0

if __name__ == '__main__':
    raise SystemExit(main())
