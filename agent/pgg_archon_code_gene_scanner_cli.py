#!/usr/bin/env python3
"""PGG Archon 标准基因模板扫描器 CLI。

输入 Python 源码目录/文件，输出标准 5 层基因 JSON。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agent.pgg_archon_code_gene_scanner import (
    scan_directory,
    scan_source,
    write_to_genedb,
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description='PGG Archon 标准基因模板扫描器 — 从 Python 源码提取 5 层基因',
    )
    ap.add_argument(
        '--path',
        required=True,
        help='Python 源码目录或 .py 文件路径（必须）',
    )
    ap.add_argument(
        '--recursive',
        action='store_true',
        help='递归扫描子目录（仅对目录有效）',
    )
    ap.add_argument(
        '--write',
        action='store_true',
        help='写入 GeneDB 为 candidate（默认 --dry-run 不写入）',
    )
    ap.add_argument(
        '--promote',
        action='store_true',
        help='写入时标记为 verified（需要 --write）',
    )
    ap.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='默认 True：预览结果，不写入 GeneDB',
    )
    args = ap.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(
            json.dumps(
                {
                    'status': 'BLOCKED',
                    'error': f'path not found: {args.path}',
                    'boundary': 'pgg_archon_code_gene_scanner_cli',
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        return 2

    # Scan
    if target.is_dir():
        genes = scan_directory(str(target), recursive=args.recursive)
    else:
        genes = scan_source(str(target))

    if not genes:
        print(
            json.dumps(
                {
                    'status': 'BLOCKED',
                    'warning': 'no candidate genes found',
                    'genes': [],
                    'count': 0,
                    'boundary': 'pgg_archon_code_gene_scanner_cli',
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        return 2

    # Write to GeneDB if requested (and not dry-run)
    genedb_result = None
    if args.write and not args.dry_run:
        genedb_result = write_to_genedb(
            genes,
            write=True,
            promote=args.promote,
        )
    elif args.dry_run or not args.write:
        # Dry-run validation
        genedb_result = write_to_genedb(
            genes,
            write=False,
            promote=False,
        )

    output = {
        'status': 'PASS',
        'count': len(genes),
        'path': str(target),
        'recursive': args.recursive if target.is_dir() else False,
        'genes': genes,
        'genedb': genedb_result,
        'boundary': 'pgg_archon_code_gene_scanner_cli',
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
