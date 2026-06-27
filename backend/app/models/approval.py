import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ApprovalQueueStatus, ApprovalStatus, TimestampMixin, new_uuid


class ApprovalQueue(Base, TimestampMixin):
    __tablename__ = "approval_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default=ApprovalQueueStatus.NEEDS_REVIEW.value, nullable=False
    )
    approval_status: Mapped[str] = mapped_column(
        String(50), default=ApprovalStatus.PENDING.value, nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    ai_recommendation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    failed_rules: Mapped[list | None] = mapped_column(JSON, nullable=True)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(default=0, nullable=False)

    invoice = relationship("Invoice", back_populates="approval_queue")


class RuleEngineLog(Base, TimestampMixin):
    __tablename__ = "rule_engine_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True
    )
    email_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id"), nullable=True
    )
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_category: Mapped[str] = mapped_column(String(100), nullable=False)
    passed: Mapped[bool] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)


class BusinessRule(Base, TimestampMixin):
    __tablename__ = "business_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition_expression: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="general", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    priority: Mapped[int] = mapped_column(default=0, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
