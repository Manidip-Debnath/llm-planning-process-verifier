Results file: Qwen2.5-7B-Instruct.jsonl   problems: 100   model: Qwen/Qwen2.5-7B-Instruct (4-bit)   samples/problem: 32

| Method | Validity | Tokens / problem | Optimality gap (valid plans) |
|---|---|---|---|
| Greedy | 7.0% | 38 | nan% |
| Self-consistency, N=1 | 4.0% | 39 | nan% |
| Self-consistency, N=2 | 4.0% | 77 | nan% |
| Self-consistency, N=4 | 5.0% | 154 | nan% |
| Self-consistency, N=8 | 7.0% | 307 | nan% |
| Self-consistency, N=16 | 7.0% | 612 | nan% |
| Self-consistency, N=32 | 6.0% | 1228 | nan% |

| N | Avg single-sample validity | Self-consistency validity | Oracle best-of-N (ceiling) | Tokens |
|---|---|---|---|---|
| 1 | 4.0% | 4.0% | 4.0% | 39 |
| 2 | 4.5% | 4.0% | 6.0% | 77 |
| 4 | 5.5% | 5.0% | 10.0% | 154 |
| 8 | 5.5% | 7.0% | 12.0% | 307 |
| 16 | 6.0% | 7.0% | 14.0% | 612 |
| 32 | 5.8% | 6.0% | 14.0% | 1228 |

| Blocks | Problems | Greedy validity | Avg sample validity | Oracle best-of-N |
|---|---|---|---|---|
| 3 | 25 | 24.0% | 16.4% | 36.0% |
| 4 | 25 | 4.0% | 6.9% | 20.0% |
| 5 | 25 | 0.0% | 0.0% | 0.0% |
| 6 | 25 | 0.0% | 0.0% | 0.0% |

Greedy outputs with no parseable action: 0.0%
Most common failure reasons among sampled plans: precondition not met (2982), goal not reached (19), unknown object (12), unstack expects 2 arguments, got 1 (1)
