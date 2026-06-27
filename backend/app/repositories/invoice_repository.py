from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invoice import ERPExport, Invoice
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Invoice)

    async def get_by_number(self, invoice_number: str) -> Invoice | None:
        result = await self.session.execute(
            select(Invoice).where(Invoice.invoice_number == invoice_number)
        )
        return result.scalar_one_or_none()

    async def get_with_details(self, invoice_id: UUID) -> Invoice | None:
        result = await self.session.execute(
            select(Invoice)
            .options(
                selectinload(Invoice.client),
                selectinload(Invoice.approval_queue),
                selectinload(Invoice.erp_exports),
                selectinload(Invoice.dispatches),
            )
            .where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def list_invoices(
        self,
        *,
        status: str | None = None,
        search: str | None = None,
        min_amount: Decimal | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Invoice], int]:
        query = select(Invoice)
        count_query = select(func.count()).select_from(Invoice)

        if status:
            query = query.where(Invoice.status == status)
            count_query = count_query.where(Invoice.status == status)
        if search:
            pattern = f"%{search}%"
            filt = (Invoice.invoice_number.ilike(pattern)) | (Invoice.vendor_name.ilike(pattern))
            query = query.where(filt)
            count_query = count_query.where(filt)
        if min_amount is not None:
            query = query.where(Invoice.total_amount >= min_amount)
            count_query = count_query.where(Invoice.total_amount >= min_amount)

        query = query.order_by(Invoice.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        count_result = await self.session.execute(count_query)
        return list(result.scalars().all()), count_result.scalar_one()

    async def get_next_sequence(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Invoice))
        return result.scalar_one() + 2381

    async def find_similar_invoices(
        self, vendor_name: str | None, total_amount: Decimal | None, days: int = 90
    ) -> list[Invoice]:
        query = select(Invoice)
        if vendor_name:
            query = query.where(Invoice.vendor_name.ilike(f"%{vendor_name}%"))
        if total_amount:
            tolerance = total_amount * Decimal("0.01")
            query = query.where(
                Invoice.total_amount.between(total_amount - tolerance, total_amount + tolerance)
            )
        result = await self.session.execute(query.limit(20))
        return list(result.scalars().all())


class ERPExportRepository(BaseRepository[ERPExport]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ERPExport)

    async def get_by_invoice(self, invoice_id: UUID) -> list[ERPExport]:
        result = await self.session.execute(
            select(ERPExport).where(ERPExport.invoice_id == invoice_id)
        )
        return list(result.scalars().all())
