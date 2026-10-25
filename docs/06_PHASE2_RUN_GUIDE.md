# Phase 2 Run Guide: Planner Baselines

Goal: measure how well a small open LLM plans on Blocksworld **without** any verifier, so you have the baselines the verifier must beat.

| What | Where it runs | Why |
|---|---|---|
| Generate problems, solve optimally, VAL checks | Your PC (Ubuntu/WSL) | Needs Fast Downward and VAL (Linux), no GPU |
| LLM sampling (greedy and 32 samples per problem) | Colab or Kaggle GPU | Your PC has no NVIDIA GPU |
| Summary tables | Anywhere | Plain Python |

## What was built

| File | Purpose |
|---|---|
| `planners/strips_sim.py` | Python simulator that checks a plan step by step (needed again for labels in Phase 3). Tested against VAL: 480/480 agreement |
| `planners/prompts.py` | Plain-language Blocksworld prompt (one worked example) and the plan parser |
| `planners/llm_backend.py` | Hugging Face model backend, plus a fake "mock" backend for testing |
| `planners/run_baselines.py` | Runs greedy + N samples per problem, saves everything |
| `eval/summarize_baselines.py` | Computes greedy, self-consistency at N = 1..32, oracle best-of-N, tokens, optimality gap |
| `eval/check_sim_vs_val.py` | Cross-checks the simulator against VAL |
| `notebooks/01_planner_baselines.ipynb` | Colab notebook that runs all of the above |

One run saves every sample, so greedy, self-consistency at every N, and the oracle best-of-N ceiling all come from the same file. "Oracle best-of-N" is the fraction of problems where at least one of the first N samples is valid. It is the ceiling a perfect verifier could reach.

## Step 1: Push the code to GitHub (PowerShell)

```powershell
cd $HOME\Desktop\AI_Planning_PRM_Project
git add .
git commit -m "Add STRIPS simulator, planner prompts, baseline runner, and summary tools"
git push
```

## Step 2: Check the pipeline on your PC (Ubuntu, 1 minute)

```bash
cd /mnt/c/Users/manid/Desktop/AI_Planning_PRM_Project
python3 data/gen_blocksworld.py --sizes 3 4 5 6 --count 25 --seed 0 --out data/blocksworld/problems
python3 data/solve_optimal.py --domain data/domains/blocksworld/domain.pddl --problems data/blocksworld/problems --out data/blocksworld/solutions.jsonl
python3 eval/check_sim_vs_val.py --domain data/domains/blocksworld/domain.pddl --problems data/blocksworld/problems --solutions data/blocksworld/solutions.jsonl
```

Expected: `agreement: 600/600 (100.0%)` (or a similar all-agree line). Then test the whole pipeline without a GPU using the fake LLM:

```bash
python3 planners/run_baselines.py --backend mock --solutions data/blocksworld/solutions.jsonl --problems data/blocksworld/problems --out data/runs/mock.jsonl
python3 eval/summarize_baselines.py --results data/runs/mock.jsonl --solutions data/blocksworld/solutions.jsonl
```

(The mock numbers are meaningless. They only prove the tables work.)

## Step 3: Run on Colab (about 15 minutes of setup, then waiting)

1. Go to https://colab.research.google.com and sign in with your Google account.
2. **File > Upload notebook** and choose `notebooks/01_planner_baselines.ipynb` from your project folder (or open it from your GitHub repo: File > Open notebook > GitHub tab).
3. **Runtime > Change runtime type > T4 GPU**, then Save.
4. Run the cells in order. Do the **smoke test first** (3 problems, 1.5B model). Read the printed model output. You should see a `Plan:` followed by action lines.
5. If the smoke test looks sane, run the full baseline cell with `Qwen/Qwen2.5-3B-Instruct`.
6. Download the zip at the end and unzip it into your project folder (`data/runs/` stays out of Git, and `results/` is committed).

Free Colab sessions can disconnect. The runner **resumes**: if it stops, run the same cell again and it skips problems already done.

Kaggle alternative: create a notebook, set **Accelerator = GPU T4 x2** and **Internet = On**, paste the notebook's code cells, and replace the Colab download cell by saving files in `/kaggle/working`.

## Step 4: Tune difficulty (the most important check)

Open the summary table, "Blocks" section. You want greedy validity around **20 to 50%** on the sizes you will use.

| What you see | What to do |
|---|---|
| Greedy near 0% on every size | Use smaller sizes (3 and 4 blocks), or a bigger model (Qwen2.5-7B with `--load-4bit`) |
| Greedy near 100% | Add larger sizes (7, 8 blocks): regenerate with `--sizes 6 7 8` |
| Oracle best-of-32 is also near 0% | A verifier cannot help; the planner is too weak, so go easier or bigger |
| Oracle best-of-N is much higher than self-consistency | Good: this gap is exactly the room your verifier can fill |

## Step 5: Commit the evidence

Copy the summary markdown into `results/` and commit it, so your Git history shows the experiment:

```powershell
git add results docs
git commit -m "Planner baselines: greedy and self-consistency results"
git push
```

## Checkpoint 2 (target Nov 1)

A table of greedy vs. self-consistency validity at N = 1..32, with tokens per problem, committed in `results/`. Fill the numbers into `docs/04_PROGRESS_TRACKER.md`.

## Notes for your report

- Qwen2.5 models: the 0.5B, 1.5B and 7B are Apache-2.0; the 3B uses Qwen's own research license (fine for coursework). Verify each license on the model's Hugging Face page and list it in the README.
- "Equal compute" is counted in generated tokens. The runner stores `tokens` for every sample.
- Prompts matter. If you change `planners/prompts.py`, rerun everything so all methods share one prompt.
