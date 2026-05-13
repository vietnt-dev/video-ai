"""
AutoShorts FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.routers import video
from app.routers import youtube

app = FastAPI(
    title="AutoShorts API",
    description="AI-powered short video generator for TikTok, Reels & YouTube Shorts",
    version="1.0.0",
)

# CORS - cho phép Next.js frontend kết nối
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files để serve video output
Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=settings.output_dir), name="outputs")

# Routers
app.include_router(video.router)
app.include_router(youtube.router)


@app.get("/")
async def root():
    return {
        "name": "AutoShorts API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
