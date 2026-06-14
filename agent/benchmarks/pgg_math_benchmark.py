"""PGG Archon AgentSPEX Benchmark - MATH

10个代表性问题，stdlib-only。
"""

from fractions import Fraction
import math

PROBLEMS = [
    {"id": 1, "prompt": "Solve: 2x + 5 = 17. Give x.", "expected_output": "6"},
    {"id": 2, "prompt": "A right triangle has legs 6 and 8. Find the hypotenuse.", "expected_output": "10"},
    {"id": 3, "prompt": "What is the sum of the first 20 positive integers?", "expected_output": "210"},
    {"id": 4, "prompt": "Find the larger root of x^2 - 5x + 6 = 0.", "expected_output": "3"},
    {"id": 5, "prompt": "Compute the slope through points (2, 3) and (6, 11).", "expected_output": "2"},
    {"id": 6, "prompt": "A 30-60-90 triangle has short leg 5. Find its area.", "expected_output": "25*sqrt(3)/2"},
    {"id": 7, "prompt": "Simplify 3/4 + 5/6 as a reduced fraction.", "expected_output": "19/12"},
    {"id": 8, "prompt": "If f(x)=x^2-1, compute f(4)-f(2).", "expected_output": "12"},
    {"id": 9, "prompt": "How many 3-person committees can be chosen from 8 people?", "expected_output": "56"},
    {"id": 10, "prompt": "The mean of 4, 8, 10, and x is 9. Find x.", "expected_output": "14"},
]


def _reference(problem_id: int) -> str:
    if problem_id == 1:
        return str((17 - 5) // 2)
    if problem_id == 2:
        return str(int(math.hypot(6, 8)))
    if problem_id == 3:
        return str(sum(range(1, 21)))
    if problem_id == 4:
        roots = [2, 3]
        return str(max(roots))
    if problem_id == 5:
        return str((11 - 3) // (6 - 2))
    if problem_id == 6:
        return "25*sqrt(3)/2"
    if problem_id == 7:
        return str(Fraction(3, 4) + Fraction(5, 6))
    if problem_id == 8:
        f = lambda x: x * x - 1
        return str(f(4) - f(2))
    if problem_id == 9:
        return str(math.comb(8, 3))
    if problem_id == 10:
        return str(9 * 4 - (4 + 8 + 10))
    raise KeyError(problem_id)


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
