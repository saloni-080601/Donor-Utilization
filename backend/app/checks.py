from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from .money import D, TOLERANCE, pool_shares, q2, residuals_ok, shares_sum_to_one


def run_checks(
    period_start: date,
    period_end: date,
    grants: list[dict],
    direct_rows: list[dict],
    central_rows: list[dict],
    allocated: list[dict],
    mappings: dict[str, str],
) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if period_end < period_start:
        blockers.append("Period end date is before the start date.")

    ledgers = {row["ledger"] for row in direct_rows} | {row["ledger"] for row in central_rows}
    unmapped = sorted(ledger for ledger in ledgers if ledger not in mappings)
    if unmapped:
        blockers.append("Unmapped ledgers: " + ", ".join(unmapped))

    totals_by_grant = defaultdict(lambda: Decimal("0.00"))
    mapped_by_grant = defaultdict(lambda: Decimal("0.00"))
    for line in allocated:
        totals_by_grant[line["grant_code"]] += line["total"]
        if line["budget_head"]:
            mapped_by_grant[line["grant_code"]] += line["total"]

    for code, total in totals_by_grant.items():
        mapped = mapped_by_grant.get(code, Decimal("0.00"))
        if abs(q2(mapped) - q2(total)) > TOLERANCE:
            blockers.append(
                f"{code}: mapped actuals {mapped} do not equal grant total {total} (tolerance ₹1)."
            )

    for kind, key in (("campus", "campus_pool"), ("central", "central_pool")):
        pools: dict[str, list[tuple[str, Decimal]]] = defaultdict(list)
        for grant in grants:
            pools[grant[key]].append((grant["code"], D(grant["approved_amount"])))
        used_pools = {row["pool"] for row in central_rows if row["pool_kind"] == kind}
        for pool in used_pools:
            members = pools.get(pool)
            if not members:
                blockers.append(f"{kind.title()} pool {pool} is used in the export but has no grants.")
                continue
            shares = pool_shares(members)
            if not shares_sum_to_one(shares):
                blockers.append(f"{kind.title()} pool {pool} shares do not add up to 100%.")
            pool_in = q2(sum((D(r["amount"]) for r in central_rows if r["pool"] == pool and r["pool_kind"] == kind), Decimal("0")))
            alloc_field = "campus_alloc" if kind == "campus" else "central_alloc"
            pool_out = q2(
                sum(
                    (D(line[alloc_field]) for line in allocated if any(g["code"] == line["grant_code"] and g[key] == pool for g in grants)),
                    Decimal("0"),
                )
            )
            if abs(pool_in - pool_out) > TOLERANCE:
                blockers.append(
                    f"{kind.title()} pool {pool} is not fully shared out ({pool_in} in, {pool_out} allocated)."
                )

    for grant in grants:
        locations = grant.get("locations") or []
        loc_total = q2(sum((D(item["amount"]) for item in locations), Decimal("0")))
        approved = q2(grant["approved_amount"])
        if locations and abs(loc_total - approved) > TOLERANCE:
            blockers.append(
                f"{grant['code']}: location figures {loc_total} do not add up to approved {approved}."
            )

        budget_total = q2(sum((D(b["amount"]) for b in grant.get("budget_lines") or []), Decimal("0")))
        if budget_total and abs(budget_total - approved) > TOLERANCE:
            warnings.append(
                f"{grant['code']}: donor budget {budget_total} does not equal approved grant {approved}."
            )
        if grant.get("end_date") is None:
            warnings.append(f"{grant['code']}: grant has no end date.")

    unknown_grants = sorted({row["grant_code"] for row in direct_rows} - {g["code"] for g in grants})
    if unknown_grants:
        blockers.append("Utilization export has unknown grants: " + ", ".join(unknown_grants))

    if not residuals_ok(
        (D(r["amount"]) for r in direct_rows),
        (D(line["direct"]) for line in allocated),
    ):
        blockers.append("Direct spend in the export does not reconcile to allocated direct lines.")

    return blockers, warnings
