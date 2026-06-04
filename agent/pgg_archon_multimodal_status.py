"""Bounded PGG Archon Multimodal Status Surface.

This is a *status surface*, not a real multimodal engine. It defines:
  - the four canonical modalities (text, image, audio, video)
  - a probe that checks for installed tool affordances on this machine
  - a write-up helper that emits a JSON status list

It does NOT generate images / audio / video. To actually exercise any
modality, you must invoke a configured image_gen / tts / video_gen tool.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

MODALITIES = ["text", "image", "audio", "video"]

# Each modality has a list of affordance probes. A probe passes if the
# binary / python module / skill is present on disk.
AFFORDANCES: dict[str, list[dict[str, str]]] = {
    "text": [
        {"id": "txt-hermes-agent", "kind": "skill", "path": "hermes-agent/agent/"},
        {"id": "txt-pgg-archon-runtime", "kind": "skill", "path": "hermes-agent/skills/workflow/pgg-archon-runtime/"},
    ],
    "image": [
        {"id": "img-apikey-image-gen", "kind": "skill", "path": "hermes-agent/skills/apikey-image-gen/"},
        {"id": "img-apex-native-typography", "kind": "skill", "path": "hermes-agent/skills/creative/apex-native-typography-governance/"},
    ],
    "audio": [
        {"id": "aud-hermes-tts", "kind": "config", "path": "hermes-agent/hermes_cli/main.py"},
        {"id": "aud-edge-tts", "kind": "binary", "exec": "edge-tts"},
    ],
    "video": [
        {"id": "vid-hyperframes", "kind": "skill", "path": "hermes-agent/skills/hyperframes/"},
        {"id": "vid-grok-image-to-video", "kind": "skill", "path": "hermes-agent/skills/grok-image-to-video/"},
    ],
}


@dataclass
class ModalityStatus:
    modality: str
    state: str  # present / partial / absent
    affordances_present: list[str]
    affordances_total: int


def _check_path(path: str, home: Path) -> bool:
    if path.startswith("/"):
        return Path(path).exists()
    return (home / path).exists()


def _check_exec(name: str) -> bool:
    return shutil.which(name) is not None


def collect_multimodal_status(home: Path | None = None) -> dict[str, Any]:
    home = home or Path.home() / ".hermes"
    out: list[ModalityStatus] = []
    for mod in MODALITIES:
        items = AFFORDANCES.get(mod, [])
        present: list[str] = []
        for aff in items:
            kind = aff.get("kind")
            if kind == "binary":
                if _check_exec(aff["exec"]):
                    present.append(aff["id"])
            else:
                if _check_path(aff["path"], home):
                    present.append(aff["id"])
        if not items:
            state = "absent"
        elif len(present) == len(items):
            state = "present"
        elif present:
            state = "partial"
        else:
            state = "absent"
        out.append(ModalityStatus(modality=mod, state=state, affordances_present=present, affordances_total=len(items)))
    overall_present = sum(1 for c in out if c.state == "present")
    return {
        "schema": "PGGArchonMultimodalStatus/v1",
        "modalities": [asdict(c) for c in out],
        "overall": "READY" if overall_present == len(MODALITIES) else (
            "PARTIAL" if overall_present > 0 else "ABSENT"
        ),
        "boundary": "status surface only; no actual image/audio/video generation; tools must be invoked separately",
    }


def write_multimodal_status(path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = collect_multimodal_status()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path.home() / ".hermes/workspace/audit/multimodal_status.json"))
    args = ap.parse_args()
    data = write_multimodal_status(Path(args.out))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
