#!/usr/bin/env python3
"""Validate a plan with VAL.

Set the VAL binary with --val or the VAL_PATH environment variable
(path to the `Validate` executable).

Usage as a script:
    python data/validate_plan.py --domain D.pddl --problem P.pddl --plan plan.txt

Usage as a module:
    from validate_plan import validate
    ok, message = validate(val_path, domain, problem, ["(pick-up b1)", ...])

Plan format: one action per line in parentheses, e.g. "(unstack b1 b2)".
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def validate(val_path, domain, problem, actions, timeout=30):
    """Return (is_valid, raw_output). Empty or malformed plans are invalid."""
    if not actions:
        return False, "empty plan"
    with tempfile.TemporaryDirectory() as tmp:
        plan_file = Path(tmp) / "plan.txt"
        plan_file.write_text("\n".join(actions) + "\n")
        proc = subprocess.run(
            [str(val_path), "-v", str(domain), str(problem), str(plan_file)],
            capture_output=True, text=True, timeout=timeout)
    out = proc.stdout + proc.stderr
    return "Plan valid" in out, out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--val", default=os.environ.get("VAL_PATH"))
    ap.add_argument("--domain", required=True)
    ap.add_argument("--problem", required=True)
    ap.add_argument("--plan", required=True)
    args = ap.parse_args()
    if not args.val or not Path(args.val).exists():
        sys.exit("VAL not found. Set --val or VAL_PATH to the Validate executable")
    actions = [ln.strip() for ln in Path(args.plan).read_text().splitlines()
               if ln.strip() and not ln.startswith(";")]
    ok, out = validate(args.val, args.domain, args.problem, actions)
    print("VALID" if ok else "INVALID")
    print(out)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
