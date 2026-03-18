"""
Populate catalog tables with initial data (previously hardcoded in seed.py).
After this migration, all data is managed via Django Admin.
"""
from decimal import Decimal

from django.db import migrations


def populate_services(apps, schema_editor):
    CatalogService = apps.get_model("botapp", "CatalogService")
    if CatalogService.objects.exists():
        return

    services = [
        {
            "name_en": "Regular grave cleaning",
            "name_ru": "Обычная уборка могилы",
            "name_uz": "Oddiy qabr tozalash",
            "description_en": "Cleaning the grave area, removing trash and restoring order.",
            "description_ru": "Уборка территории могилы, удаление мусора и наведение порядка.",
            "description_uz": "Qabr maydonini tozalash, axlat olib tashlash va tartibga keltirish.",
            "price": Decimal("50000"),
            "category": "cleaning",
        },
        {
            "name_en": "Marble cleaning",
            "name_ru": "Уборка мрамора",
            "name_uz": "Marmar tozalash",
            "description_en": "Cleaning and maintaining marble surfaces.",
            "description_ru": "Чистка и уход за мраморными поверхностями.",
            "description_uz": "Marmar sirtlarni tozalash va parvarish qilish.",
            "price": Decimal("80000"),
            "category": "cleaning",
        },
        {
            "name_en": "Monument cleaning",
            "name_ru": "Уборка памятника",
            "name_uz": "Yodgorlik tozalash",
            "description_en": "Cleaning and restoring monuments or memorial structures.",
            "description_ru": "Чистка и восстановление памятников или мемориальных сооружений.",
            "description_uz": "Yodgorliklar yoki xotira inshootlarini tozalash va tiklash.",
            "price": Decimal("100000"),
            "category": "cleaning",
        },
    ]
    for s in services:
        CatalogService.objects.create(**s)


def populate_flowers(apps, schema_editor):
    CatalogFlowerCategory = apps.get_model("botapp", "CatalogFlowerCategory")
    CatalogFlowerProduct = apps.get_model("botapp", "CatalogFlowerProduct")
    if CatalogFlowerCategory.objects.exists():
        return

    cat1 = CatalogFlowerCategory.objects.create(
        name_en="Flowers planted around the grave",
        name_ru="Цветы, посаженные вокруг могилы",
        name_uz="Qabr atrofida ekilgan gullar",
        sort_order=1,
    )
    cat2 = CatalogFlowerCategory.objects.create(
        name_en="Flowers placed on the grave",
        name_ru="Цветы, размещённые на могиле",
        name_uz="Qabr ustiga qo'yilgan gullar",
        sort_order=2,
    )

    planted = [
        {
            "name_en": "Decorative flowers around the grave mound",
            "name_ru": "Декоративные цветы вокруг могильного холма",
            "name_uz": "Qabr tepalig atrofidagi dekorativ gullar",
            "description_en": "Beautiful flowers planted in soil around the grave area.",
            "description_ru": "Красивые цветы, посаженные в почву вокруг могилы.",
            "description_uz": "Qabr atrofidagi tuproqda ekilgan chiroyli gullar.",
            "price": Decimal("45000"),
        },
        {
            "name_en": "Planted flowers around the grave",
            "name_ru": "Посаженные цветы вокруг могилы",
            "name_uz": "Qabr atrofida ekilgan gullar",
            "description_en": "Professional planting of flowers around the grave with care.",
            "description_ru": "Профессиональная посадка цветов вокруг могилы с уходом.",
            "description_uz": "Qabr atrofida gullarni professional ekish va parvarish.",
            "price": Decimal("55000"),
        },
    ]
    for p in planted:
        CatalogFlowerProduct.objects.create(category=cat1, **p)

    placed = [
        {
            "name_en": "Fresh flowers bouquet",
            "name_ru": "Букет свежих цветов",
            "name_uz": "Yangi gullar buketi",
            "description_en": "Fresh flower bouquet placed on the grave.",
            "description_ru": "Свежий букет цветов на могиле.",
            "description_uz": "Qabr ustiga qo'yilgan yangi gullar buketi.",
            "price": Decimal("30000"),
        },
        {
            "name_en": "Mixed bouquet",
            "name_ru": "Смешанный букет",
            "name_uz": "Aralash buket",
            "description_en": "Mixed fresh flowers for the grave.",
            "description_ru": "Смешанный букет свежих цветов для могилы.",
            "description_uz": "Qabr uchun aralash yangi gullar.",
            "price": Decimal("40000"),
        },
        {
            "name_en": "Artificial flowers",
            "name_ru": "Искусственные цветы",
            "name_uz": "Sun'iy gullar",
            "description_en": "Durable artificial flowers for the grave.",
            "description_ru": "Прочные искусственные цветы для могилы.",
            "description_uz": "Qabr uchun bardoshli sun'iy gullar.",
            "price": Decimal("25000"),
        },
        {
            "name_en": "Wreath",
            "name_ru": "Венок",
            "name_uz": "Guldasta",
            "description_en": "Memorial wreath for the grave.",
            "description_ru": "Поминальный венок для могилы.",
            "description_uz": "Qabr uchun xotira guldastasi.",
            "price": Decimal("60000"),
        },
    ]
    for p in placed:
        CatalogFlowerProduct.objects.create(category=cat2, **p)


class Migration(migrations.Migration):

    dependencies = [
        ("botapp", "0002_catalogflowercategory_catalogservice_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_services, migrations.RunPython.noop),
        migrations.RunPython(populate_flowers, migrations.RunPython.noop),
    ]
