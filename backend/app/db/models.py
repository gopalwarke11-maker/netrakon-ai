"""Persistent SQLAlchemy entities. Pydantic API schemas stay in app.models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CameraRecord(Base):
    __tablename__ = "cameras"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sector: Mapped[str] = mapped_column(String(120), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ONLINE")
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="FILE")
    stream_url: Mapped[str | None] = mapped_column(String(500))
    storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    boundaries: Mapped[list[BoundaryRecord]] = relationship(back_populates="camera", passive_deletes=True)
    alerts: Mapped[list[AlertRecord]] = relationship(back_populates="camera", passive_deletes=True)
    intrusion_events: Mapped[list[IntrusionEventRecord]] = relationship(back_populates="camera", passive_deletes=True)
    behavior_observations: Mapped[list[BehaviorObservationRecord]] = relationship(back_populates="camera", passive_deletes=True)


class BoundaryRecord(Base):
    __tablename__ = "boundaries"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    point_a: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    point_b: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    restricted_side: Mapped[str] = mapped_column(String(10), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    tolerance: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    camera: Mapped[CameraRecord] = relationship(back_populates="boundaries")
    alerts: Mapped[list[AlertRecord]] = relationship(back_populates="boundary", passive_deletes=True)
    intrusion_events: Mapped[list[IntrusionEventRecord]] = relationship(back_populates="boundary", passive_deletes=True)


class AlertRecord(Base):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    event_id: Mapped[str | None] = mapped_column(String(80), unique=True, index=True)
    camera_id: Mapped[str | None] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"), index=True)
    boundary_id: Mapped[str | None] = mapped_column(
        ForeignKey("boundaries.id", ondelete="SET NULL"), index=True
    )
    sector: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="SYSTEM")
    severity: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    track_id: Mapped[str | None] = mapped_column(String(80), index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", index=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, index=True)
    risk_level: Mapped[str | None] = mapped_column(String(10), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    camera: Mapped[CameraRecord | None] = relationship(back_populates="alerts")
    boundary: Mapped[BoundaryRecord | None] = relationship(back_populates="alerts")


class IntrusionEventRecord(Base):
    __tablename__ = "intrusion_events"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    camera_id: Mapped[str | None] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"), index=True)
    boundary_id: Mapped[str | None] = mapped_column(ForeignKey("boundaries.id", ondelete="SET NULL"), index=True)
    boundary_name: Mapped[str] = mapped_column(String(120), nullable=False)
    track_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    object_class: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    previous_anchor: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    current_anchor: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    crossing_direction: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, default="INTRUSION")
    alert_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, index=True)
    risk_level: Mapped[str | None] = mapped_column(String(10), index=True)
    risk_factors: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    camera: Mapped[CameraRecord | None] = relationship(back_populates="intrusion_events")
    boundary: Mapped[BoundaryRecord | None] = relationship(back_populates="intrusion_events")


Index("ix_intrusion_events_camera_timestamp", IntrusionEventRecord.camera_id, IntrusionEventRecord.timestamp)


class BehaviorObservationRecord(Base):
    """Behavior analysis observations for tracked objects."""
    __tablename__ = "behavior_observations"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    track_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    intrusion_event_id: Mapped[str | None] = mapped_column(String(80), index=True)
    behavior_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    behavior_score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    observations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    duration_window_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    camera: Mapped[CameraRecord] = relationship(back_populates="behavior_observations")


Index("ix_behavior_observations_camera_track", BehaviorObservationRecord.camera_id, BehaviorObservationRecord.track_id)
Index("ix_behavior_observations_type", BehaviorObservationRecord.behavior_type)
