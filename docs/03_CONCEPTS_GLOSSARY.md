# Concepts and Glossary

## The big picture

LLMs are weak at planning: they produce plans that look reasonable but violate a rule midway. We can check plans exactly with classical tools. This project turns those exact checks into training labels for a verifier and uses the verifier to steer the LLM.

## Planning terms

| Term | Meaning |
|---|---|
| **PDDL** | A standard language for planning problems. A *domain* file defines actions (preconditions + effects). A *problem* file defines the start state and the goal. |
| **STRIPS** | The simple model PDDL builds on: a state is a set of true facts; an action needs some facts true (preconditions) and adds/removes facts (effects). |
| **Plan** | A sequence of actions that takes the start state to the goal. |
| **Prefix** | The first k actions of a plan (a partial plan). |
| **Executable** | Every action so far had its preconditions satisfied. |
| **Optimal plan** | The cheapest (usually shortest) valid plan. |
| **h\*(s)** | The true optimal remaining cost from state s to the goal. |
| **Heuristic** | An estimate of remaining cost used to guide search. |
| **Dead end** | A state from which the goal cannot be reached. Blocksworld has none (every move is reversible). |
| **Fast Downward** | A classical planner. With `astar(lmcut())` it returns optimal plans. |
| **VAL** | A tool that validates a plan against a domain and problem, and reports the failing step. |
| **Blocksworld** | Stack blocks on a table using pick-up, put-down, stack, unstack. |
| **Logistics / Gripper** | Transport and carrying domains, used as extra training domains. |
| **Depots / Rovers / Ferry** | More domains, candidates for the held-out (out-of-distribution) test. |

## LLM and ML terms

| Term | Meaning |
|---|---|
| **Planner LLM** | The language model that proposes plans (policy). |
| **Verifier** | A model that scores a (partial) plan. Here: a small LLM fine-tuned with LoRA. |
| **PRM (process reward model)** | A verifier that scores each *step*, not just the final answer. |
| **ORM / outcome reward** | A score only for the final result (valid or not). |
| **Best-of-N** | Sample N full plans, keep the one the verifier scores highest. |
| **Self-consistency** | Sample N plans and take the most common one (majority vote). |
| **Beam search (step-level)** | At each step, propose several next actions, score them, keep the top B partial plans. |
| **LoRA / QLoRA** | Cheap fine-tuning that trains small adapter matrices (QLoRA also uses 4-bit weights). |
| **GRPO** | An RL method that compares a group of sampled outputs and rewards the better ones, with no separate value model. |
| **Reward hacking** | The model finds outputs that score high on the reward but are actually wrong. |
| **AUROC** | How well a score separates good from bad (0.5 = random, 1.0 = perfect). |
| **ECE (calibration)** | How closely predicted confidence matches actual accuracy. |
| **OOD** | Out-of-distribution: data unlike the training data (new domain or larger size). |
| **Test-time compute** | Extra computation spent when answering (more samples, search), not when training. |

## Metrics

| Metric | Definition |
|---|---|
| **Validity** | Fraction of plans VAL accepts as reaching the goal. Main metric. |
| **Optimality gap** | (plan cost / optimal cost) - 1, over valid plans. |
| **Compute** | Generated tokens plus verifier tokens processed, in one unit. |
| **Parse failure rate** | Fraction of outputs whose actions can't be parsed (counted invalid). |

## Label definitions used in this project

For a plan prefix a1..ak and next step a(k+1):

- **executable:** a(k+1) is applicable in the state after a1..ak
- **progress:** compare h* before and after the step: *decrease* = good progress, *same* = neutral, *increase* = detour
- **invalid:** a precondition fails; the step cannot be applied

## Reading list (for related work)

1. Lightman et al. (2023), *Let's Verify Step by Step* (process reward models)
2. Wang et al. (2022), *Self-Consistency Improves Chain of Thought Reasoning in Language Models*
3. Valmeekam et al. (2022), *PlanBench*
4. Shao et al. (2024), *DeepSeekMath* (GRPO)
5. Helmert (2006), *The Fast Downward Planning System*
6. Snell et al. (2024), *Scaling LLM Test-Time Compute Optimally Can Be More Effective than Scaling Model Parameters*

Verify each citation's details (authors, year, venue) on the paper's page before putting it in the report.
