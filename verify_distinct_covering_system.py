#!/usr/bin/env python3
"""Verify whether residue classes form a distinct covering system.

A system is a distinct covering system if:

1. every modulus is greater than 1;
2. all moduli are distinct;
3. every integer is covered by at least one residue class.

Coverage is periodic with period equal to the lcm of the moduli, so it is
enough to check all residues in Z / lcm(moduli) Z.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from functools import reduce
from typing import Iterable, List, Sequence, Tuple


Progression = Tuple[int, int]  # (residue, modulus)


def lcm2(a: int, b: int) -> int:
    return a * b // math.gcd(a, b)


def lcm_list(values: Iterable[int]) -> int:
    return reduce(lcm2, values, 1)


def normalize_system(system: Iterable[Progression]) -> List[Progression]:
    normalized: List[Progression] = []
    for residue, modulus in system:
        if modulus <= 1:
            raise ValueError(f"modulus must be greater than 1, got {modulus}")
        normalized.append((residue % modulus, modulus))
    return normalized


def parse_progression(text: str) -> Progression:
    """Parse one residue class.

    Accepted examples:
      - "7 mod 12"
      - "7:12"
      - "7,12"
      - "(7, 12)"
    """
    values = re.findall(r"[+-]?\d+", text)
    if len(values) != 2:
        raise ValueError(f"expected exactly two integers in {text!r}")
    residue, modulus = int(values[0]), int(values[1])
    return residue, modulus


def load_system(path: str | None, items: Sequence[str]) -> List[Progression]:
    raw: List[Progression] = []

    if path:
        with open(path, "r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                try:
                    raw.append(parse_progression(line))
                except ValueError as exc:
                    raise ValueError(f"{path}:{line_no}: {exc}") from exc

    for item in items:
        raw.append(parse_progression(item))

    if not raw:
        raise ValueError("no residue classes were supplied")

    return normalize_system(raw)


@dataclass
class CheckResult:
    ok: bool
    n_classes: int
    min_modulus: int | None
    lcm: int | None
    covered_count: int
    uncovered_count: int
    first_uncovered: List[int]
    errors: List[str]


def check_distinct_covering_system(
    system: Sequence[Progression],
    *,
    expected_min_modulus: int | None = None,
    expected_lcm: int | None = None,
    max_lcm: int = 10_000_000,
    show_uncovered_limit: int = 20,
) -> CheckResult:
    errors: List[str] = []

    try:
        normalized = normalize_system(system)
    except ValueError as exc:
        return CheckResult(False, len(system), None, None, 0, 0, [], [str(exc)])

    moduli = [modulus for _, modulus in normalized]
    if len(moduli) != len(set(moduli)):
        repeated = sorted({m for m in moduli if moduli.count(m) > 1})
        errors.append(f"moduli are not distinct; repeated moduli: {repeated}")

    min_modulus = min(moduli)
    if expected_min_modulus is not None and min_modulus != expected_min_modulus:
        errors.append(
            f"minimum modulus is {min_modulus}, expected {expected_min_modulus}"
        )

    period = lcm_list(moduli)
    if expected_lcm is not None and period != expected_lcm:
        errors.append(f"lcm is {period}, expected {expected_lcm}")

    if period > max_lcm:
        errors.append(
            f"lcm {period} exceeds --max-lcm {max_lcm}; "
            "increase --max-lcm if this exact check is intended"
        )
        return CheckResult(
            False,
            len(normalized),
            min_modulus,
            period,
            0,
            period,
            [],
            errors,
        )

    covered = bytearray(period)
    for residue, modulus in normalized:
        for point in range(residue, period, modulus):
            covered[point] = 1

    covered_count = sum(covered)
    first_uncovered = [
        idx for idx, value in enumerate(covered) if not value
    ][:show_uncovered_limit]
    uncovered_count = period - covered_count
    if uncovered_count:
        errors.append(f"{uncovered_count} residues modulo {period} are uncovered")

    return CheckResult(
        ok=not errors,
        n_classes=len(normalized),
        min_modulus=min_modulus,
        lcm=period,
        covered_count=covered_count,
        uncovered_count=uncovered_count,
        first_uncovered=first_uncovered,
        errors=errors,
    )


def run_self_tests() -> None:
    valid = [(0, 2), (0, 3), (1, 4), (5, 6), (7, 12)]
    result = check_distinct_covering_system(valid, expected_min_modulus=2, expected_lcm=12)
    assert result.ok, result

    repeated_modulus = [(0, 2), (1, 2)]
    result = check_distinct_covering_system(repeated_modulus)
    assert not result.ok and any("not distinct" in error for error in result.errors), result

    not_covering = [(0, 2), (0, 3), (1, 4), (5, 6)]
    result = check_distinct_covering_system(not_covering)
    assert not result.ok and result.first_uncovered == [7], result

    result = check_distinct_covering_system(valid, expected_min_modulus=7)
    assert not result.ok and any("minimum modulus" in error for error in result.errors), result

    result = check_distinct_covering_system(valid, expected_lcm=24)
    assert not result.ok and any("lcm" in error for error in result.errors), result

    parsed = [parse_progression(text) for text in ["0 mod 2", "0:3", "1,4", "(5, 6)"]]
    assert parsed == [(0, 2), (0, 3), (1, 4), (5, 6)], parsed


def print_human(result: CheckResult) -> None:
    print(f"classes: {result.n_classes}")
    print(f"minimum modulus: {result.min_modulus}")
    print(f"lcm: {result.lcm}")
    print(f"covered residues: {result.covered_count}")
    print(f"uncovered residues: {result.uncovered_count}")
    if result.first_uncovered:
        print(f"first uncovered residues: {result.first_uncovered}")
    if result.errors:
        print("errors:")
        for error in result.errors:
            print(f"  - {error}")
    print("VERDICT:", "distinct covering system" if result.ok else "not a distinct covering system")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check whether residue classes form a distinct covering system."
    )
    parser.add_argument(
        "classes",
        nargs="*",
        help='residue classes such as "7 mod 12", "7:12", or "7,12"',
    )
    parser.add_argument("--file", help="text file with one residue class per line")
    parser.add_argument("--min-modulus", type=int, help="require this minimum modulus")
    parser.add_argument("--lcm", type=int, help="require this exact lcm")
    parser.add_argument(
        "--max-lcm",
        type=int,
        default=10_000_000,
        help="safety limit for exact residue checking",
    )
    parser.add_argument(
        "--show-uncovered-limit",
        type=int,
        default=20,
        help="number of uncovered residues to print",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--self-test", action="store_true", help="run built-in tests and exit")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.self_test:
        run_self_tests()
        print("self-test passed")
        return 0

    try:
        system = load_system(args.file, args.classes)
        result = check_distinct_covering_system(
            system,
            expected_min_modulus=args.min_modulus,
            expected_lcm=args.lcm,
            max_lcm=args.max_lcm,
            show_uncovered_limit=args.show_uncovered_limit,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
    else:
        print_human(result)

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
