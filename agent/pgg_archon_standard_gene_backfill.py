"""PGG Archon 标准基因模板 backfill 脚本。

将两个旧格式数据库的基因转换为版本 A 标准 8 字段模板格式，
并存入 apex_evolution_genes.sqlite3 的 absorbed_knowledge JSON 列。

安全边界:
- 只读 pgg_archon.db（版本 D）
- 只读 apex_evolution_genes.sqlite3 旧记录（版本 C）
- 写入 apex_evolution_genes.sqlite3 新记录（标准模板格式）
- 默认 dry_run=True — 不写库
- 所有新记录 status='candidate'，不自动 promote
- 不删除旧记录
- 转换失败的标 BLOCKED_NEEDS_MANUAL_MAPPING，不硬编
 - apex DB 旧记录用 'STANDARD_' + gene_id 写入，避免 PRIMARY KEY 冲突
 - pgg_archon.db 用 'pgg_' + name，不与 apex DB 冲突

标准模板 8 字段（版本 A）:
  type, id, category, signals_match, preconditions, strategy, constraints, validation
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Mapping

# --- 路径 ---
APEX_DB = Path('/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3')
PGG_DB = Path('/Users/appleoppa/.hermes/data/pgg_archon.db')
BOUNDARY = 'standard_gene_backfill; read-only old records; write candidate only; no auto-promote; no AGI/T5 claim'

REQUIRED_TEMPLATE_FIELDS = ('type', 'id', 'category', 'signals_match', 'preconditions', 'strategy', 'constraints', 'validation')


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def _hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def validate_standard_gene(gene: Mapping[str, Any]) -> dict[str, Any]:
    """验证是否符合标准模板 8 字段。"""
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


# ========================================================================
# 转换函数
# ========================================================================

def convert_apex_record(record: dict[str, Any]) -> dict[str, Any]:
    """将 apex DB 旧格式记录（版本 C）转为标准模板 A。
    
    映射规则:
    - type → 'pgg_gene'
    - id → gene_id
    - category → gate_type (空则 'apex_genedb')
    - signals_match → [defect_name, gate_type, gene_name] 过滤空值
    - preconditions → ['source evidence present', 'regression evidence present']
    - strategy → repair_mechanism 按行拆分，空则 [reusable_rule]
    - constraints → {boundary, evidence_grade}
    - validation → [verification_status]
    """
    signals = [
        str(record.get('defect_name', '')).strip(),
        str(record.get('gate_type', '')).strip(),
        str(record.get('gene_name', '')).strip(),
    ]
    strategy = [s.strip() for s in str(record.get('repair_mechanism') or '').splitlines() if s.strip()]
    if not strategy:
        strategy = [str(record.get('reusable_rule') or record.get('absorbed_knowledge') or 'apply verified repair mechanism')]

    return {
        'type': 'pgg_gene',
        'id': 'STANDARD_' + str(record.get('gene_id', '')),
        'category': str(record.get('gate_type') or 'apex_genedb'),
        'signals_match': [s for s in signals if s],
        'preconditions': ['source evidence present', 'regression evidence present'],
        'strategy': strategy,
        'constraints': {
            'boundary': str(record.get('boundary') or BOUNDARY),
            'evidence_grade': str(record.get('evidence_grade') or ''),
        },
        'validation': [str(record.get('verification_status') or 'verified by GeneDB record')],
        'origin': 'apex_genedb_backfill',
        'fitness': _fitness_from_record(record),
        'created': str(record.get('created_at') or _now()),
    }


def convert_pgg_record(record: dict[str, Any]) -> dict[str, Any]:
    """将 pgg_archon.db 旧格式记录（版本 D）转为标准模板 A。
    
    映射规则（信息稀疏，很多字段需要推断）:
    - type → 'apex_gene_candidate' (不是 verified gene)
    - id → 'pgg_' + name
    - category → pattern_type
    - signals_match → [name] + name 分词
    - preconditions → ['source repo verification needed']
    - strategy → ['pattern absorption from ' + source_repo]
    - constraints → {boundary, quality_score}
    - validation → ['pending_review_backfill_conversion']
    """
    name = str(record.get('name', ''))
    pattern_type = str(record.get('pattern_type', ''))
    source_repo = str(record.get('source_repo', ''))
    quality_score = float(record.get('quality_score') or 0)

    # Tokenize name for signals
    tokens = name.replace('_', ' ').replace('-', ' ').split()
    signals = [name] + [t.lower() for t in tokens if len(t) > 2]

    return {
        'type': 'apex_gene_candidate',
        'id': f'pgg_{name}',
        'category': pattern_type or 'pgg_pattern',
        'signals_match': signals[:12],
        'preconditions': ['source repo verification needed'],
        'strategy': [f'pattern absorption from {source_repo}'] if source_repo else ['pattern absorption pending source identification'],
        'constraints': {
            'boundary': 'backfill from pgg_archon.db; sparse metadata; candidate only',
            'quality_score': quality_score,
        },
        'validation': ['pending_review_backfill_conversion'],
        'origin': 'pgg_archon_db_backfill',
        'fitness': int(quality_score) if quality_score > 0 else 0,
        'created': _now(),
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


# ========================================================================
# Backfill 主逻辑
# ========================================================================

def backfill_apex_db(*, dry_run: bool = True, limit: int = 0) -> dict[str, Any]:
    """从 apex DB 读取旧记录，转换为标准模板，写回新记录。"""
    con = sqlite3.connect(str(APEX_DB))
    con.row_factory = sqlite3.Row
    results: list[dict[str, Any]] = []
    converted = 0
    blocked = 0
    written = 0
    errors_list: list[str] = []

    try:
        rows = con.execute('SELECT * FROM evolution_genes ORDER BY defect_no').fetchall()
        if limit > 0:
            rows = rows[:limit]
        
        for row in rows:
            record = {k: row[k] for k in row.keys()}
            gene = convert_apex_record(record)
            validation = validate_standard_gene(gene)
            
            if validation['status'] == 'PASS':
                converted += 1
                if not dry_run:
                    # Write as new candidate record with standard template JSON in absorbed_knowledge
                    gene_json = json.dumps(gene, ensure_ascii=False)
                    cycle_id = 'BACKFILL-STANDARD-TEMPLATE-20260612'
                    try:
                        con.execute(
                            'INSERT OR IGNORE INTO evolution_cycles(cycle_id,created_at,theme,sequence_logic,status,evidence_grade,boundary) VALUES(?,?,?,?,?,?,?)',
                            (cycle_id, _now(), '标准模板backfill', '12534', 'candidate', 'B', BOUNDARY),
                        )
                        con.execute(
                            '''INSERT OR IGNORE INTO evolution_genes(
                                gene_id,cycle_id,created_at,defect_no,defect_name,gene_name,
                                absorbed_knowledge,source_refs_json,repair_mechanism,
                                severity_rank,apex_variables,gate_type,reusable_rule,
                                status,evidence_grade,verification_status,boundary,gene_hash,
                                fitness,execution_count,last_executed
                            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (
                                gene['id'], cycle_id, _now(), 48, '标准模板backfill',
                                gene['id'], gene_json,
                                json.dumps([{'backfill_source': 'apex_genedb', 'original_gene_id': record.get('gene_id')}], ensure_ascii=False),
                                '\n'.join(gene.get('strategy', [])),
                                1, 'standard_template_backfill', gene['category'],
                                'standard gene template backfill conversion',
                                'candidate', 'B', 'pending_review_backfill', BOUNDARY,
                                _hash(gene), gene.get('fitness', 0), 0, None,
                            ),
                        )
                        con.commit()
                        written += 1
                    except Exception as e:
                        errors_list.append(f'{gene["id"]}: {e}')
                results.append({'id': gene['id'], 'status': 'PASS', 'validation': validation})
            else:
                blocked += 1
                results.append({'id': gene['id'], 'status': 'BLOCKED_NEEDS_MANUAL_MAPPING', 'validation': validation})

    finally:
        con.close()

    return {
        'schema': 'PGGStandardTemplateBackfill/v1',
        'source': 'apex_evolution_genes.sqlite3',
        'total_records': len(results),
        'converted': converted,
        'blocked': blocked,
        'written': written,
        'dry_run': dry_run,
        'errors': errors_list,
        'boundary': BOUNDARY,
    }


def backfill_pgg_db(*, dry_run: bool = True, limit: int = 0) -> dict[str, Any]:
    """从 pgg_archon.db 读取旧记录，转换为标准模板，写入 apex DB。"""
    # Read from pgg_archon.db
    src_con = sqlite3.connect(str(PGG_DB))
    src_con.row_factory = sqlite3.Row
    
    results: list[dict[str, Any]] = []
    converted = 0
    blocked = 0
    written = 0
    errors_list: list[str] = []

    try:
        rows = src_con.execute('SELECT * FROM genes ORDER BY id').fetchall()
        if limit > 0:
            rows = rows[:limit]
        
        for row in rows:
            record = {k: row[k] for k in row.keys()}
            gene = convert_pgg_record(record)
            validation = validate_standard_gene(gene)
            
            if validation['status'] == 'PASS':
                converted += 1
                if not dry_run:
                    # Write to apex DB
                    dst_con = sqlite3.connect(str(APEX_DB))
                    try:
                        gene_json = json.dumps(gene, ensure_ascii=False)
                        cycle_id = 'BACKFILL-PGG-DB-STANDARD-TEMPLATE-20260612'
                        dst_con.execute(
                            'INSERT OR IGNORE INTO evolution_cycles(cycle_id,created_at,theme,sequence_logic,status,evidence_grade,boundary) VALUES(?,?,?,?,?,?,?)',
                            (cycle_id, _now(), 'pgg_archon.db标准模板backfill', '12534', 'candidate', 'B', BOUNDARY),
                        )
                        dst_con.execute(
                            '''INSERT OR IGNORE INTO evolution_genes(
                                gene_id,cycle_id,created_at,defect_no,defect_name,gene_name,
                                absorbed_knowledge,source_refs_json,repair_mechanism,
                                severity_rank,apex_variables,gate_type,reusable_rule,
                                status,evidence_grade,verification_status,boundary,gene_hash,
                                fitness,execution_count,last_executed
                            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (
                                gene['id'], cycle_id, _now(), 49, 'pgg_db标准模板backfill',
                                gene['id'], gene_json,
                                json.dumps([{'backfill_source': 'pgg_archon_db', 'original_id': record.get('id')}], ensure_ascii=False),
                                '\n'.join(gene.get('strategy', [])),
                                2, 'standard_template_backfill_pgg', gene['category'],
                                'standard gene template backfill from pgg_archon.db',
                                'candidate', 'B', 'pending_review_backfill', BOUNDARY,
                                _hash(gene), gene.get('fitness', 0), 0, None,
                            ),
                        )
                        dst_con.commit()
                        written += 1
                    except Exception as e:
                        errors_list.append(f'{gene["id"]}: {e}')
                    finally:
                        dst_con.close()
                results.append({'id': gene['id'], 'status': 'PASS', 'validation': validation})
            else:
                blocked += 1
                results.append({'id': gene['id'], 'status': 'BLOCKED_NEEDS_MANUAL_MAPPING', 'validation': validation})
    finally:
        src_con.close()

    return {
        'schema': 'PGGStandardTemplateBackfill/v1',
        'source': 'pgg_archon.db',
        'total_records': len(results),
        'converted': converted,
        'blocked': blocked,
        'written': written,
        'dry_run': dry_run,
        'errors': errors_list,
        'boundary': BOUNDARY,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PGG 标准基因模板 backfill')
    parser.add_argument('--write', action='store_true', help='实际写入（默认 dry-run）')
    parser.add_argument('--source', choices=['apex', 'pgg', 'both'], default='both', help='数据源')
    parser.add_argument('--limit', type=int, default=0, help='限制处理条数（0=全部）')
    args = parser.parse_args()

    dry_run = not args.write
    
    if args.source in ('apex', 'both'):
        print(f'=== Backfill apex DB (dry_run={dry_run}) ===')
        result = backfill_apex_db(dry_run=dry_run, limit=args.limit)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if args.source in ('pgg', 'both'):
        print(f'\n=== Backfill pgg_archon.db (dry_run={dry_run}) ===')
        result = backfill_pgg_db(dry_run=dry_run, limit=args.limit)
        print(json.dumps(result, indent=2, ensure_ascii=False))
