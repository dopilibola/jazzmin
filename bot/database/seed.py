"""
Seed data: regions, districts, cemeteries, services, flowers.
Regions/districts/cemeteries ONLY from credentials/tashkent_cemeteries.py (Toshkent city only).
No other viloyats or cemetery sources.
"""
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    Cemetery,
    District,
    Flower,
    FlowerCategory,
    FlowerProduct,
    Region,
    Service,
)


# District name translations (uz from file -> en, ru)
# Note: "Mirzo Ulug'bek" uses Unicode apostrophe U+2019
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

    # Remove all existing regions (CASCADE deletes districts and cemeteries)
    await session.execute(delete(Region))
    await session.flush()

    # 1 region: Toshkent
    region = Region(
        name_en="Tashkent",
        name_ru="Ташкент",
        name_uz="Toshkent",
    )
    session.add(region)
    await session.flush()
    region_id = region.id

    # Districts and cemeteries from TASHKENT_CEMETERIES
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


async def seed_services(session: AsyncSession) -> None:
    """Insert grave care services if empty."""
    result = await session.execute(select(Service).limit(1))
    if result.scalar_one_or_none() is not None:
        return

    services_data = [
        {
            "name_en": "Regular grave cleaning",
            "name_ru": "Обычная уборка могилы",
            "name_uz": "Oddiy qabr tozalash",
            "description_en": "Cleaning the grave area, removing trash and restoring order.",
            "description_ru": "Уборка территории могилы, удаление мусора и наведение порядка.",
            "description_uz": "Qabr maydonini tozalash, axlat olib tashlash va tartibga keltirish.",
            "price": 50000,
            "category": "cleaning",
        },
        {
            "name_en": "Marble cleaning",
            "name_ru": "Уборка мрамора",
            "name_uz": "Marmar tozalash",
            "description_en": "Cleaning and maintaining marble surfaces.",
            "description_ru": "Чистка и уход за мраморными поверхностями.",
            "description_uz": "Marmar sirtlarni tozalash va parvarish qilish.",
            "price": 80000,
            "category": "cleaning",
        },
        {
            "name_en": "Monument cleaning",
            "name_ru": "Уборка памятника",
            "name_uz": "Yodgorlik tozalash",
            "description_en": "Cleaning and restoring monuments or memorial structures.",
            "description_ru": "Чистка и восстановление памятников или мемориальных сооружений.",
            "description_uz": "Yodgorliklar yoki xotira inshootlarini tozalash va tiklash.",
            "price": 100000,
            "category": "cleaning",
        },
    ]
    for s in services_data:
        session.add(Service(**s))

    await session.flush()


async def seed_flowers(session: AsyncSession) -> None:
    """Insert flower catalog if empty."""
    result = await session.execute(select(Flower).limit(1))
    if result.scalar_one_or_none() is not None:
        return

    flowers_data = [
        {"name_en": "Rose bouquet", "name_ru": "Букет роз", "name_uz": "Atirgul buketi", "price": 30000},
        {"name_en": "Lily bouquet", "name_ru": "Букет лилий", "name_uz": "Zambak buketi", "price": 35000},
        {"name_en": "Carnation bouquet", "name_ru": "Букет гвоздик", "name_uz": "Qaranfil buketi", "price": 25000},
        {"name_en": "Mixed bouquet", "name_ru": "Смешанный букет", "name_uz": "Aralash buket", "price": 40000},
    ]
    for f in flowers_data:
        session.add(Flower(**f))

    await session.flush()


async def seed_flower_categories_and_products(session: AsyncSession) -> None:
    """Insert flower categories and products for flower feature module."""
    result = await session.execute(select(FlowerCategory).limit(1))
    if result.scalar_one_or_none() is not None:
        return

    # Category 1: Flowers planted around the grave
    cat1 = FlowerCategory(
        name_en="Flowers planted around the grave",
        name_ru="Цветы, посаженные вокруг могилы",
        name_uz="Qabr atrofida ekilgan gullar",
    )
    session.add(cat1)
    await session.flush()

    # Category 2: Flowers placed on the grave
    cat2 = FlowerCategory(
        name_en="Flowers placed on the grave",
        name_ru="Цветы, размещённые на могиле",
        name_uz="Qabr ustiga qo'yilgan gullar",
    )
    session.add(cat2)
    await session.flush()

    # Products for category 1 (planted)
    products_planted = [
        {
            "name_en": "Decorative flowers around the grave mound",
            "name_ru": "Декоративные цветы вокруг могильного холма",
            "name_uz": "Qabr tepalig atrofidagi dekorativ gullar",
            "description_en": "Beautiful flowers planted in soil around the grave area.",
            "description_ru": "Красивые цветы, посаженные в почву вокруг могилы.",
            "description_uz": "Qabr atrofidagi tuproqda ekilgan chiroyli gullar.",
            "price": 45000,
        },
        {
            "name_en": "Planted flowers around the grave",
            "name_ru": "Посаженные цветы вокруг могилы",
            "name_uz": "Qabr atrofida ekilgan gullar",
            "description_en": "Professional planting of flowers around the grave with care.",
            "description_ru": "Профессиональная посадка цветов вокруг могилы с уходом.",
            "description_uz": "Qabr atrofida gullarni professional ekish va parvarish.",
            "price": 55000,
        },
    ]
    for p in products_planted:
        session.add(FlowerProduct(category_id=cat1.id, **p))

    # Products for category 2 (placed)
    products_placed = [
        {
            "name_en": "Fresh flowers bouquet",
            "name_ru": "Букет свежих цветов",
            "name_uz": "Yangi gullar buketi",
            "description_en": "Fresh flower bouquet placed on the grave.",
            "description_ru": "Свежий букет цветов на могиле.",
            "description_uz": "Qabr ustiga qo'yilgan yangi gullar buketi.",
            "price": 30000,
        },
        {
            "name_en": "Mixed bouquet",
            "name_ru": "Смешанный букет",
            "name_uz": "Aralash buket",
            "description_en": "Mixed fresh flowers for the grave.",
            "description_ru": "Смешанный букет свежих цветов для могилы.",
            "description_uz": "Qabr uchun aralash yangi gullar.",
            "price": 40000,
        },
        {
            "name_en": "Artificial flowers",
            "name_ru": "Искусственные цветы",
            "name_uz": "Sun'iy gullar",
            "description_en": "Durable artificial flowers for the grave.",
            "description_ru": "Прочные искусственные цветы для могилы.",
            "description_uz": "Qabr uchun bardoshli sun'iy gullar.",
            "price": 25000,
        },
        {
            "name_en": "Wreath",
            "name_ru": "Венок",
            "name_uz": "Guldasta",
            "description_en": "Memorial wreath for the grave.",
            "description_ru": "Поминальный венок для могилы.",
            "description_uz": "Qabr uchun xotira guldastasi.",
            "price": 60000,
        },
    ]
    for p in products_placed:
        session.add(FlowerProduct(category_id=cat2.id, **p))

    await session.flush()
