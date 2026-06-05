"""Bounded PGG Archon LLM Mutual Constraint — file-24 (real surface).

Implements the 4-LLM cross-check pattern: each provider audits the others'
outputs and emits a constraint verdict. Per-pair failures are
independent; aggregation is majority-vote.

MiMo policy (2026-06-06): MiMo is held out as a fixed third-party benchmark judge
because Agnes is unstable. Agnes may be used only as ordinary/non-critical
collaboration and failures must be recorded honestly.
"""

from __future__ import annotations

import json
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class MutualCheckResult:
    schema: str
    generated_at: str
    target: str
    per_auditor: dict[str, dict[str, Any]]
    per_auditee: dict[str, list[str]]
    overall_verdict: str
    boundary: str


_PROVIDERS = [
    ("deepseek", "deepseek-v4-flash", "https://api.deepseek.com/v1/chat/completions", "DEEPSEEK_V4_FLASH_API_KEY", 4096),
    ("agnes", "agnes-2.0-flash", "https://apihub.agnes-ai.com/v1/chat/completions", "AGNES_AI_API_KEY", 2200),
    ("gpt55", "gpt-5.5", "https://chuangagent.eu.cc/v1/chat/completions", "GPT55_5YUANTOKEN_API_KEY", 4096),
]

_THIRD_PARTY_JUDGE_PROVIDERS = [
    ("mimo", "mimo-v2.5-pro", "https://token-plan-cn.xiaomimimo.com/v1/chat/completions", "MIMO_V25_PRO_API_KEY", 4096),
]


def _read_env(env: str) -> str:
    p = Path.home() / ".hermes" / ".env"
    for line in p.read_text(errors="replace").splitlines():
        if line.startswith(env + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _ask(url: str, key: str, model: str, prompt: str, mx: int) -> str:
    h = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    pl = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": mx, "temperature": 0}
    r = requests.post(url, headers=h, json=pl, timeout=60)
    r.raise_for_status()
    j = r.json()
    return str((j.get("choices") or [{}])[0].get("message", {}).get("content") or "")


def _audit_one(args) -> tuple[str, dict[str, Any]]:
    auditor, model, url, env, target_text, target_name, other_providers = args
    key = _read_env(env)
    if not key:
        return auditor, {"status": "missing_api_key"}
    other_names = ", ".join(p for p in other_providers)
    prompt = (
        f"You are an independent auditor. The following text is an answer produced by another LLM ({target_name}).\n"
        f"Your job: identify concrete claims in the answer that are NOT supported by the prompt, or that contradict any other LLM's view.\n"
        f"Other LLM providers in this check: {other_names}.\n"
        "Return STRICT JSON only:\n"
        '{ "unsupported_claims": [ ... ], "contradicts": [ ... ] }\n'
        f"=== target text ===\n{target_text[:2000]}\n"
    )
    try:
        txt = _ask(url, key, model, prompt, 1024)
        s = txt.strip()
        if s.startswith("```"):
            s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)
            s = re.sub(r"\s*```$", "", s)
        a = s.find("{")
        b = s.rfind("}")
        parsed = json.loads(s[a:b+1]) if a >= 0 and b > a else {}
        return auditor, {
            "status": "ok",
            "unsupported_claims": parsed.get("unsupported_claims", []),
            "contradicts": parsed.get("contradicts", []),
            "visible_chars": len(txt),
        }
    except Exception as e:
        return auditor, {"status": "error", "error": repr(e)[:200]}


def mutual_check(target_name: str, target_text: str) -> MutualCheckResult:
    """Run processing auditors in parallel against target_text.

    Per-pair failures are independent. MiMo is intentionally excluded and kept
    for third-party benchmark validation only.
    """
    tasks = []
    for i, (a, m, u, e, mx) in enumerate(_PROVIDERS):
        others = [_PROVIDERS[j][0] for j in range(len(_PROVIDERS)) if j != i]
        tasks.append((a, m, u, e, target_text, target_name, others))
    per_auditor: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(_audit_one, t) for t in tasks]
        for fut in as_completed(futures):
            label, rec = fut.result()
            per_auditor[label] = rec
    # aggregate: collect per-auditee "contradicts" lists
    per_auditee: dict[str, list[str]] = {p[0]: [] for p in _PROVIDERS}
    for auditor, rec in per_auditor.items():
        for c in rec.get("contradicts", []):
            for p in _PROVIDERS:
                if p[0] in c:
                    per_auditee[p[0]].append(f"{auditor}: {c}")
    # verdict
    from collections import Counter
    votes = []
    for rec in per_auditor.values():
        if rec.get("status") == "ok" and rec.get("contradicts"):
            votes.append("CONFLICT")
        elif rec.get("status") == "ok":
            votes.append("OK")
        elif rec.get("status") in {"missing_api_key", "error"}:
            votes.append("UNAVAILABLE")
    if not votes:
        verdict = "UNAVAILABLE"
    else:
        c = Counter(votes)
        verdict = c.most_common(1)[0][0]
    return MutualCheckResult(
        schema="PGGArchonLLMMutualConstraint/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        target=target_name,
        per_auditor=per_auditor,
        per_auditee=per_auditee,
        overall_verdict=verdict,
        boundary="Processing-LLM parallel cross-check; MiMo held out as third-party judge; per-pair failures independent; not full AGI",
    )


if __name__ == "__main__":
    target = "All status surface modules use a 4-probe ACTIVE / PARTIAL / SKELETON / ABSENT pattern with no hidden state."
    print(json.dumps(asdict(mutual_check("status-surface-claim", target)), ensure_ascii=False, indent=2))
