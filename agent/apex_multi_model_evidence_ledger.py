"""Read-only multi-model call evidence ledger.

This ledger records only metadata needed for adjudication: provider, model,
status, hashes and decision. It never stores prompts, raw responses or keys.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

DEFAULT_REVIEW_DIR = Path("workspace/llm_next_stage_reviews")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ledger_entry_from_review_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    provider = "unknown"
    model = "unknown"
    status = "RECORDED"
    decision = "review_file_present"
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            first_mapping = next((item for item in parsed if isinstance(item, dict)), {})
            parsed_map = first_mapping if isinstance(first_mapping, dict) else {}
            parsed_text = json.dumps(parsed, ensure_ascii=False)
        elif isinstance(parsed, dict):
            parsed_map = parsed
            parsed_text = json.dumps(parsed, ensure_ascii=False)
        else:
            parsed_map = {}
            parsed_text = str(parsed)
        provider = str(parsed_map.get("provider") or parsed_map.get("source") or provider)
        model = str(parsed_map.get("model") or model)
        content = parsed_map.get("content")
        if (isinstance(content, str) and "不允许" in content) or "不允许" in parsed_text:
            decision = "hold_or_guarded_next_stage"
        elif isinstance(parsed_map.get("decision"), str):
            decision = str(parsed_map["decision"])[:240]
    except json.JSONDecodeError:
        status = "UNPARSED_RECORDED"
    return {
        "schema": "ApexMultiModelCallEvidence/v1",
        "provider": provider,
        "model": model,
        "status": status,
        "decision": decision,
        "evidence_hash": _hash_text(raw),
        "source_path_hash": _hash_text(str(p)),
        "raw_response_stored": False,
        "credential_stored": False,
    }


def build_multi_model_evidence_ledger(*, review_dir: str | Path = DEFAULT_REVIEW_DIR) -> dict[str, Any]:
    root = Path(review_dir)
    entries: list[dict[str, Any]] = []
    if root.exists():
        for path in sorted(root.glob("*.json")):
            entries.append(ledger_entry_from_review_file(path))
    providers = sorted({e["provider"] for e in entries if e.get("provider") and e.get("provider") != "unknown"})
    status = "UNKNOWN" if not entries else ("PASS" if providers else "WATCH")
    return {
        "schema": "ApexMultiModelEvidenceLedger/v1",
        "status": status,
        "entry_count": len(entries),
        "provider_count": len(providers),
        "providers": providers,
        "entries": entries,
        "side_effects": "read_only_ledger",
        "external_calls_made": False,
        "raw_responses_stored": False,
        "credentials_stored": False,
    }


__all__ = ["build_multi_model_evidence_ledger", "ledger_entry_from_review_file"]
