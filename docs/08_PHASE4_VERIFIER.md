# Phase 4: Verifier training and best-of-N test

**Verifier.** Qwen2.5-0.5B-Instruct with LoRA (r=16) and a 2-output head. Input: problem text, steps so far, step to
judge. Outputs P(legal) and P(progress), trained with binary cross-entropy on the Phase 3 labels
(`verifier/train_verifier.py`). A plan's score is the sum of log-probabilities of its steps (`legal_sum`), the minimum
step probability (`legal_min`), or legal plus progress (`legal+prog`).

**Baseline without state tracking.** `verifier/baseline_features.py` predicts the same labels from the action names and the previous action only
(gradient boosting, CPU). The neural verifier has to beat it to be worth using.

**Test.** `verifier/rerank_eval.py` picks one plan out of the first N samples per held-out problem and reports validity next to
self-consistency, the random sample and the oracle ceiling, with the same generated-token count for all methods.

## Pipeline check on the first 60-problem run (not a result)
Baseline trained on the 43 train problems, evaluated on val/test AUROC: legal 0.89/0.85, progress 0.84/0.89.
Best-of-16 over all 60 problems (train problems included, so optimistic): baseline verifier 21.7% vs self-consistency 11.7%,
random 8.6%, oracle 28.3%. The real numbers need the larger dataset and the held-out test split only (`--split test`).

## Run
Notebook `notebooks/02_train_verifier.ipynb` (Colab T4): labels, baseline, LoRA training (about 15-20 minutes for 25k rows), reranking.
Go/no-go for RL (milestone 9, Nov 13): continue to RL only if the verifier beats both the baseline and self-consistency on the test split.
