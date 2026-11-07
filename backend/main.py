import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import works, chapters, terms, translate, scrape

# Load .env from the project root (two levels up from this file).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

app = FastAPI(title="DeepSeek Translator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(works.router)
app.include_router(chapters.router)
app.include_router(terms.router)
app.include_router(translate.router)
app.include_router(scrape.router)


@app.get("/api/health")
def health():
    return {"ok": True }


@app.get("/api/health")
def health():
    return {"ok": True}
