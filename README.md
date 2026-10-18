# Free Process Supervision for LLM Planning

**Learning step-level verifiers from solver labels, and using them to guide LLM planners**

CSI-4130/5130 Artificial Intelligence, Course Project (solo)
Author: Manidip Debnath (manidipdeb@oakland.edu)

> Status: initial proposal (October 2026). This README will be updated with results, run instructions, and the video link before the final submission.

## Problem Statement

Large language models often produce plans that look plausible but break a rule partway through, such as picking up a block that has another block on top of it. Process reward models (PRMs), which score each reasoning step rather than only the final answer, can help, but they normally require expensive human step-level labels.

Classical planning offers a shortcut. A plan validator and an optimal solver can label every step of a partial plan exactly and for free. This project asks:

> **Can a small verifier trained on exact, solver-derived step labels guide an LLM planner to produce more valid plans than self-consistency, at equal test-time compute?**

## Hypotheses

- **H1.** A verifier trained on solver labels used for best-of-N and step-level beam search yields higher plan validity than self-consistency at equal compute (generated tokens plus verifier cost).
- **H2.** Dense process rewards from the exact solver labels make RL fine-tuning of the planner more sample-efficient than outcome-only (valid / invalid) rewards.
- **H3 (stretch).** A learned verifier generalizes to larger instances and unseen domains, at least partially.

## Proposed Method

1. **Data generation.** Generate planning problems (PDDL) with `pddl-generators` and solve them optimally with Fast Downward. Collect plans from an LLM planner (valid and invalid), optimal solver plans, and perturbed plans.
2. **Exact step labels.** For every prefix of every plan, compute with a Python STRIPS simulator and Fast Downward:
   - *executable*: no precondition has been violated so far
   - *progress*: whether the step reduced, preserved, or increased the optimal remaining cost h*
   - *h\**: the optimal remaining cost from the reached state

   Final plan validity is checked with VAL, and the simulator is cross-checked against VAL on a sample.
3. **Verifier.** Fine-tune a small LLM (0.5B to 1.5B, LoRA) on (problem, partial plan, candidate action) to predict step validity and progress, with an optional h* regression head.
4. **Verifier-guided planning.** Use a small open LLM (about 3B) as the planner and compare:
   - greedy decoding
   - self-consistency (majority vote)
   - best-of-N with an untrained LLM judge
   - best-of-N with the trained verifier
   - step-level beam search with the trained verifier
   - VAL as an oracle upper bound
5. **RL with process rewards (planned, scoped to one domain).** Fine-tune the planner with GRPO under three reward variants: outcome-only, exact dense rewards, and learned-verifier dense rewards.

## Evaluation

- **Metrics:** plan validity (VAL), optimality gap vs. the solver, verifier AUROC and calibration.
- **Headline figure:** plan validity vs. test-time compute (generated tokens plus verifier cost), one curve per method.
- **Generalization:** larger instance sizes, unseen domains, and obfuscated (PlanBench "Mystery"-style) domains.
- **Rigor:** multiple seeds with bootstrap confidence intervals.
- **Qualitative:** a taxonomy of failure cases with concrete examples (verifier accepts a bad step, rejects a good one).

## Data Sources

- Synthetic planning problems from [`pddl-generators`](https://github.com/AI-Planning/pddl-generators) (Blocksworld, Logistics, Gripper for training; held-out domains such as Depots, Rovers, or Ferry for out-of-distribution tests).
- Labels computed by this project's pipeline using Fast Downward and VAL.
- PlanBench for reference on LLM planning evaluation and obfuscated domains.

No human-labeled or private data is used.

## Tools and Compute

Python, PyTorch, Hugging Face Transformers, PEFT/LoRA, TRL or Unsloth, Fast Downward, VAL. Training runs on Google Colab / Kaggle GPUs.

## Timeline

| Dates | Milestone |
|---|---|
| Oct 18-26 | Repo setup, tool installation, Blocksworld generator |
| Oct 26-Nov 1 | Planner baselines (greedy, self-consistency) |
| Nov 2-8 | STRIPS simulator and label pipeline |
| Nov 9-13 | Verifier training and verifier-only evaluation |
| Nov 14-18 | Verifier-guided search and headline plot |
| Nov 16-25 | RL with process rewards, generalization tests, ablations |
| Nov 24-29 | Report, demo, and video |
| Nov 30 | Final submission |

## Repository Structure (planned)

```
data/        problem generators, labeled prefixes, data cards
planners/    LLM planning code and prompts
verifier/    verifier training and inference
search/      best-of-N, beam search
eval/        metrics and plotting
notebooks/   Colab entry points
report/      final report (PDF)
```

## How to Run

_To be added with the final submission._

## Demo Video

_Link to be added._

## Citations and Acknowledgements

Tools and libraries:
- Helmert, M. (2006). The Fast Downward Planning System. *Journal of Artificial Intelligence Research*.
- Howey, R., Long, D., and Fox, M. (2004). VAL: Automatic Plan Validation, Continuous Effects and Mixed Initiative Planning Using PDDL. *ICTAI*.
- Seipp, J., Torralba, A., and Hoffmann, J. PDDL generators (`pddl-generators`).

Papers that motivate this work:
- Lightman, H. et al. (2023). Let's Verify Step by Step.
- Wang, X. et al. (2022). Self-Consistency Improves Chain of Thought Reasoning in Language Models.
- Valmeekam, K. et al. (2022). PlanBench: An Extensible Benchmark for Evaluating Large Language Models on Planning and Reasoning about Change.
- Shao, Z. et al. (2024). DeepSeekMath (introduces GRPO).

Open-source models and libraries (Qwen, Hugging Face Transformers, PEFT, TRL, Unsloth) will be listed with versions and licenses as they are used. Any code adapted from other sources will be attributed in the source files and here.
