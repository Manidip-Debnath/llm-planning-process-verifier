Results file: Qwen2.5-7B-Instruct_state.jsonl   problems: 60   model: Qwen/Qwen2.5-7B-Instruct   samples/problem: 16

| Method | Validity | Tokens / problem | Optimality gap (valid plans) |
|---|---|---|---|
| Greedy | 6.7% | 209 | nan% |
| Self-consistency, N=1 | 8.3% | 216 | nan% |
| Self-consistency, N=2 | 8.3% | 416 | nan% |
| Self-consistency, N=4 | 6.7% | 841 | nan% |
| Self-consistency, N=8 | 8.3% | 1682 | nan% |
| Self-consistency, N=16 | 11.7% | 3343 | nan% |

| N | Avg single-sample validity | Self-consistency validity | Oracle best-of-N (ceiling) | Tokens |
|---|---|---|---|---|
| 1 | 8.3% | 8.3% | 8.3% | 216 |
| 2 | 5.8% | 8.3% | 10.0% | 416 |
| 4 | 5.4% | 6.7% | 11.7% | 841 |
| 8 | 7.1% | 8.3% | 21.7% | 1682 |
| 16 | 8.6% | 11.7% | 28.3% | 3343 |

| Blocks | Problems | Greedy validity | Avg sample validity | Oracle best-of-N |
|---|---|---|---|---|
| 3 | 20 | 15.0% | 20.9% | 60.0% |
| 4 | 20 | 5.0% | 4.7% | 20.0% |
| 5 | 20 | 0.0% | 0.3% | 5.0% |

Greedy outputs with no parseable action: 0.0%
Most common failure reasons among sampled plans: precondition not met (811), goal not reached (28), unstack expects 2 arguments, got 1 (21), unknown object (15), stack expects 2 arguments, got 1 (1)
