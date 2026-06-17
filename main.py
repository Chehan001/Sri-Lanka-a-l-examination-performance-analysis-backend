import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import analysis_routes, export_routes, upload_routes
from services.csv_combiner import ensure_directories
from services.database_service import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs when the server starts.
    Creates required folders and database tables.
    """
    ensure_directories()
    init_db()
    yield


# Create the FastAPI application
app = FastAPI(
    title="Sri Lanka G.C.E. A/L Performance Analysis API",
    description=(
        "Analyzes G.C.E. Advanced Level performance reports (2020–2025) "
        "uploaded as official PDF reports or CSV files extracted from them."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# Frontend URLs allowed to call this backend
# Add your real Vercel frontend URL in Render environment variable FRONTEND_URL
FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip().rstrip("/")

allowed_origins = [
    "http://localhost:5173",      # Vite local frontend
    "http://localhost:3000",      # Next.js/React local frontend
]

if FRONTEND_URL:
    allowed_origins.append(FRONTEND_URL)


# Enable CORS for local frontend + Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register route modules
app.include_router(upload_routes.router)
app.include_router(analysis_routes.router)
app.include_router(export_routes.router)


@app.get("/")
def root():
    """Health check and welcome message."""
    return {
        "message": "Sri Lanka G.C.E. A/L Performance Analysis API is running.",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
        "allowed_origins": allowed_origins,
    }


@app.get("/health")
def health_check():
    """Simple health check endpoint for monitoring."""
    return {"status": "ok"}