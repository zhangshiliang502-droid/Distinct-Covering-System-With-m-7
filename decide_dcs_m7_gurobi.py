#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
decide_dcs_m7_gurobi.py

用 Gurobi 判定是否存在 distinct covering system：
    minimum modulus m = 7
    lcm L 可通过 --lcm 指定，默认 L = 7560

默认模型：
    1. 候选模数为所有 d | L 且 d >= 7 的因子；
    2. 每个候选模数恰好用一次。
       这是等价的存在性判定：若某个子集能覆盖，把缺失因子随便加上一个 residue，
       仍然是 distinct covering system，且 lcm 不变；
    3. 默认固定：
           6 mod 7, 7 mod 8, 8 mod 9, 33 mod 35
       以减少变量和覆盖约束。
"""

from __future__ import annotations

import argparse
import math
import sys
from functools import reduce
from typing import Dict, Iterable, List, Tuple

try:
    import gurobipy as gp
    from gurobipy import GRB
except ImportError:
    print(
        "错误：没有找到 gurobipy。请先安装 Gurobi Python 接口并配置 license：\n"
        "    python -m pip install gurobipy",
        file=sys.stderr,
    )
    raise


Progression = Tuple[int, int]  # (a, m) 表示 a mod m


def divisors(n: int) -> List[int]:
    """返回 n 的全部正因子，升序。"""
    small, large = [], []
    r = int(math.isqrt(n))
    for d in range(1, r + 1):
        if n % d == 0:
            small.append(d)
            if d * d != n:
                large.append(n // d)
    return small + large[::-1]


def lcm2(a: int, b: int) -> int:
    return a * b // math.gcd(a, b)


def lcm_list(values: Iterable[int]) -> int:
    return reduce(lcm2, values, 1)


def prime_power_factors(n: int) -> List[int]:
    """返回 L 的最高素数幂因子，例如 7560 -> [8, 27, 5, 7]。"""
    ans = []
    x = n
    d = 2
    while d * d <= x:
        if x % d == 0:
            pp = 1
            while x % d == 0:
                x //= d
                pp *= d
            ans.append(pp)
        d += 1 if d == 2 else 2
    if x > 1:
        ans.append(x)
    return ans


def parse_preset(s: str) -> Progression:
    """解析 'a:m' 或 'a,m'。"""
    sep = ":" if ":" in s else ","
    a_str, m_str = s.split(sep, 1)
    m = int(m_str)
    return int(a_str) % m, m


def normalize_presets(presets: Iterable[Progression]) -> List[Progression]:
    out = []
    seen = set()
    for a, m in presets:
        if m <= 0:
            raise ValueError(f"非法模数：{m}")
        if m in seen:
            raise ValueError(f"同一个模数 {m} 被 preset 了两次")
        seen.add(m)
        out.append((a % m, m))
    return out


def default_presets(use_35: bool = True) -> List[Progression]:
    # 7, 8, 9 两两互素；平移 + CRT 可把它们固定为下面三个 residue。
    presets = [(6, 7), (7, 8), (8, 9)]

    # 更强归一化：固定 33 mod 35。
    # 若想只用最保守归一化，运行 --safe。
    if use_35:
        presets.append((33, 35))

    return presets


def covered_by_presets(b: int, presets: List[Progression]) -> bool:
    return any(b % m == a for a, m in presets)


def verify_system(system: List[Progression], L: int, min_modulus: int) -> bool:
    """独立校验：distinct、min modulus、lcm，以及覆盖 Z/LZ。"""
    mods = [m for _, m in system]

    if len(mods) != len(set(mods)):
        print("校验失败：模数不是 distinct。")
        return False

    if min(mods) != min_modulus:
        print(f"校验失败：最小模数是 {min(mods)}，不是 {min_modulus}。")
        return False

    actual_lcm = lcm_list(mods)
    if actual_lcm != L:
        print(f"校验失败：lcm 是 {actual_lcm}，不是 {L}。")
        return False

    uncovered = [
        b for b in range(L)
        if not any(b % m == (a % m) for a, m in system)
    ]
    if uncovered:
        print(f"校验失败：还有 {len(uncovered)} 个 residue 未覆盖；前几个：{uncovered[:20]}")
        return False

    return True


def build_model(
    min_modulus: int,
    L: int,
    presets: List[Progression],
    force_all_divisors: bool,
    heuristics: float,
    mip_focus: int,
    presolve: int,
    cuts: int,
    symmetry: int,
    threads: int,
    time_limit: float | None,
):
    if L <= 0:
        raise ValueError("L 必须为正整数")
    if min_modulus <= 1:
        raise ValueError("min_modulus 必须大于 1")
    if L % min_modulus != 0:
        raise ValueError(f"{min_modulus} 必须整除 L={L}")

    presets = normalize_presets(presets)
    preset_moduli = {m for _, m in presets}

    all_moduli = [d for d in divisors(L) if d >= min_modulus]
    bad_presets = [(a, m) for a, m in presets if m not in all_moduli]
    if bad_presets:
        raise ValueError(f"这些 preset 的模数不是 L 的 >= min_modulus 因子：{bad_presets}")

    remaining_moduli = [m for m in all_moduli if m not in preset_moduli]
    points_to_cover = [b for b in range(L) if not covered_by_presets(b, presets)]

    model = gp.Model(f"DCS_min{min_modulus}_L{L}")
    model.setObjective(0.0, GRB.MINIMIZE)

    # 变量 x[m,r]：是否选 r mod m。
    # 若 m 是某 preset 模数 m0 的倍数，且 r ≡ a0 mod m0，
    # 则 r mod m 完全包含在已固定的 a0 mod m0 中，冗余，可删掉。
    keys: List[Tuple[int, int]] = []
    skipped_contained = 0

    for m in remaining_moduli:
        for r in range(m):
            contained = False
            for a0, m0 in presets:
                if m % m0 == 0 and r % m0 == a0:
                    contained = True
                    break
            if contained:
                skipped_contained += 1
                continue
            keys.append((m, r))

    x = model.addVars(keys, vtype=GRB.BINARY, name="x")

    vars_by_mod: Dict[int, List] = {}
    select_expr_by_mod: Dict[int, object] = {}

    for m in remaining_moduli:
        vars_by_mod[m] = [x[m, r] for r in range(m) if (m, r) in x]
        select_expr_by_mod[m] = gp.quicksum(vars_by_mod[m])

    # distinct：每个模数最多一次。
    # 默认 force_all_divisors=True：每个 d|L, d>=m 的模数恰好一次。
    for m in remaining_moduli:
        if not vars_by_mod[m]:
            if force_all_divisors:
                model.addConstr(0 == 1, name=f"no_allowed_residue[{m}]")
            continue

        if force_all_divisors:
            model.addConstr(select_expr_by_mod[m] == 1, name=f"use_exactly_one[{m}]")
        else:
            model.addConstr(select_expr_by_mod[m] <= 1, name=f"use_at_most_one[{m}]")

    # 可选：原始子集模型。一般比 force_all 慢，但逻辑更接近“至多一次”。
    if not force_all_divisors:
        if min_modulus not in preset_moduli:
            model.addConstr(select_expr_by_mod[min_modulus] == 1, name="force_min_modulus")

        # 保证 lcm 精确为 L：每个最高素数幂都至少被某个选中模数包含。
        for pp in prime_power_factors(L):
            if any(m % pp == 0 for _, m in presets):
                continue
            candidates = [
                select_expr_by_mod[m]
                for m in remaining_moduli
                if m % pp == 0 and vars_by_mod[m]
            ]
            model.addConstr(gp.quicksum(candidates) >= 1, name=f"force_lcm_ppow[{pp}]")

    # 覆盖约束：对每个未被 preset 覆盖的 b in Z/LZ，
    # 至少一个选中同余类覆盖 b。
    empty_cover_rows = []
    for b in points_to_cover:
        cover_vars = []
        for m in remaining_moduli:
            v = x.get((m, b % m))
            if v is not None:
                cover_vars.append(v)

        if cover_vars:
            model.addConstr(gp.quicksum(cover_vars) >= 1, name=f"cover[{b}]")
        else:
            empty_cover_rows.append(b)
            model.addConstr(0 == 1, name=f"uncoverable[{b}]")

    # 分支优先级：小模数覆盖密度大，通常优先分支更好。
    for (m, r), var in x.items():
        var.BranchPriority = max(1, int(100000 // m))

    # 求不可行时，关掉启发式通常更快；MIPFocus=3 偏向证明。
    model.Params.Heuristics = heuristics
    model.Params.MIPFocus = mip_focus
    model.Params.Presolve = presolve
    model.Params.Cuts = cuts
    model.Params.Symmetry = symmetry
    model.Params.Threads = threads

    if time_limit is not None and time_limit > 0:
        model.Params.TimeLimit = time_limit

    metadata = {
        "L": L,
        "min_modulus": min_modulus,
        "all_moduli": all_moduli,
        "remaining_moduli": remaining_moduli,
        "presets": presets,
        "points_to_cover": points_to_cover,
        "num_binary_vars": len(keys),
        "num_mod_constraints": len(remaining_moduli),
        "num_cover_constraints": len(points_to_cover),
        "skipped_contained_vars": skipped_contained,
        "empty_cover_rows": empty_cover_rows,
        "force_all_divisors": force_all_divisors,
    }

    return model, x, metadata


def extract_solution(x, presets: List[Progression]) -> List[Progression]:
    system = list(presets)
    for (m, r), var in x.items():
        if var.X > 0.5:
            system.append((r % m, m))
    system.sort(key=lambda am: (am[1], am[0]))
    return system


def main() -> int:
    parser = argparse.ArgumentParser(
        description="用 Gurobi 判定是否存在 m=7、指定 L 的 distinct covering system。"
    )

    parser.add_argument("--min-modulus", type=int, default=7)
    parser.add_argument("--lcm", type=int, default=7560)

    parser.add_argument(
        "--safe",
        action="store_true",
        help="只使用 6 mod 7, 7 mod 8, 8 mod 9；不固定 33 mod 35。",
    )
    parser.add_argument(
        "--no-default-presets",
        action="store_true",
        help="不使用默认 preset。一般不建议。",
    )
    parser.add_argument(
        "--add-preset",
        action="append",
        default=[],
        help="额外固定一个同余类，格式 a:m，例如 --add-preset 33:35。可重复。",
    )

    parser.add_argument(
        "--allow-subset",
        action="store_true",
        help="使用原始子集模型：每个模数至多一次；默认使用等价但更快的所有因子恰好一次模型。",
    )

    parser.add_argument("--time-limit", type=float, default=None)
    parser.add_argument("--threads", type=int, default=0)
    parser.add_argument("--heuristics", type=float, default=0.0)
    parser.add_argument("--mip-focus", type=int, default=3)
    parser.add_argument("--presolve", type=int, default=2)
    parser.add_argument("--cuts", type=int, default=2)
    parser.add_argument("--symmetry", type=int, default=2)

    parser.add_argument(
        "--log-file",
        default=None,
        help="可选：把 Gurobi 日志写入文件，例如 m7_L7560.log。",
    )

    parser.add_argument(
        "--write-model",
        default=None,
        help="可选：写出模型文件，例如 model.mps 或 model.lp。",
    )
    parser.add_argument(
        "--write-solution",
        default=None,
        help="可选：若找到解，将覆盖系统写入文本文件。",
    )
    parser.add_argument(
        "--iis",
        action="store_true",
        help="若不可行，计算 IIS 并写出 iis.ilp；可能很慢。",
    )

    args = parser.parse_args()

    presets: List[Progression] = []
    if not args.no_default_presets:
        presets.extend(default_presets(use_35=not args.safe))
    presets.extend(parse_preset(s) for s in args.add_preset)
    presets = normalize_presets(presets)

    model, x, meta = build_model(
        min_modulus=args.min_modulus,
        L=args.lcm,
        presets=presets,
        force_all_divisors=not args.allow_subset,
        heuristics=args.heuristics,
        mip_focus=args.mip_focus,
        presolve=args.presolve,
        cuts=args.cuts,
        symmetry=args.symmetry,
        threads=args.threads,
        time_limit=args.time_limit,
    )

    if args.log_file:
        model.Params.LogFile = args.log_file
        print(f"Gurobi 日志将写入：{args.log_file}")

    print("========== 模型信息 ==========")
    print(f"L = {meta['L']}, min_modulus = {meta['min_modulus']}")
    print(f"全部候选模数个数 = {len(meta['all_moduli'])}")
    print(f"preset = {meta['presets']}")
    print(f"剩余待选模数个数 = {len(meta['remaining_moduli'])}")
    print(f"二元变量个数 = {meta['num_binary_vars']}")
    print(f"需覆盖 residue 个数 = {meta['num_cover_constraints']}")
    print(f"删掉的冗余变量个数 = {meta['skipped_contained_vars']}")
    print(
        "模型模式 = "
        + ("所有 >=m 的 L 因子恰好一次" if meta["force_all_divisors"] else "子集模型")
    )
    print("候选模数：")
    print(meta["all_moduli"])
    print("==============================")

    if args.write_model:
        model.write(args.write_model)
        print(f"已写出模型：{args.write_model}")

    model.optimize()

    status = model.Status
    status_name = {
        GRB.OPTIMAL: "OPTIMAL / FEASIBLE",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INTERRUPTED: "INTERRUPTED",
    }.get(status, str(status))

    print(f"\nGurobi status = {status_name}")

    if model.SolCount > 0:
        system = extract_solution(x, presets)
        ok = verify_system(system, args.lcm, args.min_modulus)

        print(f"\n找到 covering system；独立校验 = {ok}")
        print("系统如下：")
        for a, m in system:
            print(f"{a} mod {m}")

        if args.write_solution:
            with open(args.write_solution, "w", encoding="utf-8") as f:
                for a, m in system:
                    f.write(f"{a} mod {m}\n")
            print(f"已写出解：{args.write_solution}")

        return 0

    if status == GRB.INFEASIBLE:
        print(
            "\n结论：Gurobi 证明模型不可行；因此不存在 "
            f"minimum modulus = {args.min_modulus}, L = {args.lcm} "
            "的 distinct covering system。"
        )

        if args.iis:
            print("开始计算 IIS...")
            model.computeIIS()
            model.write("iis.ilp")
            print("已写出 IIS: iis.ilp")

        return 0

    print("\n没有得到最终结论。若是 TIME_LIMIT，请增大时间限制或继续求解写出的 MPS/LP 模型。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
