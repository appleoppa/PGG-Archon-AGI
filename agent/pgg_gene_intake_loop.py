"""PGG Gene Intake Loop — automated candidate gene pipeline.

Scans local code → dedup by source_hash → write candidate → score fitness
→ run additive/multiplicative fusion dry-run → output top-N promotion packet.

Boundary:
- local-only: filesystem + SQLite; no network, no LLM calls;
- dry_run=True by default — no GeneDB writes without explicit --write;
- no Hermes core/provider/scheduler mutation;
- promotion is output packet only; actual GeneDB promotion needs human review.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from agent.pgg_archon_gene_fusion_engine import (
    DEFAULT_DB,
    BOUNDARY as FUSION_BOUNDARY,
    _fitness_from_record,
    fuse_genedb_records,
    insert_fused_gene,
)
from agent.pgg_archon_code_gene_scanner import scan_source

# ── Config ────────────────────────────────────────────────────────────

INTAKE_SOURCE_DIRS = [
    Path('/Users/appleoppa/.hermes/hermes-agent/agent'),
]

SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv',
             '.tox', 'dist', 'build', '.mypy_cache', '.pytest_cache'}

BOUNDARY = (
    'pgg_gene_intake_loop; local-only; dry_run default; '
    'promotion output packet only; no AGI/T5/ASI claim'
)

# ── Helpers ───────────────────────────────────────────────────────────

def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def _source_hash(filepath: str) -> str:
    """Generate a deterministic hash from file content for dedup."""
    try:
        content = Path(filepath).read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]
    except OSError:
        return ''


# ── Core intake steps ─────────────────────────────────────────────────

def scan_for_candidates(
    source_dirs: list[Path] | None = None,
    *,
    dedup_db: str | Path = DEFAULT_DB,
    max_candidates: int = 30,
) -> list[dict[str, Any]]:
    """Scan source dirs for new code, avoiding duplicates by source_hash.

    Returns list of candidate gene dicts (not yet in GeneDB).
    """
    dirs = source_dirs or INTAKE_SOURCE_DIRS
    db = sqlite3.connect(str(dedup_db))
    try:
        # Collect all existing source_hash values from GeneDB
        existing_hashes = set()
        try:
            for row in db.execute('SELECT gene_hash FROM evolution_genes WHERE gene_hash IS NOT NULL'):
                existing_hashes.add(str(row[0]).strip())
        except sqlite3.OperationalError:
            pass  # column might not exist

        candidates: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()  # in-memory dedup for this pass

        for source_dir in dirs:
            if not source_dir.exists():
                continue
            for fpath in sorted(source_dir.rglob('*.py')):
                # Skip private/init files unless they have public content
                if any(skip in str(fpath) for skip in SKIP_DIRS):
                    continue
                if len(candidates) >= max_candidates:
                    break

                sh = _source_hash(str(fpath))
                if sh in existing_hashes or sh in seen_hashes:
                    continue
                seen_hashes.add(sh)

                genes = scan_source(str(fpath))
                for g in genes:
                    g['source_hash'] = sh
                    g['scan_file'] = str(fpath)
                    candidates.append(g)
                    if len(candidates) >= max_candidates:
                        break

        return candidates

    finally:
        db.close()


def score_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach fitness/confidence to candidate genes."""
    scored: list[dict[str, Any]] = []
    for g in candidates:
        strategy = g.get('strategy', [])
        method_count = len(strategy) if isinstance(strategy, list) else 0
        confidences = [s.get('confidence', 'low') for s in strategy if isinstance(s, dict)]
        high_count = sum(1 for c in confidences if c == 'high')
        # Compute fitness: base 500 + 50 per high-confidence method
        base_fitness = min(999, 500 + high_count * 50 + method_count * 10)
        fitness = max(0, min(999, base_fitness))
        g['fitness'] = fitness
        g['intake_score'] = fitness
        g['intake_at'] = _now()
        scored.append(g)
    # Sort by fitness descending
    scored.sort(key=lambda x: -(x.get('fitness', 0) or 0))
    return scored


def dedup_by_template_hash(
    candidates: list[dict[str, Any]],
    *,
    db_path: str | Path = DEFAULT_DB,
) -> list[dict[str, Any]]:
    """Deduplicate candidates against GeneDB gene_hash."""
    db = sqlite3.connect(str(db_path))
    try:
        existing = set()
        try:
            for row in db.execute('SELECT gene_hash FROM evolution_genes WHERE gene_hash IS NOT NULL'):
                h = str(row[0]).strip()
                if h:
                    existing.add(h)
        except sqlite3.OperationalError:
            pass

        # Also dedup by gene_id
        existing_ids = set()
        try:
            for row in db.execute('SELECT gene_id FROM evolution_genes'):
                existing_ids.add(str(row[0]).strip())
        except sqlite3.OperationalError:
            pass

        unique: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()
        seen_ids: set[str] = set()
        for g in candidates:
            gid = g.get('id', '')
            if gid in existing_ids or gid in seen_ids:
                continue
            seen_ids.add(gid)
            unique.append(g)
        return unique
    finally:
        db.close()


def run_fusion_dry_run(
    candidates: list[dict[str, Any]],
    top_n: int = 5,
    db_path: str | Path = DEFAULT_DB,
) -> list[dict[str, Any]]:
    """Run pairwise fusion dry-run on top-N candidates.

    Returns list of fusion output dicts (dry-run only).
    """
    top = candidates[:top_n]
    results: list[dict[str, Any]] = []
    for i in range(len(top)):
        for j in range(i + 1, len(top)):
            pid_a = top[i].get('id', '')
            pid_b = top[j].get('id', '')
            if not pid_a or not pid_b:
                continue
            # additive dry-run
            out_add = fuse_genedb_records(
                [pid_a, pid_b], db_path=db_path, write=False, promote=False, mode='additive',
            )
            results.append({
                'parents': [pid_a, pid_b],
                'mode': 'additive',
                'fusion_status': out_add.get('fusion', {}).get('status'),
                'synergy': out_add.get('fusion', {}).get('synergy'),
                'fitness': out_add.get('fusion', {}).get('offspring_gene', {}).get('fitness'),
            })
            # multiplicative dry-run
            out_mul = fuse_genedb_records(
                [pid_a, pid_b], db_path=db_path, write=False, promote=False, mode='multiplicative',
            )
            results.append({
                'parents': [pid_a, pid_b],
                'mode': 'multiplicative',
                'fusion_status': out_mul.get('fusion', {}).get('status'),
                'synergy': out_mul.get('fusion', {}).get('synergy'),
                'fitness': out_mul.get('fusion', {}).get('offspring_gene', {}).get('fitness'),
            })
    return results


def build_promotion_packet(
    candidates: list[dict[str, Any]],
    fusion_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build top-N promotion packet (read-only, not writing)."""
    top = candidates[:10]
    return {
        'schema': 'PGGGeneIntakePromotionPacket/v1',
        'created_at': _now(),
        'top_candidates': [
            {
                'id': g.get('id', ''),
                'signals': g.get('signals_match', [])[:3],
                'fitness': g.get('fitness', 0),
                'source_file': g.get('scan_file', ''),
            }
            for g in top
        ],
        'fusion_dry_run_count': len(fusion_results),
        'fusion_passed_count': sum(
            1 for r in fusion_results if r.get('fusion_status') == 'PASS'
        ),
        'fusion_results': fusion_results[:20],
        'boundary': BOUNDARY,
    }


def run_intake_loop(
    *,
    source_dirs: list[Path] | None = None,
    db_path: str | Path = DEFAULT_DB,
    write_candidates: bool = False,
    top_n: int = 5,
) -> dict[str, Any]:
    """Run the complete intake loop pipeline (default dry-run)."""
    t0 = time.time()
    # Step 1: scan
    candidates = scan_for_candidates(source_dirs=source_dirs, dedup_db=db_path)
    # Step 2: score
    scored = score_candidates(candidates)
    # Step 3: dedup by template hash
    deduped = dedup_by_template_hash(scored, db_path=db_path)
    if not deduped:
        return {
            'schema': 'PGGGeneIntakeLoop/v1',
            'status': 'PASS_NO_NEW_CANDIDATES',
            'scanned': 0,
            'new_candidates': 0,
            'elapsed_seconds': round(time.time() - t0, 3),
            'boundary': BOUNDARY,
        }
    # Step 4: (optionally write candidates to GeneDB)
    write_info = None
    if write_candidates:
        con = sqlite3.connect(str(db_path))
        try:
            written_count = 0
            for g in deduped[:10]:
                validation = (
                    g.get('validation') or []
                )
                if not validation:
                    validation = ['pending_intake_loop_review']
                gid = g.get('id', '')
                if con.execute(
                    'SELECT 1 FROM evolution_genes WHERE gene_id = ?', (gid,)
                ).fetchone():
                    continue  # skip if already exists (belt-and-suspenders)
                # Insert as candidate
                now_ts = _now()
                source_refs = json.dumps({
                    'source_file': g.get('source_file', ''),
                    'source_hash': g.get('source_hash', ''),
                }, ensure_ascii=False)
                con.execute(
                    '''INSERT OR IGNORE INTO evolution_genes
                    (gene_id,cycle_id,created_at,defect_no,defect_name,gene_name,
                     absorbed_knowledge,source_refs_json,repair_mechanism,
                     severity_rank,apex_variables,gate_type,reusable_rule,
                     status,evidence_grade,verification_status,boundary,gene_hash,fitness)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (
                        gid, 'GENE_INTAKE_LOOP_CYCLE_20260611', now_ts,
                        0, 'automated code scann intake',
                        g.get('id', ''), '',
                        source_refs, str(g.get('strategy', [])),
                        1, '', 'gene_intake_loop',
                        '', 'candidate', 'B (intake loop)',
                        'pending_intake_loop_review', BOUNDARY,
                        g.get('source_hash', ''),
                        g.get('fitness', 500),
                    ),
                )
                written_count += 1
            con.commit()
            write_info = {'written_count': written_count, 'candidate_status': 'candidate'}
        finally:
            con.close()

    # Step 5: fusion dry-run on top candidates
    fusion_results = run_fusion_dry_run(deduped, top_n=top_n, db_path=db_path)
    # Step 6: build promotion packet
    packet = build_promotion_packet(deduped, fusion_results)
    return {
        'schema': 'PGGGeneIntakeLoop/v1',
        'status': 'PASS_NEW_CANDIDATES',
        'scanned': len(candidates),
        'after_dedup': len(deduped),
        'written_to_genedb': write_info,
        'fusion_dry_run_results': fusion_results,
        'promotion_packet': packet,
        'elapsed_seconds': round(time.time() - t0, 3),
        'boundary': BOUNDARY,
    }


__all__ = [
    'scan_for_candidates', 'score_candidates', 'dedup_by_template_hash',
    'run_fusion_dry_run', 'build_promotion_packet', 'run_intake_loop',
]
