# Direct Gurobi Feasibility Results

These results were produced by the direct feasibility solver
`decide_dcs_m7_gurobi.py` or its local per-`L` variants.

The model uses the Klein-lemma / saturation reduction: for a fixed `L`, it is
enough to assign exactly one residue class to every divisor `d | L` with
`d >= 7`. If Gurobi proves this saturated model infeasible, then no distinct
covering system exists for that setup.

## Solver Settings

Typical proof-oriented settings:

```bash
--heuristics 0 --mip-focus 3 --presolve 2 --cuts 2 --symmetry 2
```

For the `L = 10080` feasibility search, the run used a more solution-oriented
configuration:

```bash
--heuristics 0.5 --mip-focus 1 --presolve 2 --cuts 1 --symmetry 2 --threads 32
```

## Main Direct Runs

| L | status | runtime | explored nodes | simplex iterations | fixed classes | notes |
|---:|---|---:|---:|---:|---|---|
| 5040 | INFEASIBLE | 13789.26s | 98459 | 530782259 | 6:7, 7:8, 8:9, 33:35 | proved infeasible on server |
| 7560 | INFEASIBLE | 13159.68s | 13533 | 186697085 | 6:7, 7:8, 8:9, 33:35 | proved infeasible on server |
| 8400 | INFEASIBLE | 922.05s | 43 | 1029894 | 6:7, 7:8, 14:15 | proved infeasible on server |
| 9240 | INFEASIBLE | 590.53s | 19 | 574977 | 6:7, 7:8, 10:11, 14:15 | proved infeasible on server |
| 10080 | FEASIBLE | 9419.56s | 122934 | 212547442 | 6:7, 7:8, 8:9, 33:35 | covering system found; independent verification passed |

## Selected L Batch

The following selected `L` values were tested with the same direct feasibility
model and the listed CRT-normalized fixed classes.

| L | status | runtime | fixed classes |
|---:|---|---:|---|
| 5544 | INFEASIBLE | 5.34s | 6:7, 7:8, 8:9, 10:11 |
| 5880 | INFEASIBLE | 7.91s | 6:7, 7:8, 14:15 |
| 6048 | INFEASIBLE | 6.88s | 6:7, 7:8, 8:9 |
| 6300 | INFEASIBLE | 21.05s | 6:7, 8:9, 9:10 |
| 6552 | INFEASIBLE | 6.46s | 6:7, 7:8, 8:9, 12:13 |
| 6720 | INFEASIBLE | 132.31s | 6:7, 7:8, 14:15 |
| 6930 | INFEASIBLE | 5.13s | 6:7, 8:9, 9:10, 10:11 |
| 7056 | INFEASIBLE | 5.78s | 6:7, 7:8, 8:9 |
| 7392 | INFEASIBLE | 6.99s | 6:7, 7:8, 10:11 |
| 8064 | INFEASIBLE | 7.24s | 6:7, 7:8, 8:9 |
| 8568 | INFEASIBLE | 7.08s | 6:7, 7:8, 8:9, 16:17 |
| 8820 | INFEASIBLE | 17.90s | 6:7, 8:9, 9:10 |
| 9072 | INFEASIBLE | 9.54s | 6:7, 7:8, 8:9 |
| 9576 | INFEASIBLE | 9.03s | 6:7, 7:8, 8:9, 18:19 |

## Summary

Direct Gurobi infeasibility proofs in this record:

```text
5040, 5544, 5880, 6048, 6300, 6552, 6720, 6930, 7056, 7392,
7560, 8064, 8400, 8568, 8820, 9072, 9240, 9576
```

Direct Gurobi feasible run in this record:

```text
10080
```

## Source Logs

Local result files used to prepare this summary:

- `5040.txt`
- `7560.txt`
- `L_run_results.txt`
- `remote_decide_m7_L8400_20260506_233446.log`
- `remote_decide_m7_L9240_20260506_233501.log`
- `remote_decide_m7_L10080_find_20260507_000110.log`
