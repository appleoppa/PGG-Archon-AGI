"""Focused regression tests for route-chain hard gate source integration."""
from pathlib import Path


def test_conversation_loop_has_route_chain_hard_gate_and_autowrite_hooks():
    src = Path("agent/conversation_loop.py").read_text(encoding="utf-8")
    assert "Route-Chain Evidence Gate hard integration" in src
    assert "hard_enforce" in src
    assert "auto_write_gene_db" in src
    assert "write_route_chain_candidate_to_gene_db" in src
    assert "record_controlled_autonomous_promotion" in src
    assert "不声明AGI完成" in src


def test_route_chain_config_enables_controlled_hard_gate():
    cfg = Path("/Users/appleoppa/.hermes/config.yaml").read_text(encoding="utf-8")
    assert "route_chain_gate:" in cfg
    assert "  execute_for_agi: true" in cfg
    assert "  emit_gene_candidate: true" in cfg
    assert "  hard_enforce: true" in cfg
    assert "  auto_write_gene_db: true" in cfg
    assert "  autonomous_promotion_enabled: true" in cfg
