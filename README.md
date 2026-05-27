# Minimum-Modulus 7 Covering-System Experiments

Author: Shiliang Zhang

This repository contains Gurobi-based scripts used for experiments on distinct covering systems with minimum modulus `m = 7`.

## Scripts

- `partial_cover_bound_gurobi.py`

  Computes a rigorous partial-cover upper bound. The first `k` moduli are optimized with Gurobi to maximize the number of covered residues, while the remaining moduli are bounded by their reciprocal sum. If

  ```text
  covered_fraction_bound + remaining_reciprocal_sum < 1,
  ```

  then the selected `L` cannot admit a full cover under that setup.

- `decide_dcs_m7_gurobi.py`

  Direct feasibility model for deciding whether a distinct covering system with minimum modulus `7` and a chosen lcm `L` exists. Candidate moduli are all divisors `d | L` with `d >= 7`; CRT-normalized residue classes can be fixed with repeated `--add-preset a:m` options.

## Example commands

```bash
python partial_cover_bound_gurobi.py --L 7560 --prefix-count 23 --local-blocks
```

```bash
python decide_dcs_m7_gurobi.py --lcm 8400 --no-default-presets \
  --add-preset 6:7 --add-preset 7:8 --add-preset 14:15
```

```bash
python decide_dcs_m7_gurobi.py --lcm 10080 --no-default-presets \
  --add-preset 6:7 --add-preset 7:8 --add-preset 8:9 --add-preset 33:35 \
  --heuristics 0.5 --mip-focus 1
```

## Requirements

- Python 3.9+
- Gurobi with a valid license
- `gurobipy`

Some experimental variants may also use `numpy` or `scipy`, but the two scripts listed above are the main files for the partial-bound and direct-feasibility approaches.
