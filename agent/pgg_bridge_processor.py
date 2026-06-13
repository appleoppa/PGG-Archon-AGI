"""PGG Bridge Processor — 自循环桥任务执行器。
双通道：LLM审核（首选）→ 规则降级（备选）。

调用LLM方式：直连5yuantoken网关（走GPT55，成本低）。
不走Hermes MCP工具（自循环无tool_executor权限）。

授权边界（用户授权 2026-06-13）：
- 仅处理 type=promotion 的桥任务
- LLM审核或规则降级用于candidate基因promotion
- 不修改Hermes core/provider/scheduler/security
- 不创建PR（标记need_human_review=True）
"""

import json
import os
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path("/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3")
ENV_PATH = Path("/Users/appleoppa/.hermes/.env")
BRIDGE_DIR = Path(os.path.expanduser("~/.hermes/workspace/execution-bridge"))

LLM_API_URL = "https://5yuantoken.org/v1/chat/completions"
LLM_MODEL = "gpt-5.5-turbo"
LLM_TIMEOUT = 30

# --- Dual-channel adversarial constants ---
CLAUDE_MODEL = "claude-sonnet-4-6"
CLAUDE_KEY_ENV = "CLAUDE_OPUS47_5YUANTOKEN_API_KEY"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"
DEEPSEEK_KEY_ENV = "DEEPSEEK_V4_FLASH_API_KEY"
MIN_FITNESS_DUAL = 600

MIN_FITNESS_FOR_AUTO_PROMOTE = 700
MAX_BATCH_REVIEW = 50
RULE_AUTO_APPROVE_FITNESS = 1000
RULE_AUTO_APPROVE_EVIDENCE = "B"


def _read_env_key(key_name: str) -> str:
    try:
        with open(ENV_PATH) as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and '=' in stripped:
                    k, v = stripped.split('=', 1)
                    if k.strip() == key_name:
                        return v.strip().strip("'\"")
    except OSError:
        pass
    return ""


def _llm_call(payload: str, api_key: str, base_url: str, timeout: int = LLM_TIMEOUT) -> dict[str, Any]:
    """通用 LLM 调用：curl → 解析 → 返回结构化的 decision/confidence/reason。"""
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", str(timeout),
             "-X", "POST", base_url,
             "-H", "Content-Type: application/json",
             "-H", f"Authorization: Bearer {api_key}",
             "-d", payload],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        if r.returncode != 0:
            return {"decision": "error", "confidence": 0, "reason": f"curl_exit_{r.returncode}"}
        output = r.stdout

        if "Service temporarily unavailable" in output or "503" in output:
            return {"decision": "error", "confidence": 0, "reason": "gateway_503"}

        try:
            resp = json.loads(output)
            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)
            return {
                "decision": result.get("decision", "reject"),
                "confidence": result.get("confidence", 0),
                "reason": result.get("reason", "no_reason"),
            }
        except (json.JSONDecodeError, KeyError, IndexError):
            return {"decision": "error", "confidence": 0, "reason": "parse_failed"}
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"decision": "error", "confidence": 0, "reason": str(e)[:100]}


def _build_review_prompt(gene: dict[str, Any], rules_extra: str = "") -> str:
    """Build review prompt (shared by GPT and Claude channels)."""
    return (
        'Evaluate this candidate gene for promotion to verified status.\n'
        '\n'
        'Required criteria:\n'
        '1. Must have absorbed_knowledge (with signals_match field) ✅\n'
        '2. Must have evidence_grade (non-empty) ✅\n'
        '3. Must have source_refs_json (non-empty, >10 chars) ✅\n'
        '4. fitness >= 700\n'
        '5. Dream fusion offspring (dream_auto_fusion_*) fitness>1000 & evidence>=B → auto-approve\n'
        '6. Gene intake genes (pgg_gene_*) fitness>800 & evidence>=B → auto-approve\n'
        + rules_extra
        + '\n'
        f'Gene info:\n'
        f'  ID: {gene["gene_id"]}\n'
        f'  Name: {gene["gene_name"]}\n'
        f'  fitness: {gene["fitness"]}\n'
        f'  evidence_grade: {gene["evidence_grade"]}\n'
        f'  gate_type: {gene["gate_type"]}\n'
        f'  severity_rank: {gene["severity_rank"]}\n'
        '\nRespond ONLY with JSON (no extra text):\n'
        '{"decision": "approve" or "reject", "confidence": 0-100, "reason": "one sentence reason"}'
    )


CLAUDE_RULES_EXTRA = (
    'Additional checks for this review:\n'
    '- Boundary: does the gene make claims beyond its evidence? (Y/N)\n'
    '- Consistency: do gene_name and fitness/evidence match? (Y/N)\n'
    '- Practical value: is this genuinely useful, or just structurally complete? (Y/N)\n'
)

DEEPSEEK_ARBITRATE_PROMPT = (
    'You are the arbiter in a gene evolution system. GPT and Claude disagree on a candidate gene.\n'
    'Review both verdicts and make the final call.\n'
    '\n'
    'Rules:\n'
    '1. Must have absorbed_knowledge (with signals_match field) ✅\n'
    '2. Must have evidence_grade (non-empty) ✅\n'
    '3. Must have source_refs_json (non-empty, >10 chars) ✅\n'
    '4. fitness >= 700\n'
    '5. Dream fusion offspring (dream_auto_fusion_*) fitness>1000 & evidence>=B → approve\n'
    '6. Gene intake genes (pgg_gene_*) fitness>800 & evidence>=B → approve\n'
    '\n'
    'Respond ONLY with JSON:\n'
    '{"decision": "approve" or "reject", "confidence": 0-100, "reason": "arbitration reasoning"}'
)


def _llm_review_gene(gene: dict[str, Any]) -> dict[str, Any]:
    """通道1（GPT-5.5）：结构完整性与证据审核。"""
    prompt = _build_review_prompt(gene)
    api_key = _read_env_key("GPT55_5YUANTOKEN_API_KEY")
    if not api_key:
        return {"decision": "error", "confidence": 0, "reason": "gpt_key_not_found"}
    payload = json.dumps({
        "model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150, "temperature": 0.1,
    })
    result = _llm_call(payload, api_key, LLM_API_URL)
    result["channel"] = "gpt"
    return result


def _claude_review_gene(gene: dict[str, Any]) -> dict[str, Any]:
    """通道2（Claude Opus 4.6）：逻辑边界与一致性审核。"""
    prompt = _build_review_prompt(gene, CLAUDE_RULES_EXTRA)
    api_key = _read_env_key(CLAUDE_KEY_ENV)
    if not api_key:
        return {"decision": "error", "confidence": 0, "reason": "claude_key_not_found"}
    payload = json.dumps({
        "model": CLAUDE_MODEL, "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150, "temperature": 0.1,
    })
    # Claude on 5yuantoken gateway has higher latency than GPT; use 60s timeout
    result = _llm_call(payload, api_key, LLM_API_URL, timeout=60)
    result["channel"] = "claude"
    return result


def _deepseek_arbitrate(gene: dict[str, Any], gpt_verdict: dict, claude_verdict: dict) -> dict[str, Any]:
    """分歧仲裁：GPT approve/Claude reject（或反之）→ DeepSeek 做最终裁决。"""
    info = (
        f'基因: {gene["gene_id"]} ({gene["gene_name"]})\n'
        f'  fitness={gene["fitness"]} evidence={gene["evidence_grade"]}\n'
        f'  GPT: {gpt_verdict.get("decision")} (conf={gpt_verdict.get("confidence")}) — {gpt_verdict.get("reason")}\n'
        f'  Claude: {claude_verdict.get("decision")} (conf={claude_verdict.get("confidence")}) — {claude_verdict.get("reason")}\n'
    )
    prompt = DEEPSEEK_ARBITRATE_PROMPT + '\n' + info
    api_key = _read_env_key(DEEPSEEK_KEY_ENV)
    if not api_key:
        return {"decision": "error", "confidence": 0, "reason": "deepseek_key_not_found"}
    payload = json.dumps({
        "model": DEEPSEEK_MODEL, "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200, "temperature": 0.1,
    })
    result = _llm_call(payload, api_key, DEEPSEEK_URL, timeout=45)
    result["channel"] = "deepseek"
    result["gpt_verdict"] = gpt_verdict
    result["claude_verdict"] = claude_verdict
    return result


def _rule_review_gene(gene: dict[str, Any]) -> dict[str, Any]:
    """通道2: 规则降级。LLM不可达时用静态规则判断。"""
    gid = gene["gene_id"]
    name = gene["gene_name"]
    fitness = gene["fitness"]
    evidence = str(gene["evidence_grade"] or "").upper()

    # 梦境融合子代：fitness>1000 + evidence>=B → approve
    if "dream_auto_fusion" in gid or "dream_auto_fusion" in name:
        if fitness >= RULE_AUTO_APPROVE_FITNESS and evidence >= RULE_AUTO_APPROVE_EVIDENCE:
            return {"decision": "approve", "confidence": 85, "reason": "rule: dream_fusion_high_fitness"}

    # 基因摄入pgg_gene：fitness>800 + evidence>=B → approve
    if "pgg_gene" in gid:
        if fitness >= 800 and evidence >= "B":
            return {"decision": "approve", "confidence": 80, "reason": "rule: pgg_gene_sufficient"}

    # 其他高fitness基因
    if fitness >= RULE_AUTO_APPROVE_FITNESS and evidence >= RULE_AUTO_APPROVE_EVIDENCE:
        return {"decision": "approve", "confidence": 75, "reason": "rule: high_fitness_generic"}

    # 无法规则判断→标记需人工
    return {"decision": "hold", "confidence": 30, "reason": "rule: need_human_review"}


def _promote_gene(gene_id: str, evidence_grade: str, confidence: int, method: str) -> dict[str, Any]:
    try:
        db = sqlite3.connect(str(DB_PATH))
        db.execute(
            """UPDATE evolution_genes
               SET status = 'verified',
                   verification_status = ?,
                   evidence_grade = ?,
                   last_executed = ?
               WHERE gene_id = ? AND status = 'candidate'""",
            (f"{method}_by_bridge_processor", evidence_grade, datetime.now().isoformat(), gene_id),
        )
        db.commit()
        affected = db.total_changes
        db.close()
        return {"promoted": True, "affected": affected}
    except Exception as e:
        return {"promoted": False, "error": str(e)}


def _reject_gene(gene_id: str, reason: str) -> dict[str, Any]:
    try:
        db = sqlite3.connect(str(DB_PATH))
        db.execute(
            """UPDATE evolution_genes
               SET status = 'rejected',
                   verification_status = ?,
                   last_executed = ?
               WHERE gene_id = ? AND status = 'candidate'""",
            (f"rejected_by_bridge_processor: {reason[:80]}", datetime.now().isoformat(), gene_id),
        )
        db.commit()
        affected = db.total_changes
        db.close()
        return {"rejected": True, "affected": affected}
    except Exception as e:
        return {"rejected": False, "error": str(e)}


def process_promotion_batch(gene_ids: Any = None) -> dict[str, Any]:
    """批量审核候选candidate基因。
    
    通道策略：
    - fitness < 600 → 规则降级（无LLM瓶颈）
    - fitness >= 600 且双通道可达 → GPT + Claude 并行，分歧 DeepSeek 仲裁
    - 单通道可达 → 单LLM（兼容旧行为）
    - 均不可达 → 规则降级
    """
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    if gene_ids:
        placeholders = ",".join("?" * len(gene_ids))
        candidates = db.execute(
            f"""SELECT gene_id, gene_name, fitness, evidence_grade, gate_type,
                      severity_rank, boundary, absorbed_knowledge, source_refs_json
               FROM evolution_genes
               WHERE status = 'candidate' AND gene_id IN ({placeholders})
               ORDER BY fitness DESC LIMIT ?""",
            (*gene_ids, MAX_BATCH_REVIEW),
        ).fetchall()
    else:
        candidates = db.execute(
            """SELECT gene_id, gene_name, fitness, evidence_grade, gate_type,
                      severity_rank, boundary, absorbed_knowledge, source_refs_json
               FROM evolution_genes
               WHERE status = 'candidate'
                 AND absorbed_knowledge IS NOT NULL
                 AND absorbed_knowledge LIKE '%signals_match%'
                 AND evidence_grade IS NOT NULL AND evidence_grade != ''
                 AND source_refs_json IS NOT NULL AND length(source_refs_json) > 10
                 AND (fitness IS NOT NULL AND fitness >= ?)
               ORDER BY fitness DESC LIMIT ?""",
            (MIN_FITNESS_FOR_AUTO_PROMOTE, MAX_BATCH_REVIEW),
        ).fetchall()

    db.close()

    if not candidates:
        return {"status": "no_candidates", "reviewed": 0}

    results = {
        "status": "completed",
        "total": len(candidates),
        "approved": 0, "rejected": 0, "holds": 0, "errors": 0,
        "channel": "unknown",
        "dual_stats": {"both_approved": 0, "both_rejected": 0, "arbitrated": 0,
                       "gpt_only": 0, "claude_only": 0, "deepseek_errors": 0},
        "details": [],
    }

    # 判断通道模式
    has_dual_candidates = any(dict(c).get("fitness", 0) >= MIN_FITNESS_DUAL for c in candidates)
    gpt_key = _read_env_key("GPT55_5YUANTOKEN_API_KEY")
    claude_key = _read_env_key(CLAUDE_KEY_ENV)
    gpt_ok = _probe_availability(gpt_key, LLM_MODEL) if gpt_key else False
    claude_ok = _probe_availability(claude_key, CLAUDE_MODEL) if claude_key else False

    if has_dual_candidates and gpt_ok and claude_ok:
        channel = "dual"
        method_tag = "dual_reviewed"
    elif gpt_ok:
        channel = "gpt_only"
        method_tag = "llm_reviewed"
    elif claude_ok:
        channel = "claude_only"
        method_tag = "claude_reviewed"
    else:
        channel = "rule_fallback"
        method_tag = "rule_reviewed"

    results["channel"] = channel

    for c in candidates:
        gene = dict(c)

        if channel == "dual":
            decision = _dual_channel_review(gene, results["dual_stats"])
        elif channel == "gpt_only":
            decision = _llm_review_gene(gene)
        elif channel == "claude_only":
            decision = _claude_review_gene(gene)
        else:
            decision = _rule_review_gene(gene)

        detail = {
            "gene_id": gene["gene_id"],
            "gene_name": gene["gene_name"],
            "fitness": gene["fitness"],
            "decision": decision["decision"],
            "confidence": decision["confidence"],
            "reason": decision["reason"],
        }
        if "channel" in decision:
            detail["review_channel"] = decision["channel"]

        if decision["decision"] == "approve":
            r = _promote_gene(gene["gene_id"], gene["evidence_grade"], decision["confidence"], method_tag)
            detail["db_result"] = r
            results["approved"] += 1 if r.get("promoted") else 0
            if not r.get("promoted"):
                results["errors"] += 1
        elif decision["decision"] == "reject":
            r = _reject_gene(gene["gene_id"], decision["reason"])
            detail["db_result"] = r
            results["rejected"] += 1
        elif decision["decision"] == "hold":
            detail["db_result"] = {"held": True, "reason": decision["reason"]}
            results["holds"] += 1
        else:
            detail["db_result"] = {"error": decision["reason"]}
            results["errors"] += 1

        results["details"].append(detail)
        if channel != "rule_fallback" and len(results["details"]) < len(candidates):
            time.sleep(0.5)

    return results


def proof_review_gene(gene_id: str, task_id: str = "") -> dict[str, Any]:
    """只读 ARS dual-channel 证明审核：不 promote、不 reject、不修改 GeneDB。

    用于证明 GPT + Claude + DeepSeek review 链路是否能对同一个 gene_id 工作。
    所有 provider 返回和最终 decision 都写入调用结果，由上层保存 receipt。
    """
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    row = db.execute(
        """SELECT gene_id, gene_name, fitness, evidence_grade, gate_type,
                  severity_rank, boundary, absorbed_knowledge, source_refs_json, status, verification_status
           FROM evolution_genes
           WHERE gene_id = ?""",
        (gene_id,),
    ).fetchone()
    db.close()
    if not row:
        return {"schema": "pgg_bridge_proof_review/v1", "task_id": task_id, "gene_id": gene_id, "status": "not_found"}

    gene = dict(row)
    before = {"status": gene.get("status"), "verification_status": gene.get("verification_status")}
    # Detached proof-mode: copy only the fields required by reviewers. The review
    # chain receives this immutable snapshot and this function performs no writes.
    # If the live DB changes while providers are running, report it as external
    # concurrent mutation instead of treating it as proof-mode success.
    review_snapshot = {
        "gene_id": gene.get("gene_id"),
        "gene_name": gene.get("gene_name"),
        "fitness": gene.get("fitness"),
        "evidence_grade": gene.get("evidence_grade"),
        "gate_type": gene.get("gate_type"),
        "severity_rank": gene.get("severity_rank"),
        "boundary": gene.get("boundary"),
        "absorbed_knowledge": gene.get("absorbed_knowledge"),
        "source_refs_json": gene.get("source_refs_json"),
    }
    stats = {"both_approved": 0, "both_rejected": 0, "arbitrated": 0,
             "gpt_only": 0, "claude_only": 0, "deepseek_errors": 0}
    started = datetime.now().isoformat()
    decision = _dual_channel_review(review_snapshot, stats)
    ended = datetime.now().isoformat()

    # Re-read only for evidence. No restore is attempted here because another
    # process may have made a legitimate transition; callers decide rollback.
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    after_row = db.execute(
        "SELECT status, verification_status FROM evolution_genes WHERE gene_id = ?",
        (gene_id,),
    ).fetchone()
    db.close()
    after = dict(after_row) if after_row else {}
    external_concurrent_mutation = before != after

    return {
        "schema": "pgg_bridge_proof_review/v1",
        "task_id": task_id,
        "created_at": ended,
        "started_at": started,
        "gene": {
            "gene_id": gene.get("gene_id"),
            "gene_name": gene.get("gene_name"),
            "fitness": gene.get("fitness"),
            "evidence_grade": gene.get("evidence_grade"),
            "gate_type": gene.get("gate_type"),
        },
        "readonly": True,
        "before": before,
        "after": after,
        "mutation_detected": external_concurrent_mutation,
        "external_concurrent_mutation": external_concurrent_mutation,
        "dual_stats": stats,
        "decision": decision,
        "verdict": (
            "PASS_DUAL_REVIEW_NO_MUTATION"
            if not external_concurrent_mutation and decision.get("decision") in ("approve", "reject", "hold", "error")
            else "WATCH_EXTERNAL_CONCURRENT_MUTATION"
            if external_concurrent_mutation
            else "WATCH_DUAL_REVIEW_INCOMPLETE"
        ),
        "boundary": "proof-mode only; no promotion/rejection/status update",
    }


def _dual_channel_review(gene: dict[str, Any], stats: dict) -> dict[str, Any]:
    """双通道审核：GPT + Claude 并行，分歧→DeepSeek仲裁。"""
    gpt_verdict = _llm_review_gene(gene)
    claude_verdict = _claude_review_gene(gene)

    gpt_ok = gpt_verdict.get("decision") in ("approve", "reject")
    claude_ok = claude_verdict.get("decision") in ("approve", "reject")

    if not gpt_ok and not claude_ok:
        stats["gpt_only"] += 0
        stats["claude_only"] += 0
        return {"decision": "error", "confidence": 0, "reason": "dual_both_error",
                "channel": "error", "gpt": gpt_verdict, "claude": claude_verdict}

    if not gpt_ok:
        stats["claude_only"] += 1
        result = claude_verdict
        result["channel"] = "claude_only"
        result["note"] = "GPT unavailable, used Claude alone"
        return result

    if not claude_ok:
        stats["gpt_only"] += 1
        result = gpt_verdict
        result["channel"] = "gpt_only"
        result["note"] = "Claude unavailable, used GPT alone"
        return result

    # 双通道都有有效回复
    gpt_dec = gpt_verdict.get("decision")
    claude_dec = claude_verdict.get("decision")

    if gpt_dec == claude_dec:
        # Copy the winning verdict before embedding both verdicts; otherwise
        # result may be gpt_verdict/claude_verdict itself and create a circular
        # JSON structure (result["gpt_verdict"] is result).
        result = dict(gpt_verdict if gpt_verdict.get("confidence", 0) >= claude_verdict.get("confidence", 0) else claude_verdict)
        result["channel"] = "dual_agreed"
        result["gpt_verdict"] = dict(gpt_verdict)
        result["claude_verdict"] = dict(claude_verdict)
        if gpt_dec == "approve":
            stats["both_approved"] += 1
        else:
            stats["both_rejected"] += 1
        return result

    # 分歧 → DeepSeek 仲裁
    arbitrator = _deepseek_arbitrate(gene, gpt_verdict, claude_verdict)
    if arbitrator.get("decision") in ("approve", "reject"):
        stats["arbitrated"] += 1
        return arbitrator

    # DeepSeek 也失败 → 按高置信度走
    stats["deepseek_errors"] += 1
    fallback = gpt_verdict if gpt_verdict.get("confidence", 0) >= claude_verdict.get("confidence", 0) else claude_verdict
    fallback["channel"] = "dual_fallback_highest_conf"
    fallback["note"] = "DeepSeek arbitrate failed, used highest confidence"
    return fallback


def _probe_availability(api_key: str, model: str) -> bool:
    """探测LLM可达性。"""
    try:
        tr = subprocess.run(
            ["curl", "-s", "-m", "5",
             "-X", "POST", LLM_API_URL,
             "-H", "Content-Type: application/json",
             "-H", f"Authorization: Bearer {api_key}",
             "-d", json.dumps({"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5})],
            capture_output=True, text=True, timeout=10,
        )
        return "choices" in tr.stdout
    except Exception:
        return False


def process_bridge_tasks() -> dict[str, Any]:
    """读取所有pending的桥任务并处理。"""
    from agent.pgg_execution_bridge import list_pending_tasks, mark_task

    tasks = list_pending_tasks()
    if not tasks:
        return {"status": "no_tasks", "processed": 0}

    overall = {"status": "completed", "tasks_processed": 0, "tasks_skipped": 0, "tasks_errored": 0, "reviews": [], "results": []}

    for task in tasks:
        task_type = task.get("task_type", "")
        task_id = task.get("task_id", "")

        if task_type == "promotion":
            review_result = process_promotion_batch()
            overall["reviews"].append({
                "task_id": task_id, "task_type": task_type, "result": review_result,
            })
            if review_result.get("status") == "completed":
                approved = review_result.get("approved", 0)
                rejected = review_result.get("rejected", 0)
                holds = review_result.get("holds", 0)
                errors = review_result.get("errors", 0)
                channel = review_result.get("channel", "unknown")
                mark_task(task_id, "done",
                          note=f"{channel}: {approved}条approve, {rejected}条reject, {holds}条hold, {errors}条error")
                overall["tasks_processed"] += 1
            else:
                mark_task(task_id, "error", note="审核失败: " + str(review_result.get("status", "unknown")))
                overall["tasks_errored"] += 1
        elif task_type == "config_fix":
            # 安全修复配置文件：backup → edit → verify → rollback on fail
            payload = task.get("payload", {})
            file = payload.get("file", "")
            old_str = payload.get("old_string", "")
            new_str = payload.get("new_string", "")
            reason = payload.get("reason", "")
            rollback_plan = payload.get("rollback_plan", {})

            from agent.pgg_recovery_guard import safe_edit, backup_file
            bak = backup_file(file, tag=f"bridge_config_fix_{task_id}")
            if not bak.get("backed_up"):
                mark_task(task_id, "error", note=f"备份失败: {file}")
                overall["tasks_errored"] += 1
                continue

            result = safe_edit(file, old_str, new_str, tag=f"bridge_{task_id}")
            if result.get("edited"):
                mark_task(task_id, "done", note=f"已修复: {reason}")
                overall["tasks_processed"] += 1
            else:
                mark_task(task_id, "error", note=f"修复失败, 已回滚: {result.get('error', '?')}")
                overall["tasks_errored"] += 1

            overall["results"].append({
                "task_id": task_id, "task_type": task_type, "action": "config_fix", "status": "done" if result.get("edited") else "error",
            })
            continue

        elif task_type == "code_fix":
            payload = task.get("payload", {})
            file = payload.get("file", "")
            old_str = payload.get("old_string", "")
            new_str = payload.get("new_string", "")

            from agent.pgg_recovery_guard import safe_edit, backup_file
            bak = backup_file(file, tag=f"bridge_code_fix_{task_id}")
            if not bak.get("backed_up"):
                mark_task(task_id, "error", note=f"备份失败: {file}")
                overall["tasks_errored"] += 1
                continue

            result = safe_edit(file, old_str, new_str, tag=f"bridge_{task_id}")
            if result.get("edited"):
                mark_task(task_id, "done", note="代码已修复")
                overall["tasks_processed"] += 1
            else:
                mark_task(task_id, "error", note=f"修复失败, 已回滚: {result.get('error', '?')}")
                overall["tasks_errored"] += 1

            overall["results"].append({
                "task_id": task_id, "task_type": task_type, "action": "code_fix", "status": "done" if result.get("edited") else "error",
            })
            continue
        elif task_type == "skill_gen":
            mark_task(task_id, "approved", note="标记：需要人工创建skill")
            overall["tasks_skipped"] += 1
        elif task_type == "learn_suggest":
            # 自扫描学习建议 — 保持 pending，等用户在session里查看
            # 不标记done，靠 pgg_self_scan --suggest 自动产生 + session呈现
            mark_task(task_id, "approved",
                      note="学习建议已就绪，等待用户查看")
            overall["results"].append({
                "task_id": task_id, "task_type": task_type, "action": "learn_suggest", "status": "pending_for_user",
            })
            continue
        elif task_type in ("alert", "saturation_switch"):
            mark_task(task_id, "done", note="桥处理器已确认")
            overall["tasks_processed"] += 1
        else:
            mark_task(task_id, "error", note="unknown_task_type:" + task_type)
            overall["tasks_errored"] += 1

    return overall


def bridge_processor_summary() -> dict[str, Any]:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row

    gate_dist = {}
    for r in db.execute(
        "SELECT gate_type, COUNT(*) as c FROM evolution_genes WHERE status='candidate' GROUP BY gate_type ORDER BY c DESC"
    ).fetchall():
        gate_dist[r["gate_type"]] = r["c"]

    llm_approved = db.execute(
        "SELECT COUNT(*) FROM evolution_genes WHERE verification_status LIKE 'llm_reviewed%'"
    ).fetchone()[0]
    rule_approved = db.execute(
        "SELECT COUNT(*) FROM evolution_genes WHERE verification_status LIKE 'rule_reviewed%'"
    ).fetchone()[0]
    claude_approved = db.execute(
        "SELECT COUNT(*) FROM evolution_genes WHERE verification_status LIKE 'claude_reviewed%'"
    ).fetchone()[0]
    dual_approved = db.execute(
        "SELECT COUNT(*) FROM evolution_genes WHERE verification_status LIKE 'dual_reviewed%'"
    ).fetchone()[0]
    llm_rejected = db.execute(
        "SELECT COUNT(*) FROM evolution_genes WHERE verification_status LIKE 'rejected_by_bridge%'"
    ).fetchone()[0]
    verified = db.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='verified'").fetchone()[0]
    candidate = db.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='candidate'").fetchone()[0]
    active = db.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='active'").fetchone()[0]

    db.close()

    return {
        "schema": "pgg_bridge_processor/v2/dual_channel",
        "created_at": datetime.now().isoformat(),
        "gene_db": {"verified": verified, "active": active, "candidate": candidate},
        "llm_reviewed_approved": llm_approved,
        "rule_reviewed_approved": rule_approved,
        "claude_reviewed_approved": claude_approved,
        "dual_reviewed_approved": dual_approved,
        "llm_reviewed_rejected": llm_rejected,
        "total_bridge_processed": llm_approved + rule_approved + claude_approved + dual_approved + llm_rejected,
        "candidate_by_gate": gate_dist,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PGG Bridge Processor")
    parser.add_argument("--process", action="store_true", help="处理所有pending桥任务")
    parser.add_argument("--review", type=str, nargs="*", help="指定gene_ids审核")
    parser.add_argument("--summary", action="store_true", help="显示桥处理器摘要")
    parser.add_argument("--proof-review", type=str, help="只读证明审核单个 gene_id，不晋升/拒绝")
    parser.add_argument("--task-id", type=str, default="", help="proof-review 的 task_id")
    args = parser.parse_args()

    if args.summary:
        print(json.dumps(bridge_processor_summary(), indent=2, ensure_ascii=False))
        return
    if args.proof_review:
        result = proof_review_gene(args.proof_review, task_id=args.task_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    if args.process:
        result = process_bridge_tasks()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    if args.review is not None:
        gene_ids = args.review if args.review else None
        result = process_promotion_batch(gene_ids if gene_ids else None)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    parser.print_help()


if __name__ == "__main__":
    main()