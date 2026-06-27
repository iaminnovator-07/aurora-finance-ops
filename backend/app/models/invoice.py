import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Float, ForeignKey, Numeric, String, Text
from sqlalchemy import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import InvoiceStatus, TimestampMixin, new_uuid


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emails.id"), nullable=True
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True
    )
    extraction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_extractions.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default=InvoiceStatus.DRAFT.value, nullable=False)
    vendor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    po_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    line_items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extracted_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    field_confidences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pdf_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pdf_storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    processing_history: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rules_passed: Mapped[bool | None] = mapped_column(nullable=True)
    rules_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    client = relationship("Client", back_populates="invoices")
    erp_exports = relationship("ERPExport", back_populates="invoice")
    approval_queue = relationship("ApprovalQueue", back_populates="invoice", uselist=False)
    dispatches = relationship("DispatchRecord", back_populates="invoice")


class ERPExport(Base, TimestampMixin):
    __tablename__ = "erp_exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    format: Mapped[str] = mapped_column(String(50), default="sap_excel", nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    row_count: Mapped[int] = mapped_column(default=0, nullable=False)
    mapping_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    exported_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="generated", nullable=False)
    exported_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    invoice = relationship("Invoice", back_populates="erp_exports")
