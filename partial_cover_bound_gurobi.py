#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import Dict, Iterable, List, Optional, Sequence


def factorint(n: int) -> Dict[int, int]:
    if n <= 0:
        raise ValueError("n must be positive")
    out: Dict[int, int] = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            out[d] = out.get(d, 0) + 1
            n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        out[n] = out.get(n, 0) + 1
    return out


def divisors_from_factorization(factors: Dict[int, int]) -> List[int]:
    divs = [1]
    for p, a in factors.items():
        divs = [d * (p**e) for d in divs for e in range(a + 1)]
    return sorted(divs)


def divisors(n: int) -> List[int]:
    return divisors_from_factorization(factorint(n))


def choose_fixed_residues(moduli: Sequence[int], min_mod: int = 7, max_fixed: int = 4) -> Dict[int, int]:
    selected: List[int] = []
    ordered = []
    if min_mod in moduli:
        ordered.append(min_mod)
    ordered.extend([d for d in sorted(moduli) if d != min_mod])
    for d in ordered:
        if len(selected) >= max_fixed:
            break
        if all(math.gcd(d, e) == 1 for e in selected):
            selected.append(d)
    return {d: d - 1 for d in selected}


def fixed_covered_points(L: int, fixed: Dict[int, int]) -> set[int]:
    covered: set[int] = set()
    for mod, residue in fixed.items():
        covered.update(j for j in range(residue, L, mod))
    return covered


def reciprocal_sum(moduli: Iterable[int]) -> Fraction:
    return sum((Fraction(1, d) for d in moduli), Fraction(0, 1))


def max_new_points_for_mod(mod: int, uncovered_points: Sequence[int]) -> int:
    counts = [0] * mod
    for point in uncovered_points:
        counts[point % mod] += 1
    return max(counts) if counts else 0


def frac_float(frac: Fraction) -> float:
    return float(frac.numerator) / float(frac.denominator)


def strict_cover_limit(L: int, remaining_recip: Fraction) -> int:
    """Largest integer c with c / L + remaining_recip < 1."""
    target = Fraction(L, 1) * (1 - remaining_recip)
    return (target.numerator - 1) // target.denominator


@dataclass
class PartialCoverBoundResult:
    L: int
    min_mod: int
    prefix_count: int
    status: str
    runtime_sec: float
    n_all_moduli: int
    n_selected_moduli: int
    n_remaining_moduli: int
    fixed: Dict[int, int]
    base_covered_count: int
    uncovered_count: int
    n_free_moduli: int
    n_y_variables: int
    n_x_variables: int
    global_reciprocal_sum: str
    global_reciprocal_float: float
    precheck_selected_cover_bound: int
    precheck_remaining_cover_bound: int
    precheck_total_cover_bound: int
    precheck_total_upper: float
    precheck_certifies_infeasible: bool
    bound_certify_cover_limit: int
    bound_certify_added_limit: int
    bound_stop_triggered: bool
    n_local_block_constraints: int
    objective_incumbent_added: Optional[int]
    objective_bound_added: Optional[int]
    incumbent_covered: Optional[int]
    bound_covered: Optional[int]
    remaining_reciprocal_sum: str
    remaining_reciprocal_float: float
    incumbent_total_upper: Optional[float]
    certified_total_upper: Optional[float]
    certifies_infeasible: bool
    selected_moduli: List[int]
    remaining_moduli: List[int]
    note: str = ""


def solve_partial_cover_bound_gurobi(
    L: int = 8400,
    min_mod: int = 7,
    prefix_count: int = 46,
    max_fixed: int = 4,
    time_limit: Optional[float] = 0.0,
    threads: int = 0,
    seed: Optional[int] = None,
    mip_focus: int = 3,
    output_flag: int = 1,
    precheck_only: bool = False,
    local_blocks: bool = False,
    local_qs: Optional[Sequence[int]] = None,
) -> PartialCoverBoundResult:
    t0 = time.time()
    all_moduli = [d for d in divisors(L) if d >= min_mod]
    if not 1 <= prefix_count <= len(all_moduli):
        raise ValueError(f"prefix_count must be in [1, {len(all_moduli)}]")

    selected_moduli = all_moduli[:prefix_count]
    remaining_moduli = all_moduli[prefix_count:]
    fixed_all = choose_fixed_residues(all_moduli, min_mod=min_mod, max_fixed=max_fixed)
    fixed = {d: r for d, r in fixed_all.items() if d in selected_moduli}

    covered_by_fixed = fixed_covered_points(L, fixed)
    uncovered = [j for j in range(L) if j not in covered_by_fixed]
    free_moduli = [d for d in selected_moduli if d not in fixed]
    global_recip = reciprocal_sum(all_moduli)
    remaining_recip = reciprocal_sum(remaining_moduli)

    max_new_by_mod = {mod: max_new_points_for_mod(mod, uncovered) for mod in all_moduli if mod not in fixed}
    precheck_selected_bound = len(covered_by_fixed) + sum(max_new_by_mod[mod] for mod in free_moduli)
    precheck_remaining_bound = sum(max_new_by_mod[mod] for mod in remaining_moduli)
    precheck_total_bound = precheck_selected_bound + precheck_remaining_bound
    precheck_total_upper = precheck_total_bound / L
    precheck_certifies = global_recip < 1 or precheck_total_bound < L
    bound_certify_cover_limit = strict_cover_limit(L, remaining_recip)
    bound_certify_added_limit = bound_certify_cover_limit - len(covered_by_fixed)

    valid_residues: Dict[int, List[int]] = {}
    for mod in free_moduli:
        if local_blocks:
            residues = list(range(mod))
        else:
            residues = sorted({j % mod for j in uncovered})
        if not residues:
            residues = [0]
        valid_residues[mod] = residues

    if precheck_certifies or precheck_only:
        if global_recip < 1:
            note = "global reciprocal sum is below 1"
        elif precheck_total_bound < L:
            note = "fixed-residue independent coverage precheck is below L"
        else:
            note = "precheck did not certify infeasibility"
        return PartialCoverBoundResult(
            L=L,
            min_mod=min_mod,
            prefix_count=prefix_count,
            status="PRECHECK_INFEASIBLE" if precheck_certifies else "PRECHECK_UNKNOWN",
            runtime_sec=time.time() - t0,
            n_all_moduli=len(all_moduli),
            n_selected_moduli=len(selected_moduli),
            n_remaining_moduli=len(remaining_moduli),
            fixed=fixed,
            base_covered_count=len(covered_by_fixed),
            uncovered_count=len(uncovered),
            n_free_moduli=len(free_moduli),
            n_y_variables=sum(len(v) for v in valid_residues.values()),
            n_x_variables=len(uncovered),
            global_reciprocal_sum=f"{global_recip.numerator}/{global_recip.denominator}",
            global_reciprocal_float=frac_float(global_recip),
            precheck_selected_cover_bound=precheck_selected_bound,
            precheck_remaining_cover_bound=precheck_remaining_bound,
            precheck_total_cover_bound=precheck_total_bound,
            precheck_total_upper=precheck_total_upper,
            precheck_certifies_infeasible=precheck_certifies,
            bound_certify_cover_limit=bound_certify_cover_limit,
            bound_certify_added_limit=bound_certify_added_limit,
            bound_stop_triggered=precheck_certifies,
            n_local_block_constraints=0,
            objective_incumbent_added=None,
            objective_bound_added=None,
            incumbent_covered=None,
            bound_covered=None,
            remaining_reciprocal_sum=f"{remaining_recip.numerator}/{remaining_recip.denominator}",
            remaining_reciprocal_float=frac_float(remaining_recip),
            incumbent_total_upper=None,
            certified_total_upper=None,
            certifies_infeasible=precheck_certifies,
            selected_moduli=selected_moduli,
            remaining_moduli=remaining_moduli,
            note=note,
        )

    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model(f"partial_cover_bound_L{L}_k{prefix_count}")
    model.Params.OutputFlag = int(output_flag)
    model.Params.Presolve = 2
    model.Params.Cuts = 3
    model.Params.Symmetry = 2
    model.Params.MIPFocus = int(mip_focus)
    model.Params.Heuristics = 0.0
    model.Params.IntFeasTol = 1e-9
    if threads:
        model.Params.Threads = int(threads)
    if time_limit is not None and time_limit > 0:
        model.Params.TimeLimit = float(time_limit)
    if seed is not None:
        model.Params.Seed = int(seed)

    y = {}
    for mod in free_moduli:
        for residue in valid_residues[mod]:
            y[mod, residue] = model.addVar(vtype=GRB.BINARY, name=f"y_{mod}_{residue}")
        model.addConstr(
            gp.quicksum(y[mod, residue] for residue in valid_residues[mod]) == 1,
            name=f"one_residue_{mod}",
        )

    n_local_block_constraints = 0
    if local_blocks:
        if local_qs:
            q_values = sorted(set(int(q) for q in local_qs if int(q) > 1))
        else:
            q_values = [q for q in divisors(L) if q > 1]
        bad_qs = [q for q in q_values if L % q != 0]
        if bad_qs:
            raise ValueError(f"local q values must divide L={L}: {bad_qs}")

        for q in q_values:
            tail_capacity = sum((Fraction(math.gcd(mod, q), mod) for mod in remaining_moduli), Fraction(0, 1))
            if tail_capacity >= 1:
                continue
            for c in range(q):
                rhs = Fraction(1, 1) - tail_capacity
                for mod, residue in fixed.items():
                    g = math.gcd(mod, q)
                    if residue % g == c % g:
                        rhs -= Fraction(g, mod)
                if rhs <= 0:
                    continue

                terms = []
                for mod in free_moduli:
                    g = math.gcd(mod, q)
                    need = c % g
                    coeff = float(Fraction(g, mod))
                    terms.extend(
                        coeff * y[mod, residue]
                        for residue in valid_residues[mod]
                        if residue % g == need
                    )
                model.addConstr(
                    gp.quicksum(terms) >= float(rhs),
                    name=f"local_block_q{q}_c{c}",
                )
                n_local_block_constraints += 1

    x = {}
    for point in uncovered:
        x[point] = model.addVar(vtype=GRB.BINARY, name=f"x_{point}")
        covering_terms = [y[mod, point % mod] for mod in free_moduli if (mod, point % mod) in y]
        if covering_terms:
            model.addConstr(x[point] <= gp.quicksum(covering_terms), name=f"covered_{point}")
        else:
            model.addConstr(x[point] == 0, name=f"uncoverable_{point}")

    model.setObjective(gp.quicksum(x.values()), GRB.MAXIMIZE)

    model._bound_stop_triggered = False
    model._last_bound_added = None
    model._last_bound_covered = None

    def stop_when_bound_certifies(model, where):
        if where != GRB.Callback.MIP:
            return
        raw_bound = model.cbGet(GRB.Callback.MIP_OBJBND)
        if not math.isfinite(raw_bound):
            return
        bound_added_cb = int(math.floor(raw_bound + 1e-9))
        bound_covered_cb = len(covered_by_fixed) + bound_added_cb
        model._last_bound_added = bound_added_cb
        model._last_bound_covered = bound_covered_cb
        if Fraction(bound_covered_cb, L) + remaining_recip < 1:
            model._bound_stop_triggered = True
            model.terminate()

    model.optimize(stop_when_bound_certifies)
    runtime = time.time() - t0

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INTERRUPTED: "INTERRUPTED",
        GRB.INFEASIBLE: "MODEL_INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }
    status = status_map.get(model.Status, f"GUROBI_STATUS_{model.Status}")
    if getattr(model, "_bound_stop_triggered", False):
        status = "BOUND_CERTIFIED"

    incumbent_added: Optional[int] = None
    incumbent_covered: Optional[int] = None
    incumbent_total_upper: Optional[float] = None

    bound_added: Optional[int] = None
    bound_covered: Optional[int] = None
    certified_total_upper: Optional[float] = None
    if getattr(model, "_bound_stop_triggered", False) and model._last_bound_added is not None:
        bound_added = int(model._last_bound_added)
        bound_covered = int(model._last_bound_covered)
    elif model.Status in {GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.INTERRUPTED, GRB.SUBOPTIMAL}:
        # This is a rigorous integer upper bound on the number of additionally coverable points.
        if math.isfinite(model.ObjBound):
            bound_added = int(math.floor(model.ObjBound + 1e-9))
            bound_covered = len(covered_by_fixed) + bound_added

    remaining_recip_float = frac_float(remaining_recip)

    if incumbent_covered is not None:
        incumbent_total_upper = incumbent_covered / L + remaining_recip_float
    if bound_covered is not None:
        certified_total_upper = bound_covered / L + remaining_recip_float

    certifies = certified_total_upper is not None and certified_total_upper < 1.0
    note = ""
    if certifies:
        note = "selected-prefix coverage upper bound plus remaining reciprocal sum is below 1"
    elif certified_total_upper is not None:
        note = "bound is not below 1"
    else:
        note = "no usable objective bound"

    return PartialCoverBoundResult(
        L=L,
        min_mod=min_mod,
        prefix_count=prefix_count,
        status=status,
        runtime_sec=runtime,
        n_all_moduli=len(all_moduli),
        n_selected_moduli=len(selected_moduli),
        n_remaining_moduli=len(remaining_moduli),
        fixed=fixed,
        base_covered_count=len(covered_by_fixed),
        uncovered_count=len(uncovered),
        n_free_moduli=len(free_moduli),
        n_y_variables=sum(len(v) for v in valid_residues.values()),
        n_x_variables=len(x),
        global_reciprocal_sum=f"{global_recip.numerator}/{global_recip.denominator}",
        global_reciprocal_float=frac_float(global_recip),
        precheck_selected_cover_bound=precheck_selected_bound,
        precheck_remaining_cover_bound=precheck_remaining_bound,
        precheck_total_cover_bound=precheck_total_bound,
        precheck_total_upper=precheck_total_upper,
        precheck_certifies_infeasible=precheck_certifies,
        bound_certify_cover_limit=bound_certify_cover_limit,
        bound_certify_added_limit=bound_certify_added_limit,
        bound_stop_triggered=getattr(model, "_bound_stop_triggered", False),
        n_local_block_constraints=n_local_block_constraints,
        objective_incumbent_added=incumbent_added,
        objective_bound_added=bound_added,
        incumbent_covered=incumbent_covered,
        bound_covered=bound_covered,
        remaining_reciprocal_sum=f"{remaining_recip.numerator}/{remaining_recip.denominator}",
        remaining_reciprocal_float=remaining_recip_float,
        incumbent_total_upper=incumbent_total_upper,
        certified_total_upper=certified_total_upper,
        certifies_infeasible=certifies,
        selected_moduli=selected_moduli,
        remaining_moduli=remaining_moduli,
        note=note,
    )


def print_result(result: PartialCoverBoundResult) -> None:
    fixed_str = ", ".join(f"{r} mod {d}" for d, r in sorted(result.fixed.items()))
    print("\n" + "=" * 80)
    print(f"L={result.L}, prefix_count={result.prefix_count}/{result.n_all_moduli}")
    print(f"selected_moduli={result.selected_moduli}")
    print(f"remaining_moduli={result.remaining_moduli}")
    print(f"fixed=[{fixed_str}]")
    print(
        f"status={result.status}, time={result.runtime_sec:.2f}s, "
        f"y_vars={result.n_y_variables}, x_vars={result.n_x_variables}, "
        f"base_covered={result.base_covered_count}, uncovered={result.uncovered_count}"
    )
    print(
        f"global_density={result.global_reciprocal_sum}~{result.global_reciprocal_float:.6f}, "
        f"precheck_total_bound={result.precheck_total_cover_bound}/{result.L}="
        f"{result.precheck_total_upper:.6f}, "
        f"precheck_certifies={result.precheck_certifies_infeasible}"
    )
    print(
        f"precheck_parts: selected_bound={result.precheck_selected_cover_bound}, "
        f"remaining_bound={result.precheck_remaining_cover_bound}"
    )
    print(
        f"bound_certify_limits: bound_cover<={result.bound_certify_cover_limit}, "
        f"bound_added<={result.bound_certify_added_limit}, "
        f"bound_stop_triggered={result.bound_stop_triggered}"
    )
    print(f"local_block_constraints={result.n_local_block_constraints}")
    if result.incumbent_covered is not None:
        print(
            f"incumbent_cover={result.incumbent_covered}/{result.L}="
            f"{result.incumbent_covered / result.L:.6f}, "
            f"incumbent_total_upper={result.incumbent_total_upper:.6f}"
        )
    if result.bound_covered is not None:
        print(
            f"bound_cover={result.bound_covered}/{result.L}={result.bound_covered / result.L:.6f}, "
            f"remaining_sum={result.remaining_reciprocal_sum}~{result.remaining_reciprocal_float:.6f}, "
            f"certified_total_upper={result.certified_total_upper:.6f}"
        )
    print(f"certifies_infeasible={result.certifies_infeasible}")
    print(f"note={result.note}")


def parse_counts(text: Optional[str]) -> List[int]:
    if not text:
        return []
    out: List[int] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.extend(range(int(lo), int(hi) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--L", type=int, default=8400)
    parser.add_argument("--min-mod", type=int, default=7)
    parser.add_argument("--prefix-count", type=int, default=46)
    parser.add_argument("--scan-prefix-counts", default=None, help="comma/range list, e.g. 15-30,35")
    parser.add_argument("--max-fixed", type=int, default=4)
    parser.add_argument("--time-limit", type=float, default=0.0)
    parser.add_argument("--threads", type=int, default=0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--mip-focus", type=int, default=3)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--precheck-only", action="store_true")
    parser.add_argument("--local-blocks", action="store_true")
    parser.add_argument("--local-qs", default=None, help="comma/range list of q|L for local block constraints")
    parser.add_argument("--json-out", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    counts = parse_counts(args.scan_prefix_counts) or [args.prefix_count]
    results: List[PartialCoverBoundResult] = []
    for count in counts:
        result = solve_partial_cover_bound_gurobi(
            L=args.L,
            min_mod=args.min_mod,
            prefix_count=count,
            max_fixed=args.max_fixed,
            time_limit=args.time_limit,
            threads=args.threads,
            seed=args.seed,
            mip_focus=args.mip_focus,
            output_flag=0 if args.quiet else 1,
            precheck_only=args.precheck_only,
            local_blocks=args.local_blocks,
            local_qs=parse_counts(args.local_qs),
        )
        results.append(result)
        print_result(result)
        if result.certifies_infeasible:
            print(f"\nCERTIFIED at prefix_count={count}; stopping scan.")
            break

    if args.json_out:
        out_path = os.path.abspath(args.json_out)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False)
        print(f"\nJSON written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
