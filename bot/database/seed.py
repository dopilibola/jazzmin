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
    "Zangiota tumani": ("Zangiata", "Зангиота"),
}


async def seed_locations(session: AsyncSession) -> None:
    """Clear all regions/districts/cemeteries and re-seed from config files."""
    from credentials.tashkent_cemeteries import TASHKENT_CEMETERIES
    from credentials.tashkent_region_cemeteries import TASHKENT_REGION_CEMETERIES

    await session.execute(delete(Region))
    await session.flush()

    # 1. Toshkent shahri
    region_city = Region(
        name_en="Tashkent city",
        name_ru="г. Ташкент",
        name_uz="Toshkent shahri",
    )
    session.add(region_city)
    await session.flush()
    city_id = region_city.id

    for district_uz in TASHKENT_CEMETERIES:
        cemeteries = TASHKENT_CEMETERIES[district_uz]
        name_en, name_ru = DISTRICT_NAMES.get(
            district_uz, (district_uz.replace(" tumani", ""), district_uz)
        )
        district = District(
            region_id=city_id,
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

    # 2. Toshkent viloyati
    region_region = Region(
        name_en="Tashkent region",
        name_ru="Ташкентская область",
        name_uz="Toshkent viloyati",
    )
    session.add(region_region)
    await session.flush()
    region_id = region_region.id

    for district_uz in TASHKENT_REGION_CEMETERIES:
        cemeteries = TASHKENT_REGION_CEMETERIES[district_uz]
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
