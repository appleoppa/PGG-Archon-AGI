#!/usr/bin/env python3
"""Route + Hetu-Luoshu evidence gate.

This is a bounded evidence gate for PGG Archon/Hermes evolution tasks.  It can
run as a sidecar before the main model turn, write route evidence, optionally
execute a real multi-model chain, emit a candidate gene, and fail closed when
stage evidence is incomplete.

Safety boundaries:
- Does not patch files or switch the active main model.
- Does not claim AGI completion.
- Candidate gene != formal gene DB write; formal write is handled by a separate
  audited gate after hash validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/Users/appleoppa/.hermes"))
EVIDENCE_DIR = HERMES_HOME / "workspace" / "agi-routing" / "evidence"
GENE_CANDIDATE_DIR = HERMES_HOME / "workspace" / "agi-routing" / "gene-candidates"
QR_BIN = os.environ.get("QR_BIN", "qr")

MODEL_TIERS = {
    "A": {"provider": "gpt55_5yuantoken", "model": "gpt-5.5", "role": "GPT 主脑/最终裁判", "base_url": "https://chuangagent.eu.cc/v1/responses", "key_env": "GPT55_5YUANTOKEN_API_KEY", "api_format": "responses"},
    "B": {"provider": "deepseek_v4_flash", "model": "deepseek-v4-flash", "role": "DeepSeek 中文/法律/性价比", "base_url": "https://api.deepseek.com/v1/chat/completions", "key_env": "DEEPSEEK_V4_FLASH_API_KEY", "api_format": "chat"},
    "C": {"provider": "claude_opus47_5yuantoken", "model": "claude-opus-4-7", "role": "Claude 反证/代码/架构", "base_url": "https://chuangagent.eu.cc/v1/responses", "key_env": "CLAUDE_OPUS47_5YUANTOKEN_API_KEY", "api_format": "responses"},
    "D": {"provider": "minimax-m27_highspeed", "model": "MiniMax-M2.7-highspeed", "role": "MiniMax 摘要/旁证/低风险", "base_url": "https://api.minimaxi.com/anthropic/v1/messages", "key_env": "MINIMAX_CN_API_KEY", "api_format": "anthropic"},
}
CHAIN_TEMPLATES = {
    "quick": ["主脑统筹", "主脑收束"],
    "three_stage": ["主脑统筹", "反证审错", "主脑收束"],
    "five_stage": ["主脑统筹", "反证审错", "修复落地", "旁证压缩", "主脑收束"],
    "dual_strong_review": ["GPT主脑统筹", "Claude反证审错", "修复落地", "旁证压缩", "GPT主脑收束"],
}
AGI_KEYWORDS = ["agi", "apex", "pgg", "archon", "进化", "自我改造", "自改进", "准agi", "核心架构", "量子路由", "河图洛书"]
LEGAL_KEYWORDS = ["法律", "案件", "合同", "法条", "案例", "办案", "诉讼"]
CODING_KEYWORDS = ["代码", "rust", "python", "调试", "重构", "测试", "部署", "配置"]
HIGH_RISK_KEYWORDS = ["删除", "凭证", "密钥", "生产", "核心", "系统服务", "长期后台", "不可逆"]
SENSITIVE_PATTERNS = [r"(?i)api[_-]?key\s*[:=]\s*\S+", r"(?i)secret\s*[:=]\s*\S+", r"(?i)token\s*[:=]\s*\S+", r"sk-[A-Za-z0-9_-]{16,}", r"AKIA[0-9A-Z]{16}", r"-----BEGIN [A-Z ]+PRIVATE KEY-----"]


def now_ms() -> int:
    return int(time.time() * 1000)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_obj(obj: Any) -> str:
    return sha256_text(json.dumps(obj, ensure_ascii=False, sort_keys=True))


def redact_text(text: str) -> tuple[str, list[str]]:
    findings: list[str] = []
    redacted = text
    for idx, pat in enumerate(SENSITIVE_PATTERNS, 1):
        if re.search(pat, redacted):
            findings.append(f"sensitive_pattern_{idx}")
            redacted = re.sub(pat, "[REDACTED]", redacted)
    return redacted, findings


def run_cmd(args: list[str], timeout: int = 90) -> dict[str, Any]:
    started = now_ms()
    try:
        cp = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        raw = (cp.stdout or cp.stderr or "").strip()
        try:
            parsed: Any = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}
        return {"ok": cp.returncode == 0, "returncode": cp.returncode, "stdout_hash": sha256_text(cp.stdout or ""), "stderr_hash": sha256_text(cp.stderr or ""), "data": parsed, "latency_ms": now_ms() - started}
    except Exception as exc:
        return {"ok": False, "error": repr(exc), "latency_ms": now_ms() - started}


def classify_task(task: str, explicit: str | None = None) -> dict[str, Any]:
    low = task.lower()
    if explicit and explicit != "auto":
        task_class = explicit
    elif any(k in low for k in AGI_KEYWORDS):
        task_class = "evolution_agi"
    elif any(k in low for k in LEGAL_KEYWORDS):
        task_class = "legal"
    elif any(k in low for k in CODING_KEYWORDS):
        task_class = "coding"
    else:
        task_class = "daily"
    risk = "high" if any(k in low for k in HIGH_RISK_KEYWORDS) else ("medium" if task_class in {"evolution_agi", "legal", "coding"} else "low")
    return {"task_class": task_class, "risk_level": risk}


def select_chain(task_class: str, risk_level: str) -> dict[str, Any]:
    if task_class == "evolution_agi":
        return {"selected_chain": "dual_strong_review", "stages": CHAIN_TEMPLATES["dual_strong_review"], "model_roles": {"GPT主脑统筹": MODEL_TIERS["A"], "Claude反证审错": MODEL_TIERS["C"], "修复落地": MODEL_TIERS["A"], "旁证压缩": MODEL_TIERS["D"], "GPT主脑收束": MODEL_TIERS["A"]}, "hard_rules": ["AGI/进化任务 GPT(A) 与 Claude(C) 强制参与；qr 推荐不得覆盖该规则。"]}
    if task_class == "legal":
        chain_name = "five_stage" if risk_level != "low" else "three_stage"
        return {"selected_chain": chain_name, "stages": CHAIN_TEMPLATES[chain_name], "model_roles": {"主脑统筹": MODEL_TIERS["B"], "反证审错": MODEL_TIERS["A"], "修复落地": MODEL_TIERS["B"], "旁证压缩": MODEL_TIERS["D"], "主脑收束": MODEL_TIERS["A"]}, "hard_rules": ["法律任务 DeepSeek(B) 优先，复杂论证由 GPT(A)/Claude(C) 复核。"]}
    if task_class == "coding":
        chain_name = "five_stage" if risk_level == "high" else "three_stage"
        return {"selected_chain": chain_name, "stages": CHAIN_TEMPLATES[chain_name], "model_roles": {"主脑统筹": MODEL_TIERS["C"], "反证审错": MODEL_TIERS["A"], "修复落地": MODEL_TIERS["C"], "旁证压缩": MODEL_TIERS["B"], "主脑收束": MODEL_TIERS["C"]}, "hard_rules": ["代码/架构实现 Claude(C) 优先，GPT(A) 反证或收束。"]}
    return {"selected_chain": "quick", "stages": CHAIN_TEMPLATES["quick"], "model_roles": {"主脑统筹": MODEL_TIERS["D"], "主脑收束": MODEL_TIERS["D"]}, "hard_rules": ["日常任务走低成本快速链。"]}


def provider_online(health: dict[str, Any], provider: str) -> bool:
    data = health.get("data")
    return isinstance(data, list) and any(item.get("name") == provider and item.get("status") == "ok" for item in data if isinstance(item, dict))


def model_for_stage(stage: str, chain: dict[str, Any]) -> dict[str, Any]:
    return chain["model_roles"].get(stage) or chain["model_roles"].get(stage.replace("GPT", "").replace("Claude", "")) or {}


def _fallback_model_for(model: dict[str, Any], stage: str) -> tuple[dict[str, Any], str] | None:
    provider = model.get("provider")
    # MiniMax endpoint/key is currently the most fragile.  Use DeepSeek for
    # compression/side evidence so the chain can produce an auditable failure or
    # fallback record instead of hanging on a known bad endpoint.
    if provider == "minimax-m27_highspeed":
        return dict(MODEL_TIERS["B"]), "minimax_unavailable_or_endpoint_failed_fallback_to_deepseek"
    if provider == "gpt55_5yuantoken" and "收束" not in stage:
        return dict(MODEL_TIERS["C"]), "gpt_unavailable_pre_final_fallback_to_claude"
    return None


def _build_payload(effective: dict, stage_prompt: str) -> dict:
    fmt = effective.get("api_format", "chat")
    if fmt == "responses":
        return {"model": effective["model"], "input": [{"role": "user", "content": stage_prompt}], "instructions": "你是严谨的多模型会审阶段执行者，只输出可验证内容。", "temperature": 0.2, "max_output_tokens": 1800}
    if fmt == "anthropic":
        return {"model": effective["model"], "messages": [{"role": "user", "content": stage_prompt}], "system": "你是严谨的多模型会审阶段执行者，只输出可验证内容。", "max_tokens": 1800, "temperature": 0.2}
    # chat_completions (default)
    return {"model": effective["model"], "messages": [{"role": "system", "content": "你是严谨的多模型会审阶段执行者，只输出可验证内容。"}, {"role": "user", "content": stage_prompt}], "temperature": 0.2, "max_tokens": 1800}


def _extract_text(data: dict, fmt: str) -> tuple[str, str, dict | None]:
    if fmt == "responses":
        text = ""
        try:
            text = data["output"][0]["content"][0]["text"]
        except (KeyError, IndexError, TypeError):
            text = str(data.get("output", [{}])[0].get("content", [{}])[0].get("text", "")) if data.get("output") else ""
        return text, str(data.get("id", "")), data.get("usage")
    if fmt == "anthropic":
        text = ""
        try:
            text = data["content"][0]["text"]
        except (KeyError, IndexError, TypeError):
            text = ""
        return text, str(data.get("id", "")), data.get("usage")
    # chat_completions (default)
    text = ""
    try:
        text = data["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError, TypeError):
        text = ""
    return text, str(data.get("id", "")), data.get("usage")


def call_model(model: dict[str, Any], stage: str, task: str, prior_summary: str, max_tokens: int, request_timeout: int = 45) -> dict[str, Any]:
    started = now_ms()
    attempts: list[tuple[dict[str, Any], bool, str | None]] = [(dict(model), False, None)]
    fb = _fallback_model_for(model, stage)
    if fb:
        attempts.append((fb[0], True, fb[1]))
    last_error = None
    for effective, fallback_used, fallback_reason in attempts:
        key = os.getenv(effective.get("key_env", ""))
        if not key:
            last_error = f"missing env {effective.get('key_env')}"
            continue
        fmt = effective.get("api_format", "chat")
        stage_prompt = f"""你正在参与 Hermes/PGG Archon 准AGI 的"量子路由 + 河图洛书"真实五段链。
阶段：{stage}
角色：{effective.get('role')}
任务：{task}
前序摘要：{prior_summary[-1800:] if prior_summary else '无'}

要求：中文；极短；输出本阶段的判断增量/反证增量/修复增量；不声称修改文件或接管系统；若证据不足明确写"证据不足"；最后给出 verdict: pass / fail / uncertain。"""
        payload = _build_payload(effective, stage_prompt)
        if fmt == "chat":
            payload["max_tokens"] = max_tokens
        elif fmt == "responses":
            payload["max_output_tokens"] = max_tokens
        elif fmt == "anthropic":
            payload["max_tokens"] = max_tokens
        req = urllib.request.Request(effective["base_url"], data=json.dumps(payload).encode("utf-8"), headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=request_timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text, response_id, usage = _extract_text(data, fmt)
            low = text.lower()
            verdict = "pass" if "verdict: pass" in low or "verdict：pass" in low else ("fail" if "verdict: fail" in low or "verdict：fail" in low else "uncertain")
            return {"ok": True, "stage": stage, "provider": effective.get("provider"), "model": effective.get("model"), "response_id": response_id, "content": text, "content_hash": sha256_text(text), "usage": usage, "latency_ms": now_ms() - started, "verdict": verdict, "fallback_used": fallback_used, "fallback_reason": fallback_reason}
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
            continue
    provider = model.get("provider")
    return {"ok": False, "stage": stage, "provider": provider, "model": model.get("model"), "error": last_error, "latency_ms": now_ms() - started, "fallback_used": False, "fallback_reason": None}


def build_planned_stage_evidence(task_id: str, task: str, chain: dict[str, Any], qr_route_id: str | None) -> list[dict[str, Any]]:
    items = []
    prev_hash = sha256_text(task)
    for stage in chain["stages"]:
        model = model_for_stage(stage, chain)
        payload = {"task_id": task_id, "stage": stage, "model_id": model.get("model"), "provider": model.get("provider"), "role": model.get("role"), "qr_decision_id": qr_route_id, "input_hash": prev_hash, "output_hash": None, "verdict": "planned_not_called", "reason_code": "sidecar_planning_only", "ts_start": None, "ts_end": None, "latency_ms": None, "tokens_in": None, "tokens_out": None, "cross_check_ref": prev_hash}
        payload["record_hash"] = sha256_obj(payload)
        items.append(payload)
        prev_hash = payload["record_hash"]
    return items


def _write_progress(path: Path, record: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def execute_stages(task_id: str, task: str, chain: dict[str, Any], qr_route_id: str | None, max_tokens: int, progress_path: Path | None = None, record: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], list[str], bool]:
    outputs, failures = [], []
    prior = ""
    prev_hash = sha256_text(task)
    any_fallback = False
    for stage in chain["stages"]:
        model = model_for_stage(stage, chain)
        ts_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        result = call_model(model, stage, task, prior, max_tokens)
        ts_end = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        any_fallback = any_fallback or bool(result.get("fallback_used"))
        if not result.get("ok"):
            failures.append(f"{stage}:{result.get('provider')} 调用失败：{result.get('error')}")
        content = result.get("content") or ""
        usage = result.get("usage") or {}
        payload = {"task_id": task_id, "stage": stage, "model_id": result.get("model") or model.get("model"), "provider": result.get("provider") or model.get("provider"), "role": model.get("role"), "qr_decision_id": qr_route_id, "input_hash": prev_hash, "output_hash": result.get("content_hash") if result.get("response_id") is not None else None, "response_id": result.get("response_id"), "verdict": result.get("verdict") if result.get("ok") else "fail", "reason_code": "real_model_call" if result.get("ok") else "model_call_failed", "ts_start": ts_start, "ts_end": ts_end, "latency_ms": result.get("latency_ms"), "tokens_in": usage.get("prompt_tokens"), "tokens_out": usage.get("completion_tokens"), "cross_check_ref": prev_hash, "content_excerpt": content[:1200], "fallback_used": result.get("fallback_used", False), "fallback_reason": result.get("fallback_reason"), "error": result.get("error")}
        payload["record_hash"] = sha256_obj(payload)
        outputs.append(payload)
        if content:
            prior += f"\n\n## {stage}\n{content}"
        prev_hash = payload["record_hash"]
        if progress_path and record is not None:
            record["stage_outputs"] = outputs
            record["errors_or_model_failures"] = list(failures)
            record["real_response_count"] = sum(1 for x in outputs if x.get("response_id"))
            record["last_stage"] = stage
            record["record_hash"] = sha256_obj({k: v for k, v in record.items() if k != "record_hash"})
            _write_progress(progress_path, record)
    return outputs, failures, any_fallback


def validate_record_hash(record: dict[str, Any]) -> bool:
    copied = dict(record)
    h = copied.pop("record_hash", None)
    return bool(h) and h == sha256_obj(copied)


def extract_stage_excerpt(record: dict[str, Any], keyword: str) -> str:
    for stage in record.get("stage_outputs", []):
        if keyword in stage.get("stage", ""):
            return (stage.get("content_excerpt") or "").strip()
    return ""


def build_gene_candidate(record: dict[str, Any], evidence_path: str) -> tuple[dict[str, Any], list[str]]:
    gates: list[str] = []
    real = [s for s in record.get("stage_outputs", []) if s.get("response_id") and s.get("output_hash")]
    if not validate_record_hash(record):
        gates.append("record_hash_failed")
    if not record.get("execute_stages"):
        gates.append("stages_not_executed")
    if len(real) != len(record.get("stage_outputs", [])):
        gates.append("missing_stage_response_or_hash")
    if record.get("final_decision") in {"blocked", "partial_model_execution"}:
        gates.append("final_decision_not_eligible")
    if record.get("task_class") == "evolution_agi":
        providers = {s.get("provider") for s in real}
        if "gpt55_5yuantoken" not in providers or "claude_opus47_5yuantoken" not in providers:
            gates.append("missing_gpt_or_claude")
    counter = extract_stage_excerpt(record, "反证")
    repair = extract_stage_excerpt(record, "修复")
    final = extract_stage_excerpt(record, "收束")
    if len(counter) < 40:
        gates.append("counter_delta_too_short")
    if len(repair) < 40:
        gates.append("repair_delta_too_short")
    if len(final) < 40:
        gates.append("final_delta_too_short")
    status = "candidate_ready" if not gates else "candidate_blocked"
    gene = {"schema": "route_chain_gene_candidate/v1", "status": status, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "gene_id": "gene_candidate_" + record.get("task_id", uuid.uuid4().hex[:8]), "source_task_id": record.get("task_id"), "source_evidence_path": evidence_path, "source_record_hash": record.get("record_hash"), "task_class": record.get("task_class"), "risk_level": record.get("risk_level"), "selected_chain": record.get("selected_chain"), "qr_route_id": (record.get("qr_recommendation", {}).get("data") or {}).get("route_id") if isinstance(record.get("qr_recommendation"), dict) else None, "qr_selected": (record.get("qr_recommendation", {}).get("data") or {}).get("selected") if isinstance(record.get("qr_recommendation"), dict) else None, "candidate_rule": "AGI/进化/核心架构任务必须以 GPT(A)+Claude(C) 真实双通道为门禁；qr 可给候选排序，但不得覆盖 GPT/Claude 强制审查；五段链完成后才允许生成候选基因。", "judgment_delta_excerpt": extract_stage_excerpt(record, "主脑统筹"), "counter_delta_excerpt": counter, "repair_delta_excerpt": repair, "final_delta_excerpt": final, "stage_response_ids": [s.get("response_id") for s in real], "stage_output_hashes": [s.get("output_hash") for s in real], "fallback_used": record.get("fallback_used"), "fallback_notes": record.get("errors_or_model_failures"), "verification": {"record_hash_ok": validate_record_hash(record), "stage_count": len(record.get("stage_outputs", [])), "real_response_count": len(real), "gates": gates}, "not_written_to_gene_db": True, "requires_human_or_next_gate": True}
    gene["gene_hash"] = sha256_obj(gene)
    return gene, gates


def run_gate(task: str, task_class_arg: str, execute: bool = False, allow_sensitive: bool = False, max_tokens: int = 700, out_path: Path | None = None) -> dict[str, Any]:
    task_id = "rceg_" + time.strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    redacted_task, sensitive_findings = redact_text(task)
    classified = classify_task(redacted_task, task_class_arg)
    health = run_cmd([QR_BIN, "health"], timeout=90)
    route = run_cmd([QR_BIN, "route", redacted_task], timeout=90)
    chain = select_chain(classified["task_class"], classified["risk_level"])
    route_data = route.get("data") if isinstance(route.get("data"), dict) else {}
    qr_route_id = route_data.get("route_id") if isinstance(route_data, dict) else None
    gate_findings: list[str] = []
    gate_status = "allow_planning_only"
    if sensitive_findings:
        gate_findings.append(f"检测到敏感字段并已脱敏：{','.join(sensitive_findings)}")
        if not allow_sensitive:
            execute = False
            gate_findings.append("未设置 --allow-sensitive，禁止真实模型执行，仅生成计划证据。")
    if not health.get("ok") or not route.get("ok"):
        gate_status = "blocked"
        execute = False
        gate_findings.append("qr health/route 不完整，阻断为 blocked。")
    if classified["task_class"] == "evolution_agi":
        if not provider_online(health, MODEL_TIERS["A"]["provider"]) or not provider_online(health, MODEL_TIERS["C"]["provider"]):
            gate_status = "blocked"
            execute = False
            gate_findings.append("进化/AGI任务要求 GPT(A)+Claude(C) 同时在线。")
        if route_data.get("selected") == MODEL_TIERS["B"]["provider"]:
            gate_findings.append("qr 选择了 DeepSeek(B)，但 AGI/进化硬规则覆盖为 GPT(A)+Claude(C) 双通道。")
    if classified["risk_level"] == "high":
        gate_status = "human_review_required" if gate_status != "blocked" else gate_status
        gate_findings.append("检测到高风险关键词：允许模型会审证据，但不自动执行修复。")
    record = {"schema": "route_chain_evidence_gate/v4", "sidecar_only": True, "task_id": task_id, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "user_request": redacted_task, "user_request_hash": sha256_text(redacted_task), "task_class": classified["task_class"], "risk_level": classified["risk_level"], "execute_stages": execute, "qr_available": bool(health.get("ok") and route.get("ok")), "qr_health": health, "qr_recommendation": route, "selected_chain": chain["selected_chain"], "selected_models": sorted({v.get("provider") for v in chain["model_roles"].values() if v.get("provider")}), "model_roles": chain["model_roles"], "hard_rules": chain["hard_rules"], "stage_outputs": [], "counter_evidence": [], "fix_actions": [], "external_or_internal_evidence": [], "verification_method": "stage-level progressive evidence write + qr health/route + response_id/hash + final record_hash" if execute else "只验证 qr health/route、链路选择、证据落盘；不声称已完成真实多模型五段执行。", "known_uncertainties": ["未自动执行修复动作；候选基因不等于已入库基因。"], "final_decision": gate_status, "human_review_required": gate_status in {"human_review_required", "blocked", "model_execution_completed_human_review_required"}, "fallback_used": False, "errors_or_model_failures": gate_findings, "real_response_count": 0}
    if out_path:
        record["record_hash"] = sha256_obj({k: v for k, v in record.items() if k != "record_hash"})
        _write_progress(out_path, record)
    if execute and gate_status != "blocked":
        stage_outputs, call_failures, any_fallback = execute_stages(task_id, redacted_task, chain, qr_route_id, max_tokens=max_tokens, progress_path=out_path, record=record if out_path else None)
        gate_findings.extend(call_failures)
        if call_failures:
            gate_status = "partial_model_execution"
        elif gate_status == "allow_planning_only":
            gate_status = "model_execution_completed"
        elif gate_status == "human_review_required":
            gate_status = "model_execution_completed_human_review_required"
    else:
        stage_outputs = build_planned_stage_evidence(task_id, redacted_task, chain, qr_route_id)
        any_fallback = False
    record.update({"stage_outputs": stage_outputs, "counter_evidence": [x for x in stage_outputs if "反证" in x.get("stage", "")], "fix_actions": [x for x in stage_outputs if "修复" in x.get("stage", "")], "external_or_internal_evidence": [x for x in stage_outputs if x.get("response_id") or x.get("qr_decision_id")], "final_decision": gate_status, "human_review_required": gate_status in {"human_review_required", "blocked", "model_execution_completed_human_review_required"}, "fallback_used": any_fallback, "errors_or_model_failures": gate_findings, "real_response_count": sum(1 for x in stage_outputs if x.get("response_id"))})
    record["record_hash"] = sha256_obj({k: v for k, v in record.items() if k != "record_hash"})
    if out_path:
        _write_progress(out_path, record)
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Route-chain evidence gate")
    ap.add_argument("task", help="任务描述")
    ap.add_argument("--task-class", default="auto", choices=["auto", "evolution_agi", "legal", "coding", "daily"])
    ap.add_argument("--out-dir", default=str(EVIDENCE_DIR))
    ap.add_argument("--execute-stages", action="store_true", help="真实调用每个阶段的模型，只写证据，不执行修复")
    ap.add_argument("--emit-gene-candidate", action="store_true", help="五段证据通过后生成候选基因 JSON，不写入基因库")
    ap.add_argument("--gene-dir", default=str(GENE_CANDIDATE_DIR))
    ap.add_argument("--allow-sensitive", action="store_true", help="允许脱敏后继续执行模型调用；默认检测敏感字段后只计划")
    ap.add_argument("--max-tokens", type=int, default=700)
    ap.add_argument("--json", action="store_true", help="输出完整 JSON")
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Reserve path before model execution so stage-level progress survives timeouts.
    task_id_hint = "rceg_" + time.strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    # run_gate owns task_id; create final path after first record is returned by passing
    # a deterministic temporary path then renaming is more complex, so let run_gate write
    # a stable in-progress path and copy final below.
    progress_path = out_dir / f"{task_id_hint}.json"
    record = run_gate(args.task, args.task_class, execute=args.execute_stages, allow_sensitive=args.allow_sensitive, max_tokens=args.max_tokens, out_path=progress_path)
    final_path = out_dir / f"{record['task_id']}.json"
    if progress_path != final_path:
        progress_path.replace(final_path)
    else:
        _write_progress(final_path, record)
    gene_path = None
    gene_status = None
    gene_gates: list[str] = []
    if args.emit_gene_candidate:
        gene_dir = Path(args.gene_dir)
        gene_dir.mkdir(parents=True, exist_ok=True)
        gene, gene_gates = build_gene_candidate(record, str(final_path))
        gene_path = gene_dir / f"{gene['gene_id']}.json"
        gene_path.write_text(json.dumps(gene, ensure_ascii=False, indent=2), encoding="utf-8")
        gene_status = gene["status"]
    qr_data = record["qr_recommendation"].get("data") if isinstance(record.get("qr_recommendation"), dict) else {}
    summary = {
        "ok": True,
        "evidence_path": str(final_path),
        "gene_candidate_path": str(gene_path) if gene_path else None,
        "gene_status": gene_status,
        "gene_gates": gene_gates,
        "task_id": record["task_id"],
        "task_class": record["task_class"],
        "risk_level": record["risk_level"],
        "qr_route_id": (qr_data or {}).get("route_id"),
        "selected_chain": record["selected_chain"],
        "selected_models": record["selected_models"],
        "execute_stages": record["execute_stages"],
        "stage_count": len(record["stage_outputs"]),
        "real_response_count": sum(1 for x in record["stage_outputs"] if x.get("response_id")),
        "final_decision": record["final_decision"],
        "findings": record["errors_or_model_failures"],
        "record_hash": record["record_hash"],
    }
    if args.json:
        print(json.dumps({**summary, "record": record}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if record["final_decision"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
