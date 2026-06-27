import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import DocumentType, TimestampMixin, new_uuid


class DocumentExtraction(Base, TimestampMixin):
    __tablename__ = "document_extractions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    attachment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_attachments.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(50), default=DocumentType.UNKNOWN.value)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    normalized_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    field_confidences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    classification: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ocr_engine: Mapped[str | None] = mapped_column(String(50), nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    attachment = relationship("EmailAttachment", back_populates="extraction")


class TrustScore(Base, TimestampMixin):
    __tablename__ = "trust_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True
    )
    identity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    content_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    domain_trust_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    vendor_reputation_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duplicate_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    checks: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reasoning_timeline: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    spf_result: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dkim_result: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dmarc_result: Mapped[str | None] = mapped_column(String(50), nullable=True)

    email = relationship("Email", back_populates="trust_score")
    client = relationship("Client")


class VendorProfile(Base, TimestampMixin):
    __tablename__ = "vendor_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    reputation_score: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    total_invoices: Mapped[int] = mapped_column(default=0, nullable=False)
    total_spend: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fraud_incidents: Mapped[int] = mapped_column(default=0, nullable=False)
    disputes: Mapped[int] = mapped_column(default=0, nullable=False)
    avg_dpo_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    verified_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trust_history: Mapped[list | None] = mapped_column(JSON, nullable=True)
    bank_accounts: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    client = relationship("Client", back_populates="vendor_profile")
