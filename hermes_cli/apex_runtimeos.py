"""CLI helpers for APEX RuntimeOS diagnostics."""

from __future__ import annotations

import argparse
import json
from typing import Any, Mapping

from agent.apex_runtimeos_audit_summary import render_markdown, summarize_audit
from agent.apex_system_identity import (
    CURRENT_SYSTEM_NAME,
    DIAGNOSTIC_COMMAND_ALIASES,
    LEGACY_RUNTIME_NAME,
    PRIMARY_DIAGNOSTIC_COMMAND,
    USER_FACING_SYSTEM_LABEL,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"/{PRIMARY_DIAGNOSTIC_COMMAND}",
        description=f"Show {USER_FACING_SYSTEM_LABEL} audit summary diagnostics",
    )
    parser.add_argument("command", nargs="?", default="summary", choices=("summary", "status", "feishu", "autopromote", "rollback", "autonomy", "autonomy-candidate", "quality-evidence", "co-scientist", "co-scientist-gene", "era", "flow-reward", "switch-cost", "cron-ledger", "sequence-record"))
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--limit", type=int, default=10000, help="max audit lines to read")
    parser.add_argument("--target", default="memory", choices=("memory", "skill", "all"), help="autopromote/rollback target")
    parser.add_argument("--execute", action="store_true", help="execute side effects; default is dry-run/disabled")
    parser.add_argument("--repair", action="store_true", help="quarantine bad cron-ledger lines; requires enforce mode")
    parser.add_argument("--min-occurrences", type=int, default=2, help="minimum repeated candidate count for autopromote/autonomy")
    parser.add_argument("--sequence", action="append", choices=("21354", "12534", "14325"), help="APEX sequence evidence to append; repeatable")
    parser.add_argument("--score", type=float, default=0.8, help="sequence evidence score between 0 and 1")
    parser.add_argument("--shortcoming", default="", help="sanitized shortcoming summary for sequence evidence")
    parser.add_argument("--test-cmd", action="append", default=[], help="quality-evidence test command; may be repeated")
    parser.add_argument("--output", default="", help="optional output path for generated quality evidence bundle/report")
    parser.add_argument("--documentation", action="store_true", help="mark documentation evidence present for quality-evidence")
    parser.add_argument("--audit", action="store_true", help="mark audit evidence present for quality-evidence")
    parser.add_argument("--topic", default="", help="co-scientist debate topic / APEX report task")
    parser.add_argument("--reviewer", action="append", default=[], help="co-scientist reviewer JSON; may be repeated")
    parser.add_argument("--synthesis", default="", help="co-scientist synthesis summary")
    parser.add_argument("--decision", default="hold", help="co-scientist decision")
    parser.add_argument("--path", action="append", default=[], help="ERA path JSON; may be repeated")
    parser.add_argument("--selected-path-id", default="", help="Flow reward selected path id")
    parser.add_argument("--predicted-score", type=float, default=0.0, help="Flow reward predicted path score between 0 and 1")
    parser.add_argument("--outcome", action="append", default=[], help="Flow reward outcome JSON; may be repeated")
    parser.add_argument("--current-route", default="{}", help="Switch-cost current route JSON")
    parser.add_argument("--target-route", default="{}", help="Switch-cost target route JSON")
    parser.add_argument("--switching-cost", type=float, default=None, help="explicit switching cost between 0 and 1")
    parser.add_argument("--hysteresis", type=float, default=0.15, help="minimum net gain required before switching")
    return parser


def _top_rows(items: Mapping[str, Any], *, limit: int = 6) -> list[tuple[str, Mapping[str, Any]]]:
    rows: list[tuple[str, Mapping[str, Any]]] = []
    for key, value in items.items():
        if isinstance(value, Mapping):
            rows.append((str(key), value))
    return sorted(rows, key=lambda item: int(item[1].get("count") or 0), reverse=True)[:limit]


def _status_icon(summary: Mapping[str, Any]) -> str:
    if int(summary.get("blocking_records") or 0) > 0:
        return "⚠️"
    if int(summary.get("bad_lines") or 0) > 0:
        return "🟡"
    return "✅"


def _feishu_markdown(summary: Mapping[str, Any]) -> str:
    organs = summary.get("organs") if isinstance(summary.get("organs"), Mapping) else {}
    stages = summary.get("stages") if isinstance(summary.get("stages"), Mapping) else {}
    recommendations = summary.get("recommendations") if isinstance(summary.get("recommendations"), Mapping) else {}
    recommendations_count = int(recommendations.get("count") or 0) if isinstance(recommendations, Mapping) else 0
    recommendations_status = recommendations.get("status", {}) if isinstance(recommendations, Mapping) else {}
    recommendation_gate = str(summary.get("recommendation_gate", "OK"))
    icon = _status_icon(summary)
    lines = [
        f"# {icon} {USER_FACING_SYSTEM_LABEL} 体征摘要",
        "",
        "**状态：手动只读摘要，未自动推送，未修改运行状态。**",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 有效记录 | {summary.get('records', 0)} |",
        f"| 坏行 | {summary.get('bad_lines', 0)} |",
        f"| 阻断记录 | {summary.get('blocking_records', 0)} |",
        f"| 建议数 | {recommendations_count} |",
        f"| 建议状态 | {recommendations_status} |",
        f"| 建议门禁 | {recommendation_gate} |",
        f"| audit 文件存在 | {summary.get('audit_path_exists', False)} |",
        "",
        "## 建议概览",
        "",
        "| code | severity | applied | mutates_runtime | reason |",
        "|---|---|---:|---:|---|",
    ]
    top_recommendations = recommendations.get("items") if isinstance(recommendations.get("items"), list) else []
    if top_recommendations:
        for item in top_recommendations[:6]:
            if not isinstance(item, Mapping):
                continue
            lines.append(
                f"| {item.get('code', '')} | {item.get('severity', '')} | {item.get('applied', False)} | {item.get('mutates_runtime', False)} | {item.get('reason', '')} |"
            )
    else:
        lines.append("| - | - | False | False | - |")
    lines.extend([
        "",
        "## Cron dry-run 账本",
        "",
        "| 字段 | 数值 |",
        "|---|---:|",
    ])
    autonomy_raw = summary.get("autonomy") if isinstance(summary.get("autonomy"), Mapping) else {}
    autonomy: Mapping[str, Any] = autonomy_raw if isinstance(autonomy_raw, Mapping) else {}
    health_raw = autonomy.get("health_report") if isinstance(autonomy.get("health_report"), Mapping) else {}
    health: Mapping[str, Any] = health_raw if isinstance(health_raw, Mapping) else {}
    cron_raw = autonomy.get("cron_dryrun") if isinstance(autonomy.get("cron_dryrun"), Mapping) else {}
    cron: Mapping[str, Any] = cron_raw if isinstance(cron_raw, Mapping) else {}
    lines.extend([
        f"| health_status | {health.get('status', 'OK')} |",
        f"| alert_count | {health.get('alert_count', 0)} |",
        f"| ledger_exists | {cron.get('ledger_exists', False)} |",
        f"| unique_keys | {cron.get('unique_keys', 0)} |",
        f"| bad_lines | {cron.get('bad_lines', 0)} |",
        f"| last_seen_at | {cron.get('last_seen_at', 0)} |",
    ])
    alerts = health.get("alerts") if isinstance(health.get("alerts"), list) else []
    if alerts:
        lines.extend(["", "### 阈值提醒", "", "| code | severity | count | message |", "|---|---|---:|---|"])
        for alert in alerts[:6]:
            if isinstance(alert, Mapping):
                lines.append(f"| {alert.get('code')} | {alert.get('severity')} | {alert.get('count')} | {alert.get('message')} |")
    lines.extend([
        "",
        "## Organ 概览",
        "",
        "| organ | 数量 | 阻断 | 状态 | 平均耗时 ms |",
        "|---|---:|---:|---|---:|",
    ])
    top_organs = _top_rows(organs)
    if top_organs:
        for organ, data in top_organs:
            lines.append(f"| {organ} | {data.get('count', 0)} | {data.get('blocking', 0)} | {data.get('status', {})} | {data.get('avg_elapsed_ms', 0)} |")
    else:
        lines.append("| - | 0 | 0 | {} | 0 |")
    lines.extend(["", "## Stage 概览", "", "| stage | 数量 | 阻断 | 状态 | 平均耗时 ms |", "|---|---:|---:|---|---:|"])
    top_stages = _top_rows(stages)
    if top_stages:
        for stage, data in top_stages:
            lines.append(f"| {stage} | {data.get('count', 0)} | {data.get('blocking', 0)} | {data.get('status', {})} | {data.get('avg_elapsed_ms', 0)} |")
    else:
        lines.append("| - | 0 | 0 | {} | 0 |")
    lines.extend([
        "",
        "## 边界",
        "",
        "- 只读聚合：不读取、不输出原始对话正文。",
        "- 不输出本地 audit 路径、原始错误堆栈、凭据。",
        "- 本命令只生成文本，不自动发送飞书。",
    ])
    return "\n".join(lines) + "\n"


def _cn_markdown(summary: Mapping[str, Any]) -> str:
    organs = summary.get("organs") or {}
    stages = summary.get("stages") or {}
    lines = [
        f"# {USER_FACING_SYSTEM_LABEL} 诊断摘要",
        "",
        "| 字段 | 数值 |",
        "|---|---:|",
        f"| 有效记录 | {summary.get('records', 0)} |",
        f"| 坏行 | {summary.get('bad_lines', 0)} |",
        f"| 阻断记录 | {summary.get('blocking_records', 0)} |",
        f"| audit 文件存在 | {summary.get('audit_path_exists', False)} |",
        "",
        "## Organs",
        "",
        "| organ | 数量 | 阻断 | 状态 | 平均耗时 ms |",
        "|---|---:|---:|---|---:|",
    ]
    if organs:
        for organ, data in sorted(organs.items()):
            lines.append(
                f"| {organ} | {data.get('count', 0)} | {data.get('blocking', 0)} | "
                f"{data.get('status', {})} | {data.get('avg_elapsed_ms', 0)} |"
            )
    else:
        lines.append("| - | 0 | 0 | {} | 0 |")
    lines.extend([
        "",
        "## Stages",
        "",
        "| stage | 数量 | 阻断 | 状态 | 平均耗时 ms |",
        "|---|---:|---:|---|---:|",
    ])
    if stages:
        for stage, data in sorted(stages.items()):
            lines.append(
                f"| {stage} | {data.get('count', 0)} | {data.get('blocking', 0)} | "
                f"{data.get('status', {})} | {data.get('avg_elapsed_ms', 0)} |"
            )
    else:
        lines.append("| - | 0 | 0 | {} | 0 |")
    return "\n".join(lines) + "\n"


def run_apex_runtimeos_cli(argv: list[str] | None = None) -> str:
    """Return CLI output for the PGG Archon diagnostics command.

    Output is aggregate-only: no local paths, prompts, messages, raw errors, or
    credentials are rendered.
    """
    parser = _parser()
    ns = parser.parse_args(argv or [])
    limit = max(1, min(int(ns.limit), 100000))
    if ns.command == "autonomy":
        from agent.apex_runtimeos_autonomy import summarize_autonomy_status
        status = summarize_autonomy_status(limit=limit, min_occurrences=max(1, int(ns.min_occurrences)))
        if ns.json:
            return json.dumps({"object": "hermes.apex_runtimeos.autonomy_status", "status": status}, ensure_ascii=False, indent=2)
        cron = status.get("cron_dryrun") if isinstance(status.get("cron_dryrun"), dict) else {}
        evm_gate = status.get("evm_gate") if isinstance(status.get("evm_gate"), dict) else {}
        sequence_gate = status.get("sequence_gate") if isinstance(status.get("sequence_gate"), dict) else {}
        gene_lifecycle_gate = status.get("gene_lifecycle_gate") if isinstance(status.get("gene_lifecycle_gate"), dict) else {}
        formula_report = status.get("formula_report") if isinstance(status.get("formula_report"), dict) else {}
        gep_report_raw = status.get("gep_report")
        gep_report = gep_report_raw if isinstance(gep_report_raw, dict) else {}
        gep_safety_raw = gep_report.get("safety_pipeline")
        gep_safety = gep_safety_raw if isinstance(gep_safety_raw, dict) else {}
        quality_gate = status.get("quality_gate") if isinstance(status.get("quality_gate"), dict) else {}
        quality_bundle_raw = quality_gate.get("evidence_bundle")
        quality_bundle = quality_bundle_raw if isinstance(quality_bundle_raw, dict) else {}
        quality_bundle_source_raw = status.get("quality_evidence_bundle")
        quality_bundle_source = quality_bundle_source_raw if isinstance(quality_bundle_source_raw, dict) else {}
        co_scientist_raw = status.get("co_scientist_report")
        co_scientist = co_scientist_raw if isinstance(co_scientist_raw, dict) else {}
        co_gene_raw = status.get("co_scientist_gene_candidate")
        co_gene = co_gene_raw if isinstance(co_gene_raw, dict) else {}
        era_raw = status.get("era_report")
        era_report = era_raw if isinstance(era_raw, dict) else {}
        flow_reward_raw = status.get("flow_reward_report")
        flow_reward = flow_reward_raw if isinstance(flow_reward_raw, dict) else {}
        switch_cost_raw = status.get("switch_cost_report")
        switch_cost = switch_cost_raw if isinstance(switch_cost_raw, dict) else {}
        skill_registry_policy = status.get("skill_registry_policy") if isinstance(status.get("skill_registry_policy"), dict) else {}
        gpo_raw = status.get("gpo_report")
        gpo_report = gpo_raw if isinstance(gpo_raw, dict) else {}
        gpo_scan_raw = gpo_report.get("omega_static_scan")
        gpo_scan = gpo_scan_raw if isinstance(gpo_scan_raw, dict) else {}
        unified_raw = status.get("apex_v3_unified_score")
        unified_score = unified_raw if isinstance(unified_raw, dict) else {}
        gep_index_raw = gep_report.get("capability_index")
        if isinstance(gep_index_raw, dict):
            gep_index = gep_index_raw
        else:
            gep_index = {}
        gep_counts_raw = gep_index.get("counts")
        if isinstance(gep_counts_raw, dict):
            gep_counts = gep_counts_raw
        else:
            gep_counts = {}
        promotion_lifecycle_gate = status.get("promotion_lifecycle_gate") if isinstance(status.get("promotion_lifecycle_gate"), dict) else {}
        return "\n".join([
            f"# {USER_FACING_SYSTEM_LABEL} 自主化状态",
            "",
            "字段：运行模式",
            f"值：{status.get('mode')}",
            "",
            "字段：自动晋升开启",
            f"值：{status.get('autopromote_enabled')}",
            "",
            "字段：回滚开启",
            f"值：{status.get('rollback_enabled')}",
            "",
            "字段：稳定候选数",
            f"值：{status.get('stable_ready_count')}",
            "",
            "字段：候选分组数",
            f"值：{status.get('candidate_groups')}",
            "",
            "字段：晋升记录数",
            f"值：{status.get('promotion_count')}",
            "",
            "字段：待回滚数",
            f"值：{status.get('pending_rollbacks')}",
            "",
            "字段：回滚事件数",
            f"值：{status.get('rollback_events', {}).get('count', 0)}",
            "",
            "字段：健康状态",
            f"值：{status.get('health_report', {}).get('status', 'OK')}",
            "",
            "字段：健康提醒数",
            f"值：{status.get('health_report', {}).get('alert_count', 0)}",
            "",
            "字段：EVM门禁状态",
            f"值：{evm_gate.get('status', 'UNKNOWN')}",
            "",
            "字段：EVM分数",
            f"值：{evm_gate.get('evm_value', '-')}",
            "",
            "字段：EVM缺失证据",
            f"值：{evm_gate.get('missing_completion_evidence', [])}",
            "",
            "字段：APEX三顺序门禁状态",
            f"值：{sequence_gate.get('status', 'UNKNOWN')}",
            "",
            "字段：APEX三顺序已见数量",
            f"值：{sequence_gate.get('sequence_count', 0)}",
            "",
            "字段：APEX三顺序缺失",
            f"值：{sequence_gate.get('missing_sequences', [])}",
            "",
            "字段：基因生命周期门禁状态",
            f"值：{gene_lifecycle_gate.get('status', 'UNKNOWN')}",
            "",
            "字段：基因候选数",
            f"值：{gene_lifecycle_gate.get('gene_count', 0)}",
            "",
            "字段：可晋升基因数",
            f"值：{gene_lifecycle_gate.get('promotable_count', 0)}",
            "",
            "字段：APEX公式报告状态",
            f"值：{formula_report.get('status', 'UNKNOWN')}",
            "",
            "字段：APEX v2.3分数",
            f"值：{formula_report.get('v2_3_score', '-')}",
            "",
            "字段：APEX V10最终分数",
            f"值：{formula_report.get('v10_final_score', '-')}",
            "",
            "字段：Evolver GEP报告状态",
            f"值：{gep_report.get('status', 'UNKNOWN')}",
            "",
            "字段：CMMI质量门禁状态",
            f"值：{quality_gate.get('status', 'UNKNOWN')}",
            "",
            "字段：CMMI阻断失败数",
            f"值：{quality_gate.get('blocking_failed', 0)}",
            "",
            "字段：CMMI警告失败数",
            f"值：{quality_gate.get('warning_failed', 0)}",
            "",
            "字段：CMMI缺失阻断证据",
            f"值：{quality_gate.get('missing_blocking_evidence', [])}",
            "",
            "字段：CMMI缺失警告证据",
            f"值：{quality_gate.get('missing_warning_evidence', [])}",
            "",
            "字段：CMMI证据包已读取",
            f"值：{quality_bundle.get('provided', False)}",
            "",
            "字段：CMMI证据包有效",
            f"值：{quality_bundle.get('valid', False)}",
            "",
            "字段：CMMI证据包错误",
            f"值：{quality_bundle.get('error') or status.get('quality_evidence_bundle_error') or '-'}",
            "",
            "字段：CMMI证据包键",
            f"值：{quality_bundle.get('keys', [])}",
            "",
            "字段：CMMI证据包来源",
            f"值：{quality_bundle_source.get('source', '-')}",
            "",
            "字段：GEP组件数",
            f"值：{gep_index.get('component_count', 0)}",
            "",
            "字段：GEP混淆组件数",
            f"值：{gep_counts.get('archived_obfuscated', 0)}",
            "",
            "字段：GEP安全流水线状态",
            f"值：{gep_safety.get('status', 'UNKNOWN')}",
            "",
            "字段：GEP运行接入允许",
            f"值：{gep_safety.get('runtime_allowed', False)}",
            "",
            "字段：GEP HOLD原因",
            f"值：{gep_safety.get('hold_reasons', [])}",
            "",
            "字段：GEP安全流水线阶段",
            f"值：{[stage.get('id') for stage in gep_safety.get('stages', []) if isinstance(stage, dict)]}",
            "",
            "字段：Co_Scientist状态",
            f"值：{co_scientist.get('status', 'UNKNOWN')}",
            "",
            "字段：Co_Scientist有效",
            f"值：{co_scientist.get('valid', False)}",
            "",
            "字段：Co_Scientist审查员数",
            f"值：{co_scientist.get('reviewer_count', 0)}",
            "",
            "字段：Co_Scientist决策",
            f"值：{co_scientist.get('decision', '-')}",
            "",
            "字段：Co_Scientist主题",
            f"值：{co_scientist.get('topic', '-')}",
            "",
            "字段：Co_Scientist错误",
            f"值：{status.get('co_scientist_report_error', '-')}",
            "",
            "字段：Co_Scientist基因候选状态",
            f"值：{co_gene.get('status', 'UNKNOWN')}",
            "",
            "字段：Co_Scientist基因候选可晋升",
            f"值：{co_gene.get('eligible', False)}",
            "",
            "字段：Co_Scientist基因候选证据等级",
            f"值：{co_gene.get('evidence_level', '-')}",
            "",
            "字段：Co_Scientist基因候选已写库",
            f"值：{co_gene.get('gene_library_written', False)}",
            "",
            "字段：ERA路径搜索状态",
            f"值：{era_report.get('status', 'UNKNOWN')}",
            "",
            "字段：ERA路径数量",
            f"值：{era_report.get('path_count', 0)}",
            "",
            "字段：ERA选中路径",
            f"值：{era_report.get('selected_path_id', '-')}",
            "",
            "字段：ERA选中分数",
            f"值：{era_report.get('selected_score', '-')}",
            "",
            "字段：ERA已执行",
            f"值：{era_report.get('executed', False)}",
            "",
            "字段：Flow奖励状态",
            f"值：{flow_reward.get('status', 'UNKNOWN')}",
            "",
            "字段：Flow奖励选中路径",
            f"值：{flow_reward.get('selected_path_id', '-')}",
            "",
            "字段：Flow预测分数",
            f"值：{flow_reward.get('predicted_score', '-')}",
            "",
            "字段：Flow实绩分数",
            f"值：{flow_reward.get('realized_score', '-')}",
            "",
            "字段：Flow分数差",
            f"值：{flow_reward.get('score_delta', '-')}",
            "",
            "字段：Flow结果数量",
            f"值：{flow_reward.get('outcome_count', 0)}",
            "",
            "字段：切换成本状态",
            f"值：{switch_cost.get('status', 'UNKNOWN')}",
            "",
            "字段：切换成本决策",
            f"值：{switch_cost.get('decision', '-')}",
            "",
            "字段：当前路径",
            f"值：{switch_cost.get('current_route_id', '-')}",
            "",
            "字段：目标路径",
            f"值：{switch_cost.get('target_route_id', '-')}",
            "",
            "字段：切换成本",
            f"值：{switch_cost.get('switching_cost', '-')}",
            "",
            "字段：净收益",
            f"值：{switch_cost.get('net_gain', '-')}",
            "",
            "字段：切换已执行",
            f"值：{switch_cost.get('executed', False)}",
            "",
            "字段：APEX v3统一评分状态",
            f"值：{unified_score.get('status', 'UNKNOWN')}",
            "",
            "字段：APEX v3统一评分",
            f"值：{unified_score.get('score', '-')}",
            "",
            "字段：APEX v3阻断原因",
            f"值：{unified_score.get('hold_reasons', [])}",
            "",
            "字段：APEX v3允许低风险下一轮",
            f"值：{unified_score.get('allows_next_low_risk_cycle', False)}",
            "",
            "字段：APEX v3允许自动晋升",
            f"值：{unified_score.get('allows_autonomous_promotion', False)}",
            "",
            "字段：GPO状态",
            f"值：{gpo_report.get('status', 'UNKNOWN')}",
            "",
            "字段：GPO原则数",
            f"值：{gpo_report.get('principle_count', 0)}",
            "",
            "字段：GPO知识源",
            f"值：{gpo_report.get('source_repo', '-')}",
            "",
            "字段：Omega静态扫描文件数",
            f"值：{gpo_scan.get('scanned_file_count', gpo_scan.get('py_file_count', 0))}",
            "",
            "字段：Omega静态扫描类数",
            f"值：{gpo_scan.get('class_count', 0)}",
            "",
            "字段：Omega运行接入允许",
            f"值：{gpo_report.get('runtime_allowed', False)}",
            "",
            "字段：技能注册表策略状态",
            f"值：{skill_registry_policy.get('status', 'UNKNOWN')}",
            "",
            "字段：技能注册表默认策略",
            f"值：{skill_registry_policy.get('policy', '-')}",
            "",
            "字段：高风险只读来源数",
            f"值：{skill_registry_policy.get('reference_only_high_risk_count', 0)}",
            "",
            "字段：高风险只读来源ID",
            f"值：{skill_registry_policy.get('reference_only_high_risk_ids', [])}",
            "",
            "字段：高风险晋升生命周期门禁",
            f"值：{promotion_lifecycle_gate.get('status', 'UNKNOWN')}",
            "",
            "字段：高风险晋升阻断原因",
            f"值：{promotion_lifecycle_gate.get('reason', '-')}",
            "",
            "字段：cron账本键数",
            f"值：{cron.get('unique_keys', 0)}",
            "",
            "字段：cron最后记录时间",
            f"值：{cron.get('last_seen_at', 0)}",
            "",
        ])
    if ns.command == "autonomy-candidate":
        import os
        from agent.apex_runtimeos_autonomy import persist_autonomy_recommendation_candidate
        previous_auto_write = os.environ.get("APEX_RUNTIMEOS_AUTO_WRITE_ENABLED")
        if ns.execute:
            os.environ["APEX_RUNTIMEOS_AUTO_WRITE_ENABLED"] = "1"
        try:
            result = persist_autonomy_recommendation_candidate(limit=limit, session_id="apex-runtimeos-cli")
        finally:
            if ns.execute:
                if previous_auto_write is None:
                    os.environ.pop("APEX_RUNTIMEOS_AUTO_WRITE_ENABLED", None)
                else:
                    os.environ["APEX_RUNTIMEOS_AUTO_WRITE_ENABLED"] = previous_auto_write
        if ns.json:
            return json.dumps({"object": "hermes.apex_runtimeos.autonomy_candidate", "result": result}, ensure_ascii=False, indent=2)
        return "\n".join([
            "# APEX RuntimeOS 自主候选生成",
            "",
            "字段：execute",
            f"值：{bool(ns.execute)}",
            "",
            "字段：written",
            f"值：{result.get('written', False)}",
            "",
            "字段：reason",
            f"值：{result.get('reason', '-')}",
            "",
            "字段：candidate_type",
            f"值：{result.get('candidate_type', '-')}",
            "",
        ])
    if ns.command == "quality-evidence":
        import shlex
        from pathlib import Path
        from runtime.quality.evidence_bundle import (
            build_quality_evidence_bundle,
            run_test_command_for_evidence,
            write_quality_evidence_bundle,
        )
        commands = ns.test_cmd or []
        test_results = []
        if ns.execute:
            for command in commands:
                test_results.append(run_test_command_for_evidence(shlex.split(command), timeout=600))
        passed = bool(test_results) and all(item.get("passed") for item in test_results)
        summary = "no test command executed" if not test_results else f"{sum(1 for item in test_results if item.get('passed'))}/{len(test_results)} test commands passed"
        bundle = build_quality_evidence_bundle(
            test_exit_code=0 if passed else 1,
            test_summary=summary,
            audit_present=bool(ns.audit),
            audit_summary="operator marked audit evidence present" if ns.audit else "audit evidence not marked",
            documentation_present=bool(ns.documentation),
            documentation_summary="operator marked documentation evidence present" if ns.documentation else "documentation evidence not marked",
            source="apex-runtimeos-cli-quality-evidence",
        )
        written = None
        if ns.output:
            written = write_quality_evidence_bundle(Path(ns.output).expanduser(), bundle)
        result = {"execute": bool(ns.execute), "test_results": test_results, "bundle": bundle, "written": written}
        if ns.json:
            return json.dumps({"object": "hermes.apex_runtimeos.quality_evidence", "result": result}, ensure_ascii=False, indent=2)
        return "\n".join([
            "# APEX RuntimeOS CMMI证据包生成",
            "",
            "字段：execute",
            f"值：{bool(ns.execute)}",
            "",
            "字段：test_report",
            f"值：{bundle['evidence']['test_report']['present']}",
            "",
            "字段：audit_log",
            f"值：{bundle['evidence']['audit_log']['present']}",
            "",
            "字段：documentation",
            f"值：{bundle['evidence']['documentation']['present']}",
            "",
            "字段：written",
            f"值：{bool(written)}",
            "",
        ])
    if ns.command == "co-scientist":
        from pathlib import Path
        from agent.apex_co_scientist import build_debate_report, default_debate_report_path, write_debate_report
        reviewers = []
        for raw in ns.reviewer or []:
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                item = {"status": "error", "claim": "invalid reviewer json", "role": "review"}
            if isinstance(item, dict):
                reviewers.append(item)
        report = build_debate_report(
            topic=ns.topic or "unspecified",
            reviewers=reviewers,
            synthesis=ns.synthesis,
            decision=ns.decision,
        )
        written = None
        if ns.output:
            written = write_debate_report(Path(ns.output).expanduser(), report)
        elif ns.execute:
            written = write_debate_report(default_debate_report_path(ns.topic or "debate"), report)
        result = {"execute": bool(ns.execute), "report": report, "written": written}
        if ns.json:
            return json.dumps({"object": "hermes.apex_runtimeos.co_scientist", "result": result}, ensure_ascii=False, indent=2)
        return "\n".join([
            "# APEX Co-Scientist 结构化审查",
            "",
            "字段：topic",
            f"值：{report.get('topic')}",
            "",
            "字段：status",
            f"值：{report.get('status')}",
            "",
            "字段：reviewer_count",
            f"值：{report.get('reviewer_count')}",
            "",
            "字段：decision",
            f"值：{report.get('decision')}",
            "",
            "字段：written",
            f"值：{bool(written)}",
            "",
        ])
    if ns.command == "co-scientist-gene":
        from pathlib import Path
        from agent.apex_co_scientist import (
            build_debate_report,
            build_gene_candidate_from_debate,
            default_gene_candidate_path,
            write_gene_candidate,
        )
        reviewers = []
        for raw in ns.reviewer or []:
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                item = {"status": "error", "claim": "invalid reviewer json", "role": "review"}
            if isinstance(item, dict):
                reviewers.append(item)
        report = build_debate_report(
            topic=ns.topic or "unspecified",
            reviewers=reviewers,
            synthesis=ns.synthesis,
            decision=ns.decision,
        )
        candidate = build_gene_candidate_from_debate(report)
        written = None
        if ns.output:
            written = write_gene_candidate(Path(ns.output).expanduser(), candidate)
        elif ns.execute:
            written = write_gene_candidate(default_gene_candidate_path(ns.topic or "gene_candidate"), candidate)
        result = {"execute": bool(ns.execute), "candidate": candidate, "written": written}
        if ns.json:
            return json.dumps({"object": "hermes.apex_runtimeos.co_scientist_gene", "result": result}, ensure_ascii=False, indent=2)
        return "\n".join([
            "# APEX Co-Scientist 基因候选",
            "",
            "字段：status",
            f"值：{candidate.get('status')}",
            "",
            "字段：eligible",
            f"值：{candidate.get('eligible')}",
            "",
            "字段：evidence_level",
            f"值：{candidate.get('evidence_level')}",
            "",
            "字段：gene_library_written",
            f"值：{candidate.get('gene_library_written')}",
            "",
            "字段：written",
            f"值：{bool(written)}",
            "",
        ])
    if ns.command == "era":
        from pathlib import Path
        from agent.apex_era import build_era_path_search_report, default_era_report_path, write_era_report
        paths = []
        for raw in ns.path or []:
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                item = {"id": "invalid", "title": "invalid path json", "risk": 1.0, "reward": 0.0, "evidence": 0.0, "confidence": 0.0}
            if isinstance(item, dict):
                paths.append(item)
        report = build_era_path_search_report(task=ns.topic or "unspecified", paths=paths)
        written = None
        if ns.output:
            written = write_era_report(Path(ns.output).expanduser(), report)
        elif ns.execute:
            written = write_era_report(default_era_report_path(ns.topic or "era_path_search"), report)
        result = {"execute": bool(ns.execute), "report": report, "written": written}
        if ns.json:
            return json.dumps({"object": "hermes.apex_runtimeos.era", "result": result}, ensure_ascii=False, indent=2)
        return "\n".join([
            "# APEX ERA 路径搜索",
            "",
            "字段：status",
            f"值：{report.get('status')}",
            "",
            "字段：path_count",
            f"值：{report.get('path_count')}",
            "",
            "字段：selected_path_id",
            f"值：{report.get('selected_path_id')}",
            "",
            "字段：selected_score",
            f"值：{report.get('selected_score')}",
            "",
            "字段：executed",
            f"值：{report.get('executed')}",
            "",
            "字段：written",
            f"值：{bool(written)}",
            "",
        ])
    if ns.command == "flow-reward":
        from pathlib import Path
        from agent.apex_flow_reward import build_flow_reward_report, default_flow_reward_report_path, write_flow_reward_report
        outcomes = []
        for raw in ns.outcome or []:
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                item = {"id": "invalid", "summary": "invalid outcome json", "success": False, "regression": 1.0}
            if isinstance(item, dict):
                outcomes.append(item)
        report = build_flow_reward_report(
            task=ns.topic or "unspecified",
            selected_path_id=ns.selected_path_id or "unspecified",
            predicted_score=float(ns.predicted_score),
            outcomes=outcomes,
        )
        written = None
        if ns.output:
            written = write_flow_reward_report(Path(ns.output).expanduser(), report)
        elif ns.execute:
            written = write_flow_reward_report(default_flow_reward_report_path(ns.topic or "flow_reward"), report)
        result = {"execute": bool(ns.execute), "report": report, "written": written}
        if ns.json:
            return json.dumps({"object": "hermes.apex_runtimeos.flow_reward", "result": result}, ensure_ascii=False, indent=2)
        return "\n".join([
            "# APEX Flow 奖励反馈",
            "",
            "字段：status",
            f"值：{report.get('status')}",
            "",
            "字段：selected_path_id",
            f"值：{report.get('selected_path_id')}",
            "",
            "字段：predicted_score",
            f"值：{report.get('predicted_score')}",
            "",
            "字段：realized_score",
            f"值：{report.get('realized_score')}",
            "",
            "字段：score_delta",
            f"值：{report.get('score_delta')}",
            "",
            "字段：outcome_count",
            f"值：{report.get('outcome_count')}",
            "",
            "字段：written",
            f"值：{bool(written)}",
            "",
        ])
    if ns.command == "switch-cost":
        from pathlib import Path
        from agent.apex_switch_cost import build_switch_cost_report, default_switch_cost_report_path, write_switch_cost_report
        try:
            current_route = json.loads(ns.current_route or "{}")
        except json.JSONDecodeError:
            current_route = {"id": "invalid-current", "risk": 1.0, "reward": 0.0, "evidence": 0.0, "confidence": 0.0}
        try:
            target_route = json.loads(ns.target_route or "{}")
        except json.JSONDecodeError:
            target_route = {"id": "invalid-target", "risk": 1.0, "reward": 0.0, "evidence": 0.0, "confidence": 0.0}
        if not isinstance(current_route, dict):
            current_route = {"id": "invalid-current", "risk": 1.0}
        if not isinstance(target_route, dict):
            target_route = {"id": "invalid-target", "risk": 1.0}
        report = build_switch_cost_report(
            task=ns.topic or "unspecified",
            current_route=current_route,
            target_route=target_route,
            switching_cost=ns.switching_cost,
            hysteresis=float(ns.hysteresis),
        )
        written = None
        if ns.output:
            written = write_switch_cost_report(Path(ns.output).expanduser(), report)
        elif ns.execute:
            written = write_switch_cost_report(default_switch_cost_report_path(ns.topic or "switch_cost"), report)
        result = {"execute": bool(ns.execute), "report": report, "written": written}
        if ns.json:
            return json.dumps({"object": "hermes.apex_runtimeos.switch_cost", "result": result}, ensure_ascii=False, indent=2)
        return "\n".join([
            f"# {USER_FACING_SYSTEM_LABEL} 切换成本门禁",
            "",
            "字段：status",
            f"值：{report.get('status')}",
            "",
            "字段：decision",
            f"值：{report.get('decision')}",
            "",
            "字段：current_route_id",
            f"值：{report.get('current_route_id')}",
            "",
            "字段：target_route_id",
            f"值：{report.get('target_route_id')}",
            "",
            "字段：switching_cost",
            f"值：{report.get('switching_cost')}",
            "",
            "字段：net_gain",
            f"值：{report.get('net_gain')}",
            "",
            "字段：executed",
            f"值：{report.get('executed')}",
            "",
            "字段：written",
            f"值：{bool(written)}",
            "",
        ])
    if ns.command == "cron-ledger":
        import os
        from agent.apex_runtimeos_autonomy import summarize_cron_dryrun_ledger
        previous_repair = os.environ.get("APEX_RUNTIMEOS_CRON_LEDGER_REPAIR_ENABLED")
        if ns.repair:
            os.environ["APEX_RUNTIMEOS_CRON_LEDGER_REPAIR_ENABLED"] = "1"
        try:
            ledger = summarize_cron_dryrun_ledger(limit=limit)
        finally:
            if ns.repair:
                if previous_repair is None:
                    os.environ.pop("APEX_RUNTIMEOS_CRON_LEDGER_REPAIR_ENABLED", None)
                else:
                    os.environ["APEX_RUNTIMEOS_CRON_LEDGER_REPAIR_ENABLED"] = previous_repair
        if ns.json:
            return json.dumps({"object": "hermes.apex_runtimeos.cron_dryrun_ledger", "ledger": ledger}, ensure_ascii=False, indent=2)
        return "\n".join([
            "# APEX RuntimeOS Cron Dry-run 账本",
            "",
            "| 字段 | 数值 |",
            "|---|---:|",
            f"| ledger_exists | {ledger.get('ledger_exists')} |",
            f"| unique_keys | {ledger.get('unique_keys')} |",
            f"| bad_lines | {ledger.get('bad_lines')} |",
            f"| repair_enabled | {ledger.get('repair_enabled')} |",
            f"| quarantine_exists | {ledger.get('quarantine_exists')} |",
            f"| last_seen_at | {ledger.get('last_seen_at')} |",
            "",
        ])
    if ns.command == "sequence-record":
        import os
        from agent.apex_runtimeos_sequence import record_sequence_evidence
        previous_mode = os.environ.get("APEX_RUNTIMEOS_GATE_MODE")
        if ns.execute:
            os.environ["APEX_RUNTIMEOS_GATE_MODE"] = "enforce"
        results = []
        try:
            if ns.execute:
                for sequence in (ns.sequence or []):
                    results.append(record_sequence_evidence(sequence, score=float(ns.score), shortcoming=ns.shortcoming, source="apex-runtimeos-cli"))
            else:
                results = [{"written": False, "sequence": sequence, "reason": "dry_run"} for sequence in (ns.sequence or [])]
        finally:
            if ns.execute:
                if previous_mode is None:
                    os.environ.pop("APEX_RUNTIMEOS_GATE_MODE", None)
                else:
                    os.environ["APEX_RUNTIMEOS_GATE_MODE"] = previous_mode
        result = {"execute": bool(ns.execute), "requested": ns.sequence or [], "written": sum(1 for item in results if item.get("written")), "results": results}
        if ns.json:
            return json.dumps({"object": "hermes.apex_runtimeos.sequence_record", "result": result}, ensure_ascii=False, indent=2)
        return "\n".join([
            "# APEX RuntimeOS 三顺序证据记录",
            "",
            "字段：execute",
            f"值：{bool(ns.execute)}",
            "",
            "字段：requested",
            f"值：{ns.sequence or []}",
            "",
            "字段：written",
            f"值：{result['written']}",
            "",
        ])
    if ns.command in {"autopromote", "rollback"}:
        import os
        from agent.apex_runtimeos_autonomy import execute_promotion_rollbacks, run_autopromotion_scheduler
        previous_auto = os.environ.get("APEX_RUNTIMEOS_AUTOPROMOTE_ENABLED")
        previous_rollback = os.environ.get("APEX_RUNTIMEOS_ROLLBACK_ENABLED")
        if ns.execute:
            if ns.command == "autopromote":
                os.environ["APEX_RUNTIMEOS_AUTOPROMOTE_ENABLED"] = "1"
            else:
                os.environ["APEX_RUNTIMEOS_ROLLBACK_ENABLED"] = "1"
        try:
            if ns.command == "autopromote":
                result = run_autopromotion_scheduler(target=ns.target if ns.target != "all" else "memory", limit=limit, min_occurrences=max(1, int(ns.min_occurrences)))
            else:
                result = execute_promotion_rollbacks(target=ns.target, dry_run=not ns.execute, limit=limit)
        finally:
            if previous_auto is None:
                os.environ.pop("APEX_RUNTIMEOS_AUTOPROMOTE_ENABLED", None)
            else:
                os.environ["APEX_RUNTIMEOS_AUTOPROMOTE_ENABLED"] = previous_auto
            if previous_rollback is None:
                os.environ.pop("APEX_RUNTIMEOS_ROLLBACK_ENABLED", None)
            else:
                os.environ["APEX_RUNTIMEOS_ROLLBACK_ENABLED"] = previous_rollback
        if ns.json:
            return json.dumps({"object": f"hermes.apex_runtimeos.{ns.command}", "result": result}, ensure_ascii=False, indent=2)
        return "\n".join([
            f"# APEX RuntimeOS {ns.command}",
            "",
            f"| 字段 | 数值 |",
            "|---|---:|",
            f"| execute | {bool(ns.execute)} |",
            f"| target | {ns.target} |",
            f"| promoted | {result.get('promoted', 0)} |",
            f"| rolled_back | {result.get('rolled_back', 0)} |",
            f"| skipped | {result.get('skipped', 0)} |",
            f"| reason | {result.get('reason', '')} |",
            "",
        ])
    summary = summarize_audit(limit=limit)
    summary.pop("audit_path", None)
    try:
        from agent.apex_runtimeos_autonomy import summarize_autonomy_status
        summary["autonomy"] = summarize_autonomy_status(limit=limit, min_occurrences=max(1, int(ns.min_occurrences)))
    except Exception:
        summary["autonomy"] = {"health_report": {"status": "OK", "alert_count": 0, "alerts": []}, "cron_dryrun": {}}
    if ns.json:
        return json.dumps({"object": "hermes.apex_runtimeos.audit_summary", "summary": summary}, ensure_ascii=False, indent=2)
    if ns.command == "feishu":
        return _feishu_markdown(summary)
    _ = render_markdown(summary)
    return _cn_markdown(summary)
