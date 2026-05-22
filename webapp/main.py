"""Maskan veb-ilovasi (FastAPI) — Telegram bot bilan bitta PostgreSQL bazasida ishlaydi."""
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from bot.database.queries import get_orders_by_user, list_user_graves
from webapp.config import BASE_DIR, SECRET_KEY
from webapp.db_extras import ensure_web_schema
from webapp.deps import get_current_user, get_db, render
from webapp.routers import auth, graves, orders, profile, services


@asynccontextmanager
async def lifespan(app: FastAPI):
    # users jadvalida veb uchun ustunlar borligini ta'minlash
    await ensure_web_schema()
    yield


app = FastAPI(title="Maskan Web", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=60 * 60 * 24 * 14)

app.mount("/static", StaticFiles(directory="webapp/static"), name="static")
os.makedirs(BASE_DIR / "uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(BASE_DIR / "uploads")), name="uploads")

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(graves.router)
app.include_router(services.router)
app.include_router(orders.router)


@app.get("/")
async def home(request: Request, user=Depends(get_current_user), session=Depends(get_db)):
    if not user:
        return render(request, "home.html", {"user": None})
    user_graves = await list_user_graves(session, user.id)
    user_orders = await get_orders_by_user(session, user.id)
    return render(request, "home.html", {
        "user": user,
        "graves": user_graves,
        "orders": user_orders[:5],
        "orders_count": len(user_orders),
    })


@app.get("/health")
async def health():
    return {"status": "ok"}
