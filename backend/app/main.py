from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from .auth import create_token, get_current_user, require_finance, verify_password, visible_grant_codes
from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .exports import excel_uc, grant_master_excel, pdf_uc
from . import models
from .money import format_inr, q2
from .parsers import parse_central, parse_grants, parse_utilization
from .seed import seed_if_empty
from .serialize import dump_grant, money
from .services import audit, bva_for, grant_report, latest_run, mapping_dict, recompute_run, statement_for, summary_payload

app = FastAPI(title="Donor Utilization Automation", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import inspect, text

    columns = {column["name"] for column in inspect(engine).get_columns("grants")}
    with engine.begin() as connection:
        if "reporting_cycle" not in columns:
            connection.execute(text("ALTER TABLE grants ADD COLUMN reporting_cycle VARCHAR(40)"))
        if "next_report_due" not in columns:
            connection.execute(text("ALTER TABLE grants ADD COLUMN next_report_due DATE"))
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


class LoginIn(BaseModel):
    email: str
    password: str


class MappingIn(BaseModel):
    ledger_name: str
    budget_head: str


class BudgetIn(BaseModel):
    head: str
    line_name: str
    amount: str


class GrantIn(BaseModel):
    code: str
    name: str
    donor_name: str
    uc_format: str = "Standard UC"
    approved_amount: str
    start_date: date
    end_date: Optional[date] = None
    campus_pool: str = ""
    central_pool: str
    primary_location: str
    programme_lead_id: Optional[int] = None


def _assert_grant_visible(user: models.User, code: str, db: Session) -> models.Grant:
    grant = (
        db.query(models.Grant)
        .options(joinedload(models.Grant.locations), joinedload(models.Grant.budget_lines), joinedload(models.Grant.programme_lead))
        .filter(models.Grant.code == code)
        .first()
    )
    if not grant:
        raise HTTPException(404, "Grant not found")
    allowed = visible_grant_codes(user, db)
    if allowed is not None and grant.code not in allowed:
        raise HTTPException(403, "You can only view your own grants")
    return grant


@app.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {
        "access_token": create_token(user),
        "token_type": "bearer",
        "user": {"email": user.email, "name": user.name, "role": user.role},
    }


@app.get("/auth/me")
def me(user: models.User = Depends(get_current_user)):
    return {"email": user.email, "name": user.name, "role": user.role}


@app.get("/grants")
def list_grants(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    allowed = visible_grant_codes(user, db)
    q = db.query(models.Grant).options(
        joinedload(models.Grant.locations),
        joinedload(models.Grant.budget_lines),
        joinedload(models.Grant.programme_lead),
    )
    grants = q.all()
    if allowed is not None:
        grants = [g for g in grants if g.code in allowed]
    return [dump_grant(g) for g in grants]


@app.post("/grants")
def create_grant(body: GrantIn, user: models.User = Depends(require_finance), db: Session = Depends(get_db)):
    if db.query(models.Grant).filter(models.Grant.code == body.code).first():
        raise HTTPException(400, "Grant code already exists")
    grant = models.Grant(
        code=body.code.strip(),
        name=body.name,
        donor_name=body.donor_name,
        uc_format=body.uc_format,
        approved_amount=q2(body.approved_amount),
        start_date=body.start_date,
        end_date=body.end_date,
        campus_pool=body.campus_pool.strip(),
        central_pool=body.central_pool,
        primary_location=body.primary_location,
        programme_lead_id=body.programme_lead_id,
    )
    db.add(grant)
    db.flush()
    db.add(models.GrantLocation(grant_id=grant.id, location=body.primary_location, amount=q2(body.approved_amount)))
    audit(db, user.email, "create", "grant", {"code": grant.code})
    db.commit()
    return dump_grant(grant)


@app.post("/grants/import")
def import_grants(
    file: UploadFile = File(...),
    user: models.User = Depends(require_finance),
    db: Session = Depends(get_db),
):
    try:
        grants = parse_grants(file.filename or "grants.xlsx", file.file.read())
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc

    existing = {code.casefold() for (code,) in db.query(models.Grant.code).all()}
    incoming = [grant["code"].strip() for grant in grants]
    seen = set()
    duplicate_codes = []
    for code in incoming:
        normalized = code.casefold()
        if normalized in existing or normalized in seen:
            duplicate_codes.append(code)
        seen.add(normalized)
    duplicate_codes = sorted(set(duplicate_codes))
    too_long = [code for code in incoming if len(code) > 40]
    if duplicate_codes:
        raise HTTPException(400, "Grant code already exists or is repeated in the file: " + ", ".join(duplicate_codes))
    if too_long:
        raise HTTPException(400, "Grant codes must be 40 characters or fewer: " + ", ".join(too_long))

    created = []
    for item in grants:
        grant = models.Grant(**item)
        db.add(grant)
        db.flush()
        db.add(models.GrantLocation(grant_id=grant.id, location=item["primary_location"], amount=item["approved_amount"]))
        created.append(grant.code)
    audit(db, user.email, "import", "grant_master", {"codes": created, "filename": file.filename or ""})
    db.commit()
    return {"created": len(created), "codes": created}


@app.get("/grants/export")
def export_grants(
    user: models.User = Depends(require_finance),
    db: Session = Depends(get_db),
):
    grants = db.query(models.Grant).order_by(models.Grant.id).all()
    data = grant_master_excel(
        [
            {
                "code": grant.code,
                "donor_name": grant.donor_name,
                "primary_location": grant.primary_location,
                "approved_amount": grant.approved_amount,
                "start_date": grant.start_date,
                "end_date": grant.end_date,
                "campus_pool": grant.campus_pool,
                "central_pool": grant.central_pool,
                "reporting_cycle": grant.reporting_cycle,
                "next_report_due": grant.next_report_due,
            }
            for grant in grants
        ]
    )
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="grant-master.xlsx"'},
    )


@app.get("/grants/{code}")
def get_grant(code: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return dump_grant(_assert_grant_visible(user, code, db))


@app.get("/mappings")
def list_mappings(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(models.LedgerMapping).order_by(models.LedgerMapping.ledger_name).all()
    history = db.query(models.MappingHistory).order_by(models.MappingHistory.changed_at.desc()).limit(50).all()
    return {
        "mappings": [
            {
                "id": m.id,
                "ledger_name": m.ledger_name,
                "budget_head": m.budget_head,
                "updated_by": m.updated_by,
                "updated_at": m.updated_at.isoformat(),
            }
            for m in rows
        ],
        "history": [
            {
                "ledger_name": h.ledger_name,
                "old_head": h.old_head,
                "new_head": h.new_head,
                "changed_by": h.changed_by,
                "changed_at": h.changed_at.isoformat(),
            }
            for h in history
        ],
    }


@app.post("/mappings")
def upsert_mapping(body: MappingIn, user: models.User = Depends(require_finance), db: Session = Depends(get_db)):
    existing = db.query(models.LedgerMapping).filter(models.LedgerMapping.ledger_name == body.ledger_name.strip()).first()
    old = existing.budget_head if existing else None
    if existing:
        existing.budget_head = body.budget_head
        existing.updated_by = user.email
    else:
        db.add(models.LedgerMapping(ledger_name=body.ledger_name.strip(), budget_head=body.budget_head, updated_by=user.email))
    db.add(
        models.MappingHistory(
            ledger_name=body.ledger_name.strip(),
            old_head=old,
            new_head=body.budget_head,
            changed_by=user.email,
        )
    )
    audit(db, user.email, "upsert", "mapping", {"ledger": body.ledger_name, "head": body.budget_head})
    run = latest_run(db)
    if run and run.status != "published":
        recompute_run(db, run)
    db.commit()
    return {"ok": True}


@app.get("/grants/{code}/budgets")
def get_budgets(code: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    grant = _assert_grant_visible(user, code, db)
    history = (
        db.query(models.BudgetHistory)
        .filter(models.BudgetHistory.grant_code == code)
        .order_by(models.BudgetHistory.changed_at.desc())
        .limit(20)
        .all()
    )
    return {
        "grant": dump_grant(grant),
        "history": [
            {"changed_by": h.changed_by, "changed_at": h.changed_at.isoformat(), "note": h.note, "snapshot": h.snapshot}
            for h in history
        ],
    }


@app.post("/grants/{code}/budgets")
def replace_budgets(
    code: str,
    lines: list[BudgetIn],
    user: models.User = Depends(require_finance),
    db: Session = Depends(get_db),
):
    grant = _assert_grant_visible(user, code, db)
    snapshot = [{"head": l.head, "line_name": l.line_name, "amount": money(l.amount)} for l in grant.budget_lines]
    db.add(models.BudgetHistory(grant_code=code, snapshot=snapshot, changed_by=user.email, note="replaced budget lines"))
    db.query(models.BudgetLine).filter(models.BudgetLine.grant_id == grant.id).delete()
    for line in lines:
        db.add(models.BudgetLine(grant_id=grant.id, head=line.head, line_name=line.line_name, amount=q2(line.amount)))
    audit(db, user.email, "replace", "budget", {"code": code, "lines": len(lines)})
    run = latest_run(db)
    if run and run.status != "published":
        recompute_run(db, run)
    db.commit()
    db.refresh(grant)
    return dump_grant(grant)


@app.get("/runs")
def list_runs(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    runs = db.query(models.ImportRun).order_by(models.ImportRun.id.desc()).all()
    return [
        {
            "id": r.id,
            "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(),
            "status": r.status,
            "utilization_filename": r.utilization_filename,
            "central_filename": r.central_filename,
            "uploaded_by": r.uploaded_by,
            "uploaded_at": r.uploaded_at.isoformat(),
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "blockers": r.blockers,
            "warnings": r.warnings,
        }
        for r in runs
    ]


@app.post("/runs")
def upload_run(
    period_start: date = Form(...),
    period_end: date = Form(...),
    utilization: UploadFile = File(...),
    central: UploadFile = File(...),
    user: models.User = Depends(require_finance),
    db: Session = Depends(get_db),
):
    util_bytes = utilization.file.read()
    central_bytes = central.file.read()
    try:
        util_rows = parse_utilization(utilization.filename or "util.xlsx", util_bytes)
        central_rows = parse_central(central.filename or "central.xlsx", central_bytes)
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc

    grants = db.query(models.Grant).all()

    def label_key(value: str) -> str:
        return " ".join(value.strip().casefold().split())

    grant_aliases = {}
    for grant in grants:
        grant_aliases[label_key(grant.code)] = grant.code
        grant_aliases[label_key(grant.name)] = grant.code
    missing_grants = sorted({row["grant_code"] for row in util_rows if label_key(row["grant_code"]) not in grant_aliases})
    if missing_grants:
        raise HTTPException(
            400,
            "Tally grant column(s) are not configured in Grant Master: "
            + ", ".join(missing_grants)
            + ". Add each grant with the same name or code before uploading.",
        )
    for row in util_rows:
        row["grant_code"] = grant_aliases[label_key(row["grant_code"])]

    uploaded_grant_codes = {row["grant_code"] for row in util_rows}
    for row in central_rows:
        if row["pool"] == "__AUTO_CAMPUS_POOL__":
            pools = {
                grant.campus_pool.strip()
                for grant in grants
                if grant.code in uploaded_grant_codes and grant.campus_pool.strip()
            }
            if len(pools) != 1:
                raise HTTPException(
                    400,
                    "Campus Project Support needs one shared campus pool in Grant Master. "
                    "Set the participating grants to the same campus pool, then upload again.",
                )
            row["pool"] = next(iter(pools))
        elif row["pool"] == "__AUTO_CENTRAL_POOL__":
            pools = {
                grant.central_pool.strip()
                for grant in grants
                if grant.code in uploaded_grant_codes and grant.central_pool.strip()
            }
            if len(pools) != 1:
                raise HTTPException(
                    400,
                    "Central Support needs one shared central pool in Grant Master. "
                    "Set central-pool grants to the same pool, then upload again.",
                )
            row["pool"] = next(iter(pools))

    run = models.ImportRun(
        period_start=period_start,
        period_end=period_end,
        status="draft",
        utilization_filename=utilization.filename or "",
        central_filename=central.filename or "",
        uploaded_by=user.email,
        blockers=[],
        warnings=[],
    )
    db.add(run)
    db.flush()
    for row in util_rows:
        db.add(models.UtilizationRow(run_id=run.id, grant_code=row["grant_code"], ledger=row["ledger"], amount=row["amount"]))
    for row in central_rows:
        db.add(
            models.CentralCostRow(
                run_id=run.id,
                ledger=row["ledger"],
                pool=row["pool"],
                pool_kind=row["pool_kind"],
                amount=row["amount"],
            )
        )
    db.flush()
    recompute_run(db, run)
    audit(
        db,
        user.email,
        "upload",
        "run",
        {"run_id": run.id, "period_start": str(period_start), "period_end": str(period_end)},
    )
    db.commit()
    db.refresh(run)
    return {"id": run.id, "status": run.status, "blockers": run.blockers, "warnings": run.warnings}


@app.post("/runs/{run_id}/publish")
def publish_run(run_id: int, user: models.User = Depends(require_finance), db: Session = Depends(get_db)):
    run = db.query(models.ImportRun).filter(models.ImportRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Run not found")
    recompute_run(db, run)
    if run.blockers:
        db.commit()
        raise HTTPException(400, {"detail": "Cannot publish until blockers are cleared", "blockers": run.blockers})
    run.status = "published"
    run.published_at = datetime.utcnow()
    audit(db, user.email, "publish", "run", {"run_id": run.id})
    db.commit()
    return {"id": run.id, "status": run.status}


@app.get("/reports/summary")
def reports_summary(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return summary_payload(db, visible_grant_codes(user, db))


@app.get("/reports/exceptions")
def reports_exceptions(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return summary_payload(db, visible_grant_codes(user, db))["exceptions"]


@app.get("/reports/grants/{code}")
def report_grant(code: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    grant = _assert_grant_visible(user, code, db)
    run = latest_run(db)
    if not run:
        raise HTTPException(404, "No import run yet")
    return grant_report(db, grant, run)


@app.get("/reports/grants/{code}/excel")
def report_excel(code: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    grant = _assert_grant_visible(user, code, db)
    run = latest_run(db)
    if not run:
        raise HTTPException(404, "No import run yet")
    report = grant_report(db, grant, run)
    data = excel_uc(report["grant"], report["statement"], report["budget_vs_actual"], report["run"])
    filename = f"{code}-UC-{run.period_end.isoformat()}.xlsx"
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/reports/grants/{code}/pdf")
def report_pdf(code: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    grant = _assert_grant_visible(user, code, db)
    run = latest_run(db)
    if not run:
        raise HTTPException(404, "No import run yet")
    report = grant_report(db, grant, run)
    data = pdf_uc(report["grant"], report["statement"], report["budget_vs_actual"], report["run"])
    filename = f"{code}-UC-{run.period_end.isoformat()}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/audit")
def audit_log(user: models.User = Depends(require_finance), db: Session = Depends(get_db)):
    rows = db.query(models.AuditLog).order_by(models.AuditLog.at.desc()).limit(200).all()
    return [
        {
            "id": r.id,
            "at": r.at.isoformat(),
            "actor": r.actor,
            "action": r.action,
            "entity": r.entity,
            "detail": r.detail,
        }
        for r in rows
    ]


@app.get("/calendar")
def calendar(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    allowed = visible_grant_codes(user, db)
    items = db.query(models.CalendarItem).all()
    out = []
    for item in items:
        grant = db.query(models.Grant).filter(models.Grant.id == item.grant_id).first()
        if not grant:
            continue
        if allowed is not None and grant.code not in allowed:
            continue
        out.append(
            {
                "id": item.id,
                "grant_code": grant.code,
                "grant_name": grant.name,
                "title": item.title,
                "due_date": item.due_date.isoformat(),
                "uc_format": item.uc_format,
                "status": item.status,
            }
        )
    out.sort(key=lambda r: r["due_date"])
    return out


@app.get("/health")
def health():
    return {"ok": True}
