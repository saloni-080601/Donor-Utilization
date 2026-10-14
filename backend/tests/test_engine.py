from datetime import date
from decimal import Decimal

from app.checks import run_checks
from app.engine import compute_allocations
from app.money import format_inr, pool_shares, q2


def sample_grants():
    return [
        {
            "code": "EDU-PILOT",
            "approved_amount": Decimal("10000000.00"),
            "campus_pool": "CAMPUS-DEL",
            "central_pool": "CENTRAL",
            "end_date": date(2026, 3, 31),
            "locations": [{"amount": Decimal("10000000.00")}],
            "budget_lines": [{"amount": Decimal("10000000.00")}],
        },
        {
            "code": "HLT-002",
            "approved_amount": Decimal("5000000.00"),
            "campus_pool": "CAMPUS-DEL",
            "central_pool": "CENTRAL",
            "end_date": date(2026, 3, 31),
            "locations": [{"amount": Decimal("5000000.00")}],
            "budget_lines": [{"amount": Decimal("5000000.00")}],
        },
        {
            "code": "LIV-003",
            "approved_amount": Decimal("5000000.00"),
            "campus_pool": "CAMPUS-MUM",
            "central_pool": "CENTRAL",
            "end_date": date(2027, 3, 31),
            "locations": [{"amount": Decimal("5000000.00")}],
            "budget_lines": [{"amount": Decimal("5000000.00")}],
        },
    ]


def sample_direct():
    return [
        {"grant_code": "EDU-PILOT", "ledger": "Teaching Staff", "amount": Decimal("1200000.00")},
        {"grant_code": "EDU-PILOT", "ledger": "Classroom Materials", "amount": Decimal("300000.00")},
        {"grant_code": "EDU-PILOT", "ledger": "Travel", "amount": Decimal("80000.00")},
        {"grant_code": "HLT-002", "ledger": "Clinic Staff", "amount": Decimal("400000.00")},
        {"grant_code": "HLT-002", "ledger": "Medicines", "amount": Decimal("120000.00")},
        {"grant_code": "LIV-003", "ledger": "Training Costs", "amount": Decimal("250000.00")},
        {"grant_code": "LIV-003", "ledger": "Stipends", "amount": Decimal("100000.00")},
    ]


def sample_central():
    return [
        {"ledger": "Facilities", "pool": "CAMPUS-DEL", "pool_kind": "campus", "amount": Decimal("150000.00")},
        {"ledger": "Security", "pool": "CAMPUS-DEL", "pool_kind": "campus", "amount": Decimal("30000.00")},
        {"ledger": "Facilities", "pool": "CAMPUS-MUM", "pool_kind": "campus", "amount": Decimal("60000.00")},
        {"ledger": "Admin Support", "pool": "CENTRAL", "pool_kind": "central", "amount": Decimal("200000.00")},
        {"ledger": "Finance Cell", "pool": "CENTRAL", "pool_kind": "central", "amount": Decimal("40000.00")},
    ]


MAPPINGS = {
    "Teaching Staff": "Personnel",
    "Classroom Materials": "Program Costs",
    "Travel": "Travel",
    "Clinic Staff": "Personnel",
    "Medicines": "Program Costs",
    "Training Costs": "Program Costs",
    "Stipends": "Personnel",
    "Facilities": "Admin / Occupancy",
    "Security": "Admin / Occupancy",
    "Admin Support": "Admin",
    "Finance Cell": "Admin",
}


def test_indian_grouping():
    assert format_inr(Decimal("10828000")) == "₹1,08,28,000.00"
    assert format_inr(Decimal("10000000")) == "₹1,00,00,000.00"


def test_campus_and_central_shares():
    grants = sample_grants()
    campus = [(g["code"], g["approved_amount"]) for g in grants if g["campus_pool"] == "CAMPUS-DEL"]
    shares = pool_shares(campus)
    assert shares["EDU-PILOT"] == Decimal("10000000") / Decimal("15000000")
    assert shares["HLT-002"] == Decimal("5000000") / Decimal("15000000")


def test_pilot_grant_totals_to_the_rupee():
    allocated = compute_allocations(sample_grants(), sample_direct(), sample_central(), MAPPINGS)
    edu = [r for r in allocated if r["grant_code"] == "EDU-PILOT"]
    total = q2(sum(r["total"] for r in edu))
    # Direct 15,80,000 + campus 1,20,000 + central 1,20,000
    assert total == Decimal("1820000.00")
    campus = q2(sum(r["campus_alloc"] for r in edu))
    central = q2(sum(r["central_alloc"] for r in edu))
    assert campus == Decimal("120000.00")
    assert central == Decimal("120000.00")


def test_pool_fully_shared():
    allocated = compute_allocations(sample_grants(), sample_direct(), sample_central(), MAPPINGS)
    campus_out = q2(sum(r["campus_alloc"] for r in allocated))
    central_out = q2(sum(r["central_alloc"] for r in allocated))
    assert campus_out == Decimal("240000.00")
    assert central_out == Decimal("240000.00")


def test_publish_checks_pass_on_sample():
    allocated = compute_allocations(sample_grants(), sample_direct(), sample_central(), MAPPINGS)
    blockers, warnings = run_checks(
        date(2025, 4, 1),
        date(2025, 9, 30),
        sample_grants(),
        sample_direct(),
        sample_central(),
        allocated,
        MAPPINGS,
    )
    assert blockers == []
    assert warnings == []


def test_unmapped_ledger_blocks():
    allocated = compute_allocations(sample_grants(), sample_direct(), sample_central(), {})
    blockers, _ = run_checks(
        date(2025, 4, 1),
        date(2025, 9, 30),
        sample_grants(),
        sample_direct(),
        sample_central(),
        allocated,
        {},
    )
    assert any("Unmapped" in b for b in blockers)


def test_bad_period_blocks():
    allocated = compute_allocations(sample_grants(), sample_direct(), sample_central(), MAPPINGS)
    blockers, _ = run_checks(
        date(2025, 9, 30),
        date(2025, 4, 1),
        sample_grants(),
        sample_direct(),
        sample_central(),
        allocated,
        MAPPINGS,
    )
    assert any("end date is before" in b.lower() for b in blockers)
