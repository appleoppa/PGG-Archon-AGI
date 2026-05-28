from __future__ import annotations

import json
from pathlib import Path

from agent.apex_failure_sample_library import build_failure_sample_library_status
from agent.apex_task_retrospective import build_task_retrospective_status
from agent.pgg_case_experience_bridge import discover_case_experiences, run_case_experience_bridge


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_case_experience_bridge_discovers_two_real_case_reports(tmp_path: Path):
    root = tmp_path / "苹果中枢办案库"
    case1 = root / "PGG-MS-20260528-001"
    _write(
        case1 / "11_生成文书" / "内部办案流程报告.md",
        """# PGG-MS-20260528-001｜内部办案流程报告
案件名称 | 河南民邦诉燕赵财险雇主责任险理赔纠纷
当前阶段 | 正式流程已激活，初轮部门协同已完成，证据门禁Hold
证据管理部 | 流程异常补救完成，原部门调用超时
类案尚未正式实检，不得引用具体案例号
是否可对外交付 | 否
""",
    )
    case2 = root / "002-PGGFW-20260528-原阳县汇金热力有限公司-阳光西湖二期供热费用争议"
    _write(
        case2 / "12_内部报告" / "内部办案报告.md",
        """# 阳光西湖二期供热争议｜内部办案报告
案件编号：PGG-FW-20260528-002
当前Gate | Conditional Go，接近Go
可否对外交付 | 暂不建议直接对外交付
原函629,710.20元 | 不再采用
差额 | 1,800.00元
中枢此前错误使用临时编号 CASE-20260528-081253；正式案号以 PGG-FW-20260528-002 为准。
法律依据正式复核 | 未完成
""",
    )

    cases = discover_case_experiences(root)
    assert {c.case_id for c in cases} == {"PGG-MS-20260528-001", "PGG-FW-20260528-002"}
    events = [c.to_event() for c in cases]
    assert all(e["sensitive_content_stored"] is False for e in events)
    assert any("department_timeout_or_exception" in e["issue_codes"] for e in events)
    assert any("case_number_boundary_violation" in e["issue_codes"] for e in events)
    assert any("amount_closure_required" in e["issue_codes"] for e in events)


def test_case_experience_bridge_writes_sanitized_ledgers(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "cases"
    _write(
        root / "PGG-MS-20260528-001" / "11_生成文书" / "内部办案流程报告.md",
        """# PGG-MS-20260528-001｜内部办案流程报告
当前阶段 | 正式流程已激活，证据门禁Hold
证据管理部 | 流程异常补救完成，原部门调用超时
类案尚未正式实检，不得引用具体案例号
是否可对外交付 | 否
""",
    )
    _write(
        root / "002-PGGFW-20260528-原阳县汇金热力有限公司-阳光西湖二期供热费用争议" / "12_内部报告" / "内部办案报告.md",
        """# 阳光西湖二期供热争议｜内部办案报告
案件编号：PGG-FW-20260528-002
可否对外交付 | 暂不建议直接对外交付
原函629,710.20元 | 不再采用
差额 | 1,800.00元
中枢此前错误使用临时编号 CASE-20260528-081253；正式案号以 PGG-FW-20260528-002 为准。
""",
    )

    summary = run_case_experience_bridge(case_root=root, events_dir=tmp_path / "events", write_ledgers=True)
    assert summary["status"] == "PASS"
    assert summary["case_count"] == 2
    assert summary["event_count"] == 2
    assert summary["failure_appended_count"] >= 4
    assert summary["retrospective_appended_count"] == 2
    assert Path(summary["events_path"]).exists()
    assert build_failure_sample_library_status()["sample_count"] >= 4
    assert build_task_retrospective_status()["retrospective_count"] == 2

    event_lines = Path(summary["events_path"]).read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in event_lines]
    assert all("case_name_hash" in event for event in parsed)
    assert all("raw_content" not in event for event in parsed)
