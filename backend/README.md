# Aurora TIA Backend

Enterprise-grade FastAPI backend for the Touchless Invoice Agent platform.

## Architecture

```
backend/
├── app/
│   ├── config/          # Environment settings (Pydantic Settings)
│   ├── core/            # Database, security, DI, exceptions
│   ├── models/          # SQLAlchemy ORM (18 tables)
│   ├── schemas/         # Pydantic V2 request/response models
│   ├── repositories/    # Data access layer
│   ├── services/        # Business logic + AI orchestration
│   ├── controllers/     # HTTP → service translation
│   ├── routes/          # FastAPI route definitions
│   ├── workers/         # Celery background tasks
│   ├── middleware/      # Request logging
│   └── utils/           # Email auth, helpers
├── alembic/             # Database migrations
├── tests/               # Unit + integration tests
├── scripts/seed.py      # Demo data seeder
├── docker-compose.yml   # Full stack deployment
└── requirements.txt
```

## Quick Start

### Docker (recommended)

```bash
cd backend
cp .env.example .env
# Optional: set GEMINI_API_KEY in .env

docker compose up -d
docker compose exec api python scripts/seed.py
```

API: http://localhost:8000/docs

### Local Development

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env

# Start PostgreSQL + Redis (or use Docker for just infra)
docker compose up postgres redis -d

python scripts/seed.py
uvicorn app.main:app --reload --port 8000

# Celery worker (separate terminal)
celery -A app.workers.celery_app worker -Q pipeline,mail,analytics -l info
```

### Default Login

- Email: `anya@yourcompany.com`
- Password: `aurora123`

## API Modules

| Module | Endpoints |
|--------|-----------|
| Auth | `/api/v1/auth/login`, `/register`, `/refresh` |
| Inbox | `/api/v1/emails`, `/sync`, `/process` |
| Trust | `/api/v1/trust/check` |
| Documents | `/api/v1/documents/upload`, `/extract`, `/classify`, `/normalize` |
| Rules | `/api/v1/rules/validate` |
| ERP | `/api/v1/erp/export`, `/download/{id}` |
| Invoice | `/api/v1/invoice/create`, `GET /invoice`, `/{id}` |
| Approval | `/api/v1/approvals`, `/approve`, `/reject` |
| Dispatch | `/api/v1/dispatch/email`, `/send` |
| Analytics | `/api/v1/analytics/dashboard`, `/monthly`, `/roi` |
| Copilot | `/api/v1/copilot/chat` |
| Agents | `/api/v1/agents/status` |
| Clients | `/api/v1/clients` |
| Exceptions | `/api/v1/exceptions` |

## Pipeline

Email sync → Mail Intelligence → Trust Engine → OCR → Rule Engine →
(confidence ≥ 90?) → ERP Export → Invoice → Dispatch → Analytics
(else) → Approval Queue → Human Review

All AI/OCR operations run via Celery workers.

## Environment Variables

See `.env.example` for full list. Key variables:

- `GEMINI_API_KEY` — Enables Gemini 2.5 Flash for AI features
- `GMAIL_TOKEN_PATH` — Gmail OAuth token for live email sync
- `DATABASE_URL` — PostgreSQL connection string
- `CELERY_BROKER_URL` — Redis for background jobs

## Frontend Integration

The React frontend connects via Vite proxy (`/api/v1` → `http://localhost:8000`).

```bash
# Terminal 1 — Backend
cd backend && docker compose up -d
docker compose exec api python scripts/seed.py
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Celery worker
celery -A app.workers.celery_app worker -Q pipeline,mail,analytics -l info

# Terminal 3 — Frontend
cp .env.example .env
npm install
npm run dev
```

Frontend auto-authenticates as `anya@yourcompany.com` / `aurora123` on first load.

## Firebase / Firestore Database

Set `DATABASE_BACKEND=firestore` and configure Firebase:

```bash
# backend/.env
DATABASE_BACKEND=firestore
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=./credentials/firebase-service-account.json
```

**Dual-write mode (recommended for migration):** Keep `DATABASE_BACKEND=postgresql` and set `FIREBASE_PROJECT_ID`. All SQL writes automatically mirror to Firestore collections.

**Firestore-only seed:**
```bash
python scripts/seed_firestore.py
```

**Frontend Firebase (optional realtime):** Set `VITE_FIREBASE_*` in root `.env.example`.

Collections: `users`, `emails`, `invoices`, `clients`, `trust_scores`, `approval_queue`, etc.

## Testing

```bash
pytest tests/ -v
```

## Production Notes

- Change `JWT_SECRET_KEY` before deployment
- Use Alembic migrations instead of `create_all` in production
- Configure Supabase storage via `STORAGE_BACKEND=supabase`
- Set `ENVIRONMENT=production` to enable real SMTP dispatch
