# Smart Question Bank (স্মার্ট কোয়েশ্চন ব্যাংক)

A source-grounded, Bengali-first BCS exam preparation platform built with **Next.js (App Router + TypeScript + Tailwind CSS)**, **FastAPI**, **PostgreSQL**, **Qdrant**, and **Celery + Redis**.

## Non-Negotiable Core Principles
1. Never claim or imply that any question will appear in a real BCS exam.
2. Never fabricate facts, authors, dates, citations, or page numbers.
3. Questions are generated strictly from retrieved `document_chunks` (RAG), never model memory.
4. Separate `SOURCE_GROUNDED` facts from `AI_INFERENCE`.
5. Students only see questions marked `APPROVED` by a human reviewer.
6. Keep **AI Question-Quality Accuracy** strictly separate from **Student Exam Accuracy**.

---

## Phase 1 Scope (Completed)
- Monorepo structure (`apps/web`, `apps/api`, `infra/`)
- Docker Compose (`postgres:16`, `redis:7`, `qdrant`, `api`, `worker`, `web`)
- Alembic migration (`0001_initial_schema.py`) creating all 21 normalized tables + constraints + indexes + role seeds
- Argon2 password hashing (`argon2-cffi`) + JWT access & rotating refresh tokens (`PyJWT`) + audit logging
- RBAC (`ADMIN`, `REVIEWER`, `STUDENT`) enforced on every protected endpoint
- Bengali-first Next.js shell (`Noto Sans Bengali`, `bn`/`en` toggle, loading/empty/error states, login/register, role-gated dashboards, Admin user management)
- Automated pytest suite for auth and RBAC (`apps/api/tests/`)

---

## Running Locally with Docker Compose

### 1. Configure Environment
```bash
cd smart-question-bank
cp .env.example .env
```
Edit `.env` and set strong random values for:
- `POSTGRES_PASSWORD` (and matching `DATABASE_URL`)
- `JWT_SECRET_KEY` (32+ chars)
- `JWT_REFRESH_SECRET_KEY` (different 32+ chars)
- Optional initial Admin bootstrap:
  `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD`, `INITIAL_ADMIN_NAME`

### 2. Build and Start All Services
```bash
docker compose up --build -d
```
The API container automatically runs `alembic upgrade head` and `python -m app.db.seed` before starting Uvicorn.

### 3. Access the Services
- **Frontend (Next.js):** http://localhost:3000
- **Backend API (FastAPI Swagger):** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/v1/health
- **Qdrant Dashboard:** http://localhost:6333/dashboard

---

## Running Tests

### Backend Auth & RBAC Tests (inside Docker)
```bash
docker compose exec api pytest -v
```

### Backend Tests (local Python 3.12 virtualenv without Docker)
```bash
cd smart-question-bank/apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

### Frontend Typecheck & Lint (inside Docker or local Node 22)
```bash
docker compose exec web npm run typecheck
docker compose exec web npm run lint
```

---

## Useful Docker Commands
```bash
# View logs
docker compose logs -f api worker web

# Run Alembic migration manually
docker compose exec api alembic upgrade head

# Verify Celery worker ping
docker compose exec api python -c "from app.workers.celery_app import ping; print(ping.delay().get(timeout=5))"

# Stop all containers
docker compose down
```
