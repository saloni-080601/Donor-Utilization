from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from .money import D, allocate_amount, ledger_cost, pool_shares, q2


def build_pool_membership(grants: Iterable[dict], kind: str) -> dict[str, list[tuple[str, Decimal]]]:
    pools: dict[str, list[tuple[str, Decimal]]] = defaultdict(list)
    key = "campus_pool" if kind == "campus" else "central_pool"
    for grant in grants:
        pools[grant[key]].append((grant["code"], D(grant["approved_amount"])))
    return pools


def compute_allocations(
    grants: list[dict],
    direct_rows: list[dict],
    central_rows: list[dict],
    mappings: dict[str, str],
) -> list[dict]:
    campus_pools = build_pool_membership(grants, "campus")
    central_pools = build_pool_membership(grants, "central")
    campus_shares = {name: pool_shares(members) for name, members in campus_pools.items()}
    central_shares = {name: pool_shares(members) for name, members in central_pools.items()}

    grant_by_code = {g["code"]: g for g in grants}
    lines: dict[tuple[str, str], dict] = {}

    def bucket(grant_code: str, ledger: str) -> dict:
        key = (grant_code, ledger)
        if key not in lines:
            lines[key] = {
                "grant_code": grant_code,
                "ledger": ledger,
                "budget_head": mappings.get(ledger),
                "direct": Decimal("0.00"),
                "campus_alloc": Decimal("0.00"),
                "central_alloc": Decimal("0.00"),
                "total": Decimal("0.00"),
            }
        return lines[key]

    for row in direct_rows:
        code = row["grant_code"]
        if code not in grant_by_code:
            continue
        item = bucket(code, row["ledger"])
        item["direct"] += q2(row["amount"])

    campus_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    central_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

    for row in central_rows:
        amount = q2(row["amount"])
        pool = row["pool"]
        if row["pool_kind"] == "campus":
            campus_totals[pool] += amount
            shares = campus_shares.get(pool, {})
            split = allocate_amount(amount, shares) if shares else {}
            for code, piece in split.items():
                bucket(code, row["ledger"])["campus_alloc"] += piece
        else:
            central_totals[pool] += amount
            shares = central_shares.get(pool, {})
            split = allocate_amount(amount, shares) if shares else {}
            for code, piece in split.items():
                bucket(code, row["ledger"])["central_alloc"] += piece

    result = []
    for item in lines.values():
        item["direct"] = q2(item["direct"])
        item["campus_alloc"] = q2(item["campus_alloc"])
        item["central_alloc"] = q2(item["central_alloc"])
        item["total"] = ledger_cost(item["direct"], item["campus_alloc"], item["central_alloc"])
        result.append(item)
    result.sort(key=lambda r: (r["grant_code"], r["ledger"]))
    return result
