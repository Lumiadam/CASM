"""CASMS FastAPI 應用程式進入點。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import assets, auth, health, maintenance, permissions, reservations
from app.seed import init_db_and_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.seed_on_startup:
        init_db_and_seed()
    yield


app = FastAPI(
    title="CASMS API",
    description="企業級資產與空間管理系統 RESTful API",
    version="1.0.0-mvp",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(permissions.router)
app.include_router(assets.router)
app.include_router(reservations.router)
app.include_router(maintenance.router)
