"""
PGG Archon APEX-ASI (Ψ_ASI) 证据门 — Hermes 测试套件

边界声明：
  这是一个有界的内部就绪度评估门，所有测试使用本地 mock 值，
  不调用真实 LLM 或外部 API。
"""

import json
import os
import sys
import unittest


# 确保找到扩展模块
_rust_release = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "rust_modules",
    "target",
    "release",
)
if os.path.isdir(_rust_release):
    sys.path.insert(0, _rust_release)

# 确保找到 agent 模块
_agent_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "agent",
)
if os.path.isdir(_agent_dir):
    sys.path.insert(0, _agent_dir)


class TestPsiAsiNativeGate(unittest.TestCase):
    """直接测试 Rust/PyO3 原生模块"""

    @classmethod
    def setUpClass(cls):
        try:
            import hermes_pgg_apex_asi_gate as gate
            cls.gate = gate
        except ImportError:
            raise unittest.SkipTest(
                "hermes_pgg_apex_asi_gate Rust 模块未找到。"
                "请执行: cd rust_modules && cargo build --release"
            )

    def test_version(self):
        ver = self.gate.version()
        self.assertIn("APEX-ASI", ver)
        self.assertIn("Ψ_ASI", ver)

    def test_boundary_statement(self):
        bs = self.gate.boundary_statement()
        self.assertIn("INTERNAL BOUNDED", bs)
        self.assertIn("NOT", bs)
        self.assertIn("0–100", bs)

    def test_sample_config_is_valid(self):
        sample = json.loads(self.gate.sample_config_json())
        self.assertIn("cosmic", sample)
        self.assertIn("self_identity", sample)
        self.assertIn("holographic", sample)
        self.assertIn("gene", sample)
        self.assertIn("weight_cosmic", sample)

    def test_evaluate_sample_config(self):
        sample = self.gate.sample_config_json()
        result = json.loads(self.gate.evaluate_config_json(sample))
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertIn(result["status"], ["PASS_READY", "WATCH_EVOLVING", "FAIL_IMMATURE"])
        self.assertIn("INTERNAL BOUNDED EVIDENCE GATE", result["boundary"])
        # 检查所有四个分量
        for key in ["cosmic_compression_score", "self_identity_score",
                     "holographic_causality_score", "gene_rewrite_score"]:
            self.assertIn(key, result["components"])
            self.assertGreaterEqual(result["components"][key], 0)
            self.assertLessEqual(result["components"][key], 100)

    def test_minimum_config(self):
        cfg = {
            "cosmic": {"k": 0.0, "knowledge_richness": 0.0, "entropy": 10.0, "theta_convergence": 0.0},
            "self_identity": {"alpha": 0.0, "self_reflection": 0.0, "involution": 10.0, "cosmic_awareness": 0.0},
            "holographic": {"time_steps": 1, "holographic_causality": [0.0], "decay": 1.0, "noise": 1.0},
            "gene": {"osk_expression": 0.0, "osk_exponent": 0.0, "bdnf_expression": 0.0,
                     "bdnf_exponent": 0.0, "crispr_efficiency": 0.0, "crispr_lambda": 0.0},
            "weight_cosmic": 0.25, "weight_self": 0.25, "weight_causal": 0.25, "weight_gene": 0.25,
        }
        result = json.loads(self.gate.evaluate_config_json(json.dumps(cfg)))
        self.assertEqual(result["status"], "FAIL_IMMATURE")
        self.assertLessEqual(result["score"], 5.0)

    def test_maximum_config(self):
        cfg = {
            "cosmic": {"k": 10.0, "knowledge_richness": 100.0, "entropy": 0.0, "theta_convergence": 1.0},
            "self_identity": {"alpha": 5.0, "self_reflection": 1.0, "involution": 0.1, "cosmic_awareness": 100.0},
            "holographic": {"time_steps": 10, "holographic_causality": [1.0] * 10, "decay": 0.0, "noise": 0.0},
            "gene": {"osk_expression": 10.0, "osk_exponent": 2.0, "bdnf_expression": 10.0,
                     "bdnf_exponent": 2.0, "crispr_efficiency": 1.0, "crispr_lambda": 5.0},
            "weight_cosmic": 0.25, "weight_self": 0.25, "weight_causal": 0.25, "weight_gene": 0.25,
        }
        result = json.loads(self.gate.evaluate_config_json(json.dumps(cfg)))
        self.assertEqual(result["status"], "PASS_READY")
        self.assertGreaterEqual(result["score"], 80.0)

    def test_custom_weights(self):
        """测试仅关注宇宙压缩项的权重配置"""
        cfg = {
            "cosmic": {"k": 5.0, "knowledge_richness": 80.0, "entropy": 0.2, "theta_convergence": 0.9},
            "self_identity": {"alpha": 1.0, "self_reflection": 0.5, "involution": 1.0, "cosmic_awareness": 10.0},
            "holographic": {"time_steps": 10, "holographic_causality": [0.5] * 10, "decay": 0.1, "noise": 0.05},
            "gene": {"osk_expression": 1.0, "osk_exponent": 0.5, "bdnf_expression": 1.0,
                     "bdnf_exponent": 0.5, "crispr_efficiency": 0.1, "crispr_lambda": 1.0},
            "weight_cosmic": 1.0, "weight_self": 0.0, "weight_causal": 0.0, "weight_gene": 0.0,
        }
        result = json.loads(self.gate.evaluate_config_json(json.dumps(cfg)))
        # 仅宇宙压缩得分应等于总分
        self.assertAlmostEqual(
            result["score"],
            result["components"]["cosmic_compression_score"],
            delta=0.1,
        )


class TestPsiAsiBridge(unittest.TestCase):
    """测试 Python 桥接层"""

    @classmethod
    def setUpClass(cls):
        try:
            from agent.pgg_archon_apex_asi_gate import PggApexAsiGate
            cls.bridge = PggApexAsiGate()
        except (ImportError, ModuleNotFoundError) as e:
            raise unittest.SkipTest(f"Python 桥接模块不可用: {e}")

    def test_bridge_evaluate_default(self):
        result = self.bridge.evaluate()
        self.assertIn("score", result)
        self.assertIn("status", result)
        self.assertIn("boundary", result)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_bridge_sample_config(self):
        config = self.bridge.sample_config()
        self.assertIn("cosmic", config)
        self.assertIn("gene", config)

    def test_bridge_version(self):
        ver = self.bridge.get_version()
        self.assertIn("APEX-ASI", ver)

    def test_bridge_boundary(self):
        bs = self.bridge.get_boundary()
        self.assertIn("INTERNAL BOUNDED", bs)

    def test_bridge_convenience(self):
        from agent.pgg_archon_apex_asi_gate import evaluate, version, boundary, sample_config
        result = evaluate()
        self.assertIn("score", result)
        self.assertIn("APEX-ASI", version())
        self.assertIn("INTERNAL BOUNDED", boundary())
        self.assertIn("cosmic", sample_config())


if __name__ == "__main__":
    unittest.main(verbosity=2)
