"""Tests for PGG Archon AgentSPEX 声明式规约解析器.

测试覆盖:
  - 标准 YAML 解析
  - 残缺 YAML
  - 缺少必填字段
  - 空步骤列表
  - validate() 完整性检查
  - spec_to_steps() 展平
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from agent.pgg_archon_declarative_spec_parser import (
    parse,
    spec_to_steps,
    validate,
)

# ===================================================================
# Fixtures
# ===================================================================

SAMPLE_YAML = """\
workflow:
  name: test_workflow
  version: "1.0"
  steps:
    - name: step1
      type: llm_call
      model: gpt-5.5
      input: user_message
      output: response
    - name: step2
      type: api_call
      input: step1.output
      output: api_result
    - name: search
      type: web_search
      output: raw_results
    - name: summarize
      type: llm_call
      input: raw_results
      output: summary
  control:
    - name: check_result
      type: branch
      condition: "response contains 'error'"
      if_true: retry
      if_false: step2
  parallel:
    - name: research
      steps: [search, summarize]
  modules:
    - name: retry_module
      steps: [retry]
  state:
    variables:
      user_message: string
      response: string
      retry_count: integer
"""

MINIMAL_YAML = """\
workflow:
  name: minimal
  steps: []
"""

TRUNCATED_YAML = """\
workflow:
  name: no_steps
"""

EMPTY_YAML = ""

NOT_DICT_YAML = "just a string"

STEPS_ONLY_YAML = """\
workflow:
  name: steps_only
  steps:
    - name: greet
      type: echo
      input: hello
"""

WITH_LOOP_YAML = """\
workflow:
  name: loop_workflow
  steps:
    - name: fetch
      type: api_call
      output: items
    - name: process
      type: transform
      input: items
  control:
    - name: iterate
      type: loop
      loop_var: item
      loop_over: items
      if_true: process
  state:
    variables:
      items: list
"""


# ===================================================================
# parse() — 标准 YAML
# ===================================================================


class TestParseStandardYaml:
    """标准 YAML 解析测试。"""

    def test_returns_correct_schema(self):
        result = parse(SAMPLE_YAML)
        assert result["schema"] == "PGGSpeParserOutput/v1"

    def test_valid_is_true(self):
        result = parse(SAMPLE_YAML)
        assert result["valid"] is True

    def test_no_validation_errors(self):
        result = parse(SAMPLE_YAML)
        assert result["validation_errors"] == []

    def test_boundary_declaration(self):
        result = parse(SAMPLE_YAML)
        assert "NOT a workflow execution engine" in result["boundary"]
        assert "no LLM/network calls" in result["boundary"]
        assert "local-only" in result["boundary"]

    def test_w_has_five_components(self):
        result = parse(SAMPLE_YAML)
        w = result["parsed"]["W"]
        assert set(w.keys()) == {"T", "C", "P", "M", "S"}

    def test_typed_steps_T(self):
        result = parse(SAMPLE_YAML)
        t = result["parsed"]["W"]["T"]
        assert len(t) == 4
        assert t[0]["name"] == "step1"
        assert t[0]["type"] == "llm_call"
        assert t[0]["model"] == "gpt-5.5"
        assert t[0]["input"] == "user_message"
        assert t[0]["output"] == "response"
        assert t[1]["name"] == "step2"
        assert t[2]["name"] == "search"
        assert t[3]["name"] == "summarize"

    def test_control_flow_C(self):
        result = parse(SAMPLE_YAML)
        c = result["parsed"]["W"]["C"]
        assert len(c) == 1
        assert c[0]["name"] == "check_result"
        assert c[0]["type"] == "branch"
        assert c[0]["condition"] == "response contains 'error'"
        assert c[0]["if_true"] == "retry"
        assert c[0]["if_false"] == "step2"

    def test_parallel_P(self):
        result = parse(SAMPLE_YAML)
        p = result["parsed"]["W"]["P"]
        assert len(p) == 1
        assert p[0]["name"] == "research"
        assert p[0]["steps"] == ["search", "summarize"]

    def test_modules_M(self):
        result = parse(SAMPLE_YAML)
        m = result["parsed"]["W"]["M"]
        assert len(m) == 1
        assert m[0]["name"] == "retry_module"
        assert m[0]["steps"] == ["retry"]

    def test_state_S(self):
        result = parse(SAMPLE_YAML)
        s = result["parsed"]["W"]["S"]
        assert "variables" in s
        assert s["variables"]["user_message"] == "string"
        assert s["variables"]["response"] == "string"
        assert s["variables"]["retry_count"] == "integer"


# ===================================================================
# parse() — 边界/异常情况
# ===================================================================


class TestParseEdgeCases:
    """边界与异常测试。"""

    def test_minimal_workflow(self):
        result = parse(MINIMAL_YAML)
        assert result["valid"] is True
        assert result["parsed"]["W"]["T"] == []

    def test_truncated_missing_steps_defaults_empty(self):
        result = parse(TRUNCATED_YAML)
        assert result["valid"] is True
        assert result["parsed"]["W"]["T"] == []

    def test_empty_yaml_returns_error(self):
        result = parse(EMPTY_YAML)
        assert result["valid"] is False
        assert len(result["validation_errors"]) > 0

    def test_non_dict_yaml_returns_error(self):
        result = parse(NOT_DICT_YAML)
        assert result["valid"] is False

    def test_invalid_yaml_syntax(self):
        result = parse("workflow: [unclosed: bad")
        assert result["valid"] is False

    def test_steps_only_defaults_other_fields(self):
        result = parse(STEPS_ONLY_YAML)
        assert result["valid"] is True
        assert result["parsed"]["W"]["C"] == []
        assert result["parsed"]["W"]["P"] == []
        assert result["parsed"]["W"]["M"] == []
        assert result["parsed"]["W"]["S"] == {}

    def test_with_loop_control(self):
        result = parse(WITH_LOOP_YAML)
        assert result["valid"] is True
        c = result["parsed"]["W"]["C"]
        assert len(c) == 1
        assert c[0]["type"] == "loop"
        assert c[0]["loop_var"] == "item"
        assert c[0]["loop_over"] == "items"

    def test_non_list_steps_errors(self):
        bad = "workflow:\n  steps: not_a_list"
        result = parse(bad)
        assert result["valid"] is False
        assert any("steps" in e for e in result["validation_errors"])

    def test_non_dict_step_is_skipped(self):
        y = "workflow:\n  steps:\n    - name: ok\n      type: t1\n    - just a string\n    - name: ok2\n      type: t2"
        result = parse(y)
        t = result["parsed"]["W"]["T"]
        # valid=False because a step entry was not a dict (validation warning added)
        # but the two valid dict steps are still extracted
        assert len(t) == 2
        assert t[0]["name"] == "ok"
        assert t[1]["name"] == "ok2"

    def test_state_variables_not_dict_errors(self):
        y = "workflow:\n  state:\n    variables: bad"
        result = parse(y)
        assert result["valid"] is False


# ===================================================================
# validate()
# ===================================================================


class TestValidate:
    """validate() 测试。"""

    def test_validate_passed_spec_returns_valid(self):
        spec = parse(SAMPLE_YAML)
        v = validate(spec)
        assert v["valid"] is True

    def test_validate_missing_name_in_step_auto_assigned(self):
        """parse() auto-assigns 'name' as step_N when missing, so validate passes on name."""
        y = "workflow:\n  steps:\n    - type: llm_call"
        spec = parse(y)
        # parse auto-assigns name='step_0' and type='llm_call', so validate reports no missing-field error
        v = validate(spec)
        # validate still reports valid because basic fields are auto-filled
        # (no missing name error, no missing type error)
        assert v["valid"] is True

    def test_validate_missing_type_in_step_auto_assigned(self):
        """parse() auto-assigns 'type' as 'unknown' when missing, so validate passes on type."""
        y = "workflow:\n  steps:\n    - name: foo"
        spec = parse(y)
        v = validate(spec)
        # parse auto-assigns type='unknown', so validate reports no errors
        assert v["valid"] is True

    def test_validate_broken_control_ref(self):
        y = """\
workflow:
  steps:
    - name: step_a
      type: echo
  control:
    - name: br
      type: branch
      if_true: nonexistent_step
"""
        spec = parse(y)
        v = validate(spec)
        assert v["valid"] is False
        assert any("nonexistent_step" in e for e in v["validation_errors"])

    def test_validate_broken_parallel_ref(self):
        y = """\
workflow:
  steps:
    - name: step_a
      type: echo
  parallel:
    - name: grp
      steps: [missing_step]
"""
        spec = parse(y)
        v = validate(spec)
        assert v["valid"] is False
        assert any("missing_step" in e for e in v["validation_errors"])

    def test_validate_not_dict_spec(self):
        v = validate("not a dict")
        assert v["valid"] is False

    def test_validate_wrong_schema(self):
        v = validate({"schema": "wrong/v1", "parsed": {"W": {"T": [], "C": [], "P": [], "M": [], "S": {}}}, "valid": True, "validation_errors": []})
        assert v["valid"] is False

    def test_validate_module_ref_counted_as_valid_target(self):
        y = """\
workflow:
  steps:
    - name: step1
      type: echo
  modules:
    - name: my_mod
      steps: [step1]
  control:
    - name: check
      type: branch
      if_true: my_mod
"""
        spec = parse(y)
        v = validate(spec)
        assert v["valid"] is True


# ===================================================================
# spec_to_steps()
# ===================================================================


class TestSpecToSteps:
    """spec_to_steps() 展平测试。"""

    def test_simple_flat(self):
        spec = parse(STEPS_ONLY_YAML)
        steps = spec_to_steps(spec)
        assert len(steps) == 1
        assert steps[0]["name"] == "greet"
        assert steps[0]["type"] == "echo"

    def test_meta_control_attached(self):
        spec = parse(SAMPLE_YAML)
        steps = spec_to_steps(spec)
        # step1 不应有 control 附加（check_result 的 target 是 retry/step2）
        for s in steps:
            meta = s.get("_meta", {})
            if s["name"] == "step1":
                # step1 不在 control 的 if_true/if_false 中，但按 name 查找会匹配吗？
                # 当前实现按 name == control.name 匹配，而不是 target
                # check_result.name != step1，所以不应匹配
                assert "control" not in meta or meta["control"] is None
            if s["name"] == "step2":
                # step2 被 check_result 的 if_false 引用
                # 但当前实现只按 control.name == step_name 匹配，所以这里不匹配
                pass

    def test_empty_spec_returns_empty_list(self):
        assert spec_to_steps({}) == []

    def test_bad_parsed_returns_empty(self):
        assert spec_to_steps({"parsed": "bad"}) == []

    def test_non_dict_w_returns_empty(self):
        assert spec_to_steps({"parsed": {"W": "bad"}}) == []

    def test_complex_workflow(self):
        spec = parse(SAMPLE_YAML)
        steps = spec_to_steps(spec)
        assert len(steps) == 4
        assert [s["name"] for s in steps] == ["step1", "step2", "search", "summarize"]


# ===================================================================
# 兼容性：测试输出可 JSON 序列化
# ===================================================================


class TestJsonSerializable:
    """确保 parse() 输出可 JSON 序列化。"""

    def test_full_output_serializable(self):
        result = parse(SAMPLE_YAML)
        dumped = json.dumps(result, ensure_ascii=False)
        loaded = json.loads(dumped)
        assert loaded["schema"] == result["schema"]
        assert loaded["valid"] == result["valid"]

    def test_error_output_serializable(self):
        result = parse("bad: [yaml")
        dumped = json.dumps(result, ensure_ascii=False)
        loaded = json.loads(dumped)
        assert loaded["valid"] is False


# ===================================================================
# py_compile 兼容检查 (run via pytest)
# ===================================================================


def test_module_compiles_clean():
    """验证模块可被 Python 编译。"""
    import py_compile
    import tempfile

    src = Path(__file__).resolve().parent.parent.parent / "agent" / "pgg_archon_declarative_spec_parser.py"
    # 用 py_compile 检查语法
    py_compile.compile(str(src), doraise=True)
