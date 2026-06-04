"""Bounded PGG Archon benchmark loader.

Loads benchmark items from a small, hand-curated JSONL corpus that ships
with the harness. The corpus is intentionally tiny (5 items per bench)
to keep the harness a status surface, not a real L4-L5 evaluation.

The first item in each benchmark is a self-test: the harness asserts
that the loader returns at least N items and that each item has
`question` and `answer` fields.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CORPUS_DIR = Path(__file__).parent / "corpus"

CORPUS: dict[str, list[dict[str, Any]]] = {
    "mmlu": [
        {"id": "mmlu-001", "question": "2+2=?", "answer": "4", "category": "math"},
        {"id": "mmlu-002", "question": "What is the capital of France?", "answer": "Paris", "category": "geography"},
        {"id": "mmlu-003", "question": "H2O is the chemical formula for?", "answer": "water", "category": "chemistry"},
        {"id": "mmlu-004", "question": "Who wrote Hamlet?", "answer": "Shakespeare", "category": "literature"},
        {"id": "mmlu-005", "question": "Largest planet in our solar system?", "answer": "Jupiter", "category": "astronomy"},
    ],
    "gsm8k": [
        {"id": "gsm-001", "question": "If 3 apples cost $6, how much does 1 apple cost?", "answer": "2", "category": "arithmetic"},
        {"id": "gsm-002", "question": "A train travels 60 km in 1 hour. How far in 3 hours?", "answer": "180", "category": "rate"},
        {"id": "gsm-003", "question": "12 divided by 4?", "answer": "3", "category": "arithmetic"},
        {"id": "gsm-004", "question": "20% of 150?", "answer": "30", "category": "percentage"},
        {"id": "gsm-005", "question": "Sum of 17 and 25?", "answer": "42", "category": "arithmetic"},
    ],
    "bigbench": [
        {"id": "bb-001", "question": "Translate 'good morning' to Spanish.", "answer": "buenos dias", "category": "translation"},
        {"id": "bb-002", "question": "If all roses are flowers and some flowers fade quickly, can we conclude some roses fade quickly?", "answer": "no", "category": "logic"},
        {"id": "bb-003", "question": "What is the opposite of 'ancient'?", "answer": "modern", "category": "word_opposite"},
        {"id": "bb-004", "question": "How many legs does a spider have?", "answer": "8", "category": "factual"},
        {"id": "bb-005", "question": "What comes next: 2, 4, 8, 16, ?", "answer": "32", "category": "sequence"},
    ],
}


@dataclass
class BenchItem:
    id: str
    question: str
    answer: str
    category: str


def load_benchmark(name: str) -> list[BenchItem]:
    raw = CORPUS.get(name, [])
    return [BenchItem(id=r["id"], question=r["question"], answer=r["answer"], category=r["category"]) for r in raw]


def list_benchmarks() -> list[str]:
    return list(CORPUS.keys())
