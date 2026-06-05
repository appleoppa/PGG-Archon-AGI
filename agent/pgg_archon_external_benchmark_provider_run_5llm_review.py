"""5-LLM review of the real provider-run external benchmark 100.

Reads ``provider_run_round1/summary.json``, calls each of the 5 audit
providers (DeepSeek, MiMo, Agnes, MiniMax, gpt5.5), parses the response
(MiniMax via ``pgg_archon_minimax_structured_adapter``), and writes a
combined review file compatible with the existing
``PGGArchonTriadRound3FiveLLMReview/v1`` schema family.

Boundary
--------
This is an LLM-judge review of a real provider-run of a 100-item frozen
internal smoke benchmark, not an official MMLU/GSM8K/BigBench score. Claude
is excluded by user instruction. MiniMax responses are parsed via the
structured-output adapter, which strips <think> blocks and extracts JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import requests

# Reuse the runner's load_dotenv_file
from agent.pgg_archon_external_benchmark_provider_run import load_dotenv_file
from agent.pgg_archon_minimax_structured_adapter import parse_structured_json


# 5 audit providers (Claude excluded per user instruction).
# All use chat_completions path. gpt5.5 chat mode verified 2026-06-04.
AUDIT_PROVIDERS: list[dict[str, Any]] = [
    {
        "provider_id": "deepseek",
        "model": "deepseek-v4-flash",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "key_env": "DEEPSEEK_V4_FLASH_API_KEY",
        "max_tokens": 4096,
    },
    {
        "provider_id": "mimo",
        "model": "mimo-v2.5-pro",
        "url": "https://token-plan-cn.xiaomimimo.com/v1/chat/completions",
        "key_env": "MIMO_V25_PRO_API_KEY",
        "max_tokens": 4096,
    },
    {
        "provider_id": "agnes",
        "model": "agnes-2.0-flash",
        "url": "https://apihub.agnes-ai.com/v1/chat/completions",
        "key_env": "AGNES_AI_API_KEY",
        "max_tokens": 2200,
    },
    {
        "provider_id": "minimax",
        "model": "MiniMax-M3",
        "url": "https://api.minimax.chat/v1/chat/completions",
        "key_env": "MINIMAX_API_KEY",
        "max_tokens": 2200,
    },
    {
        "provider_id": "gpt55",
        "model": "gpt-5.5",
        "url": "https://chuangagent.eu.cc/v1/chat/completions",
        "key_env": "GPT55_5YUANTOKEN_API_KEY",
        "max_tokens": 4096,
    },
]


def _build_audit_prompt(summary: dict[str, Any]) -> str:
    """Build the audit prompt that asks providers to critique the P0 summary.

    The prompt asks for structured JSON output with the same shape as the
    existing 5-LLM review family (verdict, updated_agi_score_0_100, level,
    real_progress, remaining_gaps, next_actions, caveats).
    """
    summary_json = json.dumps(summary, ensure_ascii=False, indent=2)
    return (
        "You are a PGG Archon AGI Process Auditor. "
        "Review the attached real provider-run benchmark summary for the 100-item "
        "frozen internal smoke spec (logic / tool-use / legal-boundary / long-context / "
        "self-boundary, 5 domains x 20 variants). The run called DeepSeek, MiMo, and "
        "gpt5.5 in a real chat_completions provider call. Short-answer scoring uses a "
        "deterministic substring match (not semantic). The boundary says this is not an "
        "official MMLU/GSM8K/BigBench/LegalBench score.\n\n"
        "Specifically evaluate:\n"
        "  1. Is the per-provider pass_rate reasonable given the short-answer substring scorer?\n"
        "  2. Are per-domain pass_rates coherent (e.g. self-boundary/no should usually pass, "
        "     tool-use/calculator_or_code may be hit-or-miss)?\n"
        "  3. Is the boundary statement honest (no claim of L2/full AGI)?\n"
        "  4. What does this provider-run change vs. the prior spec/scorer validation?\n"
        "  5. Remaining gaps for the L1 -> L2 transition.\n\n"
        "Output STRICT JSON with this shape (no markdown, no commentary outside JSON):\n"
        "{\n"
        '  "verdict": "WATCH" | "PASS" | "BLOCKED",\n'
        '  "updated_agi_score_0_100": <integer 0-100>,\n'
        '  "level": "L0" | "L1" | "L2",\n'
        '  "real_progress": [<bullet string>, ...],\n'
        '  "remaining_gaps": [<bullet string>, ...],\n'
        '  "next_actions": [<bullet string>, ...],\n'
        '  "caveats": [<bullet string>, ...]\n'
        "}\n\n"
        f"--- provider_run_round1 summary ---\n{summary_json}\n"
    )


def _call_audit_chat(
    provider: dict[str, Any], prompt: str, *, timeout: int = 120
) -> tuple[str, int | None, int, str | None]:
    api_key = os.environ.get(provider["key_env"])
    if not api_key:
        return "", None, 0, f"missing api key env: {provider['key_env']}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": provider["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": provider["max_tokens"],
        "temperature": 0.0,
    }
    t0 = time.time()
    try:
        r = requests.post(provider["url"], headers=headers, json=payload, timeout=timeout)
        latency = int((time.time() - t0) * 1000)
        if r.status_code >= 400:
            return "", r.status_code, latency, f"HTTP {r.status_code}: {r.text[:300]}"
        data = r.json()
        text = str(data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
        if not text:
            return "", r.status_code, latency, "empty content"
        return text, r.status_code, latency, None
    except Exception as exc:  # noqa: BLE001
        return "", None, int((time.time() - t0) * 1000), repr(exc)


def run_5llm_review(
    summary: dict[str, Any],
    *,
    providers: Sequence[dict[str, Any]] = AUDIT_PROVIDERS,
) -> dict[str, Any]:
    load_dotenv_file()
    prompt = _build_audit_prompt(summary)
    out: dict[str, Any] = {
        "schema": "PGGArchonExternalBenchmarkProviderRun5LLMReview/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "review_target_schema": summary.get("schema"),
        "review_target_path": "provider_run_round1/summary.json",
        "providers": {},
    }
    scores: list[float] = []
    verdicts: list[str] = []
    levels: list[str] = []
    structured_count = 0
    for prov in providers:
        pid = prov["provider_id"]
        print(f"[audit] calling {pid} ({prov['model']})...", flush=True)
        text, status, latency, err = _call_audit_chat(prov, prompt)
        if err or not text:
            out["providers"][pid] = {
                "provider": pid, "model": prov["model"], "ok": False,
                "http_status": status, "text_chars": 0, "visible_output_chars": 0,
                "error": err, "raw_preview": "", "parsed": None,
            }
            print(f"  {pid}: ERROR {err}", flush=True)
            continue
        # Parse: MiniMax must use structured adapter; others try json.loads directly,
        # fall back to structured adapter if that fails.
        if pid == "minimax":
            pr = parse_structured_json(text)
            parsed = pr.data if pr.ok else None
            parse_err = pr.error
        else:
            parsed = None
            parse_err = None
            try:
                parsed = json.loads(text)
            except Exception:
                pr = parse_structured_json(text)
                if pr.ok:
                    parsed = pr.data
                else:
                    parse_err = pr.error
        if isinstance(parsed, dict):
            structured_count += 1
            scores.append(float(parsed.get("updated_agi_score_0_100", 0) or 0))
            verdicts.append(str(parsed.get("verdict", "WATCH")))
            levels.append(str(parsed.get("level", "L0")))
        rec: dict[str, Any] = {
            "provider": pid, "model": prov["model"], "ok": True,
            "http_status": status, "text_chars": len(text),
            "visible_output_chars": len(text),
            "raw_preview": text[:1500],
            "parsed": parsed,
        }
        if parse_err:
            rec["parse_error"] = parse_err
        out["providers"][pid] = rec
        score_disp = parsed.get("updated_agi_score_0_100") if isinstance(parsed, dict) else "N/A"
        verdict_disp = parsed.get("verdict") if isinstance(parsed, dict) else "PARSE_FAIL"
        print(f"  {pid}: {verdict_disp} score={score_disp} latency={latency}ms", flush=True)
    out["structured_provider_count"] = structured_count
    out["scores"] = scores
    out["mean_score"] = round(sum(scores) / len(scores), 2) if scores else 0.0
    out["verdicts"] = verdicts
    out["levels"] = levels
    out["boundary"] = (
        "5-LLM LLM-judge review of real provider-run of 100-item frozen internal "
        "smoke benchmark (DeepSeek / MiMo / gpt5.5). Short-answer scoring is "
        "deterministic substring match. Not official MMLU/GSM8K/BigBench. "
        "Claude excluded. MiniMax parsed via pgg_archon_minimax_structured_adapter."
    )
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--summary",
        default="/Users/appleoppa/.hermes/workspace/audit/systemwide_agi_audit_20260605/provider_run_round1/summary.json",
    )
    parser.add_argument(
        "--output",
        default="/Users/appleoppa/.hermes/workspace/audit/systemwide_agi_audit_20260605/provider_run_round1/5llm_review.json",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    out = run_5llm_review(summary)
    out_path = Path(args.output).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    print(json.dumps({
        "structured_provider_count": out["structured_provider_count"],
        "mean_score": out["mean_score"],
        "verdicts": out["verdicts"],
        "levels": out["levels"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
