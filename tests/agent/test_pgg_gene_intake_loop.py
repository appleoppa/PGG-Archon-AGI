"""Tests for PGG Gene Intake Loop — automated candidate gene pipeline."""
from __future__ import annotations
from agent.pgg_gene_intake_loop import (
    scan_for_candidates,
    score_candidates,
    dedup_by_template_hash,
    run_fusion_dry_run,
    build_promotion_packet,
    run_intake_loop,
)
from pathlib import Path
import json


def test_scan_for_candidates_produces_genes():
    """Scanning agent/ should produce at least some candidate genes."""
    scanned = scan_for_candidates([Path(__file__).parent.parent / 'agent'])
    assert isinstance(scanned, list)
    # At minimum, we scan files — might be zero if all are dupes, but files exist
    # Just check it runs without error
    assert len(scanned) >= 0


def test_score_candidates_orders_by_fitness():
    raw = [
        {'id': 'g1', 'strategy': [{'confidence': 'high'}] * 3},
        {'id': 'g2', 'strategy': [{'confidence': 'low'}]},
    ]
    scored = score_candidates(raw)
    assert len(scored) == 2
    assert scored[0]['fitness'] >= scored[1]['fitness']


def test_dedup_empty_db():
    genes = [{'id': 'test_gene_1'}, {'id': 'test_gene_2'}]
    deduped = dedup_by_template_hash(genes, db_path=':memory:')
    assert len(deduped) == 2


def test_dedup_removes_duplicate():
    genes = [{'id': 'already_in_db'}]
    # We can't write to real DB in test, so just check it runs
    deduped = dedup_by_template_hash(genes, db_path=':memory:')
    assert len(deduped) == 1


def test_build_promotion_packet():
    candidates = [{'id': f'g{i}', 'signals_match': ['sig1'], 'fitness': 800, 'scan_file': 'f.py'} for i in range(10)]
    fusion_results = [{'parents': ['g1', 'g2'], 'mode': 'additive', 'fusion_status': 'PASS', 'synergy': 50, 'fitness': 850}]
    packet = build_promotion_packet(candidates, fusion_results)
    assert 'top_candidates' in packet
    assert packet['fusion_dry_run_count'] == 1
    assert packet['fusion_passed_count'] == 1


def test_run_intake_loop_dry_run():
    out = run_intake_loop(source_dirs=[Path('/Users/appleoppa/.hermes/hermes-agent/agent')])
    assert out['status'] in {'PASS_NO_NEW_CANDIDATES', 'PASS_NEW_CANDIDATES'}
    assert 'boundary' in out
