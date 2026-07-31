# Inventory Intelligence System

Inventory Intelligence System is a full-stack inventory operations platform for multi-company workflows, currently centered around `BKR` and `JSPL`. It combines inventory management, warehouse control, dashboard analytics, reporting, company-aware context switching, and Amazon/POS-related operational flows in a single application.

## What it does

- Company-aware login and switching for shared deployments
- Dashboard KPIs for products, warehouses, stock, alerts, scheduler health, and daily activity
- Product, warehouse, and inventory management with adjustment and upload flows
- Inventory history and downloadable reporting workflows
- POS views for company-specific sales workflows
- Amazon integration and scheduled background jobs on the backend

## Tech stack

### Frontend

- React
- Vite
- Zustand
- TanStack React Query
- CSS Modules

### Backend

- FastAPI
- SQLAlchemy
- SQLite
- Pandas / OpenPyXL
- APScheduler

## Project structure

```text
.
├── backend/
│   ├── alembic/                 # Database migrations
│   ├── app/
│   │   ├── api/routers/         # Auth, companies, dashboard, inventory, POS, reports
│   │   ├── amazon/              # Amazon sync/auth/scheduler logic
│   │   ├── models/              # DB setup and ORM schema
│   │   ├── repositories/        # Config and lookup data access
│   │   ├── services/            # Inventory, reports, scheduler, Amazon services
│   │   └── plugins/             # Transformation and mapping plugins
│   ├── config/                  # Mapping/rules/lookups configuration
│   ├── lookup_tables/           # Excel lookup files used by backend flows
│   └── tests/                   # Backend tests
├── frontend/
│   ├── src/components/          # Shared UI building blocks
│   ├── src/pages/               # Overview, products, warehouses, inventory, reports, POS
│   ├── src/services/            # API clients
│   ├── src/stores/              # Zustand stores
│   └── src/hooks/               # React Query data hooks
└── README.md
```

## Main routes

- `/login`
- `/`
- `/products`
- `/warehouses`
- `/inventory`
- `/inventory-history`
- `/reports`
- `/download-centre`
- `/settings`
- `/pos`
- `/pos-history`

## Local setup

### Prerequisites

- Node.js 18+
- Python 3.10+ recommended
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Monu123a/Inventory-Intelligence-System-BKR-JSPL-.git
cd Inventory-Intelligence-System-BKR-JSPL-
```

### 2. Start the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/sync_schema.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

If you need Amazon Selling Partner integration, copy `backend/.env.example` to `.env` and fill in the required credentials before starting the server.

### 3. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite app runs on `http://localhost:5173` by default, and the FastAPI backend runs on `http://localhost:8000`.

## Database notes

- The backend defaults to a SQLite database file at `backend/inventory.db`.
- You can override it with `DATABASE_URL`.
- For schema initialization in local development, run `python scripts/sync_schema.py`.
- Alembic files are available in `backend/alembic/` for migration-based workflows.

## Backend API areas

- `auth`
- `companies`
- `dashboard`
- `products`
- `warehouses`
- `inventory`
- `reports`
- `pos`
- transformation upload/dry-run/download/config endpoints

## Testing and build

### Frontend

```bash
cd frontend
npm run build
```

### Backend

```bash
cd backend
pytest
```

## Notes

- This repository contains both the inventory platform and legacy transformation-related modules that are still used by some backend flows.
- Local cache files, SQLite databases, logs, uploads, and generated artifacts should stay out of version control.
