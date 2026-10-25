#!/usr/bin/env python3
"""Run the LLM planner on Blocksworld problems and save every sample.

For each problem it stores
  * one greedy plan (temperature 0), and
  * N sampled plans (temperature > 0).
Every plan is checked with the Python simulator (valid / invalid, first failing
step, tokens used). Greedy, self-consistency, and oracle best-of-N are all
computed afterwards from these saved samples by eval/summarize_baselines.py,
so one run gives every baseline at every N.

Examples:
    # quick test on a GPU machine (Colab / Kaggle)
    python planners/run_baselines.py --backend hf --model Qwen/Qwen2.5-1.5B-Instruct \
        --problems data/blocksworld/problems --limit 5 --n-samples 8 \
        --out data/runs/smoke.jsonl

    # pipeline test with no GPU (fake LLM that corrupts optimal plans)
    python planners/run_baselines.py --backend mock \
        --solutions data/blocksworld/solutions.jsonl \
        --problems data/blocksworld/problems --out data/runs/mock.jsonl
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm_backend import HFBackend, MockBackend      # noqa: E402
from prompts import build_messages, parse_plan      # noqa: E402
from strips_sim import load_domain, load_problem, simulate  # noqa: E402


def evaluate(domain, problem, item):
    plan = parse_plan(item["text"])
    res = simulate(domain, problem, plan)
    return {"text": item["text"], "plan": plan, "tokens": item["tokens"],
            "valid": res["valid"], "failed_at": res["failed_at"],
            "reason": res["reason"], "steps_ok": res["steps_ok"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", choices=["hf", "mock"], default="hf")
    ap.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    ap.add_argument("--domain", default="data/domains/blocksworld/domain.pddl")
    ap.add_argument("--problems", type=Path, default=Path("data/blocksworld/problems"))
    ap.add_argument("--solutions", type=Path, help="needed only for --backend mock")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sizes", type=int, nargs="*", help="only these block counts")
    ap.add_argument("--limit", type=int, help="only the first N problems")
    ap.add_argument("--n-samples", type=int, default=32)
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--max-new-tokens", type=int, default=300)
    ap.add_argument("--chunk", type=int, default=16, help="samples generated per batch")
    ap.add_argument("--no-few-shot", action="store_true")
    ap.add_argument("--load-4bit", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    domain = load_domain(args.domain)
    index = {}
    idx_file = args.problems / "index.jsonl"
    if idx_file.exists():
        for line in idx_file.read_text().splitlines():
            r = json.loads(line)
            index[r["id"]] = r["n_blocks"]
    files = sorted(args.problems.glob("*.pddl"))
    if args.sizes:
        files = [f for f in files if index.get(f.stem) in set(args.sizes)]
    if args.limit:
        files = files[:args.limit]

    if args.backend == "mock":
        if not args.solutions:
            sys.exit("--solutions is required with --backend mock")
        backend = MockBackend(args.solutions, seed=args.seed)
    else:
        import torch
        torch.manual_seed(args.seed)
        backend = HFBackend(args.model, load_4bit=args.load_4bit, chunk=args.chunk)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if args.out.exists():
        done = {json.loads(l)["id"] for l in args.out.read_text().splitlines() if l.strip()}
        print(f"resuming: {len(done)} problems already done")

    t0 = time.time()
    with open(args.out, "a", encoding="utf-8") as out:
        for i, pf in enumerate(files, 1):
            pid = pf.stem
            if pid in done:
                continue
            problem = load_problem(pf)
            msgs = build_messages(problem, few_shot=not args.no_few_shot)
            meta = {"id": pid}
            g, plen = backend.generate(msgs, 1, 0.0, args.max_new_tokens, meta)
            s, _ = backend.generate(msgs, args.n_samples, args.temperature,
                                    args.max_new_tokens, meta)
            rec = {"id": pid, "n_blocks": index.get(pid, len(problem.objects)),
                   "model": args.model if args.backend == "hf" else "mock",
                   "prompt_tokens": plen,
                   "temperature": args.temperature,
                   "greedy": evaluate(domain, problem, g[0]),
                   "samples": [evaluate(domain, problem, x) for x in s]}
            out.write(json.dumps(rec) + "\n")
            out.flush()
            nv = sum(x["valid"] for x in rec["samples"])
            print(f"[{i}/{len(files)}] {pid} greedy={'OK ' if rec['greedy']['valid'] else 'bad'} "
                  f"samples valid {nv}/{len(rec['samples'])}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
