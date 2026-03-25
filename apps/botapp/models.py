from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

LANGUAGE_CHOICES = [
    ("uz", "O'zbekcha"),
    ("ru", "Русский"),
    ("en", "English"),
]


class TelegramUser(models.Model):
    chat_id = models.BigIntegerField(unique=True, db_index=True)
    full_name = models.CharField("Ism / Full Name", max_length=200, blank=True, default="")
    phone_number = models.CharField("Telefon / Phone", max_length=30, blank=True, default="")
    username = models.CharField("Telegram username", max_length=100, blank=True, default="")
    language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default="uz",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Telegram User"
        verbose_name_plural = "Telegram Users"

    def __str__(self):
        if self.full_name:
            return f"{self.full_name} ({self.chat_id})"
        return f"{self.chat_id} ({self.language})"


# ---------------------------------------------------------------------------
# Catalog: Services
# ---------------------------------------------------------------------------

SERVICE_CATEGORY_CHOICES = [
    ("cleaning", "Cleaning / Tozalash"),
    ("flowers", "Flowers / Gullar"),
    ("renewal", "Renewal / Yangilash"),
    ("other", "Other / Boshqa"),
]


class CatalogService(models.Model):
    name_uz = models.CharField("Nomi (UZ)", max_length=200)
    name_ru = models.CharField("Название (RU)", max_length=200)
    name_en = models.CharField("Name (EN)", max_length=200)
    description_uz = models.TextField("Tavsif (UZ)", blank=True, default="")
    description_ru = models.TextField("Описание (RU)", blank=True, default="")
    description_en = models.TextField("Description (EN)", blank=True, default="")
    price = models.DecimalField(
        "Narx / Price",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    category = models.CharField(
        max_length=30,
        choices=SERVICE_CATEGORY_CHOICES,
        default="cleaning",
    )
    is_active = models.BooleanField("Faol / Active", default=True)
    image = models.ImageField(
        "Rasm / Image",
        upload_to="services/",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"
        ordering = ["category", "name_en"]

    def __str__(self):
        return f"{self.name_en} — {self.price} sum"

    def get_name(self, lang: str) -> str:
        return getattr(self, f"name_{lang}", self.name_en) or self.name_en

    def get_description(self, lang: str) -> str:
        return getattr(self, f"description_{lang}", self.description_en) or self.description_en

    @property
    def price_int(self) -> int:
        return int(self.price)


# ---------------------------------------------------------------------------
# Catalog: Flower categories & products (COMMENTED OUT)
# ---------------------------------------------------------------------------

# class CatalogFlowerCategory(models.Model):
#     name_uz = models.CharField("Nomi (UZ)", max_length=200)
#     name_ru = models.CharField("Название (RU)", max_length=200)
#     name_en = models.CharField("Name (EN)", max_length=200)
#     is_active = models.BooleanField("Faol / Active", default=True)
#     sort_order = models.PositiveIntegerField("Tartib / Order", default=0)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         verbose_name = "Flower Category"
#         verbose_name_plural = "Flower Categories"
#         ordering = ["sort_order", "name_en"]
#
#     def __str__(self):
#         return self.name_en
#
#     def get_name(self, lang: str) -> str:
#         return getattr(self, f"name_{lang}", self.name_en) or self.name_en


# class CatalogFlowerProduct(models.Model):
#     category = models.ForeignKey(
#         CatalogFlowerCategory,
#         on_delete=models.CASCADE,
#         related_name="products",
#     )
#     name_uz = models.CharField("Nomi (UZ)", max_length=200)
#     name_ru = models.CharField("Название (RU)", max_length=200)
#     name_en = models.CharField("Name (EN)", max_length=200)
#     description_uz = models.TextField("Tavsif (UZ)", blank=True, default="")
#     description_ru = models.TextField("Описание (RU)", blank=True, default="")
#     description_en = models.TextField("Description (EN)", blank=True, default="")
#     price = models.DecimalField(
#         "Narx / Price",
#         max_digits=12,
#         decimal_places=2,
#         validators=[MinValueValidator(Decimal("0.01"))],
#     )
#     is_active = models.BooleanField("Faol / Active", default=True)
#     image = models.ImageField(
#         "Rasm / Image",
#         upload_to="flowers/",
#         blank=True,
#         null=True,
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         verbose_name = "Flower Product"
#         verbose_name_plural = "Flower Products"
#         ordering = ["category", "name_en"]
#
#     def __str__(self):
#         return f"{self.name_en} — {self.price} sum"
#
#     def get_name(self, lang: str) -> str:
#         return getattr(self, f"name_{lang}", self.name_en) or self.name_en
#
#     def get_description(self, lang: str) -> str:
#         return getattr(self, f"description_{lang}", self.description_en) or self.description_en
#
#     @property
#     def price_int(self) -> int:
#         return int(self.price)


# ---------------------------------------------------------------------------
# Worker Service Fees - Ishchilar uchun hizmat to'lovlari
# ---------------------------------------------------------------------------

class WorkerServiceFee(models.Model):
    """
    Ishchilar uchun hizmat to'lovlari.
    Har bir hizmat uchun ishchiga qancha to'lov berilishini belgilaydi.
    """
    service_name = models.CharField(
        "Hizmat nomi / Service name",
        max_length=200,
        unique=True,
        help_text="Masalan: Tozalash, Gul ekish, Yetkazib berish"
    )
    fee_amount = models.DecimalField(
        "To'lov summasi / Fee amount",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Ishchiga to'lanadigan summa (so'm)"
    )
    description = models.TextField(
        "Tavsif / Description",
        blank=True,
        default="",
        help_text="Qo'shimcha ma'lumot"
    )
    is_active = models.BooleanField(
        "Faol / Active",
        default=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ishchi Hizmat To'lovi"
        verbose_name_plural = "Ishchi Hizmat To'lovlari"
        ordering = ["service_name"]

    def __str__(self):
        return f"{self.service_name} — {self.fee_amount:,.0f} so'm"

    @property
    def fee_int(self) -> int:
        return int(self.fee_amount)
