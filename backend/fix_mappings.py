#!/usr/bin/env python3
"""
Fix script: inserts all ledger mappings and recomputes the latest run.
Run from the backend directory:
    python fix_mappings.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from app.database import SessionLocal
from app import models
from app.services import mapping_dict, recompute_run

MAPPINGS = {
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

def main():
    db = SessionLocal()
    try:
        added = 0
        updated = 0
        for ledger, head in MAPPINGS.items():
            existing = db.query(models.LedgerMapping).filter(
                models.LedgerMapping.ledger_name == ledger
            ).first()
            old_head = existing.budget_head if existing else None
            if existing:
                if existing.budget_head == head:
                    print(f"  [skip]    {ledger!r} already → {head!r}")
                    continue
                existing.budget_head = head
                existing.updated_by = "fix_script"
                updated += 1
                print(f"  [updated] {ledger!r} → {head!r}")
            else:
                db.add(models.LedgerMapping(
                    ledger_name=ledger,
                    budget_head=head,
                    updated_by="fix_script",
                ))
                added += 1
                print(f"  [added]   {ledger!r} → {head!r}")
            db.add(models.MappingHistory(
                ledger_name=ledger,
                old_head=old_head,
                new_head=head,
                changed_by="fix_script",
            ))
        db.flush()
        print(f"\nMappings: {added} added, {updated} updated.")

        # Recompute all non-published runs
        runs = db.query(models.ImportRun).filter(
            models.ImportRun.status != "published"
        ).order_by(models.ImportRun.id).all()
        print(f"Recomputing {len(runs)} run(s)…")
        for run in runs:
            recompute_run(db, run)
            status = "✅ draft (no blockers)" if not run.blockers else f"❌ blocked ({len(run.blockers)} blocker(s))"
            print(f"  Run #{run.id}: {status}")
            for b in run.blockers:
                print(f"    • {b}")
        db.commit()
        print("\nDone.")
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
