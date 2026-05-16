"""
Surgical Video AI - API Backend
Sistema de detecção de sangramento e instrumentos em cirurgias ginecológicas
FIAP Tech Challenge - Fase 4
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.routers import video, info, samples, annotation

app = FastAPI(
    title="Surgical Video AI",
    description="Sistema de detecção de sangramento e instrumentos em cirurgias ginecológicas",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(video.router, prefix="/api/video", tags=["video"])
app.include_router(info.router, prefix="/api/info", tags=["info"])
app.include_router(samples.router, prefix="/api/samples", tags=["samples"])
app.include_router(annotation.router, prefix="/api/annotation", tags=["annotation"])

# Static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def root():
    """Serve the main page."""
    return FileResponse(str(static_path / "index.html"))


@app.get("/annotation")
async def annotation_page():
    """Serve the annotation interface page."""
    return FileResponse(str(static_path / "annotation.html"))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Surgical Video AI",
        "version": "1.0.0"
    }
