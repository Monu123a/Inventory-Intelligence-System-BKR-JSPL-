# Project Knowledge & Rules

## 1. Environment & Architecture
- **Frontend**: React (Vite) hosted on Vercel. 
  - Runs locally on port `5174` (strictly enforced in `vite.config.js`).
  - Expects `VITE_API_URL` to point to the backend.
- **Backend**: Python (FastAPI) hosted on Render.
  - Connects to a cloud PostgreSQL database (Render).
  - Expects `DATABASE_URL` (starting with `postgresql://`).
  - Uses `ALLOWED_ORIGINS` for CORS configuration.
- **Database**: Local development uses SQLite (`backend/inventory.db`). Production uses PostgreSQL.

## 2. Core Business Logic & Data Rules
- **SKU Normalization**: ALL SKUs in the BKR and JSPL catalogs MUST be strictly normalized to their first 6 characters (e.g., `LG1111-2` becomes `LG1111`). This rule is critical and irreversible.
- **Inventory Aggregation**: When bulk importing inventory, if multiple source SKUs merge into the exact same 6-character normalized SKU within the *same warehouse*, the inventory quantity is determined by taking the `min()` quantity, NOT the sum.
- **Multi-Tenancy**: The application supports multiple companies. 
  - The frontend uses `X-Company-Id` headers.
  - Active companies: JSPL (ID: 3), BKR (ID: 2).
  - Test Co (ID: 1) is strictly deactivated. The UI `CompanySelector` defaults to JSPL (ID: 3).

## 3. Remote Server Manipulation
- To push bulk data updates to production (Render) in the future, create a python script using SQLAlchemy and supply the Render "External Database URL". 
- An example template exists at `backend/scratch/migrate_to_postgres.py`.

## 4. Admin Credentials
- **Username**: `test_admin`
- **Password**: `admin123`
