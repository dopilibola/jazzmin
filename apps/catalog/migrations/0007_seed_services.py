"""6 ta xizmatni catalog_service jadvaliga qo'shadi.

Ma'lumot kodda (git'da) saqlanadi — yangi joyda `migrate` ishlasa, xizmatlar
avtomatik qayta yaratiladi. Idempotent: mavjud bo'lsa qayta qo'shilmaydi.
"""
from django.db import migrations
from django.utils.text import slugify

SERVICES = [
    ("Tozalash", "1 marta", 240000),
    ("Suvoq qilish", "Bir martalik", 180000),
    ("Oddiy tablichka", "60 x 40 sm", 1200000),
    ("Nerjaveyka tablichka", "60 x 40 sm", 1800000),
    ("Rasmga olish + aniq hisobot", "Qaysi xizmat kerakligi belgilanadi", 19000),
    ("Shunchaki tozalash", "Yengil tozalash", 69000),
]


def seed_services(apps, schema_editor):
    Service = apps.get_model("catalog", "Service")
    for name, desc, price in SERVICES:
        Service.objects.get_or_create(
            slug=slugify(name) or name,
            defaults=dict(
                name=name,
                name_uz=name,
                description=desc,
                description_uz=desc,
                price=price,
                category="cleaning",
                is_active=True,
            ),
        )


def unseed_services(apps, schema_editor):
    # Ortga qaytarishda ma'lumotni o'chirmaymiz (xavfsizlik uchun)
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0006_delete_flower"),
    ]

    operations = [
        migrations.RunPython(seed_services, unseed_services),
    ]
