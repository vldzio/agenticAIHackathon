from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class AssessmentRow(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    mode: Mapped[str] = mapped_column(String(8))
    simulated: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(10))
    user_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    fitness_goal: Mapped[str] = mapped_column(String(40))
    fitness_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    injury_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    safety_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    daily_calorie_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sessions_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[str] = mapped_column(Text)  # full Assessment JSON (never contains an API key)

    logs: Mapped[list[ProgressLogRow]] = relationship(back_populates="assessment", cascade="all, delete-orphan")


class ProgressLogRow(Base):
    __tablename__ = "progress_logs"
    __table_args__ = (Index("ix_logs_assessment_date", "assessment_id", "logged_on"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"))
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(10))
    logged_on: Mapped[dt.date] = mapped_column(Date)
    planned_day: Mapped[str | None] = mapped_column(String(20), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    assessment: Mapped[AssessmentRow] = relationship(back_populates="logs")
