from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from . import models
from .checks import run_checks
from .engine import compute_allocations
from .money import D, format_inr, group_budget_vs_actual, pace, q2, TOLERANCE
from .serialize import grant_payload, json_safe, money


def audit(db: Session, actor: str, action: str, entity: str, detail: dict | None = None):
    db.add(models.AuditLog(actor=actor, action=action, entity=entity, detail=detail or {}))


def mapping_dict(db: Session) -> dict[str, str]:
    return {m.ledger_name: m.budget_head for m in db.query(models.LedgerMapping).all()}


def grant_dicts(db: Session) -> list[dict]:
    return [grant_payload(g) for g in db.query(models.Grant).all()]


def persist_allocation(db: Session, run: models.ImportRun, allocated: list[dict]):
    db.query(models.AllocatedLine).filter(models.AllocatedLine.run_id == run.id).delete()
    for line in allocated:
        db.add(
            models.AllocatedLine(
                run_id=run.id,
                grant_code=line["grant_code"],
                ledger=line["ledger"],
                budget_head=line["budget_head"],
                direct=line["direct"],
                campus_alloc=line["campus_alloc"],
                central_alloc=line["central_alloc"],
                total=line["total"],
            )
        )


def recompute_run(db: Session, run: models.ImportRun) -> models.ImportRun:
    grants = grant_dicts(db)
    mappings = mapping_dict(db)
    direct_rows = [
        {"grant_code": r.grant_code, "ledger": r.ledger, "amount": r.amount} for r in run.utilization_rows
    ]
    central_rows = [
        {"ledger": r.ledger, "pool": r.pool, "pool_kind": r.pool_kind, "amount": r.amount} for r in run.central_rows
    ]
    allocated = compute_allocations(grants, direct_rows, central_rows, mappings)
    persist_allocation(db, run, allocated)
    full_grants = []
    for grant in db.query(models.Grant).all():
        payload = grant_payload(grant)
        payload["locations"] = [{"amount": loc.amount} for loc in grant.locations]
        payload["budget_lines"] = [{"amount": line.amount} for line in grant.budget_lines]
        full_grants.append(payload)
    blockers, warnings = run_checks(
        run.period_start,
        run.period_end,
        full_grants,
        direct_rows,
        central_rows,
        allocated,
        mappings,
    )
    run.blockers = blockers
    run.warnings = warnings
    if run.status != "published":
        run.status = "blocked" if blockers else "draft"
    return run


def latest_run(db: Session, published_only: bool = False) -> models.ImportRun | None:
    q = db.query(models.ImportRun).order_by(models.ImportRun.id.desc())
    if published_only:
        q = q.filter(models.ImportRun.status == "published")
    return q.first()


def statement_for(db: Session, run: models.ImportRun, grant: models.Grant) -> list[dict]:
    budget_by_head = defaultdict(lambda: Decimal("0.00"))
    for line in grant.budget_lines:
        budget_by_head[line.head] += D(line.amount)
    actual_by_head = defaultdict(lambda: Decimal("0.00"))
    rows = []
    for line in run.allocated_lines:
        if line.grant_code != grant.code:
            continue
        if line.budget_head:
            actual_by_head[line.budget_head] += D(line.total)
        head_budget = budget_by_head.get(line.budget_head or "", Decimal("0"))
        rows.append(
            {
                "ledger": line.ledger,
                "budget_head": line.budget_head,
                "direct": money(line.direct),
                "campus_alloc": money(line.campus_alloc),
                "central_alloc": money(line.central_alloc),
                "total": money(line.total),
                "direct_inr": format_inr(line.direct),
                "campus_inr": format_inr(line.campus_alloc),
                "central_inr": format_inr(line.central_alloc),
                "total_inr": format_inr(line.total),
                "overspent": bool(line.budget_head) and D(line.total) > head_budget + TOLERANCE,
            }
        )
    return rows


def bva_for(grant: models.Grant, statement: list[dict]) -> list[dict]:
    budget_by_head = defaultdict(lambda: Decimal("0.00"))
    for line in grant.budget_lines:
        budget_by_head[line.head] += D(line.amount)
    actual_by_head = defaultdict(lambda: Decimal("0.00"))
    for row in statement:
        if row["budget_head"]:
            actual_by_head[row["budget_head"]] += D(row["total"])
    result = []
    for item in group_budget_vs_actual(budget_by_head, actual_by_head):
        result.append(
            {
                **json_safe(item),
                "budget_inr": format_inr(item["budget"]),
                "actual_inr": format_inr(item["actual"]),
                "variance_inr": format_inr(item["variance"]),
            }
        )
    return result


def grant_total(statement: list[dict]) -> Decimal:
    return q2(sum((D(r["total"]) for r in statement), Decimal("0")))


def grant_report(db: Session, grant: models.Grant, run: models.ImportRun) -> dict:
    statement = statement_for(db, run, grant)
    spend = grant_total(statement)
    as_of = run.period_end
    pace_info = pace(D(grant.approved_amount), spend, grant.start_date, grant.end_date, as_of)
    campus_share = None
    central_share = None
    grants = grant_dicts(db)
    from .engine import build_pool_membership
    from .money import pool_shares

    campus = build_pool_membership(grants, "campus")
    central = build_pool_membership(grants, "central")
    campus_share = pool_shares(campus[grant.campus_pool]).get(grant.code)
    central_share = pool_shares(central[grant.central_pool]).get(grant.code)
    return {
        "grant": {
            "code": grant.code,
            "name": grant.name,
            "donor_name": grant.donor_name,
            "uc_format": grant.uc_format,
            "approved_amount": money(grant.approved_amount),
            "approved_amount_inr": format_inr(grant.approved_amount),
            "start_date": grant.start_date.isoformat(),
            "end_date": grant.end_date.isoformat() if grant.end_date else None,
            "campus_pool": grant.campus_pool,
            "central_pool": grant.central_pool,
            "primary_location": grant.primary_location,
        },
        "run": {
            "id": run.id,
            "status": run.status,
            "start": run.period_start.isoformat(),
            "end": run.period_end.isoformat(),
            "blockers": run.blockers,
            "warnings": run.warnings,
        },
        "pool_share": {
            "campus": str(campus_share) if campus_share is not None else None,
            "central": str(central_share) if central_share is not None else None,
        },
        "spend_to_date": money(spend),
        "spend_to_date_inr": format_inr(spend),
        "balance": money(D(grant.approved_amount) - spend),
        "balance_inr": format_inr(D(grant.approved_amount) - spend),
        "pace": json_safe(pace_info),
        "statement": statement,
        "budget_vs_actual": bva_for(grant, statement),
    }


def summary_payload(db: Session, user_codes: set[str] | None) -> dict:
    run = latest_run(db)
    grants = db.query(models.Grant).all()
    if user_codes is not None:
        grants = [g for g in grants if g.code in user_codes]
    rows = []
    exceptions = []
    if run:
        for grant in grants:
            report = grant_report(db, grant, run)
            overspent = [r for r in report["budget_vs_actual"] if r["overspent"]]
            rows.append(
                {
                    "code": grant.code,
                    "name": grant.name,
                    "donor_name": grant.donor_name,
                    "approved_inr": format_inr(grant.approved_amount),
                    "spend_inr": report["spend_to_date_inr"],
                    "balance_inr": report["balance_inr"],
                    "pace": report["pace"]["status"],
                    "behind": report["pace"]["behind"],
                    "overspent_heads": len(overspent),
                }
            )
            if report["pace"]["behind"]:
                exceptions.append({"grant": grant.code, "kind": "pace", "message": "Spend is behind linear pace to fully use the grant by the end date."})
            for head in overspent:
                exceptions.append({"grant": grant.code, "kind": "overspend", "message": f"{head['head']} is overspent by {head['variance_inr']}."})
        for blocker in run.blockers or []:
            exceptions.append({"grant": None, "kind": "block", "message": blocker})
        for warning in run.warnings or []:
            exceptions.append({"grant": None, "kind": "warn", "message": warning})
    unmapped_count = 0
    if run:
        mappings = mapping_dict(db)
        ledgers = {r.ledger for r in run.utilization_rows} | {r.ledger for r in run.central_rows}
        unmapped_count = len([l for l in ledgers if l not in mappings])
    return {
        "run": None
        if not run
        else {
            "id": run.id,
            "status": run.status,
            "period_start": run.period_start.isoformat(),
            "period_end": run.period_end.isoformat(),
            "blockers": run.blockers,
            "warnings": run.warnings,
        },
        "grants": rows,
        "exceptions": exceptions,
        "unmapped_ledgers": unmapped_count,
        "grant_count": len(grants),
        "as_of": date.today().isoformat(),
    }
