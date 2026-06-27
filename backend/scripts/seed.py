"""Database seed script for demo and development."""

import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import hash_password
from app.models.approval import BusinessRule
from app.models.client import Client, ClientContact
from app.models.document import VendorProfile
from app.models.user import User

VENDORS = [
    {
        "name": "Acme Logistics",
        "legal_name": "Acme Logistics Ltd.",
        "domain": "acme-logistics.com",
        "email": "billing@acme-logistics.com",
        "phone": "+1 (510) 555-2381",
        "city": "Oakland",
        "country": "USA",
        "address": "1820 Harbor Blvd, Oakland CA 94607",
        "budget_limit": 500000,
        "trust": 94,
        "invoices": 124,
        "spend": 1240000,
    },
    {
        "name": "Globex Materials",
        "domain": "globex.com",
        "email": "ar@globex.com",
        "city": "Chicago",
        "country": "USA",
        "budget_limit": 300000,
        "trust": 78,
        "invoices": 98,
        "spend": 842000,
    },
    {
        "name": "Initech Cloud",
        "domain": "initech.cloud",
        "email": "no-reply@initech.cloud",
        "city": "Austin",
        "country": "USA",
        "budget_limit": 100000,
        "trust": 99,
        "invoices": 76,
        "spend": 210000,
    },
    {
        "name": "Hooli Services",
        "domain": "hooli.com",
        "email": "ap@hooli.com",
        "city": "Palo Alto",
        "country": "USA",
        "budget_limit": 400000,
        "trust": 91,
        "invoices": 64,
        "spend": 540000,
    },
    {
        "name": "Soylent Ind.",
        "domain": "soylent.industries",
        "email": "billing@soylent.industries",
        "city": "Los Angeles",
        "country": "USA",
        "budget_limit": 200000,
        "trust": 86,
        "invoices": 41,
        "spend": 320000,
    },
    {
        "name": "Unknown Vendor",
        "domain": "unknown-vendor.biz",
        "email": "finance@unknown-vendor.biz",
        "city": "Unknown",
        "country": "Unknown",
        "budget_limit": 10000,
        "trust": 38,
        "invoices": 3,
        "spend": 8000,
    },
]

BUSINESS_RULES = [
    {
        "name": "Auto-approve under $1,000",
        "condition_expression": "amount < 1000 AND vendor.trust > 85",
        "action": "approve + push ERP",
        "category": "auto_approval",
        "is_active": True,
    },
    {
        "name": "Flag duplicate within 30d",
        "condition_expression": "similar(invoice) > 0.95",
        "action": "queue: needs_review",
        "category": "duplicate",
        "is_active": True,
    },
    {
        "name": "Reject unknown domain + urgent keywords",
        "condition_expression": "vendor.unknown AND subject matches /urgent|wire/i",
        "action": "reject + alert security",
        "category": "fraud",
        "is_active": True,
    },
    {
        "name": "Multi-level approval > $10k",
        "condition_expression": "amount > 10000",
        "action": "request approval: manager → CFO",
        "category": "approval",
        "is_active": True,
    },
    {
        "name": "Hold if PO mismatch",
        "condition_expression": "po.amount != invoice.amount",
        "action": "queue: waiting_approval",
        "category": "po",
        "is_active": False,
    },
]


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        if (await session.execute(select(User).limit(1))).scalar_one_or_none():
            print("Database already seeded, syncing demo emails...")
            from app.services.gmail_service import GmailService

            result = await GmailService(session).sync_emails()
            await session.commit()
            print(f"Gmail sync: {result}")
            return

        admin = User(
            email="anya@yourcompany.com",
            hashed_password=hash_password("aurora123"),
            full_name="Anya K.",
            role="admin",
            is_superuser=True,
        )
        session.add(admin)

        for v in VENDORS:
            client = Client(
                name=v["name"],
                legal_name=v.get("legal_name", v["name"]),
                domain=v["domain"],
                email=v["email"],
                phone=v.get("phone"),
                city=v.get("city"),
                country=v.get("country"),
                address=v.get("address"),
                budget_limit=v.get("budget_limit"),
                is_active=v["name"] != "Unknown Vendor",
            )
            session.add(client)
            await session.flush()

            session.add(
                ClientContact(
                    client_id=client.id,
                    name=f"Billing, {v['name']}",
                    email=v["email"],
                    is_primary=True,
                )
            )
            session.add(
                VendorProfile(
                    client_id=client.id,
                    reputation_score=float(v["trust"]),
                    total_invoices=v["invoices"],
                    total_spend=float(v["spend"]),
                    is_verified=v["trust"] >= 80,
                    risk_level="low" if v["trust"] >= 80 else "medium" if v["trust"] >= 60 else "high",
                    trust_history=[{"month": i, "score": v["trust"] + (i % 3) - 1} for i in range(12)],
                )
            )

        for rule in BUSINESS_RULES:
            session.add(BusinessRule(**rule))

        await session.commit()
        print("Seeded users, vendors, and business rules")

        from app.services.gmail_service import GmailService

        result = await GmailService(session).sync_emails()
        await session.commit()
        print(f"Demo emails synced: {result}")


if __name__ == "__main__":
    asyncio.run(seed())
