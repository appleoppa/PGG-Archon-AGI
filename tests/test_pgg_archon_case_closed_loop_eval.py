from pathlib import Path

from agent import pgg_archon_case_closed_loop_eval as mod


def test_infer_case_no_from_filename(tmp_path: Path):
    root = tmp_path / "0006-PGGMS-20260605-测试"
    root.mkdir()
    rels = "正式文书/PGG-MS-20260605-0006-民事起诉状_FINAL_v2.md"
    assert mod.infer_case_no(root, rels) == "PGG-MS-20260605-0006"


def test_find_final_doc_prefers_final_v2(tmp_path: Path):
    a = tmp_path / "PGG-MS-20260605-0006-民事起诉状_FINAL_v1.md"
    b = tmp_path / "PGG-MS-20260605-0006-民事起诉状_FINAL_v2.md"
    a.write_text("a")
    b.write_text("b")
    assert mod.find_final_doc([a, b]) == b


def test_evaluate_case_with_monkeypatched_gates(tmp_path: Path, monkeypatch):
    root = tmp_path / "0005-PGGXS-20260605-测试"
    (root / "PGG-XS-20260605-0005（一审）" / "案件材料").mkdir(parents=True)
    (root / "PGG-XS-20260605-0005（一审）" / "案件过程报告").mkdir(parents=True)
    (root / "PGG-XS-20260605-0005（一审）" / "正式文书").mkdir(parents=True)
    (root / "PGG-XS-20260605-0005（一审）" / "案件材料" / "PGG-XS-20260605-0005-案件原始材料.md").write_text("材料")
    (root / "PGG-XS-20260605-0005（一审）" / "案件过程报告" / "PGG-XS-20260605-0005-CMS流转单.md").write_text("CMS")
    (root / "PGG-XS-20260605-0005（一审）" / "案件过程报告" / "PGG-XS-20260605-0005-证据管理部工作报告.md").write_text("证据")
    (root / "PGG-XS-20260605-0005（一审）" / "案件过程报告" / "PGG-XS-20260605-0005-律法支持部工作报告.md").write_text("法律依据")
    (root / "PGG-XS-20260605-0005（一审）" / "案件过程报告" / "PGG-XS-20260605-0005-刑事辩护部工作报告.md").write_text("分析")
    (root / "PGG-XS-20260605-0005（一审）" / "案件过程报告" / "PGG-XS-20260605-0005-巡视组工作报告.md").write_text("巡视")
    (root / "PGG-XS-20260605-0005（一审）" / "案件过程报告" / "PGG-XS-20260605-0005-审计组工作报告.md").write_text("审计")
    (root / "PGG-XS-20260605-0005（一审）" / "案件过程报告" / "PGG-XS-20260605-0005-三LLM协作流转单.md").write_text("三LLM")
    (root / "PGG-XS-20260605-0005（一审）" / "正式文书" / "PGG-XS-20260605-0005-取保候审申请书草稿.md").write_text("文书")
    monkeypatch.setattr(mod, "run_cms_guard", lambda root, case_type: {"status": "PASS"})
    report = mod.evaluate_case(root, "刑事案件", run_legal_gate=False)
    assert report["gate_passed"] == report["gate_total"]
    assert report["closed_loop_score"] == 1.0
    assert report["cms_guard"]["status"] == "PASS"
