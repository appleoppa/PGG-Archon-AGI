"""PGG Archon provenance / node identity / integrity check.
Absorbed from apex-spiral license/watermark module as lightweight provenance.
Boundary: no license enforcement locks, no DRM, no Hermes core mutation.
"""
from __future__ import annotations

from typing import Any

try:
    import hermes_pgg_archon_utils as _native_mod  # type: ignore[import-untyped]

    _NATIVE = True
except ImportError:
    _NATIVE = False

import hashlib
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

HERMES_HOME = Path.home() / ".hermes"


@dataclass(frozen=True)
class ProvenanceReport:
    schema: str
    status: str
    node_id: str
    repo_sha: str
    file_count: int
    integrity_ok: bool
    evidence_hash: str


if _NATIVE:

    def provenance() -> dict[str, Any]:
        import json

        raw = _native_mod.provenance("~/.hermes")
        return json.loads(raw)

else:

    def _stable_node_id() -> str:
        host = platform.node()
        user = __import__("getpass", fromlist=["getuser"]).getuser()
        raw = f"pgg_archon_{user}@{host}"
        return f"node_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

    def _repo_head() -> str:
        try:
            import subprocess

            r = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(HERMES_HOME / "hermes-agent"),
            )
            return r.stdout.strip()[:16] if r.returncode == 0 else "no_git"
        except Exception:
            return "unknown"

    def provenance() -> dict[str, Any]:
        node = _stable_node_id()
        sha = _repo_head()
        agent_dir = HERMES_HOME / "hermes-agent" / "agent"
        py_files = list(agent_dir.rglob("pgg_archon_*.py")) if agent_dir.is_dir() else []
        file_count = len(py_files)
        core = [
            "pgg_archon_delta_gate.py",
            "pgg_archon_codegenesis_scanner.py",
            "pgg_archon_memory_trace.py",
            "pgg_archon_v103_self_loop.py",
        ]
        missing = [f for f in core if not (agent_dir / f).is_file()]
        empty = [f for f in core if (agent_dir / f).stat().st_size == 0]
        integrity_ok = not missing and not empty
        warns: list[str] = []
        if missing:
            warns.append(f"missing_modules={missing}")
        if empty:
            warns.append(f"empty_modules={empty}")
        status = "PASS" if integrity_ok else "WATCH"
        payload = "|".join([node, sha, str(file_count), str(integrity_ok)])
        return asdict(
            ProvenanceReport(
                schema="PGGArchonProvenance/v1",
                status=status,
                node_id=node,
                repo_sha=sha,
                file_count=file_count,
                integrity_ok=integrity_ok,
                evidence_hash=hashlib.sha256(payload.encode()).hexdigest(),
            )
        )


__all__ = ["ProvenanceReport", "provenance"]