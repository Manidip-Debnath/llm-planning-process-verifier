#!/usr/bin/env python3
"""Exact optimal cost-to-go h*(state) for small STRIPS problems.

Blocksworld with up to ~6 blocks has at most a few thousand states, so we
enumerate every state reachable from the initial state and run one backward
breadth-first search from all goal states. That gives the exact h* (number of
actions of an optimal plan) for every state, for free, for every plan prefix.
Fast Downward (astar+lmcut) gives the same number for the initial state; the
check is in eval/check_h_vs_fd.py (run it if you built Fast Downward).

Usage as a library:
    graph = StateGraph(domain, problem)
    graph.h(state)           # int, or None if the goal is unreachable from it
"""
import itertools
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "planners"))
from strips_sim import apply_action, goal_reached  # noqa: E402


def ground_actions(domain, problem):
    """All action strings such as '(stack b1 b2)' with type-correct arguments."""
    out = []
    for name, act in domain.actions.items():
        pools = [[o for o, t in problem.objects.items() if domain.is_a(t, typ)]
                 for _, typ in act.params]
        for args in itertools.product(*pools):
            out.append(f"({name} {' '.join(args)})".replace(" )", ")"))
    return out


class StateGraph:
    def __init__(self, domain, problem, max_states=200_000):
        self.domain, self.problem = domain, problem
        self.actions = ground_actions(domain, problem)
        start = frozenset(problem.init)
        index, states, edges = {start: 0}, [start], []
        queue = deque([0])
        while queue:
            i = queue.popleft()
            for a in self.actions:
                new, err = apply_action(domain, problem, states[i], a)
                if err:
                    continue
                key = frozenset(new)
                if key not in index:
                    if len(states) >= max_states:
                        raise RuntimeError("state space too large for exact h*")
                    index[key] = len(states)
                    states.append(key)
                    queue.append(index[key])
                edges.append((i, index[key]))
        self.index, self.states = index, states
        rev = [[] for _ in states]
        for u, v in edges:
            rev[v].append(u)
        dist = [None] * len(states)
        queue = deque()
        for i, s in enumerate(states):
            if goal_reached(problem, s):
                dist[i] = 0
                queue.append(i)
        while queue:
            v = queue.popleft()
            for u in rev[v]:
                if dist[u] is None:
                    dist[u] = dist[v] + 1
                    queue.append(u)
        self.dist = dist

    def h(self, state):
        i = self.index.get(frozenset(state))
        return None if i is None else self.dist[i]
