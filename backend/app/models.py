from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

Money = Numeric(18, 2)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(32))  # finance | programme_lead
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    grants: Mapped[List["Grant"]] = relationship(back_populates="programme_lead")


class Grant(Base):
    __tablename__ = "grants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    donor_name: Mapped[str] = mapped_column(String(200))
    uc_format: Mapped[str] = mapped_column(String(80), default="Standard UC")
    approved_amount: Mapped[Decimal] = mapped_column(Money)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    campus_pool: Mapped[str] = mapped_column(String(80))
    central_pool: Mapped[str] = mapped_column(String(80))
    primary_location: Mapped[str] = mapped_column(String(80))
    programme_lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    fcra: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    programme_lead: Mapped[Optional[User]] = relationship(back_populates="grants")
    locations: Mapped[List["GrantLocation"]] = relationship(cascade="all, delete-orphan")
    budget_lines: Mapped[List["BudgetLine"]] = relationship(cascade="all, delete-orphan")
    calendar_items: Mapped[List["CalendarItem"]] = relationship(cascade="all, delete-orphan")


class GrantLocation(Base):
    __tablename__ = "grant_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    grant_id: Mapped[int] = mapped_column(ForeignKey("grants.id"))
    location: Mapped[str] = mapped_column(String(80))
    amount: Mapped[Decimal] = mapped_column(Money)


class BudgetLine(Base):
    __tablename__ = "budget_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    grant_id: Mapped[int] = mapped_column(ForeignKey("grants.id"))
    head: Mapped[str] = mapped_column(String(120))
    line_name: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Money)


class BudgetHistory(Base):
    __tablename__ = "budget_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    grant_code: Mapped[str] = mapped_column(String(40), index=True)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    changed_by: Mapped[str] = mapped_column(String(120))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    note: Mapped[str] = mapped_column(Text, default="")


class LedgerMapping(Base):
    __tablename__ = "ledger_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ledger_name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    budget_head: Mapped[str] = mapped_column(String(120))
    updated_by: Mapped[str] = mapped_column(String(120), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MappingHistory(Base):
    __tablename__ = "mapping_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ledger_name: Mapped[str] = mapped_column(String(200), index=True)
    old_head: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    new_head: Mapped[str] = mapped_column(String(120))
    changed_by: Mapped[str] = mapped_column(String(120))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ImportRun(Base):
    __tablename__ = "import_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    utilization_filename: Mapped[str] = mapped_column(String(255), default="")
    central_filename: Mapped[str] = mapped_column(String(255), default="")
    uploaded_by: Mapped[str] = mapped_column(String(120))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    blockers: Mapped[list] = mapped_column(JSONB, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, default=list)

    utilization_rows: Mapped[list["UtilizationRow"]] = relationship(cascade="all, delete-orphan")
    central_rows: Mapped[list["CentralCostRow"]] = relationship(cascade="all, delete-orphan")
    allocated_lines: Mapped[list["AllocatedLine"]] = relationship(cascade="all, delete-orphan")


class UtilizationRow(Base):
    __tablename__ = "utilization_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("import_runs.id"))
    ledger: Mapped[str] = mapped_column(String(200))
    grant_code: Mapped[str] = mapped_column(String(40), index=True)
    amount: Mapped[Decimal] = mapped_column(Money)


class CentralCostRow(Base):
    __tablename__ = "central_cost_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("import_runs.id"))
    ledger: Mapped[str] = mapped_column(String(200))
    pool: Mapped[str] = mapped_column(String(80), index=True)
    pool_kind: Mapped[str] = mapped_column(String(20))  # campus | central
    amount: Mapped[Decimal] = mapped_column(Money)


class AllocatedLine(Base):
    __tablename__ = "allocated_lines"
    __table_args__ = (UniqueConstraint("run_id", "grant_code", "ledger", name="uq_alloc_line"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("import_runs.id"))
    grant_code: Mapped[str] = mapped_column(String(40), index=True)
    ledger: Mapped[str] = mapped_column(String(200))
    budget_head: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    direct: Mapped[Decimal] = mapped_column(Money, default=0)
    campus_alloc: Mapped[Decimal] = mapped_column(Money, default=0)
    central_alloc: Mapped[Decimal] = mapped_column(Money, default=0)
    total: Mapped[Decimal] = mapped_column(Money, default=0)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(80))
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)


class CalendarItem(Base):
    __tablename__ = "calendar_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    grant_id: Mapped[int] = mapped_column(ForeignKey("grants.id"))
    title: Mapped[str] = mapped_column(String(200))
    due_date: Mapped[date] = mapped_column(Date)
    uc_format: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="upcoming")
