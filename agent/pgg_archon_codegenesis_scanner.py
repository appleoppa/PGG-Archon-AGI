"""PGG Archon CodeGenesis scanner.
Boundary: filesystem read-only scan; no auto-fix, no writes, no provider calls, bounded by max_files.
"""
from __future__ import annotations

# Rust PyO3 native bridge
_NATIVE = False
_native_scan = None
try:
    from hermes_pgg_codegenesis_scanner import scan_code_genesis as _native_scan

    _NATIVE = True
except ImportError:
    _NATIVE = False

import os
from pathlib import Path
from typing import Any

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox", "dist", "build", ".mypy_cache", ".pytest_cache"}


def scan_code_genesis(root: str = ".", max_files: int = 30) -> dict[str, Any]:
    """Scan Python files under root and return real, input-dependent metrics."""
    global _NATIVE
    if _NATIVE:
        try:
            return _native_scan(root=root, max_files=max_files)
        except Exception:
            _NATIVE = False

    scanned_root = str(Path(root).resolve())
    if max_files <= 0:
        return {"status": "BLOCKED", "py_count": 0, "findings": [], "skipped_dirs": [], "scanned_root": scanned_root, "warnings": ["max_files must be positive"]}
    if not Path(root).exists():
        return {"status": "BLOCKED", "py_count": 0, "findings": [], "skipped_dirs": [], "scanned_root": scanned_root, "warnings": [f"root not found: {root}"]}

    py_count = 0
    findings: list[dict[str, Any]] = []
    skipped_dirs: list[str] = []
    warnings: list[str] = []
    reached_limit = False

    for dirpath, dirnames, filenames in os.walk(root):
        keep=[]
        for d in dirnames:
            if d in SKIP_DIRS:
                skipped_dirs.append(str(Path(dirpath, d)))
            else:
                keep.append(d)
        dirnames[:] = keep
        for fname in filenames:
            if not fname.endswith('.py'):
                continue
            if py_count >= max_files:
                reached_limit = True
                break
            fpath = Path(dirpath, fname)
            py_count += 1
            try:
                content = fpath.read_text(encoding='utf-8', errors='replace')
                lines = content.splitlines()
                notes=[]
                if len(lines) > 500:
                    notes.append('large_file')
                if 'eval(' in content or 'exec(' in content:
                    notes.append('dynamic_exec_watch')
                if 'mock' in content.lower() or 'simulation' in content.lower() or 'dry_run' in content.lower():
                    notes.append('simulation_marker_watch')
                findings.append({"file": str(fpath), "lines": len(lines), "bytes": len(content.encode('utf-8')), "notes": notes})
            except OSError as e:
                findings.append({"file": str(fpath), "error": str(e)})
        if reached_limit:
            break

    if py_count == 0:
        status = 'BLOCKED'
        warnings.append('no python files found')
    elif reached_limit:
        status = 'WATCH'
        warnings.append(f'max_files limit reached: {max_files}')
    else:
        status = 'PASS'
    return {"status": status, "py_count": py_count, "findings": findings, "skipped_dirs": skipped_dirs, "scanned_root": scanned_root, "warnings": warnings}
