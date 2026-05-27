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

## Main Runs

| L | prefix k | Gurobi status | runtime | fixed classes | proven prefix cover bound | remaining reciprocal sum | certified total upper | conclusion |
|---:|---:|---|---:|---|---:|---:|---:|---|
| 5040 | 20 | TIME_LIMIT | 120.15s | 6:7, 7:8, 8:9 | 4616 / 5040 | 179/840 ~= 0.213095 | 1.128968 | no certificate |
| 5040 | 30 | TIME_LIMIT | 120.22s | 6:7, 7:8, 8:9 | 5040 / 5040 | 29/360 ~= 0.080556 | 1.080556 | no certificate |
| 5040 | 40 | TIME_LIMIT | 600.45s | 6:7, 7:8, 8:9 | 5040 / 5040 | 1/45 ~= 0.022222 | 1.022222 | no certificate |
| 7560 | 23 | OPTIMAL | 1158.36s | 6:7, 7:8, 8:9 | 6623 / 7560 | 17/105 ~= 0.161905 | 1.037963 | no certificate |
| 8400 | 20 | TIME_LIMIT | 600.18s | 6:7, 7:8, 14:15 | 6942 / 8400 | 83/525 ~= 0.158095 | 0.984524 | certified impossible for this setup |

## Quick Scans

These scans were used to compare choices of the prefix size `k`.

### L = 7560

Precheck scan with `k = 20, 23, 26, 30`:

| k | selected bound | tail bound | total precheck bound | conclusion |
|---:|---:|---:|---:|---|
| 20 | 7311 | 1437 | 8748 / 7560 = 1.157143 | no certificate |
| 23 | 7644 | 1104 | 8748 / 7560 = 1.157143 | no certificate |
| 26 | 7920 | 828 | 8748 / 7560 = 1.157143 | no certificate |
| 30 | 8169 | 579 | 8748 / 7560 = 1.157143 | no certificate |

### L = 8400

Short 60-second bound runs:

| k | Gurobi status | runtime | proven prefix cover bound | remaining reciprocal sum | certified total upper | conclusion |
|---:|---|---:|---:|---:|---:|---|
| 20 | TIME_LIMIT | 61.05s | 7260 / 8400 | 83/525 ~= 0.158095 | 1.022381 | no certificate |
| 25 | TIME_LIMIT | 60.84s | 8079 / 8400 | 269/2800 ~= 0.096071 | 1.057857 | no certificate |
| 30 | TIME_LIMIT | 60.32s | 8400 / 8400 | 233/4200 ~= 0.055476 | 1.055476 | no certificate |

The stronger 600-second run for `L = 8400, k = 20` did produce a certificate:

```text
6942 / 8400 + 83/525 = 0.9845238095 < 1.
```

## Source Files

Local source result files used to prepare this summary:

- `partial_bound_L5040_k20.json`
- `partial_bound_L5040_k30.json`
- `partial_bound_L5040_k40_20260504_174348.json`
- `partial_bound_L7560_k20_23_26_30_precheck.json`
- `partial_bound_L7560_k23_nolimit_boundonly_20260504_195816.json`
- `partial_bound_L8400_k20_25_30_quick60.json`
- `partial_bound_L8400_k20_600s_20260504_191913.json`
