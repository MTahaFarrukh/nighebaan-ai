"""FastAPI entrypoint for Nigehbaan AI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analyze, dashboard, files, health, whatsapp
from app.upload_limit import UploadLimitMiddleware

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(UploadLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(analyze.router, prefix=settings.api_prefix)
app.include_router(files.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(whatsapp.router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    """Root welcome payload."""
    return {"message": f"{settings.app_name} API", "docs": "/docs"}
