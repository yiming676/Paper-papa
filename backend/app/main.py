from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401
from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.migrations import run_lightweight_migrations
from app.db.session import engine


settings = get_settings()
Path(settings.assets_dir).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_lightweight_migrations(engine)
    yield


app = FastAPI(
    title="Recursive Paper Study Tool API",
    version="0.1.0",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.mount("/assets", StaticFiles(directory=settings.assets_dir), name="assets")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
