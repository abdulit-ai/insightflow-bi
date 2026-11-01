# InsightFlow BI — Sales Intelligence Dashboard

A portfolio-ready, full-stack business intelligence MVP. Upload CSV sales data, normalize it into relational tables, explore revenue KPIs, and filter interactive charts.

## Features
- React + Recharts responsive dashboard; date, region, and category filters
- FastAPI backend with documented REST API at `/docs`
- SQLAlchemy models for customers, products, sales; PostgreSQL via Docker or SQLite for local development
- CSV validation, transaction rollback on invalid input, idempotent re-imports by `order_id`
- Synthetic sample dataset; no real customer information
- Pytest API tests

## Quick start: Docker (recommended)
1. Install Docker Desktop / Docker Engine with Compose.
2. In the project root run `docker compose up --build`.
3. Open http://localhost:5173 and click **Load sample data**.
4. API documentation: http://localhost:8000/docs .
5. Stop with `docker compose down` (add `-v` to delete database data).

## Quick start: without Docker
Requires Python 3.11+ and Node.js 20+.

Terminal 1:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
SQLite is used automatically when `DATABASE_URL` is unset. The DB file is created in `backend/`.

Terminal 2:
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173; click **Load sample data**.

## Run tests
```bash
cd backend
python -m pytest -q
```

## CSV contract
Required headers: `order_id,order_date,customer,segment,region,product,category,quantity,unit_price`.
`order_date` uses ISO `YYYY-MM-DD`; `quantity` is a positive integer; `unit_price` is nonnegative decimal. Each CSV row is one order line, not necessarily one complete multi-line customer order. `order_id` is therefore a unique **line ID** in this MVP. Repeated IDs are skipped on reimport; duplicates inside a single file are rejected. 3 MB / 10,000 row upload limit. Amounts are displayed in NGN for demonstration; currency conversion is not implemented.

## API
- `GET /api/health` — health check
- `POST /api/seed` — idempotently load synthetic sample CSV
- `POST /api/import` — multipart CSV upload, `file` field
- `GET /api/dashboard?start=2026-01-01&end=2026-12-31&region=North&category=Electronics` — KPIs and chart series

Revenue = SUM(quantity × unit_price). Average order value is actually average **order-line value** in this MVP. Customer count is distinct normalized customer records; customers with same name/segment/region are merged. No tax, discounts, returns, currency conversion, or forecasting are modeled.

## Architecture
```text
CSV → FastAPI validation → SQLAlchemy → PostgreSQL / SQLite
                                   ↓
React + Recharts ← JSON dashboard aggregation ← FastAPI
```

See `schema.sql` for PostgreSQL DDL and `docs/PROJECT_PLAN.md` for implementation notes.

## Security and production notes
This is a **portfolio demonstration**, not a production multi-tenant system. Import and seed endpoints are intentionally unauthenticated. Do not expose them publicly without authentication, authorization, rate limits, and audit logging. Add migrations (Alembic), pagination/streaming imports, server-side SQL aggregates, monitoring, and CI/CD before production use. Configure CORS and credentials for your own deployment. Never upload sensitive data.

## Portfolio case study
Problem: Small teams need clear, repeatable sales metrics. Solution: A full-stack CSV-to-dashboard pipeline with relational modeling and interactive filters. Evidence: automated API tests, seeded dataset, documented schema, and screenshots you can take after running locally. Add measured performance and deployment URL only after verification.
