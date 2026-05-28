# Reciprocal-Sum / Partial-Cover Bound Results

These results were produced by `partial_cover_bound_gurobi.py`.

The method splits the moduli into a prefix part and a tail part. Gurobi is used
to upper-bound how many residues can be covered by the prefix. The tail is then
bounded by the reciprocal sum of the remaining moduli.

Certification criterion:

```text
proven_prefix_cover_bound / L + remaining_reciprocal_sum < 1
```

If this strict inequality holds, then the selected setup cannot cover all of
`Z/LZ`.

`PRECHECK_INFEASIBLE` means that the instance was certified before building the
Gurobi MIP. After the fixed residue classes are applied, the code computes, for
each remaining modulus separately, the largest number of still-uncovered points
that any one residue class modulo that modulus could cover. These independent
best-case counts are then added together. This is an optimistic upper bound,
because it ignores overlaps between different residue classes. If even this
upper bound is smaller than `L`, then a full cover is impossible.

## Remaining L Batch, k = 20

This server batch used `prefix_count = 20`, `time_limit = 600s` for each `L`, and `threads = 32`. Raw output is saved in [`partial_bound_remaining_k20_summary.txt`](partial_bound_remaining_k20_summary.txt).

| L | status | runtime | fixed classes | proven prefix cover bound | remaining reciprocal sum | certified total upper | conclusion |
|---:|---|---:|---|---:|---:|---:|---|
| 5544 | PRECHECK_INFEASIBLE | 0.01s | 6:7, 7:8, 8:9, 10:11 | NA | 265/2772 ~= 0.095599 | NA | certified by precheck |
| 5880 | PRECHECK_INFEASIBLE | 0.01s | 6:7, 7:8, 14:15 | NA | 18/245 ~= 0.073469 | NA | certified by precheck |
| 6048 | PRECHECK_INFEASIBLE | 0.01s | 6:7, 7:8, 8:9 | NA | 59/672 ~= 0.087798 | NA | certified by precheck |
| 6300 | PRECHECK_INFEASIBLE | 0.02s | 6:7, 8:9, 9:10 | NA | 79/630 ~= 0.125397 | NA | certified by precheck |
| 6552 | PRECHECK_INFEASIBLE | 0.01s | 6:7, 7:8, 8:9, 12:13 | NA | 139/1638 ~= 0.084860 | NA | certified by precheck |
| 6720 | BOUND_CERTIFIED | 52.22s | 6:7, 7:8, 14:15 | 5785 / 6720 | 311/2240 ~= 0.138839 | 0.999702 | certified |
| 6930 | PRECHECK_INFEASIBLE | 0.01s | 6:7, 8:9, 9:10, 10:11 | NA | 53/630 ~= 0.084127 | NA | certified by precheck |
| 7056 | PRECHECK_INFEASIBLE | 0.01s | 6:7, 7:8, 8:9 | NA | 101/1764 ~= 0.057256 | NA | certified by precheck |
| 7392 | PRECHECK_INFEASIBLE | 0.01s | 6:7, 7:8, 10:11 | NA | 577/7392 ~= 0.078057 | NA | certified by precheck |
| 8064 | PRECHECK_INFEASIBLE | 0.01s | 6:7, 7:8, 8:9 | NA | 293/4032 ~= 0.072669 | NA | certified by precheck |
| 8568 | PRECHECK_INFEASIBLE | 0.01s | 6:7, 7:8, 8:9, 16:17 | NA | 149/2142 ~= 0.069561 | NA | certified by precheck |
| 8820 | PRECHECK_INFEASIBLE | 0.02s | 6:7, 8:9, 9:10 | NA | 877/8820 ~= 0.099433 | NA | certified by precheck |
| 9072 | PRECHECK_INFEASIBLE | 0.01s | 6:7, 7:8, 8:9 | NA | 46/567 ~= 0.081129 | NA | certified by precheck |
| 9240 | BOUND_CERTIFIED | 235.94s | 6:7, 7:8, 10:11, 14:15 | 7483 / 9240 | 877/4620 ~= 0.189827 | 0.999675 | certified |
| 9576 | PRECHECK_INFEASIBLE | 0.02s | 6:7, 7:8, 8:9, 18:19 | NA | 11/171 ~= 0.064327 | NA | certified by precheck |
