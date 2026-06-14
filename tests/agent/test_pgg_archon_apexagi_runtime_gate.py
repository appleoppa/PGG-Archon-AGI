"""
PGG Archon ApexAGI Runtime Gate — Hermes 测试套件

边界声明：
  这是一个有界的内部就绪度评估门，所有测试使用本地 mock 值，
  不调用真实 LLM 或外部 API。
"""

import json
import os
import sys
import unittest


# 确保找到 agent 模块
_agent_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "agent",
)
if os.path.isdir(_agent_dir):
    sys.path.insert(0, _agent_dir)


class TestApexAgiNativeGate(unittest.TestCase):
    """直接测试 Rust/PyO3 原生模块"""

    @classmethod
    def setUpClass(cls):
        try:
            import hermes_pgg_apexagi_runtime_gate as gate
            cls.gate = gate
        except ImportError:
            raise unittest.SkipTest(
                "hermes_pgg_apexagi_runtime_gate Rust 模块未找到。"
                "请执行: cd rust_modules && cargo build --release"
            )

    def test_wrapper_version(self):
        w = self.gate.PggApexAgiWrapper()
        ver = w.version()
        self.assertEqual(ver, "0.2.0")

    def test_wrapper_boundary_statement(self):
        w = self.gate.PggApexAgiWrapper()
        bs = w.boundary_statement()
        self.assertIn("INTERNAL BOUNDED EVIDENCE GATE", bs)
        self.assertIn("NOT", bs)
        self.assertIn("ApexAGI", bs)

    def test_wrapper_sample(self):
        w = self.gate.PggApexAgiWrapper()
        sample = json.loads(w.sample())
        self.assertIn("O", sample)
        self.assertIn("P7", sample)
        self.assertIn("T", sample)
        self.assertIn("Vt", sample)
        self.assertIn("Au", sample)
        self.assertTrue(sample["O"]["active"])
        self.assertEqual(len(sample["P7"]), 7)

    def test_wrapper_evaluate_default(self):
        w = self.gate.PggApexAgiWrapper()
        result = json.loads(w.evaluate())
        self.assertIn("score", result)
        self.assertIn("status", result)
        self.assertIn("components", result)
        self.assertIn("gaps", result)
        self.assertIn("boundary", result)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertIn(result["status"], ["PASS", "WATCH_EVOLVING", "BLOCKED"])
        # Verify all 5 components exist
        for key in ["O", "P7", "T", "Vt", "Au"]:
            self.assertIn(key, result["components"])

    def test_wrapper_evaluate_custom(self):
        w = self.gate.PggApexAgiWrapper()
        cfg = {
            "O": {"active": True, "problem_id_capability": 100.0, "task_batch_capability": 100.0, "scheduling_capability": 100.0},
            "P7": {"identify": 100.0, "plan": 100.0, "review": 100.0, "implement": 100.0, "code_review": 100.0, "verify": 100.0, "judge": 100.0},
            "T": {"pi_bridge": True, "dbexplain_bridge": True, "cubesandbox_bridge": True, "git_pr_pipeline": True},
            "Vt": {"container_runtime_ready": True, "replay_protocol_designed": True, "verification_harness": True},
            "Au": {"user_authorization_gate": True, "hot_switch_protocol": True, "rollback_plan": True},
        }
        result = json.loads(w.evaluate_config(json.dumps(cfg)))
        self.assertEqual(result["status"], "PASS")
        self.assertGreaterEqual(result["score"], 99.0)

    def test_wrapper_minimal_config(self):
        w = self.gate.PggApexAgiWrapper()
        cfg = {
            "O": {"active": False, "problem_id_capability": 0.0, "task_batch_capability": 0.0, "scheduling_capability": 0.0},
            "P7": {"identify": 0.0, "plan": 0.0, "review": 0.0, "implement": 0.0, "code_review": 0.0, "verify": 0.0, "judge": 0.0},
            "T": {"pi_bridge": False, "dbexplain_bridge": False, "cubesandbox_bridge": False, "git_pr_pipeline": False},
            "Vt": {"container_runtime_ready": False, "replay_protocol_designed": False, "verification_harness": False},
            "Au": {"user_authorization_gate": False, "hot_switch_protocol": False, "rollback_plan": False},
        }
        result = json.loads(w.evaluate_config(json.dumps(cfg)))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertLessEqual(result["score"], 5.0)


class TestApexAgiBridge(unittest.TestCase):
    """测试 Python 桥接层"""

    @classmethod
    def setUpClass(cls):
        try:
            from agent.pgg_archon_apexagi_runtime_gate import ApexAgiP7Pipeline
            cls.bridge = ApexAgiP7Pipeline()
        except (ImportError, ModuleNotFoundError) as e:
            raise unittest.SkipTest(f"Python 桥接模块不可用: {e}")

    def test_bridge_evaluate_default(self):
        result = self.bridge.evaluate()
        self.assertIn("score", result)
        self.assertIn("status", result)
        self.assertIn("components", result)
        self.assertIn("boundary", result)
        self.assertIn("method", result)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_bridge_evaluate_custom(self):
        cfg = {
            "O": {"active": True, "problem_id_capability": 100, "task_batch_capability": 100, "scheduling_capability": 100},
            "P7": {"identify": 100, "plan": 100, "review": 100, "implement": 100, "code_review": 100, "verify": 100, "judge": 100},
            "T": {"pi_bridge": True, "dbexplain_bridge": True, "cubesandbox_bridge": True, "git_pr_pipeline": True},
            "Vt": {"container_runtime_ready": True, "replay_protocol_designed": True, "verification_harness": True},
            "Au": {"user_authorization_gate": True, "hot_switch_protocol": True, "rollback_plan": True},
        }
        result = self.bridge.evaluate(cfg)
        self.assertEqual(result["status"], "PASS")
        # Pure Python may have slightly different O score calculation
        self.assertIn("method", result)

    def test_bridge_sample_config(self):
        config = self.bridge.sample_config()
        self.assertIn("O", config)
        self.assertIn("P7", config)
        self.assertIn("T", config)
        self.assertIn("Vt", config)
        self.assertIn("Au", config)

    def test_bridge_version(self):
        ver = self.bridge.version()
        self.assertTrue(ver.startswith("0.2.0"))

    def test_bridge_boundary(self):
        bs = self.bridge.boundary()
        self.assertIn("INTERNAL BOUNDED", bs)

    def test_bridge_native_vs_py(self):
        """Default and custom eval use native when available; default carries runtime evidence."""
        result_default = self.bridge.evaluate()
        if hasattr(self.bridge, '_wrapper') and self.bridge._wrapper:
            self.assertEqual(result_default["method"], "native_rust_runtime_evidence")
            self.assertIn("evidence_config", result_default)
        result_custom = self.bridge.evaluate({"O": {"active": True, "problem_id_capability": 50, "task_batch_capability": 50, "scheduling_capability": 50}, "P7": {"identify": 50, "plan": 50, "review": 50, "implement": 50, "code_review": 50, "verify": 50, "judge": 50}, "T": {"pi_bridge": False, "dbexplain_bridge": False, "cubesandbox_bridge": False, "git_pr_pipeline": False}, "Vt": {"container_runtime_ready": False, "replay_protocol_designed": False, "verification_harness": False}, "Au": {"user_authorization_gate": False, "hot_switch_protocol": False, "rollback_plan": False}})
        if hasattr(self.bridge, '_wrapper') and self.bridge._wrapper:
            self.assertEqual(result_custom["method"], "native_rust_runtime_evidence")
        else:
            self.assertEqual(result_custom["method"], "pure_python")

    def test_bridge_p7_dryrun(self):
        result = self.bridge.run_p7_pipeline("Test task", dry_run=True)
        self.assertIn("task", result)
        self.assertIn("stages", result)
        self.assertEqual(result["task"], "Test task")
        self.assertEqual(len(result["stages"]), 7)
        # All stages should be SIMULATED
        for stage_name, stage_info in result["stages"].items():
            self.assertEqual(stage_info["status"], "SIMULATED")
            self.assertTrue(stage_info["dry_run"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
