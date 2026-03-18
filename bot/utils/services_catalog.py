"""
Services catalog. Static definitions for grave care services.
Structure: main sections -> sub-sections/items with description and price.
"""
from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceItem:
    """Single service with localized name, description, and price."""

    id: str
    name_en: str
    name_ru: str
    name_uz: str
    description_en: str
    description_ru: str
    description_uz: str
    price: int  # in smallest currency unit (e.g. cents or sum)


def _get_localized(d: dict[str, str], lang: str, key: str) -> str:
    """Get localized value. Fallback to 'en'."""
    k = f"{key}_{lang}" if lang in ("en", "ru", "uz") else f"{key}_en"
    return d.get(k, d.get(f"{key}_en", ""))


# -----------------------------------------------------------------------------
# Grave Cleaning
# -----------------------------------------------------------------------------

SVC_GC_REGULAR = ServiceItem(
    id="gc_regular",
    name_en="Regular grave cleaning (earth mound)",
    name_ru="Обычная уборка могилы (земляной холм)",
    name_uz="Oddiy qabr tozalash (tuproq tepalik)",
    description_en="Simple cleaning of the grave area, removing trash and restoring order.",
    description_ru="Простая уборка территории могилы, удаление мусора и наведение порядка.",
    description_uz="Qabr maydonini oddiy tozalash, axlat olib tashlash va tartibga keltirish.",
    price=50000,
)

SVC_GC_MARBLE = ServiceItem(
    id="gc_marble",
    name_en="Marble cleaning",
    name_ru="Уборка мрамора",
    name_uz="Marmar tozalash",
    description_en="Cleaning and maintenance of marble surfaces.",
    description_ru="Чистка и уход за мраморными поверхностями.",
    description_uz="Marmar sirtlarni tozalash va parvarish qilish.",
    price=80000,
)

SVC_GC_MONUMENT = ServiceItem(
    id="gc_monument",
    name_en="Monument cleaning",
    name_ru="Уборка памятника",
    name_uz="Yodgorlik tozalash",
    description_en="Cleaning and restoring monuments or memorial structures.",
    description_ru="Чистка и восстановление памятников или мемориальных сооружений.",
    description_uz="Yodgorliklar yoki xotira inshootlarini tozalash va tiklash.",
    price=100000,
)

# -----------------------------------------------------------------------------
# Flowers
# -----------------------------------------------------------------------------

SVC_FLOWER_ROSE = ServiceItem(
    id="flower_rose",
    name_en="Rose bouquet",
    name_ru="Букет роз",
    name_uz="Atirgul buketi",
    description_en="Fresh rose bouquet for the grave.",
    description_ru="Свежий букет роз для могилы.",
    description_uz="Qabr uchun yangi atirgul buketi.",
    price=30000,
)

SVC_FLOWER_LILY = ServiceItem(
    id="flower_lily",
    name_en="Lily bouquet",
    name_ru="Букет лилий",
    name_uz="Zambak buketi",
    description_en="Fresh lily bouquet for the grave.",
    description_ru="Свежий букет лилий для могилы.",
    description_uz="Qabr uchun yangi zambak buketi.",
    price=35000,
)

SVC_FLOWER_CARNATION = ServiceItem(
    id="flower_carnation",
    name_en="Carnation bouquet",
    name_ru="Букет гвоздик",
    name_uz="Qaranfil buketi",
    description_en="Fresh carnation bouquet for the grave.",
    description_ru="Свежий букет гвоздик для могилы.",
    description_uz="Qabr uchun yangi qaranfil buketi.",
    price=25000,
)

SVC_FLOWER_MIXED = ServiceItem(
    id="flower_mixed",
    name_en="Mixed bouquet",
    name_ru="Смешанный букет",
    name_uz="Aralash buket",
    description_en="Mixed fresh flowers for the grave.",
    description_ru="Смешанный букет свежих цветов для могилы.",
    description_uz="Qabr uchun aralash yangi gullar buketi.",
    price=40000,
)

SVC_FLOWER_PLANTING = ServiceItem(
    id="flower_planting",
    name_en="Flower planting",
    name_ru="Посадка цветов",
    name_uz="Gul ekish",
    description_en="Service for planting flowers around the grave with professional care.",
    description_ru="Услуга по посадке цветов вокруг могилы с профессиональным уходом.",
    description_uz="Qabr atrofida gullarni professional parvarish bilan ekish xizmati.",
    price=60000,
)

# -----------------------------------------------------------------------------
# Grave Renewal
# -----------------------------------------------------------------------------

SVC_RENEWAL_SOIL = ServiceItem(
    id="renewal_soil",
    name_en="Soil renewal",
    name_ru="Обновление грунта",
    name_uz="Tuproq yangilash",
    description_en="Renewal and improvement of soil around the grave area.",
    description_ru="Обновление и улучшение грунта вокруг могилы.",
    description_uz="Qabr atrofidagi tuproqni yangilash va yaxshilash.",
    price=70000,
)

# -----------------------------------------------------------------------------
# Catalog structure
# -----------------------------------------------------------------------------

# All selectable services (can add to cart)
ALL_SERVICES: dict[str, ServiceItem] = {
    s.id: s
    for s in [
        SVC_GC_REGULAR,
        SVC_GC_MARBLE,
        SVC_GC_MONUMENT,
        SVC_FLOWER_ROSE,
        SVC_FLOWER_LILY,
        SVC_FLOWER_CARNATION,
        SVC_FLOWER_MIXED,
        SVC_FLOWER_PLANTING,
        SVC_RENEWAL_SOIL,
    ]
}

# Main sections
SECTION_GRAVE_CLEANING = "grave_cleaning"
SECTION_FLOWERS = "flowers"
SECTION_GRAVE_RENEWAL = "grave_renewal"

# Section -> list of service IDs
SECTION_SERVICES: dict[str, list[str]] = {
    SECTION_GRAVE_CLEANING: ["gc_regular", "gc_marble", "gc_monument"],
    SECTION_FLOWERS: ["flower_rose", "flower_lily", "flower_carnation", "flower_mixed", "flower_planting"],
    SECTION_GRAVE_RENEWAL: ["renewal_soil"],
}


def get_service(service_id: str) -> ServiceItem | None:
    """Get service by ID."""
    return ALL_SERVICES.get(service_id)


def get_service_name(service: ServiceItem, lang: str) -> str:
    """Get localized service name."""
    return getattr(service, f"name_{lang}", service.name_en)


def get_service_description(service: ServiceItem, lang: str) -> str:
    """Get localized service description."""
    return getattr(service, f"description_{lang}", service.description_en)


def format_price(price: int, lang: str = "en") -> str:
    """Format price for display. Assumes local currency (e.g. UZS sum)."""
    return f"{price:,} sum".replace(",", " ")
