"""
FastAPI Application Entrypoint for Offline Agri-Input Shop ERP.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.api import api_router
from src.db.connection import get_db_manager

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database tables and default seeds are initialized on start."""
    db = get_db_manager()
    db.initialize_database(include_seed=True)
    yield


app = FastAPI(
    title="Krishi Agri-Input Shop ERP",
    description="Offline Billing & Inventory Management for Fertilizers, Seeds, and Pesticides",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files & templates
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API routes
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
def index_view(request: Request):
    """Render the single-page desktop billing & ERP dashboard."""
    return templates.TemplateResponse(request=request, name="index.html")
