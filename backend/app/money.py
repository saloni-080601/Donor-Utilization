from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Mapping, Sequence, Tuple

RUPEE = Decimal("0.01")
TOLERANCE = Decimal("1.00")
HUNDRED = Decimal("100")


def D(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def q2(value) -> Decimal:
    return D(value).quantize(RUPEE, rounding=ROUND_HALF_UP)


def format_inr(value, with_symbol: bool = True) -> str:
    amount = q2(value)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    whole, frac = f"{amount:.2f}".split(".")
    if len(whole) <= 3:
        grouped = whole
    else:
        last3 = whole[-3:]
        rest = whole[:-3]
        parts = []
        while rest:
            parts.append(rest[-2:])
            rest = rest[:-2]
        grouped = ",".join(reversed(parts) ) + "," + last3
    prefix = "₹" if with_symbol else ""
    return f"{sign}{prefix}{grouped}.{frac}"


def pool_shares(grants: Sequence[Tuple[str, Decimal]]) -> dict[str, Decimal]:
    total = sum((D(amount) for _, amount in grants), Decimal("0"))
    if total == 0:
        raise ValueError("Pool has no approved amount to share")
    return {code: D(amount) / total for code, amount in grants}


def shares_sum_to_one(shares: Mapping[str, Decimal], places: int = 8) -> bool:
    total = sum(shares.values(), Decimal("0"))
    quantum = Decimal("1").scaleb(-places)
    return abs(total - Decimal("1")).quantize(quantum) == 0


def allocate_amount(amount: Decimal, shares: Mapping[str, Decimal]) -> dict[str, Decimal]:
    """Split `amount` by pool shares. Round each line to paise, give leftover to the largest share."""
    amount = q2(amount)
    ordered = sorted(shares.items(), key=lambda item: (-item[1], item[0]))
    allocated: dict[str, Decimal] = {}
    running = Decimal("0")
    for i, (code, share) in enumerate(ordered):
        if i == len(ordered) - 1:
            piece = amount - running
        else:
            piece = q2(amount * share)
            running += piece
        allocated[code] = piece
    return allocated


def ledger_cost(direct: Decimal, campus_alloc: Decimal, central_alloc: Decimal) -> Decimal:
    return q2(direct) + q2(campus_alloc) + q2(central_alloc)


def pace(
    approved: Decimal,
    spend_to_date: Decimal,
    start,
    end,
    as_of,
) -> dict:
    if end is None:
        return {
            "status": "warn",
            "reason": "Grant has no end date",
            "monthly_so_far": None,
            "monthly_needed": None,
            "behind": False,
        }
    total_days = (end - start).days
    elapsed_days = max((as_of - start).days, 0)
    remaining_days = (end - as_of).days
    if total_days <= 0:
        return {
            "status": "error",
            "reason": "Grant end is not after start",
            "monthly_so_far": None,
            "monthly_needed": None,
            "behind": True,
        }
    expected = q2(approved * D(elapsed_days) / D(total_days))
    months_elapsed = max(D(elapsed_days) / D(30), D("0.01"))
    months_remaining = max(D(remaining_days) / D(30), D("0.01"))
    monthly_so_far = q2(spend_to_date / months_elapsed)
    remaining_balance = q2(approved - spend_to_date)
    monthly_needed = q2(remaining_balance / months_remaining) if remaining_days > 0 else remaining_balance
    behind = spend_to_date < expected - TOLERANCE
    return {
        "status": "behind" if behind else "on_track",
        "reason": None,
        "monthly_so_far": monthly_so_far,
        "monthly_needed": monthly_needed,
        "expected_to_date": expected,
        "spend_to_date": q2(spend_to_date),
        "behind": behind,
    }


def group_budget_vs_actual(
    budget_by_head: Mapping[str, Decimal],
    actual_by_head: Mapping[str, Decimal],
) -> list[dict]:
    heads = sorted(set(budget_by_head) | set(actual_by_head))
    rows = []
    for head in heads:
        budget = q2(budget_by_head.get(head, 0))
        actual = q2(actual_by_head.get(head, 0))
        variance = actual - budget
        pct = None if budget == 0 else q2((actual / budget) * HUNDRED)
        rows.append(
            {
                "head": head,
                "budget": budget,
                "actual": actual,
                "variance": variance,
                "pct": pct,
                "overspent": actual > budget + TOLERANCE,
            }
        )
    return rows


def residuals_ok(left: Iterable[Decimal], right: Iterable[Decimal]) -> bool:
    return abs(q2(sum(left, Decimal("0"))) - q2(sum(right, Decimal("0")))) <= TOLERANCE
