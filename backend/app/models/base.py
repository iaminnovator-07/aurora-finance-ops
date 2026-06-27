"""Shared model mixins and enums."""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class EmailStatus(str, enum.Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    SPAM = "spam"
    DUPLICATE = "duplicate"


class EmailPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmailIntent(str, enum.Enum):
    INVOICE_SUBMISSION = "invoice_submission"
    TIMESHEET = "timesheet"
    RECEIPT = "receipt"
    INQUIRY = "inquiry"
    SPAM = "spam"
    UNKNOWN = "unknown"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    AUTO_APPROVED = "auto_approved"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"
    DISPATCHED = "dispatched"
    PAID = "paid"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUEST_REVIEW = "request_review"
    RESOLVED = "resolved"


class ApprovalQueueStatus(str, enum.Enum):
    NEEDS_REVIEW = "needs_review"
    WAITING_APPROVAL = "waiting_approval"
    REJECTED = "rejected"
    RESOLVED = "resolved"


class DispatchStatus(str, enum.Enum):
    PENDING = "pending"
    PREPARED = "prepared"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


class NotificationType(str, enum.Enum):
    INVOICE_GENERATED = "invoice_generated"
    INVOICE_APPROVED = "invoice_approved"
    INVOICE_REJECTED = "invoice_rejected"
    FRAUD_DETECTED = "fraud_detected"
    DISPATCH_COMPLETED = "dispatch_completed"
    APPROVAL_REQUIRED = "approval_required"
    PROCESSING_COMPLETE = "processing_complete"
    SYSTEM = "system"


class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    ACTIVE = "active"
    THINKING = "thinking"
    ERROR = "error"


class RuleSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DocumentType(str, enum.Enum):
    PDF = "pdf"
    EXCEL = "excel"
    WORD = "word"
    IMAGE = "image"
    HANDWRITING = "handwriting"
    UNKNOWN = "unknown"
