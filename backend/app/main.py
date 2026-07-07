from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .response import ok, register_exception_handlers
from .routers import (
    categories,
    detail,
    interactions,
    participants,
    photos,
    spaces,
    stats,
)

app = FastAPI(title="CosSelect API", version="1.0.0")

origins = [o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/api/health")
def health():
    return ok({"status": "ok"})


app.include_router(spaces.router)
app.include_router(categories.router)
app.include_router(participants.router)
app.include_router(photos.router)
app.include_router(detail.router)
app.include_router(interactions.router)
app.include_router(stats.router)
