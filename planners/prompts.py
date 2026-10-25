"""Prompt construction and plan parsing for the LLM planner (Blocksworld)."""
import re

SYSTEM_PROMPT = """You control a robot arm that moves blocks on a table.

Actions:
(pick-up X)   pick up block X from the table. Needs: X is clear, X is on the table, the arm is empty.
(put-down X)  put the block X you are holding onto the table. Needs: you are holding X.
(stack X Y)   put the block X you are holding on top of block Y. Needs: you are holding X and Y is clear.
(unstack X Y) pick up block X from on top of block Y. Needs: X is on Y, X is clear, the arm is empty.

A block is "clear" if nothing is on top of it. The arm holds at most one block.
Find a short plan that reaches the goal. Write the word "Plan:" and then one action per line, with parentheses, and nothing after the plan."""

# One worked example, solved optimally (checked with the simulator and VAL).
_EXAMPLE_INIT = [("on-table", "b1"), ("on", "b2", "b1"), ("on-table", "b3"),
                 ("clear", "b2"), ("clear", "b3"), ("arm-empty",)]
_EXAMPLE_GOAL = [("on-table", "b3"), ("on", "b2", "b3"), ("on", "b1", "b2")]
_EXAMPLE_PLAN = ["(unstack b2 b1)", "(stack b2 b3)", "(pick-up b1)", "(stack b1 b2)"]


def _fact_text(fact):
    pred, *args = fact
    if pred == "on-table":
        return f"{args[0]} is on the table"
    if pred == "on":
        return f"{args[0]} is on {args[1]}"
    if pred == "clear":
        return f"{args[0]} is clear"
    if pred == "arm-empty":
        return "the arm is empty"
    if pred == "holding":
        return f"the arm is holding {args[0]}"
    return "(" + " ".join(fact) + ")"


def describe(init_facts, goal_facts, objects):
    order = {"on-table": 0, "on": 1, "clear": 2, "arm-empty": 3, "holding": 4}
    init = sorted(init_facts, key=lambda f: (order.get(f[0], 9), f[1:]))
    goal = sorted(goal_facts, key=lambda f: (order.get(f[0], 9), f[1:]))
    return (f"Blocks: {', '.join(sorted(objects))}\n"
            "Initial state:\n" + "\n".join(f"- {_fact_text(f)}" for f in init) +
            "\nGoal:\n" + "\n".join(f"- {_fact_text(f)}" for f in goal))


def problem_text(problem):
    """Describe a parsed problem (strips_sim.Problem) in plain language."""
    goal = [(pred, *args) for neg, pred, args in problem.goal if not neg]
    return describe(problem.init, goal, problem.objects)


def build_messages(problem, few_shot=True):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    if few_shot:
        msgs.append({"role": "user", "content": describe(
            _EXAMPLE_INIT, _EXAMPLE_GOAL, ["b1", "b2", "b3"])})
        msgs.append({"role": "assistant", "content": "Plan:\n" + "\n".join(_EXAMPLE_PLAN)})
    msgs.append({"role": "user", "content": problem_text(problem)})
    return msgs


_ACTION_RE = re.compile(r"\(\s*[a-z][a-z0-9_-]*(?:\s+[a-z0-9_-]+)*\s*\)")


def parse_plan(text, max_steps=80):
    """Extract actions from model output. Returns a list like ['(unstack b2 b1)', ...].

    Only text after the last 'Plan:' is used (if present). Anything that is not
    a parenthesised action is ignored, so a rambling answer yields a short or
    empty plan, which the simulator then judges invalid.
    """
    low = text.lower()
    idx = low.rfind("plan:")
    body = low[idx + len("plan:"):] if idx >= 0 else low
    steps = [" ".join(m.group(0).strip("()").split()) for m in _ACTION_RE.finditer(body)]
    return ["(" + s + ")" for s in steps][:max_steps]
