"""PGG Archon AgentSPEX Benchmark - MBPP

10个代表性问题，stdlib-only。
"""

PROBLEMS = [
    {"id": 1, "prompt": "Write a function to return the largest number in a list.", "expected_output": "9"},
    {"id": 2, "prompt": "Write a function to remove duplicates while preserving order.", "expected_output": "[3, 1, 2, 4]"},
    {"id": 3, "prompt": "Write a function to count words in a sentence.", "expected_output": "5"},
    {"id": 4, "prompt": "Write a function to check whether a number is prime.", "expected_output": "True"},
    {"id": 5, "prompt": "Write a function to transpose a 2x3 matrix.", "expected_output": "[[1, 4], [2, 5], [3, 6]]"},
    {"id": 6, "prompt": "Write a function to convert Celsius to Fahrenheit.", "expected_output": "77.0"},
    {"id": 7, "prompt": "Write a function to find common elements of two lists sorted increasingly.", "expected_output": "[2, 4]"},
    {"id": 8, "prompt": "Write a function to compute digit sum of a positive integer.", "expected_output": "15"},
    {"id": 9, "prompt": "Write a function to rotate a list left by k positions.", "expected_output": "[3, 4, 5, 1, 2]"},
    {"id": 10, "prompt": "Write a function to group words by their first letter.", "expected_output": "{'a': ['ant', 'ape'], 'b': ['bat', 'bee']}"},
]


def _reference(problem_id: int) -> str:
    if problem_id == 1:
        got = max([4, 9, 1, 7])
    elif problem_id == 2:
        seen = set()
        got = []
        for x in [3, 1, 3, 2, 1, 4]:
            if x not in seen:
                seen.add(x)
                got.append(x)
    elif problem_id == 3:
        got = len("simple benchmark problems are useful".split())
    elif problem_id == 4:
        n = 29
        got = n > 1 and all(n % d for d in range(2, int(n ** 0.5) + 1))
    elif problem_id == 5:
        matrix = [[1, 2, 3], [4, 5, 6]]
        got = [list(col) for col in zip(*matrix)]
    elif problem_id == 6:
        got = 25 * 9 / 5 + 32
    elif problem_id == 7:
        got = sorted(set([1, 2, 4, 6]) & set([2, 3, 4, 5]))
    elif problem_id == 8:
        got = sum(int(ch) for ch in str(12345))
    elif problem_id == 9:
        xs, k = [1, 2, 3, 4, 5], 2
        got = xs[k:] + xs[:k]
    elif problem_id == 10:
        got = {}
        for word in ["ant", "ape", "bat", "bee"]:
            got.setdefault(word[0], []).append(word)
    else:
        raise KeyError(problem_id)
    return str(got)


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
