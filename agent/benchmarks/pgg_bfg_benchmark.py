"""PGG Archon AgentSPEX Benchmark - BFG/BugFinder

10个代表性问题，stdlib-only。
"""

PROBLEMS = [
    {"id": 1, "prompt": "Bug: average(nums) uses sum(nums)/len(nums) but crashes on empty input. Fix to return 0 for empty list.", "expected_output": "0"},
    {"id": 2, "prompt": "Bug: is_even(n) returns n % 2 == 1. Fix it.", "expected_output": "True"},
    {"id": 3, "prompt": "Bug: max_value starts best=0, failing all-negative lists. Fix it.", "expected_output": "-2"},
    {"id": 4, "prompt": "Bug: reverse_string(s) returns s.reverse(), invalid for str. Fix it.", "expected_output": "'cba'"},
    {"id": 5, "prompt": "Bug: count_items(xs) increments by item value instead of 1. Fix it.", "expected_output": "4"},
    {"id": 6, "prompt": "Bug: safe_get(d,k,default) indexes d[k] and raises KeyError. Fix it.", "expected_output": "'missing'"},
    {"id": 7, "prompt": "Bug: join_words(words) uses ''.join, missing spaces. Fix it.", "expected_output": "'hello world'"},
    {"id": 8, "prompt": "Bug: clamp(x, lo, hi) applies min(lo, max(hi, x)). Fix order.", "expected_output": "10"},
    {"id": 9, "prompt": "Bug: parse_int(s) fails on surrounding whitespace. Fix it.", "expected_output": "42"},
    {"id": 10, "prompt": "Bug: append_item(xs, item, acc=[]) has mutable default state. Fix it.", "expected_output": "['b']"},
]


def _reference(problem_id: int) -> str:
    if problem_id == 1:
        nums = []
        got = sum(nums) / len(nums) if nums else 0
    elif problem_id == 2:
        got = 10 % 2 == 0
    elif problem_id == 3:
        got = max([-5, -2, -9])
    elif problem_id == 4:
        got = "abc"[::-1]
    elif problem_id == 5:
        got = len([10, 20, 30, 40])
    elif problem_id == 6:
        got = {"present": 1}.get("absent", "missing")
    elif problem_id == 7:
        got = " ".join(["hello", "world"])
    elif problem_id == 8:
        x, lo, hi = 15, 0, 10
        got = min(hi, max(lo, x))
    elif problem_id == 9:
        got = int(" 42\n".strip())
    elif problem_id == 10:
        def append_item(xs, item):
            acc = list(xs)
            acc.append(item)
            return acc
        _ = append_item([], "a")
        got = append_item([], "b")
    else:
        raise KeyError(problem_id)
    return repr(got) if isinstance(got, str) else str(got)


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
