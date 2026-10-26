#!/usr/bin/env python3
"""Best-of-N with a verifier vs self-consistency vs oracle, at equal samples/tokens.

For every problem in the chosen split we take the first N sampled plans and
pick one by
  * verifier   plan score from per-step verifier probabilities (see --agg)
  * sc         majority vote on the plan text (self-consistency)
  * random     the average single sample
  * oracle     any valid plan among the N (ceiling for any verifier)
Tokens are the generated tokens of all N samples, identical for all methods
(the verifier is small and its cost is reported separately in the report).

    python verifier/rerank_eval.py --runs RUN.jsonl --scorer feature --model data/verifier_baseline/scorer.pkl --split test
    python verifier/rerank_eval.py --runs RUN.jsonl --scorer neural  --model checkpoints/verifier --split test
"""
import argparse
import json
import math
import pickle
from collections import Counter
from pathlib import Path

from common import read_jsonl, auroc
from make_labels import split_of
from baseline_features import FeatureScorer  # noqa: F401  (needed to unpickle)

AGGS = {
    "legal_sum":     lambda pl, pp: sum(math.log(max(x, 1e-6)) for x in pl),
    "legal_min":     lambda pl, pp: min(pl) if pl else -1.0,
    "legal+prog":    lambda pl, pp: sum(math.log(max(a, 1e-6)) + math.log(max(b, 1e-6)) for a, b in zip(pl, pp)),
}


def load_scorer(kind, path, problems):
    if kind == "feature":
        return pickle.load(open(path, "rb"))
    from train_verifier import NeuralScorer
    return NeuralScorer(path, problems)


def plan_scores(scorer, rec, plans):
    """Per-step (P(legal), P(progress)) for every plan, scored in one batch."""
    items, owner = [], []
    for j, p in enumerate(plans):
        for k, a in enumerate(p["plan"]):
            items.append((rec["id"], rec["n_blocks"], p["plan"][:k], a))
            owner.append(j)
    P = scorer.predict(items) if items else []
    per = [([], []) for _ in plans]
    for j, row in zip(owner, P):
        per[j][0].append(float(row[0]))
        per[j][1].append(float(row[1]))
    return per


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--scorer", choices=["feature", "neural"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--problems", type=Path, default=Path("data/blocksworld/problems"))
    ap.add_argument("--split", choices=["train", "val", "test", "all"], default="test")
    ap.add_argument("--sizes", type=int, nargs="*")
    ap.add_argument("--ns", type=int, nargs="*", default=[1, 2, 4, 8, 16])
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    scorer = load_scorer(args.scorer, args.model, args.problems)
    recs = [r for r in read_jsonl(args.runs)
            if (args.split == "all" or split_of(r["id"]) == args.split)
            and (not args.sizes or r["n_blocks"] in args.sizes)]
    scored = {r["id"]: plan_scores(scorer, r, r["samples"]) for r in recs}
    print(f"{len(recs)} problems in split '{args.split}'")
    result = {}
    header = f"{'N':>3} {'tokens':>8} {'random':>7} {'SC':>6} " + " ".join(f"{a:>10}" for a in AGGS) + f" {'oracle':>7}"
    print(header)
    for n in args.ns:
        row = {"random": 0.0, "sc": 0.0, "oracle": 0.0, **{a: 0.0 for a in AGGS}}
        toks = 0.0
        for r in recs:
            s = r["samples"][:n]
            toks += sum(x["tokens"] for x in s)
            row["random"] += sum(x["valid"] for x in s) / len(s)
            row["oracle"] += any(x["valid"] for x in s)
            votes = Counter(" ".join(x["plan"]) for x in s if x["plan"])
            if votes:
                top = votes.most_common(1)[0][1]
                first = next(x for x in s if x["plan"] and votes[" ".join(x["plan"])] == top)
                row["sc"] += first["valid"]
            per = scored[r["id"]][:n]
            for a, f in AGGS.items():
                best = max(range(len(s)), key=lambda j: f(*per[j]) if s[j]["plan"] else -1e9)
                row[a] += s[best]["valid"]
        m = len(recs)
        result[n] = {k: v / m for k, v in row.items()}
        result[n]["tokens_per_problem"] = toks / m
        print(f"{n:>3} {toks / m:>8.0f} {result[n]['random']:>7.1%} {result[n]['sc']:>6.1%} "
              + " ".join(f"{result[n][a]:>10.1%}" for a in AGGS) + f" {result[n]['oracle']:>7.1%}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
