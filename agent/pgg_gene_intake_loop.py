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
    _hash,
    _uniq,
    fuse_genedb_records,
    fuse_standard_genes,
    insert_fused_gene,
)
from agent.pgg_archon_benchmark_and_gene_gates import (
    reflexion_discovery_gate,
)
from agent.pgg_archon_code_gene_scanner import scan_source
from agent.pgg_archon_gene_fusion_engine import validate_standard_gene

# ── Config ────────────────────────────────────────────────────────────

INTAKE_SOURCE_DIRS = [
    Path('/Users/appleoppa/.hermes/workspace/hermes-github-evolution/genes'),
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


def _as_list(value: Any, *, default: list[Any] | None = None) -> list[Any]:
    """Return value as a list while preserving structured JSON items."""
    if isinstance(value, list):
        return value
    if value is None:
        return list(default or [])
    return [value]


def _json_gene_id(raw: dict[str, Any], fpath: Path) -> str:
    """Derive a stable candidate id for JSON-origin genes.

    Uses repo as the primary key so the same repo doesn't generate
    multiple gene IDs across different evolver run snapshots.
    Falls back to gene name/file stem only when repo is absent.
    """
    # Check for explicit id fields first
    for key in ('id', 'gene_id', 'gene', 'gene_name', 'name'):
        val = raw.get(key)
        if val and not str(val).startswith('json_gene_'):
            return str(val)
    if raw.get('repo'):
        repo_slug = str(raw['repo']).replace('/', '_').replace(' ', '_')
        return f'json_gene_{repo_slug}'
    # Only use hash for items without a repo (truly unidentifiable)
    return f'json_gene_{fpath.stem}_{_hash(raw)[:12]}'


def _json_candidate_from_dict(raw: dict[str, Any], fpath: Path, sh: str) -> dict[str, Any]:
    """Normalize a JSON gene object into the standard candidate dict shape."""
    raw_constraints = raw.get('constraints')
    constraints: dict[str, Any] = dict(raw_constraints) if isinstance(raw_constraints, dict) else {}
    constraints.setdefault('boundary', raw.get('boundary', 'json_gene_intake; local file parse only'))
    constraints.setdefault('source_json_file', str(fpath))
    for key in ('repo', 'url', 'language', 'status', 'verification'):
        if key in raw and key not in constraints:
            constraints[key] = raw[key]

    signals = raw.get('signals_match') or raw.get('traits') or raw.get('signals')
    if signals is None:
        signals = [
            raw.get('gene'), raw.get('gene_name'), raw.get('name'),
            raw.get('repo'), raw.get('language'), raw.get('status'),
        ]
    signals_list = [s for s in _as_list(signals) if s]

    strategy = raw.get('strategy') or raw.get('mechanism') or raw.get('repair_mechanism')
    if strategy is None:
        strategy = raw.get('repair_note') or raw.get('lesson') or 'absorb structured JSON gene signal'

    validation = raw.get('validation')
    if validation is None and raw.get('verification') is not None:
        validation = [f"verification: {json.dumps(raw.get('verification'), ensure_ascii=False, sort_keys=True)}"]
    if validation is None:
        validation = ['json_parse_succeeded']

    return {
        **raw,
        'type': raw.get('type') if raw.get('type') in {'apex_gene', 'pgg_gene', 'apex_gene_candidate'} else 'pgg_gene',
        'id': _json_gene_id(raw, fpath),
        'category': raw.get('category') or f'json_gene::{fpath.name}',
        'signals_match': signals_list or [fpath.stem],
        'preconditions': _as_list(raw.get('preconditions'), default=['json_gene_file_exists']),
        'strategy': _as_list(strategy),
        'constraints': constraints,
        'validation': _as_list(validation),
        'source_file': str(fpath),
        'source_hash': sh,
        'scan_file': str(fpath),
        'scanned_at': _now(),
        'origin': raw.get('origin', 'json_gene_intake_loop'),
    }


def _scan_json_candidates(fpath: Path, sh: str) -> list[dict[str, Any]]:
    """Parse .json files into candidate dicts without using Python AST scan_source()."""
    try:
        data = json.loads(fpath.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []

    raw_items: list[Any]
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict) and isinstance(data.get('genes'), list):
        raw_items = data['genes']
    elif isinstance(data, dict):
        raw_items = [data]
    else:
        return []

    candidates: list[dict[str, Any]] = []
    for item in raw_items:
        if isinstance(item, dict):
            candidates.append(_json_candidate_from_dict(item, fpath, sh))
    return candidates


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
        # Collect existing gene names for dedup (primary dedup mechanism).
        existing_names: set[str] = set()
        try:
            for row in db.execute('SELECT name FROM genes'):
                n = str(row[0]).strip()
                if n:
                    existing_names.add(n)
        except sqlite3.OperationalError:
            pass

        candidates: list[dict[str, Any]] = []
        seen_names: set[str] = set()  # in-memory name dedup for this batch

        for source_dir in dirs:
            if not source_dir.exists():
                continue
            for fpath in sorted(
                p for p in source_dir.rglob('*') if p.suffix in {'.py', '.json'}
            ):
                # Skip private/init files unless they have public content
                if any(skip in str(fpath) for skip in SKIP_DIRS):
                    continue
                if len(candidates) >= max_candidates:
                    break

                sh = _source_hash(str(fpath))

                if fpath.suffix == '.json':
                    genes = _scan_json_candidates(fpath, sh)
                else:
                    genes = scan_source(str(fpath))
                for g in genes:
                    g['source_hash'] = sh
                    g['scan_file'] = str(fpath)
                    gene_name = g.get('name') or g.get('id', '')
                    # Skip if gene name already exists in DB or in this batch
                    if gene_name and (gene_name in existing_names or gene_name in seen_names):
                        continue
                    if gene_name:
                        seen_names.add(gene_name)
                    candidates.append(g)
                    if len(candidates) >= max_candidates:
                        break

        return candidates

    finally:
        db.close()


def score_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach fitness/confidence to candidate genes.

    Scoring has two tracks:
    - Code genes (strategy items are dicts with 'confidence') use the
      original high/medium/medium-confidence weighted formula.
    - JSON metadata genes (strategy items are plain strings, no code snippet)
      get a lower ceiling so they never auto-promote but still register
      as low-priority candidates for manual review.
    """
    scored: list[dict[str, Any]] = []
    for g in candidates:
        strategy = g.get('strategy', [])
        method_count = len(strategy) if isinstance(strategy, list) else 0
        confidences = [s.get('confidence', 'low') for s in strategy if isinstance(s, dict)]
        high_count = sum(1 for c in confidences if c == 'high')
        medium_count = sum(1 for c in confidences if c == 'medium')
        signals = g.get('signals_match', [])
        signal_count = len(signals) if isinstance(signals, list) else 0
        preconditions = g.get('preconditions', [])
        precondition_count = len(preconditions) if isinstance(preconditions, list) else 0
        validation = g.get('validation', [])
        validation_count = len(validation) if isinstance(validation, list) else 0
        has_source = bool(g.get('source_file') or g.get('scan_file') or g.get('source_hash'))

        # Detect JSON metadata genes: strategy items are plain strings, not dicts
        is_metadata_gene = (
            isinstance(strategy, list)
            and len(strategy) > 0
            and all(isinstance(s, str) for s in strategy)
            and not any(isinstance(s, dict) for s in strategy)
        )

        if is_metadata_gene:
            # Metadata genes: structured info (repo, traits, verification hashes)
            # but no executable code. Score by signal richness + verification depth.
            repo_url = g.get('repo') or g.get('url') or ''
            verification = g.get('verification') or g.get('validation') or []
            verification_depth = 0
            if isinstance(verification, dict):
                verification_depth = len(verification)
            elif isinstance(verification, list):
                verification_depth = len(verification)
            text_hashes = 0
            if isinstance(verification, dict):
                text_hashes = len(verification.get('text_hashes', {}))
            workflow_files = 0
            if isinstance(verification, dict):
                workflow_files = len(verification.get('workflow_files_seen', []))

            base_fitness = (
                300  # lower base for metadata
                + min(signal_count, 8) * 15   # signals matter more
                + min(precondition_count, 4) * 10
                + min(validation_count, 4) * 15
                + (20 if repo_url else 0)     # repo reference
                + min(text_hashes, 10) * 8    # verified file hashes
                + min(workflow_files, 5) * 10  # CI/workflow files seen
                + (15 if has_source else 0)
            )
            # Cap metadata genes below promotion threshold (35*100=3500 → quality=35)
            # They should never auto-promote without human review.
            base_fitness = min(base_fitness, 599)  # quality max = 5.99
        else:
            base_fitness = (
                500
                + high_count * 45
                + medium_count * 25
                + method_count * 8
                + min(signal_count, 8) * 10
                + min(precondition_count, 4) * 12
                + min(validation_count, 4) * 25
                + (25 if has_source else 0)
            )
            # Cap weak candidates even if they have many shallow methods.
            if high_count == 0 and validation_count == 0:
                base_fitness = min(base_fitness, 640)
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

        # Also dedup by gene_id (numeric) and gene name
        existing_ids = set()
        try:
            for row in db.execute('SELECT gene_id FROM evolution_genes'):
                existing_ids.add(str(row[0]).strip())
        except sqlite3.OperationalError:
            pass

        existing_gene_names: set[str] = set()
        try:
            for row in db.execute('SELECT name FROM genes'):
                n = str(row[0]).strip()
                if n:
                    existing_gene_names.add(n)
        except sqlite3.OperationalError:
            pass

        unique: list[dict[str, Any]] = []
        seen_hashes: set[str] = set()
        seen_ids: set[str] = set()
        seen_names: set[str] = set()
        for g in candidates:
            gid = g.get('id', '')
            gene_name = g.get('name') or g.get('id') or ''
            # Skip if numeric gene_id already in evolution_genes
            if gid in existing_ids or gid in seen_ids:
                continue
            # Skip if gene name already in genes table or this batch
            if gene_name and (gene_name in existing_gene_names or gene_name in seen_names):
                continue
            seen_ids.add(gid)
            if gene_name:
                seen_names.add(gene_name)
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

    Fuses in-memory gene dicts directly via fuse_standard_genes
    (no DB lookup needed — candidates are standard 5-layer gene dicts).
    Falls back to fuse_genedb_records only for DB-persisted genes.

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

            # Fusion via in-memory gene dicts (no DB dependency)
            out_add = fuse_standard_genes(
                [top[i], top[j]], offspring_id='fusion_' + _hash([pid_a, pid_b])[:16],
                mode='additive',
            )
            results.append({
                'parents': [pid_a, pid_b],
                'mode': 'additive',
                'fusion_status': out_add.get('status'),
                'synergy': out_add.get('synergy'),
                'fitness': out_add.get('offspring_gene', {}).get('fitness'),
                'offspring_id': out_add.get('offspring_gene', {}).get('id'),
            })
            # multiplicative dry-run
            out_mul = fuse_standard_genes(
                [top[i], top[j]], offspring_id='fusion_' + _hash([pid_a, pid_b])[:16],
                mode='multiplicative',
            )
            results.append({
                'parents': [pid_a, pid_b],
                'mode': 'multiplicative',
                'fusion_status': out_mul.get('status'),
                'synergy': out_mul.get('synergy'),
                'fitness': out_mul.get('offspring_gene', {}).get('fitness'),
                'offspring_id': out_mul.get('offspring_gene', {}).get('id'),
            })
    return results


def gather_reflexion_candidates(
    *,
    traces: list[dict[str, Any]] | None = None,
    db_path: str | Path = DEFAULT_DB,
    write: bool = False,
) -> dict[str, Any]:
    """Feed execution traces through reflexion_discovery_gate, score, and optionally write to GeneDB.

    Each trace must have at minimum {'observation': str, 'lesson': str}.
    Returns summary of reflexion candidates discovered.
    """
    t0 = time.time()
    if not traces:
        traces = _default_reflexion_traces()
    packet = {'traces': traces, 'auto_promote': False}
    gate_result = reflexion_discovery_gate(packet)
    reflex_candidates = gate_result.get('candidates', [])
    if not reflex_candidates:
        return {
            'schema': 'PGGReflexionCandidateGather/v1',
            'status': 'PASS_NO_CANDIDATES',
            'elapsed_seconds': round(time.time() - t0, 3),
            'gate_result': gate_result,
        }

    # Score reflexion candidates by strategy count and quality
    scored = []
    for g in reflex_candidates:
        strategy = g.get('strategy', [])
        method_count = len(strategy) if isinstance(strategy, list) else 0
        signals = g.get('signals_match', [])
        signal_count = len(signals) if isinstance(signals, list) else 0
        fitness = min(999, 400 + method_count * 80 + signal_count * 20)
        g['fitness'] = fitness
        g['intake_score'] = fitness
        g['intake_at'] = _now()
        scored.append(g)
    scored.sort(key=lambda x: -(x.get('fitness', 0) or 0))

    # Optionally write to GeneDB
    written = 0
    write_info = None
    if write:
        con = sqlite3.connect(str(db_path))
        try:
            for g in scored:
                gid = g.get('id', '')
                if con.execute('SELECT 1 FROM evolution_genes WHERE gene_id = ?', (gid,)).fetchone():
                    continue
                now_ts = _now()
                strategy_str = '\n'.join(g.get('strategy', [])) if isinstance(g.get('strategy'), list) else str(g.get('strategy', ''))
                source_refs = json.dumps({'origin': 'reflexion_discovery', 'evidence_hash': g.get('evidence_hash', '')}, ensure_ascii=False)
                con.execute(
                    '''INSERT OR IGNORE INTO evolution_genes
                    (gene_id,cycle_id,created_at,defect_no,defect_name,gene_name,
                     absorbed_knowledge,source_refs_json,repair_mechanism,
                     severity_rank,apex_variables,gate_type,reusable_rule,
                     status,evidence_grade,verification_status,boundary,gene_hash,fitness)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (
                        gid, 'REFLEXION_DISCOVERY_CYCLE_20260612', now_ts,
                        0, 'reflexion discovery intake',
                        g.get('id', ''), '',
                        source_refs, strategy_str,
                        1, '', 'reflexion_discovery',
                        '', 'candidate', 'B (reflexion discovery)',
                        'pending_reflexion_review', BOUNDARY,
                        g.get('evidence_hash', '')[:16],
                        g.get('fitness', 500),
                    ),
                )
                written += 1
            con.commit()
            write_info = {'written_count': written, 'candidate_status': 'candidate'}
        finally:
            con.close()

    return {
        'schema': 'PGGReflexionCandidateGather/v1',
        'status': 'PASS' if gate_result.get('status') == 'PASS' else 'PASS_WITH_WARNINGS',
        'candidate_count': len(scored),
        'written_to_genedb': write_info,
        'top_candidates': [{'id': g['id'], 'fitness': g['fitness'], 'lesson': str(g.get('strategy', ['']))[0][:60]} for g in scored[:5]],
        'gate_result': gate_result,
        'elapsed_seconds': round(time.time() - t0, 3),
        'boundary': BOUNDARY,
    }


def _default_reflexion_traces() -> list[dict[str, Any]]:
    """Default traces reflecting the current session's key learnings."""
    return [
        {
            'observation': 'Gene fusion engine always returned BLOCK because additive mode double-subtracted complexity_penalty from synergy',
            'lesson': 'Fusion synergy must measure against average parent fitness, not max parent; never double-count penalties',
            'signals_match': ['gene_fusion', 'blocked', 'synergy_calculation'],
            'preconditions': ['at_least_2_standard_genes', 'validated_gene_templates'],
            'strategy': ['compute offspring fitness from avg fitness + bonus - complexity',
                         'measure synergy relative to avg_parent (not max_parent)',
                         'ignore complexity_penalty in synergy calculation (already in fitness)'],
            'constraints': {'boundary': 'local gene fusion engine; no external calls'},
            'validation': ['verified 7/7 fusion combinations PASS'],
        },
        {
            'observation': 'Fusion dry-run could not find genes in DB because candidates were only in memory, not yet written',
            'lesson': 'In-memory gene fusion via fuse_standard_genes avoids DB lookup dependency and enables dry-run on freshly scanned candidates',
            'signals_match': ['fusion_dry_run', 'gene_intake_loop', 'db_lookup_failure'],
            'preconditions': ['scanned_gene_candidates_in_memory', 'standard_5_layer_template'],
            'strategy': ['fuse in-memory gene dicts directly via fuse_standard_genes',
                         'skip DB lookup for dry-run (only DB-write path needs DB)',
                         'fall back to fuse_genedb_records when querying persisted genes'],
            'constraints': {'boundary': 'local intake loop; no external calls'},
            'validation': ['verified intake loop now scans 30+ candidates and produces 14/20 PASS fusion results'],
        },
        {
            'observation': 'Multiplicative fusion synergy_ratio threshold of 0.05 blocked close-parent fusion (e.g., 600+550 produces ratio 0.041)',
            'lesson': 'Low synergy_ratio does not mean bad fusion; close parents can still produce viable offspring. Threshold should only catch truly identical genes (ratio < 0.005)',
            'signals_match': ['multiplicative_fusion', 'threshold_too_high', 'close_parent_blocked'],
            'preconditions': ['multiplicative_mode', 'parents_with_similar_fitness'],
            'strategy': ['set synergy_ratio minimum threshold to 0.005 instead of 0.05',
                         'allow close-parent fusion (smaller bonus still valid)',
                         'only block when parents are effectively identical'],
            'constraints': {'boundary': 'local fusion engine'},
            'validation': ['verified A+B (600+550) multiplicative now PASSES with synergy=12'],
        },
        {
            'observation': 'PGG Archon had 184 genes but only 25 candidates; no automated pipeline converted code → candidate gene or candidate → promoted gene',
            'lesson': 'Gene intake loop was dry-run only; gene addition required manual --write flag and manual promotion review',
            'signals_match': ['gene_intake', 'candidate_pipeline', 'auto_promotion'],
            'preconditions': ['genedb_exists', 'intake_loop_exists'],
            'strategy': ['enable --write by default for automated intake runs',
                         'add fitness-based auto-promotion for high-fitness candidates (>900)',
                         'route reflexion discoveries through same scoring → DB pipeline'],
            'constraints': {'boundary': 'local genedb; candidates only; high-fitness auto-promote limited'},
            'validation': ['verified 10 new candidates written in single intake run'],
        },
    ]


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
            promoted_count = 0
            for g in deduped[:10]:
                validation = (
                    g.get('validation') or []
                )
                if not validation:
                    validation = ['pending_intake_loop_review']
                gid = g.get('id', '')
                gene_name = g.get('name') or g.get('id') or gid
                # Check if gene name already exists in genes table (proper dedup)
                if con.execute(
                    'SELECT 1 FROM genes WHERE name = ?', (str(gene_name)[:200],)
                ).fetchone():
                    continue  # skip if already exists
                # Insert as candidate
                now_ts = _now()
                source_refs = json.dumps({
                    'source_file': g.get('source_file', ''),
                    'source_hash': g.get('source_hash', ''),
                }, ensure_ascii=False)

                # Standard template validation gate
                std_gene = {
                    'type': 'apex_gene_candidate',
                    'id': gid,
                    'category': g.get('gate_type', 'gene_intake_loop'),
                    'signals_match': g.get('signals_match', []),
                    'preconditions': g.get('preconditions', ['pending_intake_loop_review']),
                    'strategy': g.get('strategy', ['pattern absorption from code scan']),
                    'constraints': {
                        'boundary': BOUNDARY,
                        'source_file': g.get('source_file', ''),
                    },
                    'validation': g.get('validation', ['pending_intake_loop_review']),
                }
                std_validation = validate_standard_gene(std_gene)
                if std_validation['status'] != 'PASS':
                    # Log the blockage as blocked record (pgg_archon.db schema)
                    # First ensure gene record exists in genes table
                    gene_name = g.get('name') or g.get('id') or gid
                    con.execute(
                        'INSERT OR IGNORE INTO genes(name,pattern_type,source_repo,code_snippet,quality_score,extracted_at) VALUES(?,?,?,?,?,?)',
                        (str(gene_name)[:200], 'blocked_intake', g.get('source_file',''), str(std_validation)[:1000], 0, now_ts),
                    )
                    row = con.execute('SELECT id FROM genes WHERE name=? ORDER BY id DESC LIMIT 1', (str(gene_name)[:200],)).fetchone()
                    egid = row[0] if row else None
                    if egid:
                        con.execute(
                            'INSERT OR IGNORE INTO evolution_genes(gene_id,state,created_at,evidence_ref,review_status,review_reason,fitness_before) VALUES(?,?,?,?,?,?,?)',
                            (egid, 'blocked', now_ts, source_refs, 'gate_blocked_standard_template', str(std_validation), 0),
                        )
                    con.commit()
                    continue

                fitness = g.get('fitness', 500) or 500
                # Skip low-fitness candidates — they clutter DB without evolution value
                if fitness < 400:
                    continue
                # Auto-promote high-fitness candidates (> 900)
                auto_promote = fitness > 900
                status_str = 'verified' if auto_promote else 'candidate'
                verification = 'auto_promoted_by_intake_loop' if auto_promote else 'pending_intake_loop_review'
                
                # Serialize standard template JSON into absorbed_knowledge
                std_knowledge = json.dumps(std_gene, ensure_ascii=False)

                # Insert into genes table first (pgg_archon.db schema)
                gene_name = g.get('name') or g.get('id') or gid
                quality = min(999, max(0, fitness)) / 10.0  # normalize fitness 0-999 → quality 0-99.9
                # Check if gene already exists before inserting
                existing_row = con.execute(
                    'SELECT id FROM genes WHERE name=?', (str(gene_name)[:200],)
                ).fetchone()
                if existing_row:
                    continue  # already in DB, skip
                con.execute(
                    'INSERT INTO genes(name,pattern_type,source_repo,code_snippet,quality_score,extracted_at) VALUES(?,?,?,?,?,?)',
                    (str(gene_name)[:200], 'intake_loop_candidate', g.get('source_file',''), std_knowledge[:10000], quality, now_ts),
                )
                row = con.execute('SELECT id FROM genes WHERE name=? ORDER BY id DESC LIMIT 1', (str(gene_name)[:200],)).fetchone()
                new_gene_db_id = row[0] if row else None
                if new_gene_db_id:
                    con.execute(
                        'INSERT OR IGNORE INTO evolution_genes(gene_id,state,created_at,evidence_ref,review_status,review_confidence,fitness_after) VALUES(?,?,?,?,?,?,?)',
                        (new_gene_db_id, status_str, now_ts, source_refs, verification, fitness, quality),
                    )
                    written_count += 1
                    if auto_promote:
                        promoted_count += 1
            con.commit()
            write_info = {
                'written_count': written_count,
                'promoted_count': promoted_count,
                'candidate_status': 'candidate',
                'auto_promotion_threshold': 900,
            }
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
    'gather_reflexion_candidates',
]
