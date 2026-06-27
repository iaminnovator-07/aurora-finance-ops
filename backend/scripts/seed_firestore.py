"""Seed Firestore collections directly (use when DATABASE_BACKEND=firestore)."""

import asyncio
import os

# Must set before firebase import
os.environ.setdefault("DATABASE_BACKEND", "firestore")

from app.config import get_settings
from app.core.firestore_store import store
from app.core.security import hash_password


VENDORS = [
    {"name": "Acme Logistics", "domain": "acme-logistics.com", "email": "billing@acme-logistics.com", "trust": 94},
    {"name": "Globex Materials", "domain": "globex.com", "email": "ar@globex.com", "trust": 78},
    {"name": "Initech Cloud", "domain": "initech.cloud", "email": "no-reply@initech.cloud", "trust": 99},
]


async def seed_firestore() -> None:
    settings = get_settings()
    if settings.firestore_emulator_host:
        os.environ["FIRESTORE_EMULATOR_HOST"] = settings.firestore_emulator_host

    users = store("users")
    clients = store("clients")
    rules = store("business_rules")

    existing = await users.query("email", "==", "anya@yourcompany.com", limit=1)
    if existing:
        print("Firestore already seeded")
        return

    user = await users.create({
        "email": "anya@yourcompany.com",
        "hashed_password": hash_password("aurora123"),
        "full_name": "Anya K.",
        "role": "admin",
        "is_active": True,
        "is_superuser": True,
    })
    print(f"Created user: {user['id']}")

    for v in VENDORS:
        c = await clients.create({
            "name": v["name"],
            "domain": v["domain"],
            "email": v["email"],
            "is_active": True,
            "budget_limit": 500000,
        })
        await store("vendor_profiles").create({
            "client_id": c["id"],
            "reputation_score": float(v["trust"]),
            "is_verified": v["trust"] >= 80,
            "risk_level": "low" if v["trust"] >= 80 else "medium",
        })

    for rule in [
        {"name": "Auto-approve under $1,000", "condition_expression": "amount < 1000", "action": "approve", "is_active": True},
        {"name": "Flag duplicate within 30d", "condition_expression": "similar > 0.95", "action": "queue", "is_active": True},
    ]:
        await rules.create({**rule, "category": "general", "priority": 0})

    print("Firestore seed complete")


if __name__ == "__main__":
    asyncio.run(seed_firestore())
