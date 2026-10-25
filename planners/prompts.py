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


def towers(facts, objects):
    """Render a state as towers, bottom to top, e.g. '[b1 b2] [b3]'."""
    on = {f[1]: f[2] for f in facts if f[0] == "on"}          # top -> below
    held = [f[1] for f in facts if f[0] == "holding"]
    below = set(on.values())
    tops = [b for b in sorted(objects) if b not in below and b not in held]
    out = []
    for top in tops:
        chain, cur = [top], top
        while cur in on:
            cur = on[cur]
            chain.append(cur)
        out.append("[" + " ".join(reversed(chain)) + "]")
    s = " ".join(out) if out else "(no towers)"
    return s + ("; holding " + held[0] if held else "; hand empty")


STATE_SYSTEM = SYSTEM_PROMPT.replace(
    'Find a short plan that reaches the goal. Write the word "Plan:" and then one action per line, with parentheses, and nothing after the plan.',
    "Work step by step. First write \"Start:\" with the towers you see. Then, for each action, write the action and "
    "the towers after it, checking that its requirements hold in the current state. When the goal is reached write "
    "\"Goal reached.\" Then write the word \"Plan:\" and the actions, one per line, with parentheses, and nothing after the plan.\n"
    "A tower is written bottom to top, so [b1 b2] means b2 is on b1 and b1 is on the table.")

_EXAMPLE_STATE_ANSWER = """Start: [b1 b2] [b3]; hand empty
1. (unstack b2 b1) -> [b1] [b3]; holding b2
2. (stack b2 b3) -> [b1] [b3 b2]; hand empty
3. (pick-up b1) -> [b3 b2]; holding b1
4. (stack b1 b2) -> [b3 b2 b1]; hand empty
Goal reached.
Plan:
""" + "\n".join(_EXAMPLE_PLAN)


def _describe_towers(init, goal, objects):
    return (describe(init, goal, objects) +
            "\nStart towers: " + towers(init, objects) +
            "\nGoal towers: " + towers_goal(goal, objects))


def towers_goal(goal, objects):
    on = {f[1]: f[2] for f in goal if f[0] == "on"}
    below = set(on.values())
    tops = [b for b in sorted(objects) if b not in below and b in on or (b not in below and b not in on)]
    parts = []
    for top in tops:
        chain, cur = [top], top
        while cur in on:
            cur = on[cur]
            chain.append(cur)
        if len(chain) > 1:
            parts.append("[" + " ".join(reversed(chain)) + "]")
    return (" ".join(parts) + " (other blocks as in the goal facts)") if parts else "(just the facts above)"


def build_messages(problem, few_shot=True, style="plain"):
    """style='plain': answer is just the plan. style='state': write the towers after each action."""
    if style == "state":
        msgs = [{"role": "system", "content": STATE_SYSTEM}]
        if few_shot:
            msgs.append({"role": "user", "content": _describe_towers(
                _EXAMPLE_INIT, _EXAMPLE_GOAL, ["b1", "b2", "b3"])})
            msgs.append({"role": "assistant", "content": _EXAMPLE_STATE_ANSWER})
        goal = [(pred, *args) for neg, pred, args in problem.goal if not neg]
        msgs.append({"role": "user", "content": _describe_towers(
            problem.init, goal, problem.objects)})
        return msgs
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
