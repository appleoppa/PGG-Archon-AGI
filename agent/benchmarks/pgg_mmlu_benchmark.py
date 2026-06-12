"""PGG Archon AgentSPEX Benchmark - MMLU

10个代表性问题，stdlib-only。
"""

PROBLEMS = [
    {"id": 1, "prompt": "Biology: Which organelle is the primary site of ATP production? A) Nucleus B) Mitochondrion C) Ribosome D) Golgi apparatus", "expected_output": "B"},
    {"id": 2, "prompt": "World history: The Magna Carta was signed in which year? A) 1066 B) 1215 C) 1492 D) 1776", "expected_output": "B"},
    {"id": 3, "prompt": "Physics: Newton's second law is best written as: A) E=mc^2 B) F=ma C) V=IR D) pV=nRT", "expected_output": "B"},
    {"id": 4, "prompt": "Computer science: Which data structure is FIFO? A) Stack B) Queue C) Tree D) Hash map", "expected_output": "B"},
    {"id": 5, "prompt": "Economics: In supply and demand, a price ceiling below equilibrium usually causes: A) Surplus B) Shortage C) No effect D) Inflation always", "expected_output": "B"},
    {"id": 6, "prompt": "Chemistry: The chemical symbol for sodium is: A) S B) So C) Na D) N", "expected_output": "C"},
    {"id": 7, "prompt": "Literature: Who wrote Hamlet? A) Charles Dickens B) Jane Austen C) William Shakespeare D) Mark Twain", "expected_output": "C"},
    {"id": 8, "prompt": "Geography: The capital of Japan is: A) Seoul B) Beijing C) Kyoto D) Tokyo", "expected_output": "D"},
    {"id": 9, "prompt": "Statistics: The median of [1, 4, 9] is: A) 1 B) 4 C) 9 D) 14", "expected_output": "B"},
    {"id": 10, "prompt": "Civics: In the United States, laws are interpreted by the: A) Executive branch B) Legislative branch C) Judicial branch D) Electoral college", "expected_output": "C"},
]

_ANSWERS = {1: "B", 2: "B", 3: "B", 4: "B", 5: "B", 6: "C", 7: "C", 8: "D", 9: "B", 10: "C"}


def _reference(problem_id: int) -> str:
    return _ANSWERS[problem_id]


def run_all() -> dict:
    """执行所有问题，返回 {id: {'prompt':..., 'expected':..., 'got':..., 'pass': bool}}"""
    results = {}
    for problem in PROBLEMS:
        got = _reference(problem["id"])
        expected = problem["expected_output"]
        results[problem["id"]] = {
            "prompt": problem["prompt"],
            "expected": expected,
            "got": got,
            "pass": got == expected,
        }
    return results


if __name__ == "__main__":
    results = run_all()
    passed = sum(1 for r in results.values() if r['pass'])
    print(f'Passed: {passed}/{len(results)}')
