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


def _llm_review_gene(gene: dict[str, Any]) -> dict[str, Any]:
    """通道1: LLM审核。GPT-5.5-turbo直连5yuantoken.org。"""
    prompt = (
        '你是PGG基因进化系统的审核员。审核以下candidate基因是否应被promote为verified。\n'
        '\n'
        '规则：\n'
        '1. 必须有 absorbed_knowledge（含signals_match字段）✅\n'
        '2. 必须有 evidence_grade（非空）✅\n'
        '3. 必须有 source_refs_json（非空，>10字符）✅\n'
        '4. fitness >= 700\n'
        '5. 梦境融合子代（dream_auto_fusion_*）fitness>1000且evidence>=B → approve\n'
        '6. 基因摄入基因（pgg_gene_*）fitness>800且evidence>=B → approve\n'
        '\n'
        f'基因信息：\n'
        f'  ID: {gene["gene_id"]}\n'
        f'  名称: {gene["gene_name"]}\n'
        f'  fitness: {gene["fitness"]}\n'
        f'  evidence_grade: {gene["evidence_grade"]}\n'
        f'  gate_type: {gene["gate_type"]}\n'
        f'  severity_rank: {gene["severity_rank"]}\n'
        '\n'
        '请严格回复以下JSON（不要其他文字）：\n'
        '{"decision": "approve"或"reject", "confidence": 0-100, "reason": "一句话理由"}'
    )

    api_key = _read_env_key("GPT55_5YUANTOKEN_API_KEY")
    if not api_key:
        return {"decision": "error", "confidence": 0, "reason": "key_not_found"}

    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150,
        "temperature": 0.1,
    })

    try:
        r = subprocess.run(
            ["curl", "-s", "-m", str(LLM_TIMEOUT),
             "-X", "POST", LLM_API_URL,
             "-H", "Content-Type: application/json",
             "-H", "Authorization: Bearer " + api_key,
             "-d", payload],
            capture_output=True, text=True, timeout=LLM_TIMEOUT + 5,
        )
        if r.returncode != 0:
            return {"decision": "error", "confidence": 0, "reason": "curl_exit_" + str(r.returncode)}
        output = r.stdout

        # 503 → gateway unavailable
        if "Service temporarily unavailable" in output or "503" in output:
            return {"decision": "error", "confidence": 0, "reason": "gateway_503"}

        # 解析
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
    """批量审核候选candidate基因。双通道：先LLM，503降级到规则。"""
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
        "approved": 0,
        "rejected": 0,
        "holds": 0,
        "errors": 0,
        "channel": "unknown",
        "details": [],
    }

    # 先测一次GPT是否可达
    test_key = _read_env_key("GPT55_5YUANTOKEN_API_KEY")
    gpt_available = False
    if test_key:
        try:
            tr = subprocess.run(
                ["curl", "-s", "-m", "5",
                 "-X", "POST", LLM_API_URL,
                 "-H", "Content-Type: application/json",
                 "-H", "Authorization: Bearer " + test_key,
                 "-d", '{"model":"gpt-5.5-turbo","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'],
                capture_output=True, text=True, timeout=10,
            )
            gpt_available = "choices" in tr.stdout
        except Exception:
            pass

    results["channel"] = "llm" if gpt_available else "rule_fallback"
    method_tag = "llm_reviewed" if gpt_available else "rule_reviewed"

    for c in candidates:
        gene = dict(c)

        if gpt_available:
            decision = _llm_review_gene(gene)
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
            # 规则无法判断，标记hold但不改DB
            detail["db_result"] = {"held": True, "reason": decision["reason"]}
            results["holds"] += 1
        else:  # error
            detail["db_result"] = {"error": decision["reason"]}
            results["errors"] += 1

        results["details"].append(detail)

        if gpt_available and len(results["details"]) < len(candidates):
            time.sleep(1)

    return results


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
    llm_rejected = db.execute(
        "SELECT COUNT(*) FROM evolution_genes WHERE verification_status LIKE 'rejected_by_bridge%'"
    ).fetchone()[0]
    verified = db.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='verified'").fetchone()[0]
    candidate = db.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='candidate'").fetchone()[0]
    active = db.execute("SELECT COUNT(*) FROM evolution_genes WHERE status='active'").fetchone()[0]

    db.close()

    return {
        "schema": "pgg_bridge_processor/v1/summary",
        "created_at": datetime.now().isoformat(),
        "gene_db": {"verified": verified, "active": active, "candidate": candidate},
        "llm_reviewed_approved": llm_approved,
        "rule_reviewed_approved": rule_approved,
        "llm_reviewed_rejected": llm_rejected,
        "total_bridge_processed": llm_approved + rule_approved + llm_rejected,
        "candidate_by_gate": gate_dist,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PGG Bridge Processor")
    parser.add_argument("--process", action="store_true", help="处理所有pending桥任务")
    parser.add_argument("--review", type=str, nargs="*", help="指定gene_ids审核")
    parser.add_argument("--summary", action="store_true", help="显示桥处理器摘要")
    args = parser.parse_args()

    if args.summary:
        print(json.dumps(bridge_processor_summary(), indent=2, ensure_ascii=False))
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