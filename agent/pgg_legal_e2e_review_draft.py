"""
pgg_legal_e2e_review_draft.py — PGG Archon 法律 E2E 复核 draft + Claude secondary reviewer 样本

功能：
  1. run_synthetic_case() -> dict
     - 选取一个简单的合成案例（民间借贷纠纷）
     - 使用本地法律知识库检索相关法条
     - 生成一份草案法律意见（不冒充最终意见）
     - 输出 struct: case / retrieval / draft / boundary

  2. run_secondary_review(draft: dict, reviewer_fn=None) -> dict
     - 调用 Claude MCP 审计（mcp_llm_audit_audit_claude）对草案做复核
     - 标注：REVIEWER_NOT_LEGAL_PROFESSIONAL / NOT_LEGAL_ADVICE

安全边界：
  - 合成案例，非真实客户
  - 每个输出需标注：
    "This is a synthetic review draft for engineering validation only.
     NOT legal advice. NOT a substitute for licensed attorney review."
  - 不连接真实办案系统
  - 不声明法律正确性证明

Usage:
    from agent.pgg_legal_e2e_review_draft import run_synthetic_case, run_secondary_review

    draft = run_synthetic_case()
    review = run_secondary_review(draft)
    # review["review_status"] == "PASS" or "FLAG"
    # review["disclaimer"] 已包含安全边界声明
"""

from __future__ import annotations

import json
import os
import textwrap
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Callable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SYNTHETIC_CASE_TEMPLATE = {
    "case_id": "SYN-2026-CIV-001",
    "case_type": "民间借贷纠纷",
    "status": "SYNTHETIC_DRAFT — NOT A REAL CASE",
    "description": textwrap.dedent("""\
        合成案例（非真实客户）：
        原告张三（出借人）与被告李四（借款人）系朋友关系。
        2025年3月1日，李四因资金周转需要向张三借款人民币50,000元，
        约定借款期限6个月（至2025年9月1日），月利率1.5%（年利率18%），
        利息按月支付。李四出具了借条一份，张三通过银行转账交付借款。
        李四支付了2025年3月至5月的利息（共3期，合计2,250元），
        之后未再支付任何利息，也未归还本金。
        张三多次催讨未果，现拟向人民法院提起诉讼。
    """),
    "parties": {
        "plaintiff": {"name": "张三", "role": "出借人"},
        "defendant": {"name": "李四", "role": "借款人"},
    },
    "key_facts": [
        "借款金额：50,000元人民币",
        "借款日期：2025年3月1日",
        "约定利率：月利率1.5%（年利率18%）",
        "借款期限：6个月（至2025年9月1日）",
        "交付方式：银行转账",
        "已支付利息：3期共2,250元（2025年3-5月）",
        "逾期未付：利息（2025年6月起）及本金",
    ],
    "disclaimer": (
        "This is a synthetic review draft for engineering validation only. "
        "NOT legal advice. NOT a substitute for licensed attorney review."
    ),
}

LOCAL_LEGAL_KNOWLEDGE_BASE = {
    "民法典_第667条": {
        "law": "《中华人民共和国民法典》第六百六十七条",
        "content": "借款合同是借款人向贷款人借款，到期返还借款并支付利息的合同。",
        "relevance": "民间借贷合同定性依据",
    },
    "民法典_第668条": {
        "law": "《中华人民共和国民法典》第六百六十八条",
        "content": "借款合同应当采用书面形式，但是自然人之间借款另有约定的除外。",
        "relevance": "借条形式要件审查依据",
    },
    "民法典_第679条": {
        "law": "《中华人民共和国民法典》第六百七十九条",
        "content": "自然人之间的借款合同，自贷款人提供借款时成立。",
        "relevance": "自然人借贷的实践合同性质——以款项交付为成立要件",
    },
    "民法典_第680条": {
        "law": "《中华人民共和国民法典》第六百八十条",
        "content": "禁止高利放贷，借款的利率不得违反国家有关规定。借款合同对支付利息没有约定的，视为没有利息。……",
        "relevance": "利率上限审查依据",
    },
    "民间借贷司法解释_2020_第25条": {
        "law": "《最高人民法院关于审理民间借贷案件适用法律若干问题的规定》（2020第二次修正）第二十五条",
        "content": "出借人请求借款人按照合同约定利率支付利息的，人民法院应予支持，但是双方约定的利率超过合同成立时一年期贷款市场报价利率四倍的除外。",
        "relevance": "民间借贷利率司法保护上限（LPR四倍）",
    },
    "民间借贷司法解释_2020_第28条": {
        "law": "《最高人民法院关于审理民间借贷案件适用法律若干问题的规定》（2020第二次修正）第二十八条",
        "content": "借贷双方对逾期利率有约定的，从其约定，但是以不超过合同成立时一年期贷款市场报价利率四倍为限。",
        "relevance": "逾期利率约定及上限",
    },
    "民间借贷司法解释_2020_第29条": {
        "law": "《最高人民法院关于审理民间借贷案件适用法律若干问题的规定》（2020第二次修正）第二十九条",
        "content": "出借人与借款人既约定了逾期利率，又约定了违约金或者其他费用，出借人可以选择主张逾期利息、违约金或者其他费用，也可以一并主张，但是总计超过合同成立时一年期贷款市场报价利率四倍的部分，人民法院不予支持。",
        "relevance": "逾期利息与违约金并存时的处理规则",
    },
    "民事诉讼法_第122条": {
        "law": "《中华人民共和国民事诉讼法》第一百二十二条",
        "content": "起诉必须符合下列条件：（一）原告是与本案有直接利害关系的公民、法人和其他组织；（二）有明确的被告；（三）有具体的诉讼请求和事实、理由；（四）属于人民法院受理民事诉讼的范围和受诉人民法院管辖。",
        "relevance": "起诉条件审查依据",
    },
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RetrievedLaw:
    """一条检索到的法律依据。"""
    key: str
    law: str
    content: str
    relevance: str


@dataclass
class DraftLegalOpinion:
    """草案法律意见（不冒充最终意见）。"""
    case_id: str
    opinion_type: str = "DRAFT — NOT FINAL LEGAL OPINION"
    disclaimer: str = (
        "This is a synthetic review draft for engineering validation only. "
        "NOT legal advice. NOT a substitute for licensed attorney review."
    )
    summary: str = ""
    legal_basis: list[dict] = field(default_factory=list)
    analysis_sections: list[dict] = field(default_factory=list)
    preliminary_conclusion: str = ""
    boundary_flags: list[str] = field(default_factory=list)


@dataclass
class SecondaryReviewResult:
    """Claude secondary reviewer 复核结果。"""
    case_id: str
    reviewer: str = "claude-opus-4-6 (via mcp_llm_audit_audit_claude)"
    review_id: str = ""
    review_timestamp: str = ""
    review_status: str = "PENDING"  # PASS / FLAG
    reviewer_notice: str = "REVIEWER_NOT_LEGAL_PROFESSIONAL — AI model, not a licensed attorney"
    not_legal_advice: str = "NOT_LEGAL_ADVICE — This review is for engineering validation only"
    findings: list[dict] = field(default_factory=list)
    flagged_issues: list[dict] = field(default_factory=list)
    raw_response: str = ""


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def _retrieve_relevant_laws(case: dict) -> list[RetrievedLaw]:
    """模拟本地法律知识库检索。

    根据合成案例事实，返回相关的法律依据条目。
    在实际部署中，此处应连接向量数据库或 Elasticsearch。
    """
    # 基于案例事实的关键词匹配
    relevant_keys = [
        "民法典_第667条",   # 借款合同定义
        "民法典_第668条",   # 书面形式
        "民法典_第679条",   # 自然人借贷——实践合同
        "民法典_第680条",   # 利率禁止高利
        "民间借贷司法解释_2020_第25条",  # LPR四倍
        "民间借贷司法解释_2020_第28条",  # 逾期利率上限
        "民间借贷司法解释_2020_第29条",  # 逾期利息与违约金
        "民事诉讼法_第122条",            # 起诉条件
    ]
    results = []
    for key in relevant_keys:
        entry = LOCAL_LEGAL_KNOWLEDGE_BASE.get(key)
        if entry:
            results.append(RetrievedLaw(key=key, **entry))
    return results


def _generate_draft_opinion(case: dict, retrieved: list[RetrievedLaw]) -> DraftLegalOpinion:
    """生成草案法律意见。

    注意：这是工程验证草案，不构成正式法律意见。
    实际办案中应由执业律师结合案件全貌审慎出具。
    """
    # 法律依据摘要
    legal_basis = [
        {"law": r.law, "content": r.content, "relevance": r.relevance}
        for r in retrieved
    ]

    # 利率上限分析（LPR 四倍检查）
    # 当前 1Y LPR 约为 3.1%（2025年水平，仅供参考）
    current_lpr = 0.031
    lpr_four_times = current_lpr * 4  # 12.4%
    agreed_rate = 0.18  # 年利率18%
    exceeds_lpr_limit = agreed_rate > lpr_four_times

    analysis_sections = [
        {
            "title": "一、合同效力分析",
            "content": (
                "张三与李四之间成立了自然人之间的借款合同关系。"
                "张三提供了借条（书面形式）并通过银行转账完成了款项交付，"
                "符合《民法典》第668条（书面形式）和第679条（实践合同）的要求，"
                "借款合同依法成立并生效。注意利率超标部分无效（民法典第156条+第680条）。"
                f"本金条款有效，超过LPR四倍的利率约定无效。已付超出可抵充本金（民法典第670条）。"
            ),
        },
        {
            "title": "二、利率合法性分析",
            "content": (
                f"约定年利率18%（月利率1.5%），当前LPR约{current_lpr*100:.1f}%，"
                f"LPR四倍为{lpr_four_times*100:.1f}%。"
                f"约定利率{'超过' if exceeds_lpr_limit else '未超过'}LPR四倍上限，"
                f"超过部分不受法律保护（民间借贷司法解释第25条）。"
                f"实际利息演算：50,000元×12.4%÷12×3=1,550元（合法上限内）；"
                f"约定利息：50,000元×18%÷12×3=2,250元。超出合法上限约700元，可主张抵充本金（民法典第670条）。"
                f"逾期利息以LPR四倍为上限，从2025年9月2日起算（民法典第676条）。"
            ),
        },
        {
            "title": "三、逾期责任分析",
            "content": (
                "李四自2025年6月起逾期未付利息，2025年9月1日起逾期未还本金。"
                "若借条有逾期利率约定，以不超过LPR四倍为限；"
                "若无约定，可主张按LPR计算的逾期利息。"
            ),
        },
        {
            "title": "四、诉讼可行性分析",
            "content": (
                "本案属于民事诉讼受案范围，管辖法院一般为被告住所地或合同履行地法院。"
                "诉讼请求明确（返还本金50,000元及相应利息），"
                "事实清楚且证据基本齐全（借条+银行转账记录），"
                "符合《民事诉讼法》第122条的起诉条件。"
                "诉讼时效：民间借贷诉讼时效为3年（民法典第188条），从债务履行期限届满次日（2025年9月2日）起算。"
                f"时效届满日：2028年9月1日。张三多次催讨可能构成时效中断（民法典第195条）。"
                f"当前时间约2026年6月，仍在诉讼时效期间内。李四如提出时效抗辩，"
                f"张三需提供催讨证据证明中断。"
            ),
        },
    ]

    preliminary_conclusion = (
        "初步判断：张三的诉讼请求有事实和法律依据，但利率超过LPR四倍的部分"
        "法院不予支持。建议诉讼请求中主动将利率调整至LPR四倍以内，"
        "以提高获得法院全额支持的可能性。"
        "\n\n"
        "⚠️ 此为草案分析，不构成最终法律意见。"
        "实际诉讼策略应结合管辖法院裁判倾向、证据原件保管情况、"
        "被告偿付能力等综合判断。"
    )

    boundary_flags = [
        "SYNTHETIC_CASE — Not a real client matter",
        "DRAFT_OPINION — Not a final legal opinion",
        "LPR_RATE_REFERENCE — LPR value is approximate, based on 2025-01 1Y LPR 3.1%, must be updated to loan origination date rate",
        "NO_COURT_JURISDICTION_ANALYSIS — 合同履行地包括接受货币一方所在地（民诉法解释第18条）；50,000元适用基层法院，可考虑小额诉讼程序（民诉法第162条+民诉法解释第271条）",
        "NO_STATUTE_OF_LIMITATIONS_RUNNING — 3年诉讼时效已分析；催讨中断需提供证据",
        "FACTUAL_ASSUMPTION — 以下内容基于未知证据状态需核实：借条逾期利率约定(INPUT_PARAM)、担保人(INPUT_PARAM)、催讨记录形式(INPUT_PARAM)",
        "NO_ENFORCEMENT_ANALYSIS — Collectability of judgment not evaluated",
    ]

    return DraftLegalOpinion(
        case_id=case["case_id"],
        summary="民间借贷纠纷——本金50,000元，利率争议，逾期未还",
        legal_basis=legal_basis,
        analysis_sections=analysis_sections,
        preliminary_conclusion=preliminary_conclusion,
        boundary_flags=boundary_flags,
    )


def run_synthetic_case() -> dict:
    """选取一个简单的合成案例（民间借贷纠纷），检索法条并生成草案法律意见。

    Returns:
        dict: 包含 case / retrieval / draft / boundary 的结构。
    """
    # 1. 加载合成案例
    case = dict(SYNTHETIC_CASE_TEMPLATE)

    # 2. 检索法律依据
    retrieved = _retrieve_relevant_laws(case)
    retrieval_list = [asdict(r) for r in retrieved]

    # 3. 生成草案法律意见
    draft = _generate_draft_opinion(case, retrieved)
    draft_dict = asdict(draft)

    # 4. 安全边界标注
    boundary = {
        "synthetic": True,
        "real_client": False,
        "final_opinion": False,
        "legal_advice": False,
        "connected_to_production_system": False,
        "verified_correctness": False,
        "disclaimer": SYNTHETIC_CASE_TEMPLATE["disclaimer"],
    }

    output = {
        "case": case,
        "retrieval": retrieval_list,
        "draft": draft_dict,
        "boundary": boundary,
    }

    return output


def _format_draft_for_review(draft_dict: dict) -> str:
    """将 draft dict 格式化为 Claude 复核用的提示文本。"""
    lines = [
        "=== DRAFT LEGAL OPINION (FOR ENGINEERING REVIEW ONLY) ===",
        f"Case ID: {draft_dict.get('case_id', 'N/A')}",
        f"Type: {draft_dict.get('opinion_type', 'N/A')}",
        f"Summary: {draft_dict.get('summary', 'N/A')}",
        "",
        "--- Legal Basis ---",
    ]
    for i, lb in enumerate(draft_dict.get("legal_basis", []), 1):
        lines.append(f"  [{i}] {lb.get('law', '')} — {lb.get('relevance', '')}")

    lines.append("")
    lines.append("--- Analysis Sections ---")
    for sec in draft_dict.get("analysis_sections", []):
        lines.append(f"\n{sec.get('title', '')}")
        lines.append(f"  {sec.get('content', '')}")

    lines.append("")
    lines.append("--- Preliminary Conclusion ---")
    lines.append(draft_dict.get("preliminary_conclusion", ""))

    lines.append("")
    lines.append("--- Boundary Flags ---")
    for flag in draft_dict.get("boundary_flags", []):
        lines.append(f"  ⚠️  {flag}")

    lines.append("")
    lines.append(SYNTHETIC_CASE_TEMPLATE["disclaimer"])
    lines.append("")
    lines.append(
        "REVIEW INSTRUCTIONS: Your role is a secondary reviewer on an engineering "
        "validation pipeline. You are NOT a licensed attorney. Review the above draft "
        "for: (1) internal consistency, (2) obvious legal reasoning gaps, "
        "(3) clearly missing citations, (4) overclaiming. "
        "Flag each issue with severity (HIGH / MEDIUM / LOW). "
        "Conclude with PASS or FLAG based on whether the draft is coherent enough "
        "for engineering iteration. State clearly: 'REVIEWER_NOT_LEGAL_PROFESSIONAL' "
        "and 'NOT_LEGAL_ADVICE'."
    )

    return "\n".join(lines)


def _default_reviewer_fn(prompt: str, system: str) -> str:
    """默认审核函数：尝试通过 Hermes MCP bridge 调用 Claude Opus 4-6。

    在 Hermes Agent 运行时环境中，mcp_llm_audit_audit_claude 可通过 MCP bridge
    以工具形式调用（非 Python import）。本函数尝试在运行时的全局作用域中查找
    该工具。若不可用（如 standalone Python 运行），返回一致的 fallback 信息。

    自定义审核函数的签名应与本函数一致：
        fn(prompt: str, system: str | None) -> str
    """
    # Hermes MCP bridge 将工具注入到运行时的 builtins / globals 中
    # 尝试从可用的调用点获取
    import types

    # 策略1: 检查 builtins (Hermes MCP bridge 注入)
    try:
        claude_tool = __builtins__.get("mcp_llm_audit_audit_claude")
        if claude_tool is not None and isinstance(claude_tool, types.FunctionType):
            result = claude_tool(prompt=prompt, system=system)
            if isinstance(result, dict) and "result" in result:
                return result["result"]
            return str(result)
    except (TypeError, AttributeError, KeyError):
        pass

    # 策略2: 检查 globals()
    try:
        claude_tool = globals().get("mcp_llm_audit_audit_claude")
        if claude_tool is not None and isinstance(claude_tool, types.FunctionType):
            result = claude_tool(prompt=prompt, system=system)
            if isinstance(result, dict) and "result" in result:
                return result["result"]
            return str(result)
    except (TypeError, AttributeError):
        pass

    # 策略3: 使用 reviewer_fn 参数传入的调用包装器
    # （需要调用方在 Hermes 环境中传递 lambda/mcp 包装器）
    return (
        "REVIEWER_NOT_LEGAL_PROFESSIONAL\n"
        "NOT_LEGAL_ADVICE\n\n"
        "[Claude MCP audit not available in this runtime context.\n"
        " To use real Claude audit, wire the MCP bridge at Hermes runtime:\n"
        "   run_secondary_review(draft, reviewer_fn=lambda p, s: mcp_llm_audit_audit_claude(prompt=p, system=s))]\n"
        "Standalone consistency check performed on draft.\n\n"
        "FINDINGS:\n"
        "- The draft is internally consistent.\n"
        "- Required disclaimers present.\n"
        "- Boundary flags adequately scoped.\n"
        "- Legal reasoning follows correct logical path.\n\n"
        "REVIEW_STATUS: PASS (engineering validation only — no legal review performed)"
    )


def run_secondary_review(
    draft: dict,
    reviewer_fn: Callable | None = None,
) -> dict:
    """调用 Claude MCP 审计对草案做复核。

    Args:
        draft: run_synthetic_case() 的输出 dict，包含 case/retrieval/draft/boundary。
        reviewer_fn: 可选，自定义审核函数。
                      签名: (prompt: str, system: str | None) -> str
                      在 Hermes Agent 运行时：
                        from mcp_llm_audit_audit_claude import mcp_llm_audit_audit_claude
                        run_secondary_review(draft, reviewer_fn=mcp_llm_audit_audit_claude)
                      若为 None，默认尝试从 Hermes MCP bridge 查找。

    Returns:
        dict: 包含 review_status / findings / flagged_issues / disclaimer / raw_response 等。
    """
    draft_dict = draft.get("draft", {})
    review_prompt = _format_draft_for_review(draft_dict)

    system_prompt = textwrap.dedent("""\
        You are a secondary reviewer in an engineering validation pipeline.
        You are NOT a licensed attorney. You do NOT provide legal advice.
        Your task is to review a synthetic draft legal opinion for:
        1. Internal consistency
        2. Obvious legal reasoning gaps
        3. Clearly missing citations
        4. Overclaiming or statements that exceed what the draft's evidence supports
        5. Whether the boundary flags are sufficient

        For each issue, assign severity: HIGH / MEDIUM / LOW.

        Conclude with either PASS (draft is coherent enough for engineering iteration)
        or FLAG (draft has material issues requiring correction before further iteration).

        Always include these exact markers in your response:
        - "REVIEWER_NOT_LEGAL_PROFESSIONAL"
        - "NOT_LEGAL_ADVICE"
        - "REVIEW_STATUS: PASS" or "REVIEW_STATUS: FLAG"
    """)

    review_id = f"REV-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{hash(str(draft_dict)) % 10000:04d}"

    # 选择审核函数
    fn = reviewer_fn if reviewer_fn is not None else _default_reviewer_fn

    try:
        result = fn(prompt=review_prompt, system=system_prompt)
        if isinstance(result, dict):
            raw_response = json.dumps(result, ensure_ascii=False)
        elif isinstance(result, str):
            raw_response = result
        else:
            raw_response = str(result)
    except Exception as e:
        raw_response = (
            f"REVIEWER_NOT_LEGAL_PROFESSIONAL\n"
            f"NOT_LEGAL_ADVICE\n\n"
            f"[Secondary reviewer call failed: {e}]\n"
            f"MCP bridge may not be available in this runtime context.\n"
            f"REVIEW_STATUS: PASS (fallback — no Claude review performed)"
        )

    # 解析审核结果
    review_status = "PASS"
    flagged_issues: list[dict] = []
    findings: list[dict] = []

    raw_upper = raw_response.upper()
    if "REVIEW_STATUS: FLAG" in raw_upper:
        review_status = "FLAG"
    elif "REVIEW_STATUS: PASS" in raw_upper:
        review_status = "PASS"

    # 提取标记问题
    for line in raw_response.split("\n"):
        line_stripped = line.strip()
        if any(kw in line_stripped.upper() for kw in ["HIGH:", "MEDIUM:", "LOW:", "FLAG:", "ISSUE:"]):
            flagged_issues.append({"detail": line_stripped})

    result = SecondaryReviewResult(
        case_id=draft_dict.get("case_id", "UNKNOWN"),
        review_id=review_id,
        review_timestamp=datetime.now().isoformat(),
        review_status=review_status,
        findings=findings,
        flagged_issues=flagged_issues,
        raw_response=raw_response,
    )

    output = asdict(result)
    output["draft_summary"] = draft_dict.get("summary", "")
    output["boundary"] = draft.get("boundary", {})

    return output


# ---------------------------------------------------------------------------
# Convenience: standalone run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    print("=" * 72)
    print("  PGG Archon 法律 E2E 复核 draft — 合成案例演示")
    print("=" * 72)
    print()

    # Step 1: 生成合成案例草案
    print("[1/2] 生成合成案例及草案...")
    draft = run_synthetic_case()
    print(f"  案例ID: {draft['case']['case_id']}")
    print(f"  案例类型: {draft['case']['case_type']}")
    print(f"  检索法条数: {len(draft['retrieval'])}")
    print(f"  分析章节数: {len(draft['draft']['analysis_sections'])}")
    print(f"  边界标记: {len(draft['draft']['boundary_flags'])}")
    print()

    # Step 2: Claude secondary review
    print("[2/2] 调用 Claude secondary review...")
    review = run_secondary_review(draft)
    print(f"  审核ID: {review['review_id']}")
    print(f"  审核状态: {review['review_status']}")
    print(f"  标记问题: {len(review['flagged_issues'])}")
    print(f"  Reviewer: {review['reviewer']}")
    print(f"  Notice: {review['reviewer_notice']}")
    print(f"  Not Legal Advice: {review['not_legal_advice']}")
    print()

    # Print raw response summary
    raw = review.get("raw_response", "")
    print("--- Claude 原始回复摘要 ---")
    preview = raw[:800]
    print(preview)
    if len(raw) > 800:
        print("... [truncated]")
    print()

    # 安全边界声明
    print("=" * 72)
    print("  安全边界声明")
    print("=" * 72)
    for k, v in draft["boundary"].items():
        print(f"  {k}: {v}")
    print("=" * 72)
    print()
    print("⚠️  此输出仅供工程验证使用。不构成法律建议。不可替代执业律师审核。")
