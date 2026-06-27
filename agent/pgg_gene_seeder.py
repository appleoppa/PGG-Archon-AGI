#!/usr/bin/env python3
"""
PGG Gene Seeder v1 — 从真实代码源提取可执行基因为 candidate。
扫描 agent/、Rust modules、Hermes core、Skills、Binaries、PGG workspace。
写入 pgg_archon.db → genes 表 + gene_lifecycle 表 (state='candidate')。

用法:
  python3 -m agent.pgg_gene_seeder --dry-run          # 预览
  python3 -m agent.pgg_gene_seeder --sources agent    # 只扫 agent
  python3 -m agent.pgg_gene_seeder --sources all      # 扫全部（默认）
"""

import ast
import glob
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

DB_PATH = Path("/Users/appleoppa/.hermes/data/pgg_archon.db")
HERMES_DIR = Path("/Users/appleoppa/.hermes")
HERMES_AGENT_DIR = HERMES_DIR / "hermes-agent"
RUST_MODULES_DIR = HERMES_AGENT_DIR / "rust_modules"
SKILLS_DIR = HERMES_DIR / "skills"
BIN_DIR = Path("/Users/appleoppa/.local/bin")
WORKSPACE_DIR = HERMES_DIR / "workspace"

MIN_CODE_LEN = 60  # 最少字符数才认为有实际价值


# ── 1. Python 函数/类提取器 ─────────────────────────────────────

def extract_python_genes(filepath: str) -> list[dict[str, Any]]:
    """Parse Python AST, extract function/class/method definitions."""
    genes = []
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source)
    except (SyntaxError, Exception) as e:
        return [{"error": f"parse failed: {e}"}]

    basename = os.path.basename(filepath).replace(".py", "")
    relpath = os.path.relpath(filepath, str(HERMES_DIR))

    for node in ast.walk(tree):
        # Top-level functions
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            lines = source.splitlines()
            start = node.lineno - 1
            end = getattr(node, "end_lineno", len(lines))
            code = "\n".join(lines[start:end])
            if len(code) < MIN_CODE_LEN:
                continue
            sig = f"def {node.name}({', '.join(a.arg for a in node.args.args if a.arg != 'self')})"
            genes.append({
                "name": f"{basename}.{node.name}",
                "pattern_type": "python_function",
                "source_repo": relpath,
                "code_snippet": code,
                "quality_score": 0.0,
                "metadata": json.dumps({"signature": sig, "type": "function"}),
            })

        # Top-level classes
        if isinstance(node, ast.ClassDef):
            lines = source.splitlines()
            start = node.lineno - 1
            end = getattr(node, "end_lineno", len(lines))
            code = "\n".join(lines[start:end])
            if len(code) < MIN_CODE_LEN:
                continue
            genes.append({
                "name": f"{basename}.{node.name}",
                "pattern_type": "python_class",
                "source_repo": relpath,
                "code_snippet": code,
                "quality_score": 0.0,
                "metadata": json.dumps({"type": "class"}),
            })

        # Async functions
        if isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_"):
            lines = source.splitlines()
            start = node.lineno - 1
            end = getattr(node, "end_lineno", len(lines))
            code = "\n".join(lines[start:end])
            if len(code) < MIN_CODE_LEN:
                continue
            genes.append({
                "name": f"{basename}.async_{node.name}",
                "pattern_type": "python_async_function",
                "source_repo": relpath,
                "code_snippet": code,
                "quality_score": 0.0,
                "metadata": json.dumps({"type": "async_function"}),
            })

    return genes


# ── 2. Rust 函数提取器 ─────────────────────────────────────────

def extract_rust_genes(filepath: str) -> list[dict[str, Any]]:
    """Extract Rust fn/struct/impl blocks via regex (no AST needed)."""
    genes = []
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as e:
        return [{"error": f"read failed: {e}"}]

    basename = Path(filepath).stem
    relpath = os.path.relpath(filepath, str(HERMES_DIR))
    lines = source.splitlines()

    # Extract pub fn / fn definitions with basic brace matching
    fn_pattern = re.compile(r'^\s*(pub\s+)?(unsafe\s+)?(async\s+)?fn\s+(\w+)')
    brace_depth = 0
    fn_start = -1
    fn_name = ""

    for i, line in enumerate(lines):
        # Track brace depth
        brace_depth += line.count("{") - line.count("}")

        if fn_start >= 0 and brace_depth <= 0:
            # End of function
            code = "\n".join(lines[fn_start:i+1])
            if len(code) >= MIN_CODE_LEN:
                genes.append({
                    "name": f"{basename}.{fn_name}",
                    "pattern_type": "rust_function",
                    "source_repo": relpath,
                    "code_snippet": code,
                    "quality_score": 0.0,
                    "metadata": json.dumps({"type": "rust_fn"}),
                })
            fn_start = -1
            fn_name = ""
            continue

        if fn_start >= 0:
            continue  # still inside function

        m = fn_pattern.match(line)
        if m:
            fn_name = m.group(4)
            if fn_name.startswith("_"):
                continue
            fn_start = i
            # Check if body starts on same line
            brace_depth = line.count("{") - line.count("}")
            if brace_depth <= 0:
                # No body (trait declaration) or one-liner
                fn_start = -1
                continue

    # Extract struct definitions
    struct_pattern = re.compile(r'^\s*(pub\s+)?struct\s+(\w+)')
    impl_start = -1
    impl_for = ""
    for i, line in enumerate(lines):
        m = struct_pattern.match(line)
        if m:
            struct_name = m.group(2)
            code = line.strip()
            if len(code) >= 30:
                genes.append({
                    "name": f"{basename}.struct_{struct_name}",
                    "pattern_type": "rust_struct",
                    "source_repo": relpath,
                    "code_snippet": code,
                    "quality_score": 0.0,
                    "metadata": json.dumps({"type": "rust_struct"}),
                })

    return genes


# ── 3. Shell script 提取器 ─────────────────────────────────────

def extract_shell_genes(filepath: str) -> list[dict[str, Any]]:
    """Extract shell functions from .sh scripts."""
    genes = []
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception:
        return []

    basename = Path(filepath).stem
    relpath = os.path.relpath(filepath, str(HERMES_DIR))
    lines = source.splitlines()

    func_pattern = re.compile(r'^\s*(\w+)\s*\(\)\s*\{')
    for i, line in enumerate(lines):
        m = func_pattern.match(line)
        if m:
            func_name = m.group(1)
            code = line
            j = i + 1
            # Find matching '}'
            depth = 1
            while j < len(lines) and depth > 0:
                depth += lines[j].count("{") - lines[j].count("}")
                j += 1
            code += "\n" + "\n".join(lines[i+1:j]).rstrip()
            if len(code) >= MIN_CODE_LEN:
                genes.append({
                    "name": f"{basename}.{func_name}",
                    "pattern_type": "shell_function",
                    "source_repo": relpath,
                    "code_snippet": code,
                    "quality_score": 0.0,
                    "metadata": json.dumps({"type": "shell_func"}),
                })
    return genes


# ── 4. 二进制描述提取器 ────────────────────────────────────────

def extract_binary_genes(bin_dir: Path) -> list[dict[str, Any]]:
    """Register compiled binaries as deployable genes."""
    genes = []
    if not bin_dir.exists():
        return genes
    for f in sorted(bin_dir.iterdir()):
        if f.is_file() and os.access(f, os.X_OK) and not f.name.startswith("."):
            # Check if it's a binary or script
            try:
                with open(f, "rb") as fh:
                    header = fh.read(4)
                    is_script = header[:2] == b"#!"
                    is_macho = header[:4] in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf")
                    is_elf = header[:4] == b"\x7fELF"
            except Exception:
                continue
            desc = "binary" if (is_macho or is_elf) else "script"
            size = f.stat().st_size
            genes.append({
                "name": f.name,
                "pattern_type": "sidecar_binary",
                "source_repo": str(f),
                "code_snippet": f"# {desc} binary: {f.name} ({size} bytes)\n# path: {f}",
                "quality_score": 0.0,
                "metadata": json.dumps({"type": desc, "size_bytes": size, "is_macho": is_macho, "is_elf": is_elf, "is_script": is_script}),
            })
    return genes


# ── 5. 扫描路由 ─────────────────────────────────────────────────

SOURCE_DEFS = {
    "agent": {
        "glob": str(HERMES_AGENT_DIR / "agent" / "*.py"),
        "extractor": extract_python_genes,
        "glob_exclude": [],
    },
    "hermes_core": {
        "glob": str(HERMES_AGENT_DIR / "*.py"),
        "extractor": extract_python_genes,
        "glob_exclude": ["setup.py"],
    },
    "rust_runners": {
        "glob": str(RUST_MODULES_DIR / "pgg_*_runner" / "src" / "main.rs"),
        "extractor": extract_rust_genes,
        "glob_exclude": [],
    },
    "rust_gates": {
        "glob": str(RUST_MODULES_DIR / "pgg_*_gate" / "src" / "main.rs"),
        "extractor": extract_rust_genes,
        "glob_exclude": [],
    },
    "rust_hermes_pgg": {
        "glob": str(RUST_MODULES_DIR / "hermes_pgg_*" / "src" / "*.rs"),
        "extractor": extract_rust_genes,
        "glob_exclude": [],
    },
    "skills_scripts": {
        "glob": str(SKILLS_DIR / "*" / "scripts" / "*.py"),
        "extractor": extract_python_genes,
        "glob_exclude": ["__pycache__"],
    },
    "skills_rust": {
        "glob": str(SKILLS_DIR / "*" / "scripts" / "*.rs"),
        "extractor": extract_rust_genes,
        "glob_exclude": [],
    },
    "skills_shell": {
        "glob": str(SKILLS_DIR / "*" / "scripts" / "*.sh"),
        "extractor": extract_shell_genes,
        "glob_exclude": [],
    },
    "binaries": {
        "extractor": lambda: extract_binary_genes(BIN_DIR),
        "glob": None,
    },
    "pgg_governance_python": {
        "glob": str(WORKSPACE_DIR / "pgg-archon-governance" / "**" / "*.py"),
        "extractor": extract_python_genes,
        "glob_exclude": ["__pycache__"],
    },
    "pgg_recovery_python": {
        "glob": str(WORKSPACE_DIR / "pgg-recovery" / "**" / "*.py"),
        "extractor": extract_python_genes,
        "glob_exclude": ["__pycache__"],
    },
}


def scan_source(key: str, defn: dict, dry_run: bool) -> list[dict]:
    """Scan one source definition, return genes."""
    genes = []
    extractor = defn["extractor"]
    has_glob = bool(defn.get("glob"))
    if not has_glob:
        # Callable extractor (for binaries)
        extracted = extractor()  # type: ignore[operator]
        if dry_run:
            print(f"  [{key}] {len(extracted)} candidate(s) from callable")  # type: ignore[arg-type]
        return extracted  # type: ignore[return-value]

    files = sorted(glob.glob(defn["glob"], recursive="**" in defn["glob"]))
    exclude = defn.get("glob_exclude", [])
    files = [f for f in files if not any(ex in f for ex in exclude)]
    for fp in files:
        if not os.path.isfile(fp):
            continue
        extracted = extractor(str(fp))
        errors = [e for e in extracted if "error" in e]
        valid = [e for e in extracted if "error" not in e]
        if dry_run and valid:
            print(f"  [{key}] {len(valid)} gene(s) from {Path(fp).name}" + (f" ({len(errors)} errors)" if errors else ""))
        genes.extend(valid)
    return genes


# ── 6. 写入DB ───────────────────────────────────────────────────

def write_genes_to_db(genes: list[dict], dry_run: bool = False) -> dict:
    """Write genes to pgg_archon.db."""
    if not genes:
        return {"written": 0, "skipped_dup": 0}

    db_path = str(DB_PATH)
    if dry_run:
        return {"written": len(genes), "skipped_dup": 0, "dry_run": True}

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    written = 0
    skipped_dup = 0
    for g in genes:
        # Check duplicate by name + source_repo
        cur.execute(
            "SELECT id FROM genes WHERE name = ? AND source_repo = ?",
            (g["name"], g["source_repo"]),
        )
        if cur.fetchone():
            skipped_dup += 1
            continue

        # Insert into genes table
        now = __import__("datetime").datetime.now().isoformat()
        cur.execute(
            "INSERT INTO genes (name, pattern_type, source_repo, code_snippet, quality_score, extracted_at) VALUES (?, ?, ?, ?, ?, ?)",
            (g["name"], g["pattern_type"], g["source_repo"], g["code_snippet"], g["quality_score"], now),
        )
        gene_id = cur.lastrowid

        # Insert into gene_lifecycle as candidate
        cur.execute(
            "INSERT INTO gene_lifecycle (gene_id, state, quality_score, candidate_at) VALUES (?, 'candidate', ?, ?)",
            (gene_id, g["quality_score"], now),
        )

        # Also insert into evolution_genes for full tracking
        cur.execute(
            "INSERT INTO evolution_genes (gene_id, state, generation, mutation_vector, fitness_before, fitness_after, created_at) VALUES (?, 'candidate', 0, 'seed', 0.0, 0.0, ?)",
            (gene_id, now),
        )

        written += 1
        if written % 50 == 0:
            conn.commit()

    conn.commit()
    conn.close()
    return {"written": written, "skipped_dup": skipped_dup}


# ── 7. 主入口 ───────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="PGG Gene Seeder — 从真实代码源提取基因为 candidate")
    parser.add_argument("--sources", default="all", help="all|agent|rust|skills|hermes_core|binaries|governance")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写入")
    args = parser.parse_args()

    print(f"PGG Gene Seeder v1 — DB: {DB_PATH}")
    print(f"Dry run: {args.dry_run}")
    print()

    source_keys = list(SOURCE_DEFS.keys())
    if args.sources != "all":
        source_keys = [k for k in source_keys if args.sources in k]

    total_genes = []
    per_source = {}

    for key in source_keys:
        defn = SOURCE_DEFS[key]
        if args.sources != "all" and args.sources not in key:
            continue
        genes = scan_source(key, defn, args.dry_run)
        per_source[key] = len(genes)
        total_genes.extend(genes)

    print()
    print("=== 汇总 ===")
    for key, count in sorted(per_source.items(), key=lambda x: -x[1]):
        print(f"  {key:25s} {count:5d} genes")
    print(f"  {'TOTAL':25s} {len(total_genes):5d} genes")

    if args.dry_run:
        # Show a sample
        sample = total_genes[:5] if total_genes else []
        for g in sample:
            print(f"\n  ── {g['name']} ({g['pattern_type']}) ──")
            print(f"      source: {g['source_repo']}")
            print(f"      code_len: {len(g['code_snippet'])} chars")
            print(f"      preview: {g['code_snippet'][:100]}...")
        print(f"\n[Dry-run] {len(total_genes)} candidate(s) would be written")
        return

    # Write
    result = write_genes_to_db(total_genes)
    print(f"\n  写入: {result['written']} genes")
    print(f"  跳过(重复): {result['skipped_dup']} genes")

    # Verify
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM gene_lifecycle WHERE state='candidate'")
    cand_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM genes WHERE pattern_type != 'auto_fusion' AND LENGTH(COALESCE(code_snippet,'')) > 10")
    real_code_count = cur.fetchone()[0]
    conn.close()
    print(f"  db candidate状态: {cand_count}")
    print(f"  db 真实可执行基因(非空非遗auto_fusion): {real_code_count}")


if __name__ == "__main__":
    main()