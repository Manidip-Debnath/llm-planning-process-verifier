# Report, Presentation, Demo, and Video Checklist

Grading: presentation 60% (peer + instructor), report 30%, GitHub progress 10%.

## Final report (PDF, short-paper style)

Required sections (from the course description). Suggested length: 6-8 pages.

- [ ] **Title and author**
- [ ] **Abstract** (150-200 words): problem, approach, headline result with numbers
- [ ] **Introduction:** why LLM planning fails, why process supervision helps, why solver labels are "free", your contributions as 2-3 bullets
- [ ] **Related Work:** process reward models, test-time compute scaling, LLM planning (PlanBench), LLM + classical planner hybrids. State how this differs.
- [ ] **Data:** domains, problem generator, sizes, how plans were collected, how labels were computed, splits (by problem), data card summary
- [ ] **Methods:** simulator and labels, verifier (input format, model, LoRA settings), baselines, best-of-N, beam search, compute accounting, RL setup (if done)
- [ ] **Experiments & Results:**
  - headline figure: validity vs. compute
  - table: all methods at matched compute
  - verifier-only metrics (AUROC, accuracy by step position)
  - generalization (size, domain)
  - ablations
  - **qualitative analysis**: 3-5 real examples, with the failing step shown and the failure taxonomy
  - seeds and confidence intervals
- [ ] **Conclusion:** results, limitations (be honest: small models, few domains, synthetic problems), future work
- [ ] **Citations & Acknowledgements:** all tools, models, papers, code adapted from others

Tips:
- State the hypothesis and say clearly whether the results support it.
- A negative or partial result is fine if analyzed honestly.
- Every figure needs labeled axes, units, and a caption that says what to conclude.

## GitHub repo (final state)

- [ ] README updated: problem, method, results summary, **how to run** (exact commands), video link, citations
- [ ] Final report PDF in `report/`
- [ ] All source code, with small sample data and scripts to regenerate the rest
- [ ] Commit history shows steady progress
- [ ] No API keys, tokens, or huge files committed
- [ ] Fresh-clone test: clone to a new folder and follow your own README

## Presentation (Dec 1 or Dec 3)

Suggested structure from the course, with a time guide for roughly 8-10 minutes (confirm the actual time limit with your instructor):

1. **Problem (1-2 min):** show a real LLM plan that fails at step k, with the exact violated rule
2. **Solution (2 min):** the key idea, "solver labels are free and exact", plus a one-slide pipeline diagram
3. **Results and demo (3-4 min):** headline plot; live demo
4. **Impact and future work (1-2 min):** limitations, what you'd do next

Slide tips:
- One message per slide; large text; no dense tables
- Headline plot gets its own slide and a one-sentence takeaway
- Show one verifier failure honestly

### Demo plan

- [ ] Input: a Blocksworld problem the baseline LLM fails
- [ ] Show the LLM's plan and VAL marking the failing step
- [ ] Show the verifier scores per step, highlighting the low-scoring one
- [ ] Show verifier-guided search recovering a valid plan
- [ ] **Backup:** screenshots or a short pre-recorded clip of the same demo
- [ ] Test on the presentation computer or have it run from a cached notebook (no live training in the demo)

### Peer feedback

You will grade classmates. Give specific, constructive comments (what was clear, what was missing, one suggestion).

## Video

- [ ] 5-8 minutes, covering the same four parts
- [ ] Upload to YouTube (unlisted is fine) or Google Drive with link sharing on
- [ ] Add the link to the README
- [ ] Check the link works while logged out

## Final-week schedule

| Date | Task |
|---|---|
| Nov 24 | Experiments frozen. Export all figures and tables |
| Nov 25-27 | Write Results, Intro, Related Work, Abstract, Conclusion |
| Nov 28 | Record video; finalize slides and demo backup |
| Nov 29 | Proofread; fresh-clone test of the repo |
| Nov 30 | Submit before 11:00 PM (aim for the afternoon) |
