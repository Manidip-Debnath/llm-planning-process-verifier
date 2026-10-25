#!/usr/bin/env python3
"""Turn sampled LLM plans into step-level training labels (Phase 3).

For every sampled plan (and the greedy plan) and every prefix of it we ask the
exact simulator and the exact solver:

  legal      is this step executable in the state reached so far?  (VAL-style label)
  h_before   optimal number of actions still needed before the step (exact, BFS)
  h_after    same, after the step (None if the step was illegal)
  progress   legal and h_after < h_before        (the step moves closer to the goal)
  optimal    legal and h_after == h_before - 1   (the step is on a shortest plan)
  plan_valid does the whole plan reach the goal (outcome label, same for all steps)

A plan is cut at its first illegal step: that step is kept (legal=0, a negative
example) and later steps are dropped, since their state is undefined.
The split is by PROBLEM (never by sample), so the verifier is tested on problems
it has not seen. Rows go to data/labeled/{train,val,test}.jsonl.

    python verifier/make_labels.py --runs RUN.jsonl --problems DIR --out data/labeled
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "planners"))
sys.path.insert(0, str(ROOT / "verifier"))
from strips_sim import load_domain, load_problem, apply_action, goal_reached  # noqa: E402
from exact_h import StateGraph  # noqa: E402


def split_of(pid, val=0.15, test=0.15, salt="prm-v1"):
    """Deterministic split by problem id (stable when more problems are added)."""
    u = int(hashlib.sha256((salt + pid).encode()).hexdigest()[:8], 16) / 16 ** 8
    return "test" if u < test else "val" if u < test + val else "train"


def label_plan(domain, problem, graph, plan, source, sample_id, valid, rec):
    state = set(problem.init)
    rows = []
    h_prev = graph.h(state)
    for k, action in enumerate(plan):
        new, err = apply_action(domain, problem, state, action)
        row = {"id": rec["id"], "n_blocks": rec["n_blocks"], "source": source,
               "sample": sample_id, "step": k, "prefix": plan[:k], "action": action,
               "legal": err is None, "h_before": h_prev, "plan_valid": valid}
        if err is None:
            h_new = graph.h(new)
            row.update(h_after=h_new, progress=h_new is not None and h_new < h_prev,
                       optimal=h_new == h_prev - 1, reason=None)
            state, h_prev = new, h_new
            rows.append(row)
        else:
            row.update(h_after=None, progress=False, optimal=False, reason=err)
            rows.append(row)
            break
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, required=True, help="JSONL from run_baselines.py")
    ap.add_argument("--problems", type=Path, default=Path("data/blocksworld/problems"))
    ap.add_argument("--domain", default="data/domains/blocksworld/domain.pddl")
    ap.add_argument("--out", type=Path, default=Path("data/labeled"))
    args = ap.parse_args()

    domain = load_domain(args.domain)
    args.out.mkdir(parents=True, exist_ok=True)
    outs = {s: open(args.out / f"{s}.jsonl", "w", encoding="utf-8") for s in ("train", "val", "test")}
    stats = Counter()
    for line in args.runs.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        problem = load_problem(args.problems / f"{rec['id']}.pddl")
        graph = StateGraph(domain, problem)
        split = split_of(rec["id"])
        plans = [("greedy", 0, rec["greedy"])] + [("sample", i, s) for i, s in enumerate(rec["samples"])]
        for source, i, p in plans:
            rows = label_plan(domain, problem, graph, p["plan"], source, i, p["valid"], rec)
            for r in rows:
                r["split"] = split
                outs[split].write(json.dumps(r) + "\n")
                stats[(split, "rows")] += 1
                stats[(split, "legal")] += r["legal"]
                stats[(split, "progress")] += r["progress"]
                stats[(split, "optimal")] += r["optimal"]
            stats[(split, "plans")] += 1
            stats[(split, "valid_plans")] += p["valid"]
        stats[(split, "problems")] += 1
    for f in outs.values():
        f.close()
    for s in ("train", "val", "test"):
        n = max(stats[(s, "rows")], 1)
        print(f"{s:5s} problems={stats[(s,'problems')]:4d} plans={stats[(s,'plans')]:6d} "
              f"valid_plans={stats[(s,'valid_plans')]:5d} step_rows={stats[(s,'rows')]:7d} "
              f"legal={stats[(s,'legal')]/n:.1%} progress={stats[(s,'progress')]/n:.1%} "
              f"optimal={stats[(s,'optimal')]/n:.1%}")


if __name__ == "__main__":
    main()
