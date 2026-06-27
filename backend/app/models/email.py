import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import (
    EmailIntent,
    EmailPriority,
    EmailStatus,
    TimestampMixin,
    new_uuid,
)


class Email(Base, TimestampMixin):
    __tablename__ = "emails"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    gmail_message_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    from_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=EmailStatus.RECEIVED.value, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default=EmailPriority.MEDIUM.value, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_spam: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True
    )
    trust_score_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pipeline_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pipeline_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_headers: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    attachments = relationship("EmailAttachment", back_populates="email", cascade="all, delete-orphan")
    trust_score = relationship("TrustScore", back_populates="email", uselist=False)
    client = relationship("Client")


class EmailAttachment(Base, TimestampMixin):
    __tablename__ = "email_attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    email = relationship("Email", back_populates="attachments")
    extraction = relationship("DocumentExtraction", back_populates="attachment", uselist=False)
