"""
Django `catalog_service` jadvaliga moslangan SQLAlchemy modeli.

Xizmatlar YAGONA manbada — Django admin panelidagi `catalog_service` jadvali.
Bot (apps.catalog.Service orqali) va veb-sayt (shu model orqali) AYNAN shu
jadvaldan o'qiydi. Xizmat faqat admin panelidan qo'shiladi.

Bu jadval Django migratsiyasi bilan yaratiladi — webapp uni faqat O'QIYDI,
shuning uchun alohida Base ishlatamiz (create_all unga tegmaydi).
"""
from sqlalchemy import Boolean, Integer, Numeric, String, Text, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class _CatalogBase(DeclarativeBase):
    """Webapp bu jadvalni yaratmaydi/o'zgartirmaydi — Django boshqaradi."""
    pass


class CatalogService(_CatalogBase):
    """Django admin'dagi `catalog_service` jadvali (apps.catalog.Service)."""

    __tablename__ = "catalog_service"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    name_uz: Mapped[str] = mapped_column(String(200), default="")
    name_ru: Mapped[str] = mapped_column(String(200), default="")
    name_en: Mapped[str] = mapped_column(String(200), default="")
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    description: Mapped[str] = mapped_column(Text, default="")
    description_uz: Mapped[str] = mapped_column(Text, default="")
    description_ru: Mapped[str] = mapped_column(Text, default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(20), default="cleaning")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def get_name(self, lang: str) -> str:
        return getattr(self, f"name_{lang}", "") or self.name

    def get_description(self, lang: str) -> str:
        return getattr(self, f"description_{lang}", "") or self.description


async def get_catalog_services(session) -> list[CatalogService]:
    """Admin paneldagi faol xizmatlar (nom bo'yicha tartiblangan)."""
    result = await session.execute(
        select(CatalogService)
        .where(CatalogService.is_active.is_(True))
        .order_by(CatalogService.name)
    )
    return list(result.scalars().all())


async def get_catalog_service(session, service_id: int) -> CatalogService | None:
    """Bitta xizmatni ID bo'yicha oladi."""
    result = await session.execute(
        select(CatalogService).where(CatalogService.id == service_id)
    )
    return result.scalar_one_or_none()
