# Step-by-Step Guide

Tick the boxes as you go. Each phase ends with a **checkpoint**; do not move on until it passes. If you fall behind, see the fallback table at the end.

Dates assume today is Oct 18, 2026 and the final submission is Nov 30, 2026.

---

## Phase 0: Decisions (Oct 18-19)

- [ ] **Planner LLM:** Qwen2.5-3B-Instruct (or Llama-3.2-3B-Instruct). Run locally so you get cheap sampling and token counts.
- [ ] **Verifier base model:** Qwen2.5-0.5B (upgrade to 1.5B if needed), trained with LoRA.
- [ ] **Training domains:** Blocksworld first; add Logistics and Gripper only after Blocksworld works end to end.
- [ ] **Held-out domains (OOD):** pick one of Depots, Rovers, Ferry. Lock the list by **Nov 1**.
- [ ] **Compute:** Colab (free T4) or Kaggle (2x T4) for LLM work. Fast Downward and VAL need Linux: use Colab, Kaggle, or WSL2 Ubuntu on your PC (see `02_SETUP_TOOLS.md`).
- [ ] **Compute unit:** define "equal compute" as **total generated tokens** (plus verifier tokens processed). Write this down; it is your core claim.

**Rule for difficulty:** the planner's greedy validity must land around **20-50%**. At ~0% or ~100% a verifier has nothing to improve. Tune the number of blocks to hit this range.

---

## Phase 1: Repo and tools (Oct 18-26, submit by Oct 27)

### 1.1 Create the GitHub repo

```bash
cd AI_Planning_PRM_Project
git init
git add .
git commit -m "Initial README, docs, and project skeleton"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

- [ ] Create an empty **public** repo on github.com first (no README, since you already have one).
- [ ] Put your real name and student number in `README.md` before pushing.
- [ ] Push. Check the repo is visible while logged out.
- [ ] **Submit the repo link on Moodle. Do this early, not on Oct 27.**

### 1.2 Install the tools (details in `02_SETUP_TOOLS.md`)

- [ ] Python environment with the packages in `requirements.txt`.
- [ ] Fast Downward builds, and solves one Blocksworld problem with `astar(lmcut())`.
- [ ] VAL builds, and validates a hand-written plan (try a correct one and a broken one).

### 1.3 Blocksworld problems

- [ ] **Blocksworld generator:** `data/gen_blocksworld.py` makes random problems (start and goal towers) for any block count and writes PDDL files, plus `data/solve_optimal.py` (Fast Downward wrapper) and `data/validate_plan.py` (VAL wrapper). These are already written and tested; run them as in `02_SETUP_TOOLS.md` section 4c and read the code so you can explain it. Add your own sizes (3-8 blocks) and cite `pddl-generators` only if you use it.
- [ ] Save the domain file `data/domains/blocksworld/domain.pddl` (standard 4-operator version: pick-up, put-down, stack, unstack).
- [ ] Solve every problem optimally with Fast Downward and save `plan` and `cost` (one JSON line per problem in `data/blocksworld/solutions.jsonl`, done by `solve_optimal.py`).
- [ ] Generate ~1,000 problems with sizes 3-8. Keep a seed in the script so the data is reproducible.

**Checkpoint 1 (by Oct 26):** repo is public and linked on Moodle; solver, VAL, and the generator all work on Blocksworld.

---

## Phase 2: Planner baselines (Oct 26 - Nov 1)

Code goes in `planners/`. **Already written and tested; follow `docs/06_PHASE2_RUN_GUIDE.md`.** The steps below describe what the code does.

- [ ] **Prompt:** domain rules (natural language or PDDL), the problem, required output format (one action per line, e.g. `(unstack a b)`), plus 1-2 few-shot examples.
- [ ] **Parser:** extract actions from the output. Anything malformed counts as invalid.
- [ ] **Greedy baseline:** run on ~200 problems, validate every plan with VAL. Record validity, plan length, optimality gap (plan cost / optimal cost), and generated tokens.
- [ ] **Tune difficulty** until greedy validity is 20-50%.
- [ ] **Self-consistency:** sample N = 4, 8, 16, 32 plans at temperature ~0.7-1.0 and take the most frequent identical plan (or majority vote on validity-agnostic plan strings). Log tokens used.
- [ ] Save all outputs as JSONL in `data/runs/` (do not commit huge files; see `.gitignore`).

**Checkpoint 2 (by Nov 1):** a table of greedy vs. self-consistency validity for each N, committed.

---

## Phase 3: Label generation (Nov 2-8)

This is the main engineering phase. Code goes in `data/` (or a new `labeling/` folder).

### 3.1 Collect plans to label

A verifier trained only on correct plans cannot recognize errors. Mix three sources:

- [ ] **LLM-sampled plans** (valid and invalid): matches the test-time distribution
- [ ] **Optimal solver plans:** known-good examples
- [ ] **Perturbed plans:** swap, drop, or insert an action in an optimal plan

### 3.2 Write a STRIPS simulator

- [ ] `data/strips_sim.py`: parse the domain and problem, track the state, apply an action if its preconditions hold, report which step first fails.
- [ ] **Cross-check against VAL** on ~100 plans. They must agree on validity. Fix disagreements before continuing.

### 3.3 Compute labels for every prefix

For prefix `a1..ak` of each plan:

- [ ] **executable:** did all steps so far satisfy their preconditions? (simulator)
- [ ] **h\*(s):** optimal remaining cost from the state reached. Write the state out as a new `:init`, run Fast Downward, record the cost.
- [ ] **progress:** compare h* before and after the step: *decreased* (good), *same* (neutral), *increased* (detour). Invalid steps get their own class.

Note: Blocksworld is reversible, so no state is a true dead end. That is why the progress / h* label matters. A true dead-end domain is an optional Tier C extension.

### 3.4 Data hygiene

- [ ] Cache everything to JSONL. Solver calls are the slow part: batch and parallelize them.
- [ ] **Split by problem, not by prefix** (train / val / test), or you will leak.
- [ ] Hand-check ~20 labeled examples.
- [ ] Write a short data card (`data/DATA_CARD.md`): size, label balance, sources, split sizes.

Target: roughly 20k-50k labeled prefixes.

**Checkpoint 3 (by Nov 8):** labeled Blocksworld dataset plus data card committed (large files stay out of git; commit the generation scripts and a small sample).

---

## Phase 4: Train the verifier (Nov 9-13)

Code goes in `verifier/`.

- [ ] **Input format:** `[domain + problem] [actions so far] [candidate next action]`
- [ ] **Output:** class (valid-and-progress / valid-neutral / valid-detour / invalid). Optionally add an h* regression head later.
- [ ] **Train:** LoRA on the 0.5B model, 1-3 epochs, on Colab or Kaggle. Log precision/recall for the "invalid" class.
- [ ] **Compare against:**
  - the same base model used zero-shot as a judge (no training)
  - a trivial heuristic (e.g. penalize repeated actions)
- [ ] **Report:** accuracy, AUROC, and error by plan position, all on held-out *problems*.

**Checkpoint 4 (by Nov 13):** the trained verifier clearly beats the untrained judge. If not, fix it now (more negatives, more data, larger model).

**Go/no-go decision (Nov 13):** if the verifier clearly beats the judge, plan Tier B (beam search + RL). If not, skip RL and spend the time on search, generalization, and ablations.

---

## Phase 5: Verifier-guided search (Nov 14-18)

Code goes in `search/`.

- [ ] **Best-of-N:** sample N full plans, score each (e.g. product or minimum of step scores), return the best. N = 4, 8, 16, 32.
- [ ] **Step-level beam search:** at each step sample k candidate next actions, score with the verifier, keep the top B beams, stop on goal or step limit.
- [ ] **Compute accounting:** per method and setting, count generated tokens plus verifier tokens in one unit.
- [ ] **Headline plot** (`eval/plot_headline.py`): x = compute, y = VAL validity. Curves: greedy, self-consistency, untrained-judge best-of-N, trained-verifier best-of-N, trained-verifier beam search, and VAL oracle as a ceiling line.

**Checkpoint 5 (by Nov 18):** the headline figure exists. A negative or partial result is still a finding; report it honestly.

---

## Phase 6: Generalization, RL, ablations (Nov 16-25)

### 6.1 Generalization (Tier A needs at least one)

- [ ] **Larger instances:** train on up to 6 blocks, test on 8-10.
- [ ] **Unseen domain:** train on Blocksworld (+ Logistics, Gripper), test on a held-out domain.
- [ ] Optional: obfuscated action names (PlanBench "Mystery" style).

### 6.2 RL with process rewards (Tier B; start the first run around Nov 16)

- [ ] Warm start: supervised fine-tune the planner on optimal plans.
- [ ] GRPO (TRL or Unsloth) on **one domain** with two rewards:
  1. outcome only (VAL: valid = 1, else 0)
  2. exact dense reward (progress in h* per step)
- [ ] Compare sample efficiency (validity vs. training steps). Use 3 seeds if you can.
- [ ] Tier C: reward from the learned verifier and a reward-hacking analysis (verifier score vs. VAL over training).

### 6.3 Ablations (pick 3-4)

- [ ] Labels: executable only vs. executable + progress
- [ ] Negatives: with vs. without perturbed plans
- [ ] Verifier size: 0.5B vs. 1.5B
- [ ] Beam width and candidates per step

### 6.4 Error analysis

- [ ] Collect 10-15 concrete failures (verifier accepts a bad step, rejects a good one) and group them into a taxonomy: wrong object, violated precondition, redundant loop, goal-forgetting. These feed the report and the demo.

**Freeze experiments on Nov 24.** No new runs after that.

---

## Phase 7: Report, demo, video (Nov 19-29)

See `05_REPORT_AND_PRESENTATION.md` for the full checklist.

- [ ] Draft Data and Methods sections **early** (early Nov), not at the end.
- [ ] Results, figures, and qualitative examples (Nov 24-27).
- [ ] Demo: LLM proposes a plan, verifier flags the bad step, search recovers a valid plan. Cache examples in case the live demo fails.
- [ ] Record the video, upload it, and link it in `README.md`.
- [ ] Update `README.md` with run instructions and results.
- [ ] Put the final PDF in `report/`.
- [ ] **Submit by Nov 30, 11:00 PM.**

---

## Commit rhythm (10% of grade)

Commit every 2-3 days with specific messages, for example:

- `add Blocksworld problem generator`
- `add VAL wrapper and plan parser`
- `greedy and self-consistency baselines, 200 problems`
- `STRIPS simulator, cross-checked vs VAL`
- `label prefixes with h* and progress`
- `train verifier v1 (0.5B LoRA)`
- `best-of-N and beam search with verifier`
- `headline plot: validity vs compute`

Do not commit large files (model weights, big JSONL). Keep them out via `.gitignore` or link to where they are stored.

---

## Fallbacks if you fall behind

| Problem | What to cut |
|---|---|
| Labeling too slow | Drop h* regression; use executable + progress on small instances only |
| Verifier training unstable | Frozen-embedding classifier or smaller verifier |
| Beam search too complex | Ship best-of-N only; mention beam search as future work |
| RL not working by Nov 20 | Drop RL entirely; Tier A + search + generalization is a full project |
| No time for OOD domains | One held-out domain, or larger instances only |

**Minimum viable project:** Blocksworld only; greedy, self-consistency, and verifier best-of-N; one headline plot; one OOD test.

---

## Common pitfalls

- Baseline validity near 0% or 100%: nothing to improve, so re-tune problem size.
- Splitting by prefix instead of by problem: leaks labels and inflates verifier scores.
- Counting only the planner's tokens: "equal compute" must include verifier cost.
- Comparing methods on different problem sets: always use the same test problems and seeds.
- Leaving the Moodle link and README citations to the last day.
