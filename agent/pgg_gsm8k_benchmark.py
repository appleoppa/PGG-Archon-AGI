#!/usr/bin/env python3
"""
Lightweight GSM8K-style arithmetic benchmark for PGG Archon readiness checks.

This file is intentionally self-contained and uses only the Python standard
library. It embeds ten small grade-school math word problems, provides a generic
benchmark_model(model_fn) runner, and can be executed directly:

    python3 pgg_gsm8k_benchmark.py

When run standalone, it uses a deterministic local text parser/solver so the
benchmark harness can be smoke-tested without any model or network dependency.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Union


# 1) Mia has 18 stickers. She gives 7 to Noah and then buys 12 more.
#    Step 1: 18 - 7 = 11 stickers remain after giving some away.
#    Step 2: 11 + 12 = 23 stickers after buying more.
#    Answer: 23
# 2) A bakery makes 6 trays of muffins with 8 muffins on each tray. It sells 19 muffins.
#    Step 1: 6 * 8 = 48 muffins made in total.
#    Step 2: 48 - 19 = 29 muffins left.
#    Answer: 29
# 3) Carlos reads 15 pages on Monday, twice as many pages on Tuesday, and 9 pages on Wednesday.
#    Step 1: Tuesday pages are 2 * 15 = 30.
#    Step 2: 15 + 30 + 9 = 54 pages read in total.
#    Answer: 54
# 4) Priya has 5 boxes with 14 pencils in each box. She shares them equally among 10 students.
#    Step 1: 5 * 14 = 70 pencils total.
#    Step 2: 70 / 10 = 7 pencils per student.
#    Answer: 7
# 5) A bus starts with 42 passengers. At the first stop, 13 get off and 8 get on.
#    Step 1: 42 - 13 = 29 passengers after people get off.
#    Step 2: 29 + 8 = 37 passengers after people get on.
#    Answer: 37
# 6) Lena saves $9 each week for 7 weeks. She then spends $23 on a game.
#    Step 1: 9 * 7 = 63 dollars saved.
#    Step 2: 63 - 23 = 40 dollars left.
#    Answer: 40
# 7) A farmer collects 96 eggs and packs them into cartons that hold 12 eggs each.
#    Step 1: 96 / 12 = 8 cartons.
#    Answer: 8
# 8) Jamal buys 3 notebooks for $4 each and 2 pens for $3 each.
#    Step 1: 3 * 4 = 12 dollars for notebooks.
#    Step 2: 2 * 3 = 6 dollars for pens.
#    Step 3: 12 + 6 = 18 dollars total.
#    Answer: 18
# 9) There are 27 red marbles and 35 blue marbles in a jar. Sam removes 16 marbles.
#    Step 1: 27 + 35 = 62 marbles initially.
#    Step 2: 62 - 16 = 46 marbles left.
#    Answer: 46
# 10) A class has 24 students. Three-fourths of them bring lunch from home.
#     Step 1: 24 * 3 / 4 = 18 students bring lunch from home.
#     Answer: 18
PROBLEMS: List[Dict[str, Any]] = [
    {
        "question": "Mia has 18 stickers. She gives 7 stickers to Noah and then buys 12 more stickers. How many stickers does Mia have now?",
        "answer": 23,
    },
    {
        "question": "A bakery makes 6 trays of muffins with 8 muffins on each tray. It sells 19 muffins before lunch. How many muffins are left?",
        "answer": 29,
    },
    {
        "question": "Carlos reads 15 pages on Monday, twice as many pages on Tuesday, and 9 pages on Wednesday. How many pages does he read in all?",
        "answer": 54,
    },
    {
        "question": "Priya has 5 boxes with 14 pencils in each box. She shares all the pencils equally among 10 students. How many pencils does each student get?",
        "answer": 7,
    },
    {
        "question": "A bus starts with 42 passengers. At the first stop, 13 passengers get off and 8 passengers get on. How many passengers are on the bus now?",
        "answer": 37,
    },
    {
        "question": "Lena saves $9 each week for 7 weeks. She then spends $23 on a game. How many dollars does she have left?",
        "answer": 40,
    },
    {
        "question": "A farmer collects 96 eggs and packs them into cartons that hold 12 eggs each. How many full cartons can the farmer fill?",
        "answer": 8,
    },
    {
        "question": "Jamal buys 3 notebooks for $4 each and 2 pens for $3 each. How many dollars does Jamal spend in total?",
        "answer": 18,
    },
    {
        "question": "There are 27 red marbles and 35 blue marbles in a jar. Sam removes 16 marbles. How many marbles are left in the jar?",
        "answer": 46,
    },
    {
        "question": "A class has 24 students. Three-fourths of them bring lunch from home. How many students bring lunch from home?",
        "answer": 18,
    },
]

Number = Union[int, float]
ModelFn = Callable[[str], Any]


def _to_number(value: Any) -> Optional[Number]:
    """Extract the final numeric answer from a model response or raw value."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if float(value).is_integer() else float(value)

    text = str(value).strip()
    if not text:
        return None

    # Prefer explicit final-answer formats when present.
    answer_patterns = [
        r"(?:answer|final answer|therefore|so)\s*(?:is|=|:)?\s*([-+]?\d+(?:\.\d+)?)",
        r"####\s*([-+]?\d+(?:\.\d+)?)",
    ]
    for pattern in answer_patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            number = float(matches[-1])
            return int(number) if number.is_integer() else number

    # Fall back to the last number in the response, which matches common GSM8K output.
    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", text.replace(",", ""))
    if not matches:
        return None
    number = float(matches[-1])
    return int(number) if number.is_integer() else number


def _numbers(question: str) -> List[int]:
    """Return integer quantities from a question, including simple word fractions."""
    normalized = question.lower().replace(",", "")
    nums = [int(x) for x in re.findall(r"\$?(\d+)", normalized)]
    return nums


def local_solver(question: str) -> str:
    """
    Deterministic parser for the embedded benchmark questions.

    This is deliberately simple: it recognizes the small set of arithmetic
    constructions used below (add/subtract, multiplication, equal sharing, and a
    three-fourths phrase). It is not intended to be a general GSM8K solver.
    """
    q = question.lower()
    nums = _numbers(q)

    if "stickers" in q and "gives" in q and "buys" in q:
        result = nums[0] - nums[1] + nums[2]
    elif "trays of muffins" in q and "sells" in q:
        result = nums[0] * nums[1] - nums[2]
    elif "twice as many" in q and "pages" in q:
        result = nums[0] + (2 * nums[0]) + nums[1]
    elif "boxes" in q and "pencils" in q and "equally" in q:
        result = (nums[0] * nums[1]) / nums[2]
    elif "bus" in q and "get off" in q and "get on" in q:
        result = nums[0] - nums[1] + nums[2]
    elif "saves" in q and "each week" in q and "spends" in q:
        result = nums[0] * nums[1] - nums[2]
    elif "eggs" in q and "cartons" in q:
        result = nums[0] / nums[1]
    elif "notebooks" in q and "pens" in q:
        result = nums[0] * nums[1] + nums[2] * nums[3]
    elif "red marbles" in q and "blue marbles" in q and "removes" in q:
        result = nums[0] + nums[1] - nums[2]
    elif "three-fourths" in q or "three fourths" in q or "3/4" in q:
        result = nums[0] * 3 / 4
    else:
        raise ValueError("local_solver does not recognize this question pattern")

    if float(result).is_integer():
        result = int(result)
    return f"The answer is {result}."


def _answers_equal(predicted: Optional[Number], expected: Number) -> bool:
    if predicted is None:
        return False
    return abs(float(predicted) - float(expected)) < 1e-9


def benchmark_model(model_fn: ModelFn) -> float:
    """
    Run the 10-question mini benchmark against model_fn.

    model_fn is called once per problem as model_fn(question). Its return value
    may be a number or text containing a final numeric answer. The function
    returns accuracy as a 0-100 score.
    """
    correct = 0
    for problem in PROBLEMS:
        response = model_fn(problem["question"])
        predicted = _to_number(response)
        if _answers_equal(predicted, problem["answer"]):
            correct += 1
    return correct * 100.0 / len(PROBLEMS)


def _env_llm_model_fn(question: str) -> str:
    """
    Minimal stdlib JSON HTTP client for optional local/API model testing.

    Set PGG_GSM8K_API_URL to an endpoint that accepts POST JSON with a "prompt"
    field. Optionally set PGG_GSM8K_API_KEY for a Bearer token and
    PGG_GSM8K_MODEL for a model name. Common response shapes are supported:
    {"text": ...}, {"response": ...}, {"answer": ...}, or OpenAI-style
    {"choices": [{"message": {"content": ...}}]}.
    """
    url = os.environ.get("PGG_GSM8K_API_URL")
    if not url:
        return local_solver(question)

    payload = {
        "model": os.environ.get("PGG_GSM8K_MODEL", "pgg-archon"),
        "prompt": (
            "Solve the arithmetic word problem. Show brief reasoning and end "
            "with 'Answer: <number>'.\n\nQuestion: " + question
        ),
        "max_tokens": 256,
        "temperature": 0,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("PGG_GSM8K_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"PGG_GSM8K_API_URL request failed: {exc}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    for key in ("text", "response", "answer", "content", "completion"):
        if key in parsed:
            return str(parsed[key])
    choices = parsed.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict) and "content" in message:
                return str(message["content"])
            if "text" in first:
                return str(first["text"])
    return raw


def run_mini_gsm8k() -> float:
    """
    Run the mini benchmark and print per-problem results.

    If PGG_GSM8K_API_URL is set, an stdlib HTTP JSON client is used. Otherwise,
    the standalone deterministic local_solver is used. Returns accuracy 0-100.
    """
    model_fn: ModelFn = _env_llm_model_fn if os.environ.get("PGG_GSM8K_API_URL") else local_solver
    correct = 0

    print("PGG Archon mini GSM8K-style benchmark")
    print(f"Problems: {len(PROBLEMS)}")
    print(f"Runner: {'HTTP API via PGG_GSM8K_API_URL' if os.environ.get('PGG_GSM8K_API_URL') else 'local_solver'}")
    print("-" * 72)

    for index, problem in enumerate(PROBLEMS, start=1):
        response = model_fn(problem["question"])
        predicted = _to_number(response)
        expected = problem["answer"]
        ok = _answers_equal(predicted, expected)
        correct += int(ok)
        status = "PASS" if ok else "FAIL"
        print(f"{index:02d}. {status} expected={expected!r} predicted={predicted!r}")
        print(f"    Q: {problem['question']}")
        print(f"    Response: {str(response).strip()}")

    accuracy = correct * 100.0 / len(PROBLEMS)
    print("-" * 72)
    print(f"Accuracy: {accuracy:.1f}% ({correct}/{len(PROBLEMS)})")
    return accuracy


if __name__ == "__main__":
    score = run_mini_gsm8k()
    sys.exit(0 if score == 100.0 else 1)
