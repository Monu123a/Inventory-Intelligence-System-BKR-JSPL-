from app.api.dependencies import get_current_user
from fastapi import Depends, APIRouter
from app.models.schema import User

import json
import logging
import os
import shutil
import time
from datetime import datetime
from typing import List

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

from app.models.context import ExecutionContext, LogLevel, TransformationWarning
from app.repositories.config_repository import ConfigRepository
from app.repositories.lookup_repository import LookupRepository
from app.engines.transformation import TransformationEngine
from app.engines.validation import ValidationEngine
from app.plugins.plugin_registry import PluginRegistry
from app.services.transformation_service import TransformationService

# New routers
from app.api.routers.products import router as products_router
from app.api.routers.warehouses import router as warehouses_router
from app.api.routers.inventory import router as inventory_router
from app.api.routers.dashboard import router as dashboard_router
from app.api.routers.reports import router as reports_router
from app.api.routers.companies import router as companies_router
from app.api.routers.auth import router as auth_router
from app.api.routers.pos import router as pos_router
from app.api.routers.company_settings import router as company_settings_router
from app.api.routers.replenishment import router as replenishment_router
from app.api.routers.transfers import router as transfers_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("amazon_logic_transformer")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
CONFIG_DIR = os.path.join(BASE_DIR, "config")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
LOOKUP_DIR = os.path.join(BASE_DIR, "lookup_tables")

for d in (UPLOAD_DIR, OUTPUT_DIR, LOGS_DIR):
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------------------
# Repositories & engines
# ---------------------------------------------------------------------------
config_repo = ConfigRepository(config_dir=CONFIG_DIR)
lookup_repo = LookupRepository(base_dir=LOOKUP_DIR)
plugin_registry = PluginRegistry()
transformation_engine = TransformationEngine(registry=plugin_registry)
validation_engine = ValidationEngine()

transformation_service = TransformationService(
    transformation_engine=transformation_engine,
    validation_engine=validation_engine,
    config_repo=config_repo,
    output_dir=OUTPUT_DIR,
    logs_dir=LOGS_DIR,
)

from app.services.scheduler_service import start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Amazon Logic Transformer...")
    start_scheduler()
    yield
    # Shutdown
    logger.info("Shutting down Amazon Logic Transformer...")
    shutdown_scheduler()

# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(title="Amazon Logic Transformer", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "https://halte-data-transformation.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Inventory Management Routers
app.include_router(companies_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(warehouses_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(pos_router, prefix="/api")
app.include_router(company_settings_router, prefix="/api")
app.include_router(replenishment_router, prefix="/api")
app.include_router(transfers_router, prefix="/api")


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------
class UploadResponse(BaseModel):
    files: list
    message: str


class StatsResponse(BaseModel):
    rows_read: int = 0
    rows_processed: int = 0
    rows_removed: int = 0
    rows_failed: int = 0
    duplicate_invoices: int = 0
    missing_gst: int = 0
    missing_account_code: int = 0
    execution_time_ms: float = 0.0


class TransformResponse(BaseModel):
    output_filename: str = ""
    audit_filename: str = ""
    requirement_filename: str = ""
    duplicate_filename: str = ""
    stats: StatsResponse
    warnings: list
    message: str = ""


class DryRunResponse(BaseModel):
    preview_data: list
    preview_columns: list
    stats: StatsResponse
    warnings: list


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_context() -> ExecutionContext:
    mapping = config_repo.load_mapping()
    rules = config_repo.load_rules()
    lookups_cfg = config_repo.load_lookups_config()

    # Load Excel lookup tables
    loaded_lookups = {}
    for key, path in lookups_cfg.items():
        full_path = os.path.join(LOOKUP_DIR, path)
        if os.path.exists(full_path):
            try:
                if key == "account_lookup":
                    df = pd.read_excel(full_path, header=2)
                else:
                    df = pd.read_excel(full_path)
                # Clean column names
                df.columns = df.columns.str.strip()
                # Drop fully-empty rows
                df = df.dropna(how="all")
                loaded_lookups[key] = df
                logger.info("Loaded lookup '%s' with %d rows.", key, len(df))
            except Exception as exc:
                logger.error("Failed to load lookup %s: %s", path, exc)

    return ExecutionContext(mapping=mapping, rules=rules, lookups=loaded_lookups)


def _read_uploaded_files(filenames: List[str]) -> pd.DataFrame:
    frames = []
    for fname in filenames:
        safe_name = os.path.basename(fname)
        path = os.path.join(UPLOAD_DIR, safe_name)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"File not found: {safe_name}")
        df = pd.read_excel(path)
        frames.append(df)
    if not frames:
        raise HTTPException(status_code=400, detail="No files to process.")
    return pd.concat(frames, ignore_index=True)





# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

legacy_router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Amazon Logic Transformer is running."}


@legacy_router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload one or more Excel files."""
    uploaded = []
    for f in files:
        if not f.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {f.filename}")
        dest = os.path.join(UPLOAD_DIR, os.path.basename(f.filename))
        with open(dest, "wb") as out:
            content = await f.read()
            out.write(content)
        uploaded.append({"name": f.filename, "size": len(content)})
        logger.info("Uploaded: %s (%d bytes)", f.filename, len(content))
    return UploadResponse(files=uploaded, message=f"{len(uploaded)} file(s) uploaded.")


@legacy_router.post("/transform")
async def transform(body: dict):
    """Run the full transformation pipeline and generate the output Excel."""
    filenames = body.get("filenames", [])
    if not filenames:
        raise HTTPException(status_code=400, detail="No filenames provided.")

    context = _build_context()
    context.current_data = _read_uploaded_files(filenames)

    # Run pipeline via service
    output_filename, audit_filename, result_dict = transformation_service.process(context, filenames)

    return TransformResponse(**result_dict)


@legacy_router.post("/dry-run")
async def dry_run(body: dict):
    """Run the pipeline without saving – return preview and stats."""
    filenames = body.get("filenames", [])
    if not filenames:
        raise HTTPException(status_code=400, detail="No filenames provided.")

    context = _build_context()
    context.current_data = _read_uploaded_files(filenames)

    transformation_engine.execute_pipeline(context)
    validation_engine.validate(context)

    preview = []
    columns = []
    if context.current_data is not None and not context.current_data.empty:
        preview_df = context.current_data.head(25).fillna("")
        columns = preview_df.columns.tolist()
        preview = preview_df.astype(str).values.tolist()

    return DryRunResponse(
        preview_data=preview,
        preview_columns=columns,
        stats=StatsResponse(**context.statistics.model_dump()),
        warnings=[w.model_dump() for w in context.warnings],
    )


@legacy_router.get("/download/{filename}")
async def download_file(filename: str):
    """Download a generated output file."""
    safe_filename = os.path.basename(filename)
    path = os.path.join(OUTPUT_DIR, safe_filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(
        path=path,
        filename=safe_filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@legacy_router.get("/config")
async def get_config():
    """Return the current configuration (mapping + rules + lookups)."""
    return {
        "mapping": config_repo.load_mapping(),
        "rules": config_repo.load_rules(),
        "lookups": config_repo.load_lookups_config(),
    }


@legacy_router.put("/config")
async def update_config(body: dict):
    """Update configuration files."""
    if "mapping" in body:
        config_repo.save_mapping(body["mapping"])
    if "rules" in body:
        config_repo.save_rules(body["rules"])
    if "lookups" in body:
        config_repo.save_lookups_config(body["lookups"])
    return {"status": "ok", "message": "Configuration updated."}


@legacy_router.get("/uploaded-files")
async def list_uploaded_files():
    """List files currently in the uploads directory."""
    files = []
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            fp = os.path.join(UPLOAD_DIR, f)
            if os.path.isfile(fp):
                files.append({"name": f, "size": os.path.getsize(fp)})
    return {"files": files}


@legacy_router.delete("/reset")
async def reset():
    """Clear uploads and outputs."""
    for d in (UPLOAD_DIR, OUTPUT_DIR):
        if os.path.exists(d):
            shutil.rmtree(d)
            os.makedirs(d)
    return {"status": "ok", "message": "All uploads and outputs cleared."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
app.include_router(legacy_router)
