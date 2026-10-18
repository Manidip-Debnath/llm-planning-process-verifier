#!/usr/bin/env python3
"""Solve PDDL problems optimally with Fast Downward (A* + LM-cut).

Set the location of Fast Downward with --fd or the FD_PATH environment
variable (path to the `fast-downward.py` script).

Example:
    export FD_PATH=~/fast-downward/fast-downward.py
    python data/solve_optimal.py --domain data/domains/blocksworld/domain.pddl \
        --problems data/blocksworld/problems --out data/blocksworld/solutions.jsonl

Output: one JSON line per problem: {"id", "solved", "cost", "plan", "seconds"}.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def solve(fd_path, domain, problem, timeout):
    """Return (plan_actions or None, cost or None, seconds)."""
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [sys.executable, str(fd_path), "--plan-file", "plan.txt",
               "--sas-file", "out.sas",
               str(Path(domain).resolve()), str(Path(problem).resolve()),
               "--search", "astar(lmcut())"]
        try:
            subprocess.run(cmd, cwd=tmp, capture_output=True, text=True,
                           timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, None, time.time() - t0
        plan_file = Path(tmp) / "plan.txt"
        if not plan_file.exists():
            return None, None, time.time() - t0
        actions = [ln.strip() for ln in plan_file.read_text().splitlines()
                   if ln.strip() and not ln.startswith(";")]
        return actions, len(actions), time.time() - t0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fd", default=os.environ.get("FD_PATH"),
                    help="path to fast-downward.py (or set FD_PATH)")
    ap.add_argument("--domain", required=True)
    ap.add_argument("--problems", required=True, type=Path,
                    help="directory of .pddl problem files")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--timeout", type=int, default=120, help="seconds per problem")
    args = ap.parse_args()
    if not args.fd or not Path(args.fd).exists():
        sys.exit("Fast Downward not found. Set --fd or FD_PATH to fast-downward.py")

    done = set()
    if args.out.exists():  # resume support
        for line in args.out.read_text().splitlines():
            done.add(json.loads(line)["id"])

    files = sorted(args.problems.glob("*.pddl"))
    with open(args.out, "a", encoding="utf-8") as out:
        for i, pf in enumerate(files, 1):
            pid = pf.stem
            if pid in done:
                continue
            plan, cost, secs = solve(args.fd, args.domain, pf, args.timeout)
            out.write(json.dumps({"id": pid, "solved": plan is not None,
                                  "cost": cost, "plan": plan,
                                  "seconds": round(secs, 2)}) + "\n")
            out.flush()
            if i % 20 == 0 or i == len(files):
                print(f"{i}/{len(files)} done")


if __name__ == "__main__":
    main()
