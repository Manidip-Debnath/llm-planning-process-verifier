#!/usr/bin/env python3
"""Generate random Blocksworld PDDL problems.

Each problem has a random initial configuration and a random goal
configuration (both are sets of towers). The goal lists every `on` and
`on-table` fact, so the goal state is fully specified.

Example:
    python data/gen_blocksworld.py --sizes 3 4 5 6 --count 50 --seed 0 \
        --out data/blocksworld/problems

Outputs, per problem:
    <out>/b<N>_<i>.pddl   the PDDL problem
    <out>/index.jsonl     one JSON line per problem (id, n_blocks, seed, init, goal)
"""
import argparse
import json
import random
from pathlib import Path


def random_towers(blocks, rng):
    """Shuffle blocks and cut them into random towers (lists, bottom to top)."""
    order = blocks[:]
    rng.shuffle(order)
    towers, current = [], []
    for b in order:
        current.append(b)
        # Close the tower with probability 0.4 so we get a mix of heights.
        if rng.random() < 0.4:
            towers.append(current)
            current = []
    if current:
        towers.append(current)
    return towers


def tower_facts(towers):
    facts = []
    for t in towers:
        facts.append(("on-table", t[0]))
        for lower, upper in zip(t, t[1:]):
            facts.append(("on", upper, lower))
    return facts


def clear_blocks(towers):
    return [t[-1] for t in towers]


def to_pddl(name, blocks, init_towers, goal_towers):
    init = ["(arm-empty)"]
    init += [f"(clear {b})" for b in clear_blocks(init_towers)]
    init += ["(" + " ".join(f) + ")" for f in tower_facts(init_towers)]
    goal = ["(" + " ".join(f) + ")" for f in tower_facts(goal_towers)]
    return (
        f"(define (problem {name})\n"
        f"  (:domain blocksworld)\n"
        f"  (:objects {' '.join(blocks)})\n"
        f"  (:init\n    " + "\n    ".join(init) + "\n  )\n"
        f"  (:goal (and\n    " + "\n    ".join(goal) + "\n  ))\n)\n"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", type=int, nargs="+", default=[3, 4, 5, 6])
    ap.add_argument("--count", type=int, default=50, help="problems per size")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=Path("data/blocksworld/problems"))
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    seen = set()
    records = []
    for n in args.sizes:
        blocks = [f"b{i}" for i in range(1, n + 1)]
        made, attempts = 0, 0
        while made < args.count and attempts < args.count * 50:
            attempts += 1
            # A per-problem seed makes every problem reproducible on its own.
            pseed = args.seed * 1_000_003 + n * 10_007 + attempts
            rng = random.Random(pseed)
            init_t = random_towers(blocks, rng)
            goal_t = random_towers(blocks, rng)
            key = (n, tuple(map(tuple, init_t)), tuple(map(tuple, goal_t)))
            # Skip duplicates and trivial problems (init already satisfies goal).
            if key in seen or set(tower_facts(init_t)) == set(tower_facts(goal_t)):
                continue
            seen.add(key)
            pid = f"b{n}_{made:04d}"
            (args.out / f"{pid}.pddl").write_text(
                to_pddl(pid, blocks, init_t, goal_t), encoding="utf-8")
            records.append({"id": pid, "n_blocks": n, "seed": pseed,
                            "init": init_t, "goal": goal_t})
            made += 1
        if made < args.count:
            print(f"warning: only {made}/{args.count} unique problems for n={n}")

    with open(args.out / "index.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(records)} problems to {args.out}")


if __name__ == "__main__":
    main()
