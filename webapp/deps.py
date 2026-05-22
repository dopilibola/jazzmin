"""FastAPI dependency'lari: DB sessiya, joriy foydalanuvchi, shablon renderi."""
import os

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from bot.database.db import async_session_factory
from webapp import ui
from webapp.db_extras import get_user_by_id

templates = Jinja2Templates(directory="webapp/templates")
templates.env.globals["format_price"] = ui.format_price
templates.env.globals["status_label"] = ui.status_label
templates.env.globals["status_color"] = ui.status_color
templates.env.globals["relationship_label"] = ui.relationship_label
templates.env.globals["format_years"] = ui.format_years
templates.env.globals["order_steps"] = ui.order_steps


async def get_db():
    """So'rov davomida bitta async sessiya beradi; oxirida commit/rollback qiladi."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(request: Request, session=Depends(get_db)):
    """Sessiyadagi user_id bo'yicha joriy foydalanuvchini qaytaradi (yoki None)."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return await get_user_by_id(session, user_id)


def set_flash(request: Request, message: str, category: str = "success") -> None:
    """Keyingi sahifada ko'rsatiladigan bir martalik xabar."""
    request.session["_flash"] = {"message": message, "category": category}


def render(request: Request, template_name: str, context: dict | None = None,
           status_code: int = 200):
    """Shablonni render qiladi — flash xabari avtomatik qo'shiladi."""
    ctx: dict = {"flash": request.session.pop("_flash", None)}
    # CSS keshini yangilash uchun versiya (fayl o'zgarsa avtomatik yangilanadi)
    try:
        ctx["static_v"] = int(os.path.getmtime("webapp/static/style.css"))
    except OSError:
        ctx["static_v"] = 1
    if context:
        ctx.update(context)
    ctx.setdefault("user", None)
    return templates.TemplateResponse(request, template_name, ctx, status_code=status_code)
