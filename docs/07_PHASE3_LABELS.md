# Phase 3: Step-level labels (data card)

**Goal.** Turn every plan the LLM samples into step-level training examples whose labels come from an exact
checker, with no human or LLM judging.

## How labels are made
`verifier/make_labels.py` replays each sampled plan step by step with the STRIPS simulator
(`planners/strips_sim.py`, agrees with VAL on 480/480 plans) and looks up the exact optimal cost-to-go h*
from `verifier/exact_h.py` (breadth-first search over every reachable state; for blocksworld this is the same
number Fast Downward's A*+LM-cut gives, with at most 866 states for 5 blocks).

| field | meaning |
|---|---|
| `legal` | the step is executable in the state reached so far (what VAL would accept) |
| `h_before`, `h_after` | optimal number of actions still needed before / after the step |
| `progress` | legal and `h_after < h_before` (step moves closer to the goal). In unit-cost blocksworld this equals `optimal` (step is on a shortest plan). |
| `plan_valid` | the whole plan reaches the goal (outcome label, the same for all steps of a plan) |
| `prefix`, `action` | the plan so far and the step being judged; the problem text comes from `planners/prompts.py` |

A plan is cut at its first illegal step. That step stays as a negative example (`legal=false`); later steps are dropped.

## Split
By problem, never by sample: `sha256(salt + problem_id)` puts about 70% in train, 15% in val, 15% in test.
The split is stable if more problems are added later. Test problems are used only at the end.

## First version (pipeline test)
60 problems (3, 4, 5 blocks), 16 samples + greedy each, Qwen2.5-7B-Instruct, state prompt:

| split | problems | plans | valid plans | step rows | legal | progress |
|---|---|---|---|---|---|---|
| train | 43 | 731 | 73 | 2,330 | 72.9% | 53.1% |
| val | 7 | 119 | 5 | 372 | 69.6% | 40.1% |
| test | 10 | 170 | 9 | 635 | 75.0% | 60.9% |

That is enough to test code, not to train. Target for training: about 450 problems (150 per size), roughly
7,500 plans and 25k step rows. Rerun the Colab notebook with `COUNT = 150`, the same settings otherwise and a new
output name, then run:

    python data/gen_blocksworld.py --sizes 3 4 5 --count 150 --seed 0 --out data/blocksworld/problems
    python verifier/make_labels.py --runs RUN.jsonl --out data/labeled

`data/labeled/` and raw runs stay out of git (see `.gitignore`); only this card and the code are committed.
