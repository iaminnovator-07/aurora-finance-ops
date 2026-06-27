import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import DispatchStatus, NotificationType, TimestampMixin, new_uuid


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    user = relationship("User", back_populates="audit_logs")


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="notifications")


class AnalyticsSnapshot(Base, TimestampMixin):
    __tablename__ = "analytics_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(20), default="daily", nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    invoices_processed: Mapped[int] = mapped_column(default=0, nullable=False)
    touchless_count: Mapped[int] = mapped_column(default=0, nullable=False)
    touchless_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_trust_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hours_saved: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fraud_prevented_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pending_reviews: Mapped[int] = mapped_column(default=0, nullable=False)
    roi_multiplier: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    processing_time_avg_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class AIConversation(Base, TimestampMixin):
    __tablename__ = "ai_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    messages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    context_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="ai_conversations")


class DispatchRecord(Base, TimestampMixin):
    __tablename__ = "dispatch_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=DispatchStatus.PENDING.value, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_paths: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tracking_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    invoice = relationship("Invoice", back_populates="dispatches")


class AgentRunLog(Base, TimestampMixin):
    __tablename__ = "agent_run_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="idle", nullable=False)
    task_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    log_level: Mapped[str] = mapped_column(String(10), default="info", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
