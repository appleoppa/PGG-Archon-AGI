"""PGG standard-gene fusion engine.

Boundary:
- local SQLite/file operations only;
- no network, no LLM calls, no Hermes core/provider/scheduler mutation;
- can write GeneDB only when write=True and readiness checks pass;
- fused genes are PGG internal behavior templates, not AGI/T5/ASI proof.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_DB = Path('/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3')
BOUNDARY = 'standard_gene_fusion_engine; local only; reviewed transaction; no AGI/T5/ASI claim'
REQUIRED_TEMPLATE_FIELDS = ('type','id','category','signals_match','preconditions','strategy','constraints','validation')


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def _hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _uniq(seq: Sequence[Any] | None) -> list[Any]:
    out: list[Any] = []
    for item in seq or []:
        if item not in out:
            out.append(item)
    return out


def validate_standard_gene(gene: Mapping[str, Any]) -> dict[str, Any]:
    missing = [f for f in REQUIRED_TEMPLATE_FIELDS if f not in gene]
    errors: list[str] = []
    if gene.get('type') not in {'apex_gene', 'pgg_gene', 'apex_gene_candidate'}:
        errors.append('invalid_type')
    for field in ('signals_match', 'preconditions', 'strategy', 'validation'):
        if field in gene and not isinstance(gene.get(field), list):
            errors.append(f'{field}_not_list')
    if 'constraints' in gene and not isinstance(gene.get('constraints'), dict):
        errors.append('constraints_not_dict')
    if not gene.get('id'):
        errors.append('missing_id')
    if not gene.get('category'):
        errors.append('missing_category')
    return {
        'schema': 'PGGStandardGeneTemplateValidation/v1',
        'status': 'PASS' if not missing and not errors else 'BLOCK',
        'missing': missing,
        'errors': errors,
        'boundary': BOUNDARY,
    }


def _fitness_from_record(record: Mapping[str, Any]) -> int:
    grade = str(record.get('evidence_grade') or '')
    head = grade.split(':', 1)[0].strip()
    base = {'S': 950, 'A+': 900, 'A': 850, 'A-': 800, 'B+': 700, 'B': 600}.get(head, 500)
    if str(record.get('status')) == 'verified':
        base += 50
    if 'pending' in str(record.get('verification_status', '')):
        base -= 200
    return max(0, min(999, base))


def gene_record_to_standard_gene(record: Mapping[str, Any]) -> dict[str, Any]:
    signals = [
        str(record.get('defect_name', '')).strip(),
        str(record.get('gate_type', '')).strip(),
        str(record.get('gene_name', '')).strip(),
    ]
    strategy = [s.strip() for s in str(record.get('repair_mechanism') or record.get('reusable_rule') or '').splitlines() if s.strip()]
    if not strategy:
        strategy = [str(record.get('reusable_rule') or record.get('absorbed_knowledge') or 'apply verified repair mechanism')]
    return {
        'type': 'pgg_gene',
        'id': str(record.get('gene_id')),
        'category': str(record.get('gate_type') or 'pgg_genedb'),
        'signals_match': _uniq([s for s in signals if s]),
        'preconditions': ['source evidence present', 'regression evidence present'],
        'strategy': strategy,
        'constraints': {
            'boundary': str(record.get('boundary') or BOUNDARY),
            'evidence_grade': str(record.get('evidence_grade') or ''),
        },
        'validation': [str(record.get('verification_status') or 'verified by GeneDB record')],
        'origin': 'genedb',
        'fitness': _fitness_from_record(record),
        'created': str(record.get('created_at') or _now()),
    }


def fuse_standard_genes(
    parents: Sequence[Mapping[str, Any]],
    *,
    offspring_id: str | None = None,
    category: str = 'pgg_fusion',
    reviewer: str = 'apple_didi',
    mode: str = 'additive',
) -> dict[str, Any]:
    validations = [validate_standard_gene(p) for p in parents]
    errors: list[str] = []
    if len(parents) < 2:
        errors.append('need_at_least_2_parent_genes')
    for idx, validation in enumerate(validations):
        if validation['status'] != 'PASS':
            errors.append(f'parent_{idx}_invalid')
    parent_ids = [p.get('id') for p in parents]
    oid = offspring_id or 'fusion_' + _hash(parent_ids)[:16]
    signals: list[Any] = []
    preconditions: list[Any] = []
    strategy: list[Any] = []
    validation_items: list[Any] = []
    constraints: dict[str, Any] = {'parents': parent_ids, 'reviewer': reviewer, 'boundary': BOUNDARY}
    fitnesses: list[float] = []
    for parent in parents:
        signals += list(parent.get('signals_match') or [])
        preconditions += list(parent.get('preconditions') or [])
        strategy += list(parent.get('strategy') or [])
        validation_items += list(parent.get('validation') or [])
        constraints[f"parent_{parent.get('id')}_constraints"] = parent.get('constraints', {})
        try:
            fitnesses.append(float(parent.get('fitness', 0)))
        except Exception:
            pass
    complexity_penalty = max(0.0, float((len(_uniq(strategy)) - 8) * 2))
    avg_parent = sum(fitnesses) / len(fitnesses) if fitnesses else 500.0
    max_parent = max(fitnesses) if fitnesses else 500.0
    if mode == 'multiplicative':
        # Normalized multiplicative: offspring = avg × (1 + synergy_ratio × multiplier)
        # synergy_ratio = spread / max_parent  (higher spread = more fusion potential)
        # multiplier scales with parent count, capped at 3.0
        synergy_ratio = (max_parent - avg_parent) / max(max_parent, 1.0)
        multiplier = min(3.0, 0.5 * (len(parents) - 1))
        raw = avg_parent * (1.0 + synergy_ratio * multiplier)
        offspring_fitness = min(9999, int(raw + 0.5))
        synergy = offspring_fitness - max_parent
        if synergy_ratio < 0.05:
            errors.append('synergy_ratio_below_threshold')
    else:
        offspring_fitness = min(999, int(avg_parent + 40 + 5 * len(parents) - complexity_penalty))
        synergy = offspring_fitness - max_parent - complexity_penalty
        if synergy <= 0:
            errors.append('synergy_not_positive_after_penalties')
    gene = {
        'type': 'pgg_gene',
        'id': oid,
        'category': category,
        'signals_match': _uniq(signals),
        'preconditions': _uniq(preconditions),
        'strategy': _uniq(strategy),
        'constraints': constraints,
        'validation': _uniq(validation_items),
        'created': _now(),
        'origin': 'pgg_standard_gene_fusion_engine',
        'fusion_mode': mode,
        'fitness': offspring_fitness,
        'parent_ids': parent_ids,
        'synergy': synergy,
        'gene_hash': '',
    }
    gene['gene_hash'] = _hash({k: v for k, v in gene.items() if k != 'gene_hash'})
    return {
        'schema': 'PGGStandardGeneFusion/v1',
        'status': 'PASS' if not errors else 'BLOCK',
        'errors': errors,
        'validations': validations,
        'offspring_gene': gene,
        'synergy': synergy,
        'boundary': BOUNDARY,
    }


def fetch_genedb_records(ids: Sequence[str], *, db_path: str | Path = DEFAULT_DB) -> list[dict[str, Any]]:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        out: list[dict[str, Any]] = []
        for gid in ids:
            row = con.execute('SELECT * FROM evolution_genes WHERE gene_id = ?', (gid,)).fetchone()
            if row:
                out.append({k: row[k] for k in row.keys()})
        return out
    finally:
        con.close()


def insert_fused_gene(
    gene: Mapping[str, Any],
    *,
    db_path: str | Path = DEFAULT_DB,
    write: bool = False,
    promote: bool = False,
) -> dict[str, Any]:
    validation = validate_standard_gene(gene)
    if validation['status'] != 'PASS':
        return {'schema': 'PGGStandardGeneFusionInsert/v1', 'status': 'BLOCK', 'errors': ['invalid_standard_gene'], 'validation': validation, 'written': False, 'boundary': BOUNDARY}
    if not write:
        return {'schema': 'PGGStandardGeneFusionInsert/v1', 'status': 'DRY_RUN', 'written': False, 'gene_id': gene['id'], 'boundary': BOUNDARY}
    status = 'verified' if promote else 'candidate'
    verification = 'verified_by_standard_gene_fusion_engine' if promote else 'pending_review_standard_gene_fusion_engine'
    cycle_id = 'APEX-STANDARD-GENE-FUSION-20260610'
    con = sqlite3.connect(str(db_path))
    try:
        con.execute(
            'INSERT OR IGNORE INTO evolution_cycles(cycle_id,created_at,theme,sequence_logic,status,evidence_grade,boundary) VALUES(?,?,?,?,?,?,?)',
            (cycle_id, _now(), '标准基因融合引擎', '12534', 'verified' if promote else 'candidate', 'A' if promote else 'B', BOUNDARY),
        )
        source_refs = json.dumps([{'parent_gene_ids': gene.get('parent_ids', []), 'standard_gene_template': True}], ensure_ascii=False)
        con.execute(
            '''INSERT OR IGNORE INTO evolution_genes(gene_id,cycle_id,created_at,defect_no,defect_name,gene_name,absorbed_knowledge,source_refs_json,repair_mechanism,severity_rank,apex_variables,gate_type,reusable_rule,status,evidence_grade,verification_status,boundary,gene_hash,fitness,execution_count,last_executed) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (
                gene['id'], cycle_id, _now(), 47, '标准基因融合引擎落地', gene['id'],
                json.dumps(gene, ensure_ascii=False), source_refs, '\n'.join(gene.get('strategy', [])),
                1, 'Φ_anti_VERIFIED_SOURCE,Ω_self,EVM_gate', 'standard_gene_fusion_engine',
                'standard gene template fusion with positive synergy', status, 'A' if promote else 'B',
                verification, BOUNDARY, gene.get('gene_hash') or _hash(gene),
                int(gene.get('fitness') or 0), 0, None,
            ),
        )
        con.commit()
        row = con.execute('SELECT status, verification_status FROM evolution_genes WHERE gene_id = ?', (gene['id'],)).fetchone()
        return {'schema': 'PGGStandardGeneFusionInsert/v1', 'status': 'PASS', 'written': True, 'promoted': promote, 'gene_id': gene['id'], 'db_status': row[0] if row else None, 'verification_status': row[1] if row else None, 'boundary': BOUNDARY}
    finally:
        con.close()


def fuse_genedb_records(
    parent_ids: Sequence[str],
    *,
    db_path: str | Path = DEFAULT_DB,
    write: bool = False,
    promote: bool = False,
    mode: str = 'additive',
) -> dict[str, Any]:
    records = fetch_genedb_records(parent_ids, db_path=db_path)
    genes = [gene_record_to_standard_gene(record) for record in records]
    fusion = fuse_standard_genes(genes, offspring_id='standard_fusion_' + _hash(parent_ids)[:16], mode=mode)
    insert = None
    if fusion['status'] == 'PASS':
        insert = insert_fused_gene(fusion['offspring_gene'], db_path=db_path, write=write, promote=promote)
    return {
        'schema': 'PGGStandardGeneFusionEngineRun/v1',
        'created_at': _now(),
        'requested_parent_ids': list(parent_ids),
        'records_found': len(records),
        'fusion': fusion,
        'insert': insert,
        'boundary': BOUNDARY,
    }

__all__ = ['validate_standard_gene', 'gene_record_to_standard_gene', 'fuse_standard_genes', 'fetch_genedb_records', 'insert_fused_gene', 'fuse_genedb_records']
