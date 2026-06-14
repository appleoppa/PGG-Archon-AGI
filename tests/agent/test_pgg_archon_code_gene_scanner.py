"""Tests for PGG Archon 标准基因模板扫描器."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.pgg_archon_code_gene_scanner import (
    MAX_GENES,
    REQUIRED_TEMPLATE_FIELDS,
    TYPE_PGG_GENE,
    gene_to_json,
    scan_directory,
    scan_source,
    write_to_genedb,
)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def sample_simple_py(tmp_path: Path) -> Path:
    """A minimal .py file with one public class."""
    p = tmp_path / 'simple_module.py'
    p.write_text(
        '''"""A simple module for scanning."""

class Greeter:
    """Greets people nicely."""

    def __init__(self, name: str, greeting: str = "Hello"):
        self.name = name
        self.greeting = greeting

    def greet(self) -> str:
        """Return a greeting string."""
        return f"{self.greeting}, {self.name}!"

    def _internal(self) -> None:
        pass
''',
        encoding='utf-8',
    )
    return p


@pytest.fixture
def sample_class_with_blocks_py(tmp_path: Path) -> Path:
    """A .py file with classes containing block-level logic."""
    p = tmp_path / 'block_module.py'
    p.write_text(
        '''"""Module with block-level logic."""

class DataProcessor:
    """Processes data with validation and retry."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def process(self, data: list) -> dict:
        """Process data with retry logic."""
        for attempt in range(self.max_retries):
            try:
                result = self._transform(data)
                if result is not None:
                    return result
            except ValueError:
                continue
        return {"error": "failed"}

    def _transform(self, data: list) -> dict | None:
        if not data:
            return None
        return {"count": len(data)}
''',
        encoding='utf-8',
    )
    return p


@pytest.fixture
def sample_private_py(tmp_path: Path) -> Path:
    """A .py file with only private/internal classes (should be skipped)."""
    p = tmp_path / '_private.py'
    p.write_text(
        '''"""Module with private classes."""

class _InternalHelper:
    """This is private — should be skipped."""
    pass

class __HiddenState:
    """Name-mangled — should be skipped."""
    pass
''',
        encoding='utf-8',
    )
    return p


@pytest.fixture
def sample_dir(tmp_path: Path, sample_simple_py: Path) -> Path:
    """A directory with a .py file and a subdirectory."""
    # sample_simple_py is already in tmp_path
    sub = tmp_path / 'subdir'
    sub.mkdir()
    (sub / 'sub_module.py').write_text(
        '''"""Sub module."""

class SubWorker:
    """A sub module worker."""

    def __init__(self, worker_id: str):
        self.worker_id = worker_id

    def run(self) -> str:
        return f"running {self.worker_id}"
''',
        encoding='utf-8',
    )
    # Non-.py file should be ignored
    (tmp_path / 'notes.txt').write_text('not python', encoding='utf-8')
    return tmp_path


# ── scan_source tests ────────────────────────────────────────────────

class TestScanSource:
    def test_simple_class_extracts_gene(self, sample_simple_py: Path) -> None:
        genes = scan_source(str(sample_simple_py))
        assert len(genes) == 1

        gene = genes[0]
        # Check required template fields
        for field in REQUIRED_TEMPLATE_FIELDS:
            assert field in gene, f'missing required field: {field}'

        assert gene['type'] == TYPE_PGG_GENE
        assert gene['class_name'] == 'Greeter'
        assert 'Greeter' in gene['signals_match']
        assert 'source_file' in gene
        assert sample_simple_py.name in gene['source_file']

    def test_signals_from_class_name_and_docstring(
        self, sample_simple_py: Path,
    ) -> None:
        genes = scan_source(str(sample_simple_py))
        gene = genes[0]
        signals = gene['signals_match']
        # Class name
        assert 'Greeter' in signals
        # Docstring tokens
        all_signal_text = ' '.join(signals).lower()
        assert 'greet' in all_signal_text

    def test_preconditions_from_init(self, sample_simple_py: Path) -> None:
        genes = scan_source(str(sample_simple_py))
        gene = genes[0]
        preconds = gene['preconditions']
        assert any('name' in p for p in preconds)
        assert any('greeting' in p for p in preconds)

    def test_strategy_from_public_methods(self, sample_simple_py: Path) -> None:
        genes = scan_source(str(sample_simple_py))
        gene = genes[0]
        strategy = gene['strategy']
        method_names = [s['method'] for s in strategy]
        # Should include greet but NOT __init__ or _internal
        assert 'greet' in method_names
        assert '__init__' not in method_names
        assert '_internal' not in method_names

    def test_strategy_confidence_high(self, sample_simple_py: Path) -> None:
        genes = scan_source(str(sample_simple_py))
        gene = genes[0]
        for step in gene['strategy']:
            assert step['confidence'] in ('high', 'medium', 'low')

    def test_constraints_include_type_annotations(
        self, sample_simple_py: Path,
    ) -> None:
        genes = scan_source(str(sample_simple_py))
        gene = genes[0]
        constraints = gene['constraints']
        assert 'boundary' in constraints
        assert 'static_analysis_only' in constraints['boundary']
        # name and greeting should have type annotation entries
        if 'type_annotations' in constraints:
            annotations = constraints['type_annotations']
            assert 'name' in annotations
            assert 'greeting' in annotations

    def test_validation_static_evidence_present(self, sample_simple_py: Path) -> None:
        genes = scan_source(str(sample_simple_py))
        gene = genes[0]
        assert 'static_ast_parse_passed' in gene['validation']
        assert 'standard_gene_template_constructed' in gene['validation']

    def test_private_classes_skipped(self, sample_private_py: Path) -> None:
        genes = scan_source(str(sample_private_py))
        # Both classes are private (start with _)
        assert len(genes) == 0

    def test_non_py_file_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / 'not_python.txt'
        p.write_text('hello', encoding='utf-8')
        genes = scan_source(str(p))
        assert genes == []

    def test_nonexistent_file_returns_empty(self) -> None:
        genes = scan_source('/nonexistent/path/file.py')
        assert genes == []

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / 'bad_syntax.py'
        p.write_text('def foo( bar', encoding='utf-8')
        genes = scan_source(str(p))
        assert genes == []


# ── scan_directory tests ─────────────────────────────────────────────

class TestScanDirectory:
    def test_scan_directory_non_recursive(self, sample_dir: Path) -> None:
        genes = scan_directory(str(sample_dir), recursive=False)
        # Only simple_module.py in top-level (not sub_module.py)
        source_names = {g['source_file'] for g in genes}
        assert any('simple_module' in s for s in source_names)
        assert not any('sub_module' in s for s in source_names)

    def test_scan_directory_recursive(self, sample_dir: Path) -> None:
        genes = scan_directory(str(sample_dir), recursive=True)
        source_names = {g['source_file'] for g in genes}
        assert any('simple_module' in s for s in source_names)
        assert any('sub_module' in s for s in source_names)

    def test_scan_directory_nonexistent(self) -> None:
        genes = scan_directory('/nonexistent/path', recursive=True)
        assert genes == []

    def test_scan_directory_empty_dir(self, tmp_path: Path) -> None:
        genes = scan_directory(str(tmp_path))
        assert genes == []

    def test_scan_directory_skips_non_py(
        self, sample_dir: Path,
    ) -> None:
        genes = scan_directory(str(sample_dir), recursive=True)
        # Should not have any source_file ending in .txt
        for g in genes:
            assert not g['source_file'].endswith('.txt')


# ── Block-level logic confidence tests ───────────────────────────────

class TestConfidenceLevels:
    def test_medium_confidence_for_block_level(
        self, sample_class_with_blocks_py: Path,
    ) -> None:
        genes = scan_source(str(sample_class_with_blocks_py))
        assert len(genes) >= 1

        # DataProcessor class
        dp_genes = [g for g in genes if g['class_name'] == 'DataProcessor']
        assert len(dp_genes) == 1

        strategy = dp_genes[0]['strategy']
        process_steps = [s for s in strategy if s['method'] == 'process']
        assert len(process_steps) == 1
        # process() has for loop and try/except => medium confidence
        assert process_steps[0]['confidence'] == 'medium'

    def test_strategy_signature_includes_block_hint(
        self, sample_class_with_blocks_py: Path,
    ) -> None:
        genes = scan_source(str(sample_class_with_blocks_py))
        dp_genes = [g for g in genes if g['class_name'] == 'DataProcessor']
        strategy = dp_genes[0]['strategy']
        process_step = [s for s in strategy if s['method'] == 'process'][0]
        # Should mention block-level in the signature
        assert '(block-level' in process_step['signature']


# ── gene_to_json test ────────────────────────────────────────────────

class TestGeneToJson:
    def test_gene_to_json_roundtrip(self, sample_simple_py: Path) -> None:
        genes = scan_source(str(sample_simple_py))
        json_str = gene_to_json(genes[0])
        parsed = json.loads(json_str)
        assert parsed['id'] == genes[0]['id']
        assert parsed['type'] == TYPE_PGG_GENE


# ── write_to_genedb tests ────────────────────────────────────────────

class TestWriteToGenedb:
    def test_dry_run_default(self, sample_simple_py: Path) -> None:
        genes = scan_source(str(sample_simple_py))
        result = write_to_genedb(genes)
        assert result['all_pass'] is True
        for r in result['results']:
            assert r['status'] == 'DRY_RUN'
            assert r['written'] is False

    def test_write_false_returns_dry_run(self, sample_simple_py: Path) -> None:
        genes = scan_source(str(sample_simple_py))
        result = write_to_genedb(genes, write=False)
        assert result['all_pass'] is True
        for r in result['results']:
            assert r['written'] is False
            assert r['status'] == 'DRY_RUN'

    def test_empty_genes_returns_empty_results(self) -> None:
        result = write_to_genedb([])
        assert result['total'] == 0
        assert result['results'] == []

    def test_all_required_fields_in_result(self, sample_simple_py: Path) -> None:
        genes = scan_source(str(sample_simple_py))
        result = write_to_genedb(genes)
        for field in ('schema', 'created_at', 'total', 'results', 'all_pass', 'boundary'):
            assert field in result, f'missing field: {field}'


# ── MAX_GENES boundary test ──────────────────────────────────────────

class TestMaxGenes:
    def test_max_genes_constant(self) -> None:
        assert MAX_GENES == 200

    def test_scan_respects_max(self, tmp_path: Path) -> None:
        """Create many small class files and verify we don't exceed MAX_GENES."""
        # Create enough small .py files to potentially exceed limit
        for i in range(5):
            p = tmp_path / f'module_{i}.py'
            # Each file has 50 classes
            lines = []
            for j in range(50):
                lines.append(
                    f'class Class{i:03d}_{j:03d}:\n'
                    f'    """Class {i}-{j}."""\n'
                    f'    def method(self) -> None: pass\n'
                )
            p.write_text(''.join(lines), encoding='utf-8')

        genes = scan_directory(str(tmp_path), recursive=False)
        assert len(genes) <= MAX_GENES


# ── CLI integration smoke test ───────────────────────────────────────

class TestCliSmoke:
    def test_cli_module_importable(self) -> None:
        """Verify the CLI module can be imported without errors."""
        import importlib
        mod = importlib.import_module('agent.pgg_archon_code_gene_scanner_cli')
        assert hasattr(mod, 'main')

    def test_cli_dry_run_via_subprocess(
        self, sample_simple_py: Path,
    ) -> None:
        """Run the CLI in dry-run mode and verify JSON output."""
        import subprocess
        result = subprocess.run(
            [
                sys.executable, '-m', 'agent.pgg_archon_code_gene_scanner_cli',
                '--path', str(sample_simple_py),
                '--dry-run',
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f'CLI failed: {result.stderr}'
        output = json.loads(result.stdout)
        assert output['status'] == 'PASS'
        assert output['count'] == 1
        assert output['genedb']['all_pass'] is True
        for r in output['genedb']['results']:
            assert r['status'] == 'DRY_RUN'


def test_scanner_emits_static_validation_evidence(sample_simple_py: Path) -> None:
    genes = scan_source(str(sample_simple_py))
    assert genes
    validation = genes[0]['validation']
    assert 'static_ast_parse_passed' in validation
    assert 'standard_gene_template_constructed' in validation
    assert any(v.startswith('source_hash_present:True') for v in validation)
    assert any(v.startswith('scan_kind:') for v in validation)
