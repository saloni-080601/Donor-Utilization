from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from .money import format_inr, q2


def money(value) -> str:
    return str(q2(value or 0))


def dump_grant(grant, include_children: bool = True) -> dict:
    data = {
        "id": grant.id,
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
        "programme_lead": grant.programme_lead.name if grant.programme_lead else None,
        "programme_lead_id": grant.programme_lead_id,
        "fcra": grant.fcra,
    }
    if include_children:
        data["locations"] = [
            {"location": loc.location, "amount": money(loc.amount), "amount_inr": format_inr(loc.amount)}
            for loc in grant.locations
        ]
        data["budget_lines"] = [
            {
                "id": line.id,
                "head": line.head,
                "line_name": line.line_name,
                "amount": money(line.amount),
                "amount_inr": format_inr(line.amount),
            }
            for line in grant.budget_lines
        ]
    return data


def grant_payload(grant) -> dict:
    return {
        "code": grant.code,
        "approved_amount": grant.approved_amount,
        "campus_pool": grant.campus_pool,
        "central_pool": grant.central_pool,
        "end_date": grant.end_date,
        "locations": [{"amount": loc.amount} for loc in grant.locations],
        "budget_lines": [{"amount": line.amount} for line in grant.budget_lines],
    }


def json_safe(value):
    if isinstance(value, Decimal):
        return str(q2(value))
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    return value
