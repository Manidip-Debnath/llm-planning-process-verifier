#!/usr/bin/env python3
"""Sequence-only baseline verifier (no state tracking), CPU only.

Features come from the action names and the previous action only (never the
simulator state). It shows how much of 'legal' and 'progress' can be guessed
from surface patterns, so the neural verifier has to beat it to count.
Gradient boosting predicts P(legal) and P(progress) per step.

    python verifier/baseline_features.py --labeled data/labeled --runs RUN.jsonl \
        --problems data/blocksworld/problems --out data/verifier_baseline
"""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

from common import read_jsonl, auroc

NAMES = ["pick-up", "put-down", "stack", "unstack"]


def _parts(a):
    p = a.strip("()").split()
    return p[0], p[1:]


def featurize(prefix, action, n_blocks):
    name, args = _parts(action)
    f = [n_blocks, len(prefix)] + [name == n for n in NAMES]
    if prefix:
        pn, pa = _parts(prefix[-1])
        f += [pn == n for n in NAMES]
        f += [bool(args) and bool(pa) and args[0] == pa[0],           # same block as last step
              bool(args) and bool(pa) and args[0] == pa[-1],
              len(args) > 1 and len(pa) > 1 and args == pa[::-1]]    # exact reversal
    else:
        f += [False] * 4 + [False, False, False]
    seen = [x for p in prefix for x in _parts(p)[1]]
    f += [bool(args) and args[0] in seen, len(set(seen))]
    return [float(x) for x in f]


class FeatureScorer:
    """Same interface as the neural scorer: predict(list of (pid, n, prefix, action))."""
    def __init__(self):
        self.models = {}

    def fit(self, rows):
        X = np.array([featurize(r["prefix"], r["action"], r["n_blocks"]) for r in rows])
        for key in ("legal", "progress"):
            y = np.array([bool(r[key]) for r in rows])
            m = GradientBoostingClassifier(n_estimators=150, max_depth=3, random_state=0)
            self.models[key] = m.fit(X, y)
        return self

    def predict(self, items):
        X = np.array([featurize(p, a, n) for _, n, p, a in items])
        return np.stack([self.models[k].predict_proba(X)[:, 1] for k in ("legal", "progress")], 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labeled", type=Path, default=Path("data/labeled"))
    ap.add_argument("--out", type=Path, default=Path("data/verifier_baseline"))
    args = ap.parse_args()
    train = read_jsonl(args.labeled / "train.jsonl")
    sc = FeatureScorer().fit(train)
    args.out.mkdir(parents=True, exist_ok=True)
    for split in ("val", "test"):
        rows = read_jsonl(args.labeled / f"{split}.jsonl")
        P = sc.predict([(r["id"], r["n_blocks"], r["prefix"], r["action"]) for r in rows])
        for i, key in enumerate(("legal", "progress")):
            print(f"{split} AUROC {key}: {auroc([bool(r[key]) for r in rows], list(P[:, i])):.3f}")
    import pickle
    pickle.dump(sc, open(args.out / "scorer.pkl", "wb"))


if __name__ == "__main__":
    main()
