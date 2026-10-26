"""Shared helpers for verifier training and evaluation (Phase 4)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "planners"))
sys.path.insert(0, str(ROOT / "verifier"))
from prompts import problem_text          # noqa: E402
from strips_sim import load_problem       # noqa: E402

_CACHE = {}


def problem_description(problem_dir, pid):
    key = (str(problem_dir), pid)
    if key not in _CACHE:
        _CACHE[key] = problem_text(load_problem(Path(problem_dir) / f"{pid}.pddl"))
    return _CACHE[key]


def verifier_text(problem_dir, pid, prefix, action):
    """Text the verifier reads: the problem, the steps so far, and the step to judge."""
    steps = "\n".join(prefix) if prefix else "(none)"
    return (f"{problem_description(problem_dir, pid)}\n"
            f"Steps so far:\n{steps}\nNext step: {action}")


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def auroc(y, s):
    """AUROC without sklearn (rank-based, ties averaged)."""
    pairs = sorted(zip(s, y))
    n_pos = sum(y)
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    rank_sum, i = 0.0, 0
    while i < len(pairs):
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        avg = (i + 1 + j) / 2
        rank_sum += avg * sum(1 for k in range(i, j) if pairs[k][1])
        i = j
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
