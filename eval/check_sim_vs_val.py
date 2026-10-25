#!/usr/bin/env python3
"""Cross-check the Python simulator against VAL.

For every solved problem it tests the optimal plan plus several corrupted
versions (dropped, swapped, inserted, truncated, wrong-object steps) and
counts how often the simulator and VAL agree on "valid / invalid".

Needs VAL_PATH (or --val) pointing at the `Validate` binary.

Example:
    python eval/check_sim_vs_val.py \
        --domain data/domains/blocksworld/domain.pddl \
        --problems data/blocksworld/problems \
        --solutions data/blocksworld/solutions.jsonl
"""
import argparse
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "planners"))
sys.path.insert(0, str(ROOT / "data"))

from strips_sim import load_domain, load_problem, simulate  # noqa: E402
from validate_plan import validate                           # noqa: E402


def corrupt(plan, objects, rng):
    """Return a list of (label, corrupted_plan)."""
    out = []
    if len(plan) >= 1:
        i = rng.randrange(len(plan))
        out.append(("drop", plan[:i] + plan[i + 1:]))
        out.append(("truncate", plan[:max(1, len(plan) - 1)]))
    if len(plan) >= 2:
        i = rng.randrange(len(plan) - 1)
        sw = plan[:]
        sw[i], sw[i + 1] = sw[i + 1], sw[i]
        out.append(("swap", sw))
    if plan:
        i = rng.randrange(len(plan))
        out.append(("insert", plan[:i] + [plan[rng.randrange(len(plan))]] + plan[i:]))
        # wrong object: replace one object name in a random step
        j = rng.randrange(len(plan))
        parts = plan[j].strip("()").split()
        k = rng.randrange(1, len(parts)) if len(parts) > 1 else None
        if k:
            parts[k] = rng.choice(objects)
            wo = plan[:]
            wo[j] = "(" + " ".join(parts) + ")"
            out.append(("wrong_object", wo))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--val", default=os.environ.get("VAL_PATH"))
    ap.add_argument("--domain", required=True)
    ap.add_argument("--problems", required=True, type=Path)
    ap.add_argument("--solutions", required=True, type=Path)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    if not args.val or not Path(args.val).exists():
        sys.exit("VAL not found. Set --val or VAL_PATH to the Validate binary")

    rng = random.Random(args.seed)
    dom = load_domain(args.domain)
    total = agree = 0
    by_label = {}
    disagreements = []
    for line in args.solutions.read_text().splitlines():
        rec = json.loads(line)
        if not rec["solved"]:
            continue
        pfile = args.problems / f"{rec['id']}.pddl"
        prob = load_problem(pfile)
        cases = [("optimal", rec["plan"])] + corrupt(rec["plan"], list(prob.objects), rng)
        for label, plan in cases:
            sim_ok = simulate(dom, prob, plan)["valid"]
            val_ok, out = validate(args.val, args.domain, pfile, plan)
            total += 1
            ok = sim_ok == val_ok
            agree += ok
            s = by_label.setdefault(label, [0, 0, 0])   # n, agree, sim-valid
            s[0] += 1
            s[1] += ok
            s[2] += sim_ok
            if not ok:
                disagreements.append((rec["id"], label, plan, sim_ok, val_ok))
    print(f"agreement: {agree}/{total} ({100 * agree / max(total, 1):.1f}%)")
    for label, (n, a, v) in sorted(by_label.items()):
        print(f"  {label:13s} cases={n:4d} agree={a:4d} sim-says-valid={v}")
    for d in disagreements[:10]:
        print("DISAGREEMENT", d)
    sys.exit(0 if not disagreements else 1)


if __name__ == "__main__":
    main()
