# START HERE

**Project:** Free Process Supervision for LLM Planning
**Course:** CSI-4130/5130 Artificial Intelligence (solo project)

## What this project is, in one paragraph

LLMs write plans that look right but break a rule partway through. A classical planner (Fast Downward) and a plan validator (VAL) can check every step of a plan exactly and for free. You will use those exact labels to train a small **verifier** that scores partial plans, then use the verifier to guide an LLM planner (best-of-N and step-level beam search). The main claim to test: at equal compute, the verifier gives more valid plans than self-consistency (majority voting).

## How this folder is organized

| Path | What it holds |
|---|---|
| `README.md` | Public GitHub README (submit the repo link on Moodle by **Oct 27**) |
| `docs/01_STEP_BY_STEP_GUIDE.md` | **The main guide.** Every step, in order, with checkboxes |
| `docs/02_SETUP_TOOLS.md` | Installing Python, Fast Downward, VAL, and running on Colab/Kaggle |
| `docs/03_CONCEPTS_GLOSSARY.md` | PDDL, VAL, PRM, GRPO and other terms, explained simply |
| `docs/04_PROGRESS_TRACKER.md` | Checklist and weekly log (update it every few days) |
| `docs/05_REPORT_AND_PRESENTATION.md` | Report outline, presentation plan, demo and video checklist |
| `data/ planners/ verifier/ search/ eval/ notebooks/ report/` | Empty code folders, filled as you go |
| `requirements.txt`, `.gitignore` | Python packages and files Git should ignore |

## Key dates

| Date | What |
|---|---|
| Tue **Oct 27**, 11:00 PM | Submit public GitHub repo link on Moodle |
| Fri **Nov 13** | Go/no-go on RL (Tier B), see guide |
| Tue **Nov 24** | Freeze experiments |
| Mon **Nov 30**, 11:00 PM | Final report (PDF) and final repo |
| **Dec 1 / Dec 3** | In-class presentations |

## Grading (what to protect)

- Presentation **60%** (peer + instructor, live demo encouraged)
- Report **30%**
- GitHub progress **10%** (regular commits, so commit every 2-3 days)

## The three scope tiers

- **Tier A (must finish):** Blocksworld, STRIPS simulator, labels, verifier, greedy / self-consistency / judge best-of-N / verifier best-of-N, headline plot, one out-of-distribution test.
- **Tier B (target):** step-level beam search, plus GRPO on one domain with outcome vs. exact-dense rewards.
- **Tier C (stretch, cut first):** learned-verifier reward, reward-hacking analysis, obfuscated and dead-end domains, compute-optimal analysis.

Tier A alone is a complete, good project.

## First 30 minutes

1. Open `docs/01_STEP_BY_STEP_GUIDE.md` and read Phase 0 and Phase 1.
2. Put your name and student number in `README.md`.
3. Create the public GitHub repo and push this folder (commands are in Phase 1).
