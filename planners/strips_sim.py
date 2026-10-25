#!/usr/bin/env python3
"""A small STRIPS simulator for PDDL domains.

It reads a domain file and a problem file, executes a plan step by step, and
reports the first step that breaks a rule. It is used to (1) check LLM plans
quickly without calling VAL, and (2) compute step-level labels in Phase 3.

Supported PDDL subset (enough for Blocksworld, Logistics, Gripper, ...):
  - :strips and :typing, with a simple type hierarchy
  - actions with :parameters, :precondition and :effect
  - conjunctions (and), positive and negated (not) literals
  - no quantifiers, disjunctions, conditional effects, or numeric fluents
    (an error is raised if they appear)

VAL stays the ground truth. Cross-check this simulator against it with
`python eval/check_sim_vs_val.py`.

Command line:
    python planners/strips_sim.py DOMAIN.pddl PROBLEM.pddl PLAN.txt
"""
import re
import sys
from pathlib import Path


# ----------------------------------------------------------------- parsing
def _tokenize(text):
    text = re.sub(r";[^\n]*", "", text)
    return re.findall(r"\(|\)|[^\s()]+", text)


def parse_sexp(text):
    """Parse PDDL text into nested lists of lowercase strings."""
    stack = [[]]
    for tok in _tokenize(text):
        if tok == "(":
            stack.append([])
        elif tok == ")":
            if len(stack) < 2:
                raise ValueError("unbalanced parentheses")
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(tok.lower())
    if len(stack) != 1:
        raise ValueError("unbalanced parentheses")
    return stack[0]


def _typed_list(items):
    """[a, b, '-', t, c] -> [(a, t), (b, t), (c, 'object')]"""
    out, pending, i = [], [], 0
    while i < len(items):
        if items[i] == "-":
            typ = items[i + 1]
            if isinstance(typ, list):
                raise NotImplementedError("'either' types are not supported")
            out += [(n, typ) for n in pending]
            pending, i = [], i + 2
        else:
            pending.append(items[i])
            i += 1
    out += [(n, "object") for n in pending]
    return out


def _literals(cond):
    """Flatten a conjunction into [(negated, predicate, args)]."""
    if not cond:
        return []
    head = cond[0]
    if head == "and":
        lits = []
        for sub in cond[1:]:
            lits += _literals(sub)
        return lits
    if head == "not":
        pred, *args = cond[1]
        return [(True, pred, tuple(args))]
    if head in ("or", "imply", "forall", "exists", "when", "increase", "="):
        raise NotImplementedError(f"unsupported PDDL construct: {head}")
    return [(False, head, tuple(cond[1:]))]


class Action:
    def __init__(self, name, params, pre, eff):
        self.name = name
        self.params = params          # [(var, type)]
        self.pre = pre                # [(negated, pred, args)]
        self.eff = eff                # [(negated, pred, args)]


class Domain:
    def __init__(self, name, actions, parent):
        self.name = name
        self.actions = actions        # name -> Action
        self.parent = parent          # type -> parent type

    def is_a(self, typ, want):
        if want == "object":
            return True
        seen = 0
        while typ is not None and seen < 50:
            if typ == want:
                return True
            typ = self.parent.get(typ)
            seen += 1
        return False


class Problem:
    def __init__(self, name, objects, init, goal):
        self.name = name
        self.objects = objects        # name -> type
        self.init = init              # set of fact tuples (pred, *args)
        self.goal = goal              # [(negated, pred, args)]


def parse_domain(text):
    forms = parse_sexp(text)[0]
    name, actions, parent = forms[1][1], {}, {}
    for f in forms[2:]:
        if f[0] == ":types":
            for n, t in _typed_list(f[1:]):
                if n != t:
                    parent[n] = t
        elif f[0] == ":action":
            opts = {f[i]: f[i + 1] for i in range(2, len(f) - 1, 2)}
            params = _typed_list(opts.get(":parameters", []))
            pre = _literals(opts.get(":precondition", []))
            eff = _literals(opts.get(":effect", []))
            actions[f[1]] = Action(f[1], params, pre, eff)
    return Domain(name, actions, parent)


def parse_problem(text):
    forms = parse_sexp(text)[0]
    name, objects, init, goal = forms[1][1], {}, set(), []
    for f in forms[2:]:
        if f[0] == ":objects":
            objects = dict(_typed_list(f[1:]))
        elif f[0] == ":init":
            init = {(x[0], *x[1:]) for x in f[1:]}
        elif f[0] == ":goal":
            goal = _literals(f[1])
    return Problem(name, objects, init, goal)


def load_domain(path):
    return parse_domain(Path(path).read_text(encoding="utf-8"))


def load_problem(path):
    return parse_problem(Path(path).read_text(encoding="utf-8"))


# -------------------------------------------------------------- execution
_ACTION_RE = re.compile(r"\(\s*([^\s()]+)((?:\s+[^\s()]+)*)\s*\)")


def parse_action(text):
    """'(stack b1 b2)' -> ('stack', ('b1', 'b2')), or None if malformed."""
    m = _ACTION_RE.fullmatch(text.strip().lower())
    if not m:
        return None
    return m.group(1), tuple(m.group(2).split())


def _ground(args, binding):
    return tuple(binding.get(a, a) for a in args)


def apply_action(domain, problem, state, action_text):
    """Apply one action. Returns (new_state, None) or (None, reason)."""
    parsed = parse_action(action_text)
    if parsed is None:
        return None, f"malformed action: {action_text!r}"
    name, args = parsed
    act = domain.actions.get(name)
    if act is None:
        return None, f"unknown action: {name}"
    if len(args) != len(act.params):
        return None, f"{name} expects {len(act.params)} arguments, got {len(args)}"
    binding = {}
    for (var, typ), obj in zip(act.params, args):
        if obj not in problem.objects:
            return None, f"unknown object: {obj}"
        if not domain.is_a(problem.objects[obj], typ):
            return None, f"{obj} is not of type {typ}"
        binding[var] = obj
    for neg, pred, pargs in act.pre:
        fact = (pred, *_ground(pargs, binding))
        if (fact in state) == neg:
            need = "false" if neg else "true"
            return None, f"precondition not met: ({pred} {' '.join(fact[1:])}) must be {need}"
    new = set(state)
    for neg, pred, pargs in act.eff:           # deletes first, then adds
        if neg:
            new.discard((pred, *_ground(pargs, binding)))
    for neg, pred, pargs in act.eff:
        if not neg:
            new.add((pred, *_ground(pargs, binding)))
    return new, None


def goal_reached(problem, state):
    return all(((pred, *args) in state) != neg for neg, pred, args in problem.goal)


def simulate(domain, problem, plan):
    """Run a plan (list of action strings).

    Returns a dict:
      valid       True only if every step is executable AND the goal holds at the end
      failed_at   index of the first illegal step, or None
      reason      text explaining the failure (or 'goal not reached')
      reached     True if the goal holds at the end of the executed steps
      steps_ok    number of steps executed successfully
    """
    state = set(problem.init)
    for i, step in enumerate(plan):
        new, err = apply_action(domain, problem, state, step)
        if err:
            return {"valid": False, "failed_at": i, "reason": err,
                    "reached": False, "steps_ok": i}
        state = new
    reached = goal_reached(problem, state)
    return {"valid": reached, "failed_at": None,
            "reason": None if reached else "goal not reached",
            "reached": reached, "steps_ok": len(plan)}


def state_after(domain, problem, plan, k):
    """State after the first k steps (None if any of them is illegal)."""
    state = set(problem.init)
    for step in plan[:k]:
        state, err = apply_action(domain, problem, state, step)
        if err:
            return None
    return state


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    domain, problem = load_domain(sys.argv[1]), load_problem(sys.argv[2])
    plan = [ln.strip() for ln in Path(sys.argv[3]).read_text().splitlines()
            if ln.strip() and not ln.startswith(";")]
    res = simulate(domain, problem, plan)
    print("VALID" if res["valid"] else f"INVALID: {res['reason']} (step {res['failed_at']})")
    sys.exit(0 if res["valid"] else 1)


if __name__ == "__main__":
    main()
