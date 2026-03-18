"""
Add "Gul ekish" (Flower planting) service with category='flowers'.
This service appears alongside flower products in the bot's Flowers menu.
"""
from decimal import Decimal

from django.db import migrations


def add_flower_service(apps, schema_editor):
    CatalogService = apps.get_model("botapp", "CatalogService")
    if CatalogService.objects.filter(category="flowers").exists():
        return
    CatalogService.objects.create(
        name_uz="Gul ekish",
        name_ru="Посадка цветов",
        name_en="Flower planting",
        description_uz="Qabr atrofida gul ekish xizmati. Professional gul ekish va parvarish.",
        description_ru="Услуга посадки цветов вокруг могилы. Профессиональная посадка и уход.",
        description_en="Flower planting service around the grave. Professional planting and care.",
        price=Decimal("70000"),
        category="flowers",
        is_active=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("botapp", "0003_populate_catalog"),
    ]

    operations = [
        migrations.RunPython(add_flower_service, migrations.RunPython.noop),
    ]
