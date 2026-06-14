"""PGG Archon 标准基因模板元能力模块。

输入 Python 源码目录，输出标准 5 层基因 JSON。

Boundary:
- filesystem read-only scan; bounded by max_genes (hard cap 200);
- dry_run=True by default — no GeneDB writes without explicit --write;
- no network, no LLM calls, no Hermes core/provider/scheduler mutation.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

# ── Config ────────────────────────────────────────────────────────────

DEFAULT_DB = Path(
    '/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3'
)
BOUNDARY = (
    'pgg_archon_code_gene_scanner; static analysis only; '
    'no runtime verification; no AGI/T5/ASI claim'
)
REQUIRED_TEMPLATE_FIELDS = (
    'type', 'id', 'category', 'signals_match',
    'preconditions', 'strategy', 'constraints', 'validation',
)
MAX_GENES = 200
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv',
             '.tox', 'dist', 'build', '.mypy_cache', '.pytest_cache'}

TYPE_PGG_GENE = 'pgg_gene'


# ── Helpers ───────────────────────────────────────────────────────────

def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def _hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:16]


def _uniq(seq: Sequence[Any] | None) -> list[Any]:
    out: list[Any] = []
    for item in seq or []:
        if item not in out:
            out.append(item)
    return out


def _gene_id(class_name: str, file_path: str) -> str:
    """Generate a deterministic gene id from class name and file path."""
    raw = f'{class_name}@{file_path}'
    return f'pgg_gene_{_hash(raw)}'


# ── Docstring & AST helpers ──────────────────────────────────────────

def _extract_docstring_top_level(tree: ast.Module) -> str:
    """Extract the module-level docstring, if present."""
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)):
        return tree.body[0].value.value
    return ''


def _extract_class_docstring(node: ast.ClassDef) -> str:
    """Extract class docstring from an AST class node."""
    if (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        return node.body[0].value.value
    return ''


def _extract_func_docstring(node: ast.FunctionDef) -> str:
    if (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        return node.body[0].value.value
    return ''


def _tokenize(text: str) -> list[str]:
    """Split a camel/Pascal/snake identifier into lowercase tokens."""
    import re
    # Split on camelCase boundaries first
    parts = re.sub(r'([A-Z])', r' \1', text).strip().split()
    tokens = []
    for part in parts:
        tokens.extend(part.lower().replace('_', ' ').split())
    return tokens


def _extract_signals(class_name: str, docstring: str) -> list[str]:
    """Build signals_match from class name + docstring keywords."""
    tokens = _tokenize(class_name)
    doc_tokens = _tokenize(docstring) if docstring else []
    all_tokens = _uniq(tokens + doc_tokens)
    # Filter noise
    stop_words = {'the', 'a', 'an', 'for', 'of', 'in', 'to', 'and', 'or',
                  'is', 'are', 'be', 'this', 'that', 'class', 'function'}
    meaningful = [t for t in all_tokens if t not in stop_words and len(t) > 1]
    # Always include the class name itself
    result = [class_name] + meaningful[:10]
    return _uniq(result)


def _extract_preconditions(class_node: ast.ClassDef) -> list[str]:
    """Extract __init__ parameter names as preconditions."""
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == '__init__':
            # Skip 'self' (first arg)
            args = [a.arg for a in item.args.args if a.arg != 'self']
            defaults = [None] * (len(args) - len(item.args.defaults)) + [
                ast.dump(d) for d in item.args.defaults
            ]
            preconds = []
            for arg, default in zip(args, defaults):
                if default is not None and 'None' in default:
                    preconds.append(f'{arg} (optional)')
                else:
                    preconds.append(f'{arg} (required)')
            return preconds if preconds else ['no_constructor_params']
    return ['no_constructor_params']


def _func_preconditions(func_node: ast.FunctionDef) -> list[str]:
    """Extract function parameters as preconditions."""
    args = [a.arg for a in func_node.args.args]
    defaults = [None] * (len(args) - len(func_node.args.defaults)) + [
        ast.dump(d) for d in func_node.args.defaults
    ]
    preconds = []
    for arg, default in zip(args, defaults):
        if default is not None and 'None' in default:
            preconds.append(f'{arg} (optional)')
        else:
            preconds.append(f'{arg} (required)')
    return preconds if preconds else ['no_constructor_params']


def _extract_constraints(class_node: ast.ClassDef) -> dict[str, Any]:
    """Extract constraints from type annotations and __init__ defaults."""
    constraints: dict[str, Any] = {
        'boundary': 'static_analysis_only: no runtime verification',
    }
    annotations: dict[str, str] = {}
    defaults: dict[str, str] = {}

    for item in class_node.body:
        # Class-level annotated attributes
        if isinstance(item, ast.AnnAssign) and item.target and isinstance(item.target, ast.Name):
            ann_str = ast.dump(item.annotation) if item.annotation else 'unknown'
            annotations[item.target.id] = ann_str
            if item.value:
                defaults[item.target.id] = ast.dump(item.value)

        # __init__ params
        if isinstance(item, ast.FunctionDef) and item.name == '__init__':
            for arg in item.args.args:
                if arg.arg == 'self':
                    continue
                if arg.annotation:
                    annotations[arg.arg] = ast.dump(arg.annotation)

            # Defaults
            args_list = [a.arg for a in item.args.args if a.arg != 'self']
            offset = len(args_list) - len(item.args.defaults)
            for i, default in enumerate(item.args.defaults):
                idx = offset + i
                if idx < len(args_list):
                    defaults[args_list[idx]] = ast.dump(default)

    if annotations:
        constraints['type_annotations'] = annotations
    if defaults:
        constraints['init_defaults'] = defaults

    return constraints


def _inspect_method_confidence(method_node: ast.FunctionDef) -> str:
    """Determine confidence level based on method body structure."""
    # Check for block-level structures
    for node in ast.walk(method_node):
        if isinstance(node, (ast.Try, ast.ExceptHandler, ast.If,
                             ast.For, ast.While, ast.With, ast.AsyncFor)):
            return 'medium'
        if isinstance(node, ast.Call):
            # Dynamic calls like getattr, exec, eval
            if isinstance(node.func, ast.Name) and node.func.id in {'exec', 'eval', 'getattr'}:
                return 'low'
            # Super() calls
            if isinstance(node.func, ast.Call) and hasattr(node.func, 'func'):
                pass
    return 'high'


def _extract_strategy(class_node: ast.ClassDef) -> list[dict[str, Any]]:
    """Extract strategy steps from public method names + signatures."""
    steps: list[dict[str, Any]] = []
    for item in class_node.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        # Skip private (starts with _) and dunder methods
        if item.name.startswith('_'):
            continue

        # Signature summary
        args = [a.arg for a in item.args.args if a.arg != 'self']
        returns = ''
        if item.returns:
            returns = ast.dump(item.returns)
        confidence = _inspect_method_confidence(item)

        sig_parts = [f'{item.name}({", ".join(args)})']
        if returns:
            sig_parts.append(f'-> {returns}')
        if item.body and len(item.body) == 1 and isinstance(item.body[0], ast.Expr):
            sig_parts.append('(one-liner)')
        elif confidence == 'medium':
            sig_parts.append('(block-level logic)')
        elif confidence == 'low':
            sig_parts.append('(dynamic/inherited)')

        steps.append({
            'method': item.name,
            'signature': ' '.join(sig_parts),
            'confidence': confidence,
        })

    return steps


def _extract_func_strategy(func_node: ast.FunctionDef) -> list[dict[str, Any]]:
    """Extract strategy from a top-level function."""
    args = [a.arg for a in func_node.args.args]
    returns = ast.dump(func_node.returns) if func_node.returns else ''
    confidence = _inspect_method_confidence(func_node)
    sig_parts = [f'{func_node.name}({", ".join(args)})']
    if returns:
        sig_parts.append(f'-> {returns}')
    sig_parts.append(f'({confidence} confidence)')
    return [{
        'method': func_node.name,
        'signature': ' '.join(sig_parts),
        'confidence': confidence,
    }]


def _extract_validation() -> list[str]:
    """Phase 1: return empty validation array."""
    return []


# ── Core scan functions ──────────────────────────────────────────────

def scan_source(path: str) -> list[dict[str, Any]]:
    """Scan a single .py file and extract class-level and function-level candidate genes.

    Returns a list of standard 5-layer gene dicts (class-level + top-level functions).
    """
    fpath = Path(path)
    if not fpath.exists():
        return []
    if fpath.suffix != '.py':
        return []

    try:
        source = fpath.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return []

    try:
        tree = ast.parse(source, filename=str(fpath))
    except SyntaxError:
        return []

    module_doc = _extract_docstring_top_level(tree)
    genes: list[dict[str, Any]] = []

    # Pass 1: class-level genes
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name.startswith('_'):
            continue

        class_doc = _extract_class_docstring(node)
        combined_doc = class_doc or module_doc

        gene_id = _gene_id(node.name, str(fpath))
        signals = _extract_signals(node.name, combined_doc)
        preconditions = _extract_preconditions(node)
        strategy = _extract_strategy(node)
        constraints = _extract_constraints(node)
        validation = _extract_validation()

        genes.append({
            'type': TYPE_PGG_GENE,
            'id': gene_id,
            'category': f'code_scan::{fpath.name}',
            'signals_match': signals,
            'preconditions': preconditions,
            'strategy': strategy,
            'constraints': constraints,
            'validation': validation,
            'source_file': str(fpath),
            'class_name': node.name,
            'scanned_at': _now(),
        })

    # Pass 2: top-level function-level genes (only if module-body direct children)
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name.startswith('_'):
            continue

        func_doc = _extract_func_docstring(node)
        combined_doc = func_doc or module_doc

        gene_id = _gene_id(node.name, str(fpath))
        signals = _extract_signals(node.name, combined_doc)
        preconditions = _func_preconditions(node)
        strategy = _extract_func_strategy(node)
        validation = _extract_validation()

        genes.append({
            'type': TYPE_PGG_GENE,
            'id': gene_id,
            'category': f'code_scan::{fpath.name}',
            'signals_match': signals,
            'preconditions': preconditions,
            'strategy': strategy,
            'constraints': {'boundary': 'static_analysis_only: no runtime verification'},
            'validation': validation,
            'source_file': str(fpath),
            'function_name': node.name,
            'scanned_at': _now(),
        })

    return genes


def scan_directory(
    path: str,
    recursive: bool = True,
) -> list[dict[str, Any]]:
    """Recursively scan a directory for .py files and extract all genes.

    Max 200 genes returned (MAX_GENES). Non-.py files are skipped.
    """
    root = Path(path)
    if not root.exists() or not root.is_dir():
        return []

    all_genes: list[dict[str, Any]] = []

    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune skip dirs
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

            for fname in filenames:
                if not fname.endswith('.py'):
                    continue
                if len(all_genes) >= MAX_GENES:
                    break
                filepath = Path(dirpath, fname)
                all_genes.extend(scan_source(str(filepath)))

            if len(all_genes) >= MAX_GENES:
                break
    else:
        for entry in sorted(root.iterdir()):
            if not entry.name.endswith('.py'):
                continue
            if len(all_genes) >= MAX_GENES:
                break
            all_genes.extend(scan_source(str(entry)))

    return all_genes[:MAX_GENES]


def gene_to_json(gene: dict[str, Any]) -> str:
    """Serialize a single gene to JSON string."""
    return json.dumps(gene, ensure_ascii=False, indent=2)


# ── GeneDB write ─────────────────────────────────────────────────────

def write_to_genedb(
    genes: Sequence[Mapping[str, Any]],
    *,
    write: bool = False,
    promote: bool = False,
) -> dict[str, Any]:
    """Write scanned genes to GeneDB.

    dry_run=True (write=False) by default — no actual DB writes.
    When write=True, inserts each gene as a candidate (or verified if promote=True).

    Returns a result dict with per-gene status.
    """
    # Validate all genes first
    from agent.pgg_archon_gene_fusion_engine import validate_standard_gene

    per_gene: list[dict[str, Any]] = []
    all_pass = True

    for gene in genes:
        validation = validate_standard_gene(gene)
        if validation['status'] != 'PASS':
            per_gene.append({
                'gene_id': gene.get('id', 'unknown'),
                'status': 'BLOCK',
                'errors': validation['errors'],
                'missing': validation['missing'],
                'written': False,
            })
            all_pass = False
            continue

        if not write:
            per_gene.append({
                'gene_id': gene['id'],
                'status': 'DRY_RUN',
                'written': False,
            })
            continue

        # Actual write
        try:
            db_path = DEFAULT_DB
            con = sqlite3.connect(str(db_path))
            con.row_factory = sqlite3.Row

            db_status = 'verified' if promote else 'candidate'
            verification = (
                'verified_by_code_gene_scanner' if promote
                else 'pending_review_code_gene_scanner'
            )
            cycle_id = 'APEX-CODE-GENE-SCANNER-20260611'
            source_refs = json.dumps([
                {'source_file': gene.get('source_file', ''),
                 'class_name': gene.get('class_name', ''),
                 'scanner': 'pgg_archon_code_gene_scanner'},
            ], ensure_ascii=False)

            con.execute(
                'INSERT OR IGNORE INTO evolution_cycles '
                '(cycle_id, created_at, theme, sequence_logic, status, evidence_grade, boundary) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (cycle_id, _now(), '代码基因扫描器', '21354',
                 'verified' if promote else 'candidate',
                 'A' if promote else 'B', BOUNDARY),
            )

            con.execute(
                '''INSERT OR IGNORE INTO evolution_genes
                   (gene_id, cycle_id, created_at, defect_no, defect_name, gene_name,
                    absorbed_knowledge, source_refs_json, repair_mechanism,
                    severity_rank, apex_variables, gate_type, reusable_rule,
                    status, evidence_grade, verification_status, boundary, gene_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    gene['id'], cycle_id, _now(), 48, '代码基因扫描落地', gene['id'],
                    json.dumps(dict(gene), ensure_ascii=False),
                    source_refs,
                    '\n'.join(
                        s.get('signature', str(s)) if isinstance(s, dict)
                        else str(s)
                        for s in gene.get('strategy', [])
                    ),
                    2, 'Φ_anti_VERIFIED_SOURCE,Ω_self,EVM_gate',
                    'code_gene_scanner',
                    'class-level static analysis gene template',
                    db_status, 'A' if promote else 'B',
                    verification, BOUNDARY, _hash(gene),
                ),
            )
            con.commit()
            row = con.execute(
                'SELECT status, verification_status FROM evolution_genes WHERE gene_id = ?',
                (gene['id'],),
            ).fetchone()
            per_gene.append({
                'gene_id': gene['id'],
                'status': 'PASS',
                'written': True,
                'promoted': promote,
                'db_status': row[0] if row else None,
                'verification_status': row[1] if row else None,
            })
            con.close()

        except Exception as exc:
            per_gene.append({
                'gene_id': gene.get('id', 'unknown'),
                'status': 'ERROR',
                'error': str(exc),
                'written': False,
            })
            all_pass = False

    return {
        'schema': 'PGGCodeGeneScannerInsert/v1',
        'created_at': _now(),
        'total': len(genes),
        'results': per_gene,
        'all_pass': all_pass,
        'boundary': BOUNDARY,
    }


__all__ = [
    'scan_source', 'scan_directory', 'gene_to_json', 'write_to_genedb',
    'MAX_GENES', 'REQUIRED_TEMPLATE_FIELDS', 'TYPE_PGG_GENE',
]
