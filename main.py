from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import analysis_routes, export_routes, upload_routes
from services.csv_combiner import ensure_directories
from services.database_service import init_db

# Create the FastAPI application
app = FastAPI(
    title="Sri Lanka G.C.E. A/L Performance Analysis API",
    description=(
        "Analyzes G.C.E. Advanced Level performance reports (2020–2025) "
        "uploaded as official PDF reports or CSV files extracted from them."
    ),
    version="1.0.0",
)

# Enable CORS for the React frontend (Vite default port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(upload_routes.router)
app.include_router(analysis_routes.router)
app.include_router(export_routes.router)


@app.on_event("startup")
def on_startup():
    """Create folders and database tables when the server starts."""
    ensure_directories()
    init_db()


@app.get("/")
def root():
    """Health check and welcome message."""
    return {
        "message": "Sri Lanka G.C.E. A/L Performance Analysis API is running.",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    """Simple health check endpoint for monitoring."""
    return {"status": "ok"}
