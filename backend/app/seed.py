from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from .auth import hash_password
from . import models
from .services import audit, recompute_run


def seed_if_empty(db: Session) -> None:
    if db.query(models.User).first():
        return

    finance = models.User(
        email="finance@org.local",
        name="Meera Iyer",
        role="finance",
        password_hash=hash_password("finance123"),
    )
    lead = models.User(
        email="lead@org.local",
        name="Arjun Shah",
        role="programme_lead",
        password_hash=hash_password("lead123"),
    )
    db.add_all([finance, lead])
    db.flush()

    # ── Grants matching the Tally export columns ──────────────────────────────
    g1 = models.Grant(
        code="Donor A - Campus 1",
        name="Donor A - Campus 1",
        donor_name="Donor A",
        uc_format="Standard UC",
        approved_amount=Decimal("6420000.00"),
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        campus_pool="CAMPUS-SUPPORT",
        central_pool="CENTRAL-SUPPORT",
        primary_location="Campus 1",
        programme_lead_id=lead.id,
        fcra=False,
    )
    g2 = models.Grant(
        code="Donor A - Campus 2",
        name="Donor A - Campus 2",
        donor_name="Donor A",
        uc_format="Standard UC",
        approved_amount=Decimal("4150000.00"),
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        campus_pool="CAMPUS-SUPPORT",
        central_pool="CENTRAL-SUPPORT",
        primary_location="Campus 2",
        programme_lead_id=lead.id,
        fcra=False,
    )
    g3 = models.Grant(
        code="Donor B - Campus 3",
        name="Donor B - Campus 3",
        donor_name="Donor B",
        uc_format="Standard UC",
        approved_amount=Decimal("5280000.00"),
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        campus_pool="CAMPUS-SUPPORT",
        central_pool="CENTRAL-SUPPORT",
        primary_location="Campus 3 + Campus 4",
        programme_lead_id=None,
        fcra=False,
    )
    g4 = models.Grant(
        code="Donor C - Alumni",
        name="Donor C - Alumni",
        donor_name="Donor C",
        uc_format="Standard UC",
        approved_amount=Decimal("1800000.00"),
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        campus_pool="",
        central_pool="CENTRAL-SUPPORT",
        primary_location="Alumni programme",
        programme_lead_id=None,
        fcra=False,
    )
    g5 = models.Grant(
        code="OTHER-CENTRAL",
        name="Other grants in central pool (not in this sample)",
        donor_name="Various",
        uc_format="Standard UC",
        approved_amount=Decimal("9850000.00"),
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        campus_pool="",
        central_pool="CENTRAL-SUPPORT",
        primary_location="Other grants",
        programme_lead_id=None,
        fcra=False,
    )
    db.add_all([g1, g2, g3, g4, g5])
    db.flush()

    db.add_all(
        [
            models.GrantLocation(grant_id=g1.id, location="Campus 1", amount=Decimal("6420000.00")),
            models.GrantLocation(grant_id=g2.id, location="Campus 2", amount=Decimal("4150000.00")),
            models.GrantLocation(grant_id=g3.id, location="Campus 3 + Campus 4", amount=Decimal("5280000.00")),
            models.GrantLocation(grant_id=g4.id, location="Alumni programme", amount=Decimal("1800000.00")),
            models.GrantLocation(grant_id=g5.id, location="Other grants", amount=Decimal("9850000.00")),
        ]
    )

    # ── Ledger → Budget head mappings (all ledgers from the sample export) ────
    mappings = {
        # GP
        "GP Sub-Grants": "Sub-Grants",
        # OA – Office Admin
        "OA Bank Charges": "Admin & Office",
        "OA Postage & Courier Charges": "Admin & Office",
        "OA Printing & Stationery": "Admin & Office",
        # OC – Occupancy / Contracts
        "OC Contract fees": "Admin / Occupancy",
        "OC Repairs & Maintenance": "Admin / Occupancy",
        "OC Venue Rent": "Admin / Occupancy",
        # OT – IT / Tech
        "OT Subscriptions": "Admin & Office",
        "OT System Maintenance": "Admin & Office",
        # OU – Utilities
        "OU Electricity Charges": "Admin / Occupancy",
        "OU Telephone & Internet Charges": "Admin / Occupancy",
        "OU Water Charges": "Admin / Occupancy",
        # OV – Travel / Visits
        "OV Food - Admissions": "Program Costs",
        "OV Travel - Admissions": "Travel",
        "OV Travel - Meetups": "Travel",
        "OV Travel - Placements": "Travel",
        # PD – People Development
        "PD Fees - Trainings": "Personnel",
        "PD Mediclaim": "Personnel",
        "PD Wellness": "Personnel",
        # PF – Professional Fees
        "PF Fees - Admissions": "Program Costs",
        "PF Fees - Communication": "Program Costs",
        "PF Fees - Curriculum & Design": "Program Costs",
        "PF Fees - Facilitators": "Program Costs",
        "PF Fees - Finance": "Admin & Office",
        "PF Fees - Placements": "Program Costs",
        # PS – Salaries
        "PS Salary - Admissions": "Personnel",
        "PS Salary - Campus Support": "Personnel",
        "PS Salary - Facilitators": "Personnel",
        "PS Salary - Finance": "Personnel",
        "PS Salary - Placements": "Personnel",
        "PS Salary - Tech & Product Development": "Personnel",
        # SM – Student Meals
        "SM Groceries": "Program Costs",
        "SM Kitchen Expenses": "Program Costs",
        # SS – Student Support
        "SS Wellness": "Program Costs",
        # SV – Student Visits
        "SV Food": "Program Costs",
        "SV Travel": "Travel",
    }
    for ledger, head in mappings.items():
        db.add(models.LedgerMapping(ledger_name=ledger, budget_head=head, updated_by="seed"))
        db.add(
            models.MappingHistory(
                ledger_name=ledger, old_head=None, new_head=head, changed_by="seed"
            )
        )

    # ── Calendar items ────────────────────────────────────────────────────────
    db.add_all(
        [
            models.CalendarItem(
                grant_id=g1.id,
                title="Quarterly UC",
                due_date=date(2026, 10, 30),
                uc_format="Standard UC",
                status="due",
            ),
            models.CalendarItem(
                grant_id=g2.id,
                title="Quarterly UC",
                due_date=date(2026, 10, 30),
                uc_format="Standard UC",
                status="due",
            ),
            models.CalendarItem(
                grant_id=g3.id,
                title="Half-yearly UC",
                due_date=date(2026, 10, 31),
                uc_format="Standard UC",
                status="due",
            ),
            models.CalendarItem(
                grant_id=g4.id,
                title="Monthly UC",
                due_date=date(2026, 10, 15),
                uc_format="Standard UC",
                status="due",
            ),
        ]
    )

    # ── Sample import run ─────────────────────────────────────────────────────
    run = models.ImportRun(
        period_start=date(2026, 4, 1),
        period_end=date(2026, 9, 30),
        status="draft",
        utilization_filename="utilization-demo.csv",
        central_filename="central-costs-demo.csv",
        uploaded_by="seed",
        uploaded_at=datetime.utcnow(),
        blockers=[],
        warnings=[],
    )
    db.add(run)
    db.flush()

    utilization = [
        ("Donor A - Campus 1", "OA Bank Charges", "26167.00"),
        ("Donor A - Campus 1", "OA Postage & Courier Charges", "51028.00"),
        ("Donor A - Campus 1", "OC Repairs & Maintenance", "37455.00"),
        ("Donor A - Campus 1", "OT Subscriptions", "41591.00"),
        ("Donor A - Campus 1", "OU Electricity Charges", "26026.00"),
        ("Donor A - Campus 1", "OV Travel - Admissions", "97448.00"),
        ("Donor A - Campus 1", "OV Travel - Meetups", "47070.00"),
        ("Donor A - Campus 1", "OV Travel - Placements", "48748.00"),
        ("Donor A - Campus 1", "PD Wellness", "18583.00"),
        ("Donor A - Campus 1", "PF Fees - Curriculum & Design", "18309.00"),
        ("Donor A - Campus 1", "PF Fees - Facilitators", "211287.00"),
        ("Donor A - Campus 1", "PF Fees - Finance", "43266.00"),
        ("Donor A - Campus 1", "PF Fees - Placements", "51926.00"),
        ("Donor A - Campus 1", "PS Salary - Campus Support", "446451.00"),
        ("Donor A - Campus 1", "PS Salary - Facilitators", "1678784.00"),
        ("Donor A - Campus 1", "PS Salary - Finance", "30298.00"),
        ("Donor A - Campus 1", "PS Salary - Placements", "172616.00"),
        ("Donor A - Campus 1", "SS Wellness", "16164.00"),
        ("Donor A - Campus 1", "SV Food", "40765.00"),
        ("Donor A - Campus 2", "OA Bank Charges", "20952.00"),
        ("Donor A - Campus 2", "OA Postage & Courier Charges", "18744.00"),
        ("Donor A - Campus 2", "OA Printing & Stationery", "13769.00"),
        ("Donor A - Campus 2", "OC Contract fees", "83406.00"),
        ("Donor A - Campus 2", "OC Repairs & Maintenance", "29236.00"),
        ("Donor A - Campus 2", "OT Subscriptions", "9310.00"),
        ("Donor A - Campus 2", "OT System Maintenance", "12840.00"),
        ("Donor A - Campus 2", "OU Telephone & Internet Charges", "16620.00"),
        ("Donor A - Campus 2", "OV Food - Admissions", "16091.00"),
        ("Donor A - Campus 2", "OV Travel - Admissions", "55190.00"),
        ("Donor A - Campus 2", "OV Travel - Meetups", "18870.00"),
        ("Donor A - Campus 2", "OV Travel - Placements", "23929.00"),
        ("Donor A - Campus 2", "PD Fees - Trainings", "19184.00"),
        ("Donor A - Campus 2", "PD Mediclaim", "16971.00"),
        ("Donor A - Campus 2", "PD Wellness", "20472.00"),
        ("Donor A - Campus 2", "PF Fees - Communication", "23556.00"),
        ("Donor A - Campus 2", "PF Fees - Facilitators", "98234.00"),
        ("Donor A - Campus 2", "PF Fees - Finance", "24555.00"),
        ("Donor A - Campus 2", "PF Fees - Placements", "27594.00"),
        ("Donor A - Campus 2", "PS Salary - Admissions", "114893.00"),
        ("Donor A - Campus 2", "PS Salary - Campus Support", "276432.00"),
        ("Donor A - Campus 2", "PS Salary - Facilitators", "385209.00"),
        ("Donor A - Campus 2", "PS Salary - Placements", "87868.00"),
        ("Donor A - Campus 2", "PS Salary - Tech & Product Development", "67795.00"),
        ("Donor A - Campus 2", "SM Groceries", "382487.00"),
        ("Donor A - Campus 2", "SM Kitchen Expenses", "10882.00"),
        ("Donor A - Campus 2", "SV Food", "21086.00"),
        ("Donor A - Campus 2", "SV Travel", "16331.00"),
        ("Donor B - Campus 3", "OA Bank Charges", "28830.00"),
        ("Donor B - Campus 3", "OA Postage & Courier Charges", "18559.00"),
        ("Donor B - Campus 3", "OA Printing & Stationery", "35586.00"),
        ("Donor B - Campus 3", "OC Contract fees", "80317.00"),
        ("Donor B - Campus 3", "OC Repairs & Maintenance", "24810.00"),
        ("Donor B - Campus 3", "OT Subscriptions", "28040.00"),
        ("Donor B - Campus 3", "OT System Maintenance", "14950.00"),
        ("Donor B - Campus 3", "OU Telephone & Internet Charges", "27009.00"),
        ("Donor B - Campus 3", "OU Water Charges", "37062.00"),
        ("Donor B - Campus 3", "OV Food - Admissions", "20312.00"),
        ("Donor B - Campus 3", "OV Travel - Admissions", "90279.00"),
        ("Donor B - Campus 3", "OV Travel - Placements", "38656.00"),
        ("Donor B - Campus 3", "PD Fees - Trainings", "25470.00"),
        ("Donor B - Campus 3", "PD Mediclaim", "13246.00"),
        ("Donor B - Campus 3", "PD Wellness", "16785.00"),
        ("Donor B - Campus 3", "PF Fees - Admissions", "13991.00"),
        ("Donor B - Campus 3", "PF Fees - Communication", "37315.00"),
        ("Donor B - Campus 3", "PF Fees - Curriculum & Design", "30545.00"),
        ("Donor B - Campus 3", "PF Fees - Facilitators", "177332.00"),
        ("Donor B - Campus 3", "PF Fees - Finance", "26634.00"),
        ("Donor B - Campus 3", "PS Salary - Admissions", "126986.00"),
        ("Donor B - Campus 3", "PS Salary - Campus Support", "137499.00"),
        ("Donor B - Campus 3", "PS Salary - Facilitators", "1385048.00"),
        ("Donor B - Campus 3", "PS Salary - Finance", "27106.00"),
        ("Donor B - Campus 3", "PS Salary - Placements", "123895.00"),
        ("Donor B - Campus 3", "PS Salary - Tech & Product Development", "104387.00"),
        ("Donor B - Campus 3", "SM Groceries", "495586.00"),
        ("Donor B - Campus 3", "SM Kitchen Expenses", "36537.00"),
        ("Donor B - Campus 3", "SS Wellness", "24679.00"),
        ("Donor B - Campus 3", "SV Food", "13999.00"),
        ("Donor B - Campus 3", "SV Travel", "19917.00"),
        ("Donor C - Alumni", "OA Bank Charges", "9361.00"),
        ("Donor C - Alumni", "OA Postage & Courier Charges", "7071.00"),
        ("Donor C - Alumni", "OA Printing & Stationery", "5171.00"),
        ("Donor C - Alumni", "OC Contract fees", "27897.00"),
        ("Donor C - Alumni", "OC Repairs & Maintenance", "9445.00"),
        ("Donor C - Alumni", "OC Venue Rent", "28905.00"),
        ("Donor C - Alumni", "OT Subscriptions", "4837.00"),
        ("Donor C - Alumni", "OV Food - Admissions", "8600.00"),
        ("Donor C - Alumni", "OV Travel - Admissions", "14272.00"),
        ("Donor C - Alumni", "OV Travel - Meetups", "8800.00"),
        ("Donor C - Alumni", "OV Travel - Placements", "8235.00"),
        ("Donor C - Alumni", "PD Mediclaim", "6339.00"),
        ("Donor C - Alumni", "PF Fees - Admissions", "8535.00"),
        ("Donor C - Alumni", "PF Fees - Communication", "5885.00"),
        ("Donor C - Alumni", "PF Fees - Curriculum & Design", "7134.00"),
        ("Donor C - Alumni", "PF Fees - Facilitators", "28687.00"),
        ("Donor C - Alumni", "PF Fees - Finance", "3884.00"),
        ("Donor C - Alumni", "PF Fees - Placements", "5281.00"),
        ("Donor C - Alumni", "PS Salary - Campus Support", "77741.00"),
        ("Donor C - Alumni", "PS Salary - Facilitators", "265892.00"),
        ("Donor C - Alumni", "PS Salary - Placements", "35463.00"),
        ("Donor C - Alumni", "PS Salary - Tech & Product Development", "47524.00"),
        ("Donor C - Alumni", "SM Groceries", "83341.00"),
        ("Donor C - Alumni", "SM Kitchen Expenses", "3897.00"),
        ("Donor C - Alumni", "OU Water Charges", "5704.00"),
    ]
    db.add_all(
        [
            models.UtilizationRow(run_id=run.id, grant_code=code, ledger=ledger, amount=Decimal(amt))
            for code, ledger, amt in utilization
        ]
    )

    central = [
        # Campus Project Support → campus pool
        ("OA Postage & Courier Charges", "CAMPUS-SUPPORT", "campus", "25568.00"),
        ("OA Printing & Stationery", "CAMPUS-SUPPORT", "campus", "38549.00"),
        ("OC Contract fees", "CAMPUS-SUPPORT", "campus", "83591.00"),
        ("OC Repairs & Maintenance", "CAMPUS-SUPPORT", "campus", "23600.00"),
        ("OC Venue Rent", "CAMPUS-SUPPORT", "campus", "213110.00"),
        ("OT Subscriptions", "CAMPUS-SUPPORT", "campus", "15057.00"),
        ("OT System Maintenance", "CAMPUS-SUPPORT", "campus", "41453.00"),
        ("OU Electricity Charges", "CAMPUS-SUPPORT", "campus", "28813.00"),
        ("OU Telephone & Internet Charges", "CAMPUS-SUPPORT", "campus", "34996.00"),
        ("OU Water Charges", "CAMPUS-SUPPORT", "campus", "17809.00"),
        ("OV Food - Admissions", "CAMPUS-SUPPORT", "campus", "37025.00"),
        ("OV Travel - Admissions", "CAMPUS-SUPPORT", "campus", "48366.00"),
        ("OV Travel - Meetups", "CAMPUS-SUPPORT", "campus", "30752.00"),
        ("OV Travel - Placements", "CAMPUS-SUPPORT", "campus", "35477.00"),
        ("PD Fees - Trainings", "CAMPUS-SUPPORT", "campus", "18555.00"),
        ("PD Mediclaim", "CAMPUS-SUPPORT", "campus", "18731.00"),
        ("PD Wellness", "CAMPUS-SUPPORT", "campus", "15311.00"),
        ("PF Fees - Admissions", "CAMPUS-SUPPORT", "campus", "19927.00"),
        ("PF Fees - Communication", "CAMPUS-SUPPORT", "campus", "18425.00"),
        ("PF Fees - Curriculum & Design", "CAMPUS-SUPPORT", "campus", "29673.00"),
        ("PF Fees - Facilitators", "CAMPUS-SUPPORT", "campus", "129427.00"),
        ("PF Fees - Finance", "CAMPUS-SUPPORT", "campus", "30637.00"),
        ("PF Fees - Placements", "CAMPUS-SUPPORT", "campus", "35014.00"),
        ("PS Salary - Admissions", "CAMPUS-SUPPORT", "campus", "297416.00"),
        ("PS Salary - Campus Support", "CAMPUS-SUPPORT", "campus", "335859.00"),
        ("PS Salary - Placements", "CAMPUS-SUPPORT", "campus", "252283.00"),
        ("PS Salary - Tech & Product Development", "CAMPUS-SUPPORT", "campus", "84576.00"),
        ("SM Groceries", "CAMPUS-SUPPORT", "campus", "482062.00"),
        ("SM Kitchen Expenses", "CAMPUS-SUPPORT", "campus", "38052.00"),
        ("SS Wellness", "CAMPUS-SUPPORT", "campus", "33756.00"),
        ("SV Travel", "CAMPUS-SUPPORT", "campus", "24786.00"),
        # Central Support → central pool
        ("OA Bank Charges", "CENTRAL-SUPPORT", "central", "74221.00"),
        ("OA Postage & Courier Charges", "CENTRAL-SUPPORT", "central", "46103.00"),
        ("OA Printing & Stationery", "CENTRAL-SUPPORT", "central", "88872.00"),
        ("OC Contract fees", "CENTRAL-SUPPORT", "central", "107804.00"),
        ("OC Repairs & Maintenance", "CENTRAL-SUPPORT", "central", "74470.00"),
        ("OC Venue Rent", "CENTRAL-SUPPORT", "central", "367708.00"),
        ("OT Subscriptions", "CENTRAL-SUPPORT", "central", "78494.00"),
        ("OT System Maintenance", "CENTRAL-SUPPORT", "central", "48359.00"),
        ("OU Electricity Charges", "CENTRAL-SUPPORT", "central", "67065.00"),
        ("OU Telephone & Internet Charges", "CENTRAL-SUPPORT", "central", "82993.00"),
        ("OU Water Charges", "CENTRAL-SUPPORT", "central", "82433.00"),
        ("OV Food - Admissions", "CENTRAL-SUPPORT", "central", "52808.00"),
        ("OV Travel - Meetups", "CENTRAL-SUPPORT", "central", "75551.00"),
        ("PD Fees - Trainings", "CENTRAL-SUPPORT", "central", "54503.00"),
        ("PD Mediclaim", "CENTRAL-SUPPORT", "central", "38237.00"),
        ("PF Fees - Admissions", "CENTRAL-SUPPORT", "central", "63428.00"),
        ("PF Fees - Communication", "CENTRAL-SUPPORT", "central", "47322.00"),
        ("PF Fees - Curriculum & Design", "CENTRAL-SUPPORT", "central", "89129.00"),
        ("PF Fees - Facilitators", "CENTRAL-SUPPORT", "central", "175328.00"),
        ("PF Fees - Finance", "CENTRAL-SUPPORT", "central", "49038.00"),
        ("PF Fees - Placements", "CENTRAL-SUPPORT", "central", "83678.00"),
        ("PS Salary - Admissions", "CENTRAL-SUPPORT", "central", "405116.00"),
        ("PS Salary - Campus Support", "CENTRAL-SUPPORT", "central", "374350.00"),
        ("PS Salary - Facilitators", "CENTRAL-SUPPORT", "central", "1420737.00"),
        ("PS Salary - Finance", "CENTRAL-SUPPORT", "central", "43949.00"),
        ("PS Salary - Placements", "CENTRAL-SUPPORT", "central", "278660.00"),
        ("PS Salary - Tech & Product Development", "CENTRAL-SUPPORT", "central", "416122.00"),
        ("SM Groceries", "CENTRAL-SUPPORT", "central", "1130386.00"),
        ("SM Kitchen Expenses", "CENTRAL-SUPPORT", "central", "63481.00"),
        ("SS Wellness", "CENTRAL-SUPPORT", "central", "56598.00"),
        ("SV Food", "CENTRAL-SUPPORT", "central", "64066.00"),
        ("SV Travel", "CENTRAL-SUPPORT", "central", "52841.00"),
    ]
    db.add_all(
        [
            models.CentralCostRow(run_id=run.id, ledger=ledger, pool=pool, pool_kind=kind, amount=Decimal(amt))
            for ledger, pool, kind, amt in central
        ]
    )
    db.flush()
    recompute_run(db, run)
    audit(db, "seed", "seed", "database", {"grants": 5, "run_id": run.id})
    db.commit()
