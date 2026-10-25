#!/usr/bin/env python3
"""Summarize a baselines run (output of planners/run_baselines.py).

Reports, over all problems:
  * greedy validity, mean tokens, mean optimality gap
  * single-sample validity (average over the first N samples)
  * self-consistency validity at N = 1, 2, 4, 8, 16, 32 (majority vote on the
    plan string) with the tokens it costs
  * oracle best-of-N = "is ANY of the first N samples valid?". This is the
    ceiling a perfect verifier could reach, so it shows how much room a
    verifier has to help.
  * greedy validity by problem size (use it to tune difficulty to 20-50%)

Optimality gap needs --solutions (the file written by data/solve_optimal.py).

Example:
    python eval/summarize_baselines.py --results data/runs/smoke.jsonl \
        --solutions data/blocksworld/solutions.jsonl --out results/baselines_smoke.md
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

NS = [1, 2, 4, 8, 16, 32, 64]


def majority_plan(samples):
    votes = Counter(tuple(s["plan"]) for s in samples if s["plan"])
    if not votes:
        return samples[0]
    best = votes.most_common(1)[0][0]
    return next(s for s in samples if tuple(s["plan"]) == best)


def gap(plan_len, opt):
    return plan_len / opt - 1.0 if opt else None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True, type=Path)
    ap.add_argument("--solutions", type=Path)
    ap.add_argument("--out", type=Path, help="also write the tables as Markdown")
    args = ap.parse_args()

    recs = [json.loads(l) for l in args.results.read_text().splitlines() if l.strip()]
    if not recs:
        raise SystemExit("no results found")
    opt = {}
    if args.solutions and args.solutions.exists():
        for l in args.solutions.read_text().splitlines():
            r = json.loads(l)
            if r["solved"]:
                opt[r["id"]] = r["cost"]

    n_avail = min(len(r["samples"]) for r in recs)
    ns = [n for n in NS if n <= n_avail]
    lines = [f"Results file: {args.results.name}   problems: {len(recs)}   "
             f"model: {recs[0].get('model')}   samples/problem: {n_avail}", ""]

    # greedy
    gv = [r["greedy"]["valid"] for r in recs]
    gtok = [r["greedy"]["tokens"] for r in recs]
    ggap = [gap(len(r["greedy"]["plan"]), opt.get(r["id"]))
            for r in recs if r["greedy"]["valid"]]
    parse_fail = mean([1.0 if not r["greedy"]["plan"] else 0.0 for r in recs])
    lines += ["| Method | Validity | Tokens / problem | Optimality gap (valid plans) |",
              "|---|---|---|---|",
              f"| Greedy | {100 * mean(gv):.1f}% | {mean(gtok):.0f} | "
              f"{100 * mean(ggap):.1f}% |"]

    rows = []
    for n in ns:
        sc_v, sc_gap, tok_n, single, oracle = [], [], [], [], []
        for r in recs:
            first = r["samples"][:n]
            pick = majority_plan(first)
            sc_v.append(pick["valid"])
            if pick["valid"]:
                sc_gap.append(gap(len(pick["plan"]), opt.get(r["id"])))
            tok_n.append(sum(s["tokens"] for s in first))
            single.append(mean([s["valid"] for s in first]))
            oracle.append(any(s["valid"] for s in first))
        rows.append((n, mean(single), mean(sc_v), mean(oracle), mean(tok_n), mean(sc_gap)))
        lines.append(f"| Self-consistency, N={n} | {100 * mean(sc_v):.1f}% | "
                     f"{mean(tok_n):.0f} | {100 * mean(sc_gap):.1f}% |")
    lines += ["", "| N | Avg single-sample validity | Self-consistency validity | "
              "Oracle best-of-N (ceiling) | Tokens |", "|---|---|---|---|---|"]
    for n, sg, sc, orc, tk, _ in rows:
        lines.append(f"| {n} | {100 * sg:.1f}% | {100 * sc:.1f}% | "
                     f"{100 * orc:.1f}% | {tk:.0f} |")

    # by size
    by = defaultdict(list)
    for r in recs:
        by[r["n_blocks"]].append(r)
    lines += ["", "| Blocks | Problems | Greedy validity | Avg sample validity | Oracle best-of-N |",
              "|---|---|---|---|---|"]
    for n in sorted(by):
        grp = by[n]
        lines.append(
            f"| {n} | {len(grp)} | {100 * mean([r['greedy']['valid'] for r in grp]):.1f}% | "
            f"{100 * mean([mean([s['valid'] for s in r['samples']]) for r in grp]):.1f}% | "
            f"{100 * mean([any(s['valid'] for s in r['samples']) for r in grp]):.1f}% |")

    # failure reasons
    reasons = Counter()
    for r in recs:
        for s in r["samples"]:
            if not s["valid"]:
                key = (s["reason"] or "other").split(":")[0]
                reasons[key] += 1
    lines += ["", f"Greedy outputs with no parseable action: {100 * parse_fail:.1f}%",
              "Most common failure reasons among sampled plans: " +
              ", ".join(f"{k} ({v})" for k, v in reasons.most_common(5))]
    text = "\n".join(lines)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"\nwritten to {args.out}")


if __name__ == "__main__":
    main()
