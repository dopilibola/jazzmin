"""
Maskan tariflarini katalogga yozadi (sayt + bot yagona manbadan o'qiydi).

Ishlatish (serverda):
    docker compose exec jazzmin-web python manage.py seed_services

Har bir tarif slug bo'yicha yangilanadi (qayta ishga tushirish xavfsiz).
Ro'yxatda yo'q eski xizmatlar is_active=False qilinadi (o'chirilmaydi).
"""
from django.core.management.base import BaseCommand

from apps.catalog.models import Service

# Tartib: base `name` raqamli prefiks bilan — sayt/bot `name` bo'yicha tartiblaydi.
# Ko'rinadigan nom esa name_uz/ru/en (toza).
SERVICES = [
    {
        "slug": "tejamkor",
        "name": "1. Tejamkor",
        "name_uz": "💚 Tejamkor",
        "name_ru": "💚 Эконом",
        "name_en": "💚 Economy",
        "price": 59000,
        "category": "cleaning",
        "description_uz": (
            "1 marta tashrif\n\n"
            "✓ Qabr toshini yuvish\n"
            "✓ Begona o'tlarni yulish\n"
            "✓ Foto-hisobot"
        ),
        "description_ru": (
            "1 визит\n\n"
            "✓ Мойка надгробия\n"
            "✓ Прополка сорняков\n"
            "✓ Фотоотчёт"
        ),
        "description_en": (
            "1 visit\n\n"
            "✓ Headstone washing\n"
            "✓ Weed removal\n"
            "✓ Photo report"
        ),
    },
    {
        "slug": "bir-martalik",
        "name": "2. Bir martalik",
        "name_uz": "🧹 Bir martalik",
        "name_ru": "🧹 Разовый",
        "name_en": "🧹 One-time",
        "price": 280000,
        "category": "cleaning",
        "description_uz": (
            "1 marta tashrif\n\n"
            "✓ Batamom tozalash\n"
            "✓ Tozalash + olib ketish\n"
            "✓ Foto-hisobot"
        ),
        "description_ru": (
            "1 визит\n\n"
            "✓ Полная уборка\n"
            "✓ Уборка + вывоз мусора\n"
            "✓ Фотоотчёт"
        ),
        "description_en": (
            "1 visit\n\n"
            "✓ Full cleaning\n"
            "✓ Cleaning + waste removal\n"
            "✓ Photo report"
        ),
    },
    {
        "slug": "oylik",
        "name": "3. Oylik",
        "name_uz": "🔥 Oylik",
        "name_ru": "🔥 Ежемесячный",
        "name_en": "🔥 Monthly",
        "price": 900000,
        "category": "cleaning",
        "description_uz": (
            "⭐️ MASHHUR  ·  Oyiga 4 marta tashrif\n\n"
            "✓ To'liq tozalash\n"
            "✓ Begona o'tlarni yulish\n"
            "✓ Qabr holatini yaxshilash\n"
            "✓ Qabr atrofi obodonlashtirish\n"
            "✓ Foto-hisobot"
        ),
        "description_ru": (
            "⭐️ ПОПУЛЯРНО  ·  4 визита в месяц\n\n"
            "✓ Полная чистка\n"
            "✓ Прополка сорняков\n"
            "✓ Улучшение состояния могилы\n"
            "✓ Благоустройство территории\n"
            "✓ Фотоотчёт"
        ),
        "description_en": (
            "⭐️ POPULAR  ·  4 visits per month\n\n"
            "✓ Complete cleaning\n"
            "✓ Weed removal\n"
            "✓ Improving the grave condition\n"
            "✓ Landscaping the surrounding area\n"
            "✓ Photo report"
        ),
    },
    {
        "slug": "yillik",
        "name": "4. Yillik",
        "name_uz": "👑 Yillik",
        "name_ru": "👑 Годовой",
        "name_en": "👑 Yearly",
        "price": 3360000,
        "category": "cleaning",
        "description_uz": (
            "💎 FOYDALI  ·  Oyiga 1 marta tashrif\n\n"
            "✓ To'liq tozalash\n"
            "✓ Begona o'tlarni yulish\n"
            "✓ Qabr holatini yaxshilash\n"
            "✓ Qabr atrofi obodonlashtirish\n"
            "✓ Foto-hisobot"
        ),
        "description_ru": (
            "💎 ВЫГОДНО  ·  1 визит в месяц\n\n"
            "✓ Полная чистка\n"
            "✓ Прополка сорняков\n"
            "✓ Улучшение состояния могилы\n"
            "✓ Благоустройство территории могилы\n"
            "✓ Фотоотчёт"
        ),
        "description_en": (
            "💎 BEST VALUE  ·  1 visit per month\n\n"
            "✓ Complete cleaning\n"
            "✓ Weed removal\n"
            "✓ Improving the grave condition\n"
            "✓ Landscaping the grave territory\n"
            "✓ Photo report"
        ),
    },
    {
        "slug": "loy-suvoq",
        "name": "5. Loy suvoq",
        "name_uz": "🧱 Loy suvoq",
        "name_ru": "🧱 Глиняная обмазка",
        "name_en": "🧱 Clay coating",
        "price": 220000,
        "category": "other",
        "description_uz": (
            "Qo'shimcha xizmat (alohida)\n\n"
            "✓ Qabrni loy bilan suvash"
        ),
        "description_ru": (
            "Дополнительная услуга (отдельно)\n\n"
            "✓ Обмазка могилы глиной"
        ),
        "description_en": (
            "Additional service (separate)\n\n"
            "✓ Coating the grave with clay"
        ),
    },
]


class Command(BaseCommand):
    help = "Maskan tariflarini katalogga yozadi (sayt + bot uchun yagona manba)."

    def handle(self, *args, **options):
        kept_slugs = []
        for data in SERVICES:
            slug = data["slug"]
            kept_slugs.append(slug)
            defaults = {
                "name": data["name"],
                "name_uz": data["name_uz"],
                "name_ru": data["name_ru"],
                "name_en": data["name_en"],
                "price": data["price"],
                "category": data["category"],
                # Asosiy (fallback) tavsif = o'zbekcha
                "description": data["description_uz"],
                "description_uz": data["description_uz"],
                "description_ru": data["description_ru"],
                "description_en": data["description_en"],
                "is_active": True,
            }
            obj, created = Service.objects.update_or_create(slug=slug, defaults=defaults)
            verb = "yaratildi" if created else "yangilandi"
            self.stdout.write(self.style.SUCCESS(f"  ✓ {obj.name} — {int(obj.price):,} so'm ({verb})".replace(",", " ")))

        # Ro'yxatda yo'q eski xizmatlarni yashirish (o'chirmasdan)
        hidden = Service.objects.exclude(slug__in=kept_slugs).filter(is_active=True).update(is_active=False)
        if hidden:
            self.stdout.write(self.style.WARNING(f"  ⚠ {hidden} ta eski xizmat yashirildi (is_active=False)."))

        self.stdout.write(self.style.SUCCESS(f"\nTayyor! {len(SERVICES)} ta tarif o'rnatildi. Sayt va bot yangilandi."))
