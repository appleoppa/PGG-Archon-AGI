"""PGG remaining gap closure gates.

Creates evidence packets for the five known remaining gaps:
1. eight paper/source route evidence matrix;
2. GeneDB quality audit;
3. multi-day autonomy elapsed sample collector status;
4. external/community benchmark track skeleton;
5. real legal E2E correctness review skeleton.

Boundary: local read-only/packet generation by default; no network, no LLM, no legal correctness proof,
no external benchmark claim, no AGI/T5/ASI claim.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

DB = Path('/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3')
OUTDIR = Path('/Users/appleoppa/.hermes/data/gene-intake-loop/gap-gates')
BOUNDARY = 'local evidence packet gates; not external benchmark/legal correctness/full AGI proof'

PAPER_SOURCES = [
    'Autogenesis AGP', 'ML Intern', 'HERMES GEPA', 'CORAL',
    'Morphogenetic Aspect Networks', 'SkillEvolver + EmbodiSkill',
    'APEX-MOSS-AGI', 'ApexSpiral'
]


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def _write(name: str, obj: dict[str, Any]) -> Path:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    p = OUTDIR / name
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    return p


def genedb_quality_audit(db_path: Path = DB) -> dict[str, Any]:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        total = con.execute('select count(*) from evolution_genes').fetchone()[0]
        by_status = {r['status']: r['n'] for r in con.execute('select status, count(*) n from evolution_genes group by status')}
        dup_hashes = [dict(r) for r in con.execute('select gene_hash, count(*) n from evolution_genes where gene_hash is not null and gene_hash != "" group by gene_hash having n > 1 limit 20')]
        no_fitness = con.execute('select count(*) from evolution_genes where fitness is null or fitness <= 0').fetchone()[0]
        stale_active_pending = [dict(r) for r in con.execute("select gene_id,status,evidence_grade,verification_status,fitness from evolution_genes where status='active' and (verification_status like '%pending%' or evidence_grade like 'C%') limit 30")]
        promotion_ready = [dict(r) for r in con.execute("select gene_id,status,evidence_grade,fitness from evolution_genes where status='candidate' and fitness >= 800 limit 20")]
        status = 'PASS_GENEDB_QUALITY_AUDIT_PACKET' if total > 0 and no_fitness == 0 else 'WATCH_GENEDB_QUALITY_AUDIT_PACKET'
        gaps = []
        if dup_hashes:
            gaps.append('duplicate_gene_hashes_need_review')
        if no_fitness:
            gaps.append('genes_missing_fitness')
        if stale_active_pending:
            gaps.append('stale_active_pending_or_low_evidence_need_review')
        return {
            'schema': 'PGGGeneDBQualityAudit/v1',
            'created_at': _now(),
            'status': status,
            'total': total,
            'by_status': by_status,
            'duplicate_hashes': dup_hashes,
            'missing_or_zero_fitness_count': no_fitness,
            'stale_active_pending_sample': stale_active_pending,
            'promotion_ready_candidates': promotion_ready,
            'gaps': gaps,
            'boundary': BOUNDARY,
        }
    finally:
        con.close()


def source_to_gate_matrix() -> dict[str, Any]:
    # Use existing local evidence only; do not claim external verification.
    matrix = []
    known_partial = {'HERMES GEPA', 'CORAL', 'APEX-MOSS-AGI', 'SkillEvolver + EmbodiSkill'}
    for src in PAPER_SOURCES:
        if src in known_partial:
            status = 'PARTIAL_LOCAL_PATTERN_ABSORBED'
            next_gate = 'paper_repo_source_parity_and_mini_benchmark'
        else:
            status = 'MISSING_SOURCE_TO_GATE_EVIDENCE'
            next_gate = 'github_first_source_lookup_then_arxiv_then_web'
        matrix.append({
            'source': src,
            'status': status,
            'required_chain': ['source_lookup', 'paper_or_repo_readback', 'mechanism_card', 'mini_benchmark', 'candidate_gene', 'promotion_gate'],
            'next_gate': next_gate,
        })
    return {
        'schema': 'PGGSourceToGateMatrix/v1',
        'created_at': _now(),
        'status': 'WATCH_SOURCE_TO_GATE_NOT_FULLY_CLOSED',
        'matrix': matrix,
        'closed_count': 0,
        'partial_count': sum(1 for r in matrix if r['status'].startswith('PARTIAL')),
        'missing_count': sum(1 for r in matrix if r['status'].startswith('MISSING')),
        'boundary': BOUNDARY,
    }


def autonomy_elapsed_sample_status() -> dict[str, Any]:
    # Start/refresh collector marker. Multi-day requires elapsed days; not complete yet.
    state_dir = OUTDIR / 'autonomy_elapsed_samples'
    state_dir.mkdir(parents=True, exist_ok=True)
    sample = {
        'ts': _now(),
        'event': 'collector_heartbeat',
        'source': 'gene_intake_launchd_runner',
        'status': 'COLLECTING',
    }
    with (state_dir / 'samples.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(sample, ensure_ascii=False) + '\n')
    samples = (state_dir / 'samples.jsonl').read_text(encoding='utf-8').splitlines()
    return {
        'schema': 'PGGAutonomyElapsedSampleStatus/v1',
        'created_at': _now(),
        'status': 'WATCH_COLLECTING_NEEDS_MULTI_DAY_ELAPSED_SAMPLES',
        'sample_count': len(samples),
        'sample_path': str(state_dir / 'samples.jsonl'),
        'required': '>=2 distinct elapsed days before multi-day claim',
        'boundary': BOUNDARY,
    }


def external_benchmark_track_packet() -> dict[str, Any]:
    return {
        'schema': 'PGGExternalBenchmarkTrack/v1',
        'created_at': _now(),
        'status': 'WATCH_BENCHMARK_TRACK_SKELETON_READY_NO_EXTERNAL_PASS',
        'tracks': [
            {'name': 'AgentSPEX claimed benchmark parity', 'status': 'NOT_RUN_LOCAL', 'next': 'choose small reproducible taskset'},
            {'name': 'software task smoke', 'status': 'LOCAL_HARNESS_NEEDED', 'next': 'deterministic scorer'},
            {'name': 'legal retrieval benchmark', 'status': 'EXISTS_RETRIEVAL_ONLY', 'next': 'correctness reviewer separate'},
        ],
        'must_not_claim': ['official external benchmark pass', 'AGI level increase'],
        'boundary': BOUNDARY,
    }


def legal_e2e_correctness_review_packet() -> dict[str, Any]:
    return {
        'schema': 'PGGLegalE2ECorrectnessReview/v1',
        'created_at': _now(),
        'status': 'WATCH_REVIEW_TRACK_DEFINED_NOT_LEGAL_CORRECTNESS_PROOF',
        'required_lanes': ['CMS case packet', 'evidence management', 'local legal KB retrieval', 'draft answer', 'secondary reviewer receipt', 'human/legal professional review'],
        'current_boundary': 'existing bounded legal E2E is retrieval benchmark only; not correctness proof',
        'next_gate': 'run one non-client synthetic case through full trusted workflow with reviewer receipt',
        'boundary': BOUNDARY,
    }


def run_all() -> dict[str, Any]:
    outputs = {
        'source_to_gate': source_to_gate_matrix(),
        'genedb_quality': genedb_quality_audit(),
        'autonomy_elapsed': autonomy_elapsed_sample_status(),
        'external_benchmark': external_benchmark_track_packet(),
        'legal_e2e_correctness': legal_e2e_correctness_review_packet(),
    }
    paths = {name: str(_write(f'{name}.json', obj)) for name, obj in outputs.items()}
    status = 'WATCH_REMAINING_GAPS_PACKETIZED_NOT_CLOSED'
    return {
        'schema': 'PGGRemainingGapClosureGates/v1',
        'created_at': _now(),
        'status': status,
        'outputs': outputs,
        'paths': paths,
        'boundary': BOUNDARY,
    }


if __name__ == '__main__':
    print(json.dumps(run_all(), ensure_ascii=False, indent=2))
