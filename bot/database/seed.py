"""
Seed data: regions, districts, cemeteries.
Regions/districts/cemeteries ONLY from credentials/tashkent_cemeteries.py (Toshkent city only).

Services and flowers are managed via Django Admin — NO hardcoded seed data.
"""
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    Cemetery,
    District,
    Region,
)

DISTRICT_NAMES: dict[str, tuple[str, str]] = {
    "Bektemir tumani": ("Bektemir", "Бектемир"),
    "Chilonzor tumani": ("Chilanzar", "Чиланзар"),
    "Mirobod tumani": ("Mirobod", "Миробод"),
    "Mirzo Ulug\u2019bek tumani": ("Mirzo Ulugbek", "Мирзо Улугбек"),
    "Olmazor tumani": ("Olmazor", "Олмазор"),
    "Sergeli tumani": ("Sergeli", "Сергели"),
    "Shayxontohur tumani": ("Shayxontohur", "Шайхонтохур"),
    "Uchtepa tumani": ("Uchtepa", "Учтепа"),
    "Yakkasaroy tumani": ("Yakkasaroy", "Яккасарай"),
    "Yashnobod tumani": ("Yashnobod", "Яшнобод"),
    "Yunusobod tumani": ("Yunusobod", "Юнусабад"),
    "Yangi Hayot tumani": ("Yangi Hayot", "Янги Хаёт"),
}


async def seed_locations(session: AsyncSession) -> None:
    """Clear all regions/districts/cemeteries and re-seed ONLY from tashkent_cemeteries.py."""
    from credentials.tashkent_cemeteries import TASHKENT_CEMETERIES

    await session.execute(delete(Region))
    await session.flush()

    region = Region(
        name_en="Tashkent",
        name_ru="Ташкент",
        name_uz="Toshkent",
    )
    session.add(region)
    await session.flush()
    region_id = region.id

    for district_uz in TASHKENT_CEMETERIES:
        cemeteries = TASHKENT_CEMETERIES[district_uz]
        name_en, name_ru = DISTRICT_NAMES.get(
            district_uz, (district_uz.replace(" tumani", ""), district_uz)
        )
        district = District(
            region_id=region_id,
            name_en=name_en,
            name_ru=name_ru,
            name_uz=district_uz,
        )
        session.add(district)
        await session.flush()

        for cemetery_name in cemeteries:
            session.add(
                Cemetery(district_id=district.id, name=cemetery_name)
            )

    await session.flush()
