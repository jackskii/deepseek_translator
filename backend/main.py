from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from .routers import works, chapters, terms, translate

# Load .env from the project root (two levels up from this file).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

app = FastAPI(title="DeepSeek Translator API", version="1.0.0")

app.include_router(works.router)
app.include_router(chapters.router)
app.include_router(terms.router)
app.include_router(terms.universal_router)
app.include_router(translate.router)


@app.get("/api/health")
def health():
    return {"ok": True}
