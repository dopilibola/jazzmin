from django.db import models

SERVICE_CATEGORY_CHOICES = [
    ("cleaning", "Cleaning"),
    ("flower", "Flower"),
    ("other", "Other"),
]


class Service(models.Model):
    name = models.CharField("Nom (asosiy)", max_length=200)
    name_uz = models.CharField("Nom (O'zbekcha)", max_length=200, blank=True, default="")
    name_ru = models.CharField("Название (Русский)", max_length=200, blank=True, default="")
    name_en = models.CharField("Name (English)", max_length=200, blank=True, default="")
    slug = models.SlugField(max_length=200, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    description_uz = models.TextField("Tavsif (O'zbekcha)", blank=True, default="")
    description_ru = models.TextField("Описание (Русский)", blank=True, default="")
    description_en = models.TextField("Description (English)", blank=True, default="")
    category = models.CharField(
        max_length=20,
        choices=SERVICE_CATEGORY_CHOICES,
        default="cleaning",
    )
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Service'
        verbose_name_plural = 'Services'

    def __str__(self):
        return f"{self.name} — {self.price} sum"

    def get_name(self, lang: str = "uz") -> str:
        """Get localized name."""
        if lang == "uz" and self.name_uz:
            return self.name_uz
        if lang == "ru" and self.name_ru:
            return self.name_ru
        if lang == "en" and self.name_en:
            return self.name_en
        return self.name

    def get_description(self, lang: str = "uz") -> str:
        """Get localized description."""
        if lang == "uz" and self.description_uz:
            return self.description_uz
        if lang == "ru" and self.description_ru:
            return self.description_ru
        if lang == "en" and self.description_en:
            return self.description_en
        return self.description


class Flower(models.Model):
    name = models.CharField("Nomi / Name", max_length=200)
    name_uz = models.CharField("Nom (O'zbekcha)", max_length=200, blank=True, default="")
    name_ru = models.CharField("Название (Русский)", max_length=200, blank=True, default="")
    name_en = models.CharField("Name (English)", max_length=200, blank=True, default="")
    slug = models.SlugField(max_length=200, unique=True)
    price = models.DecimalField("Narxi / Price", max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(
        "Dastafka narxi / Delivery fee",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Yetkazib berish narxi / Delivery cost",
    )
    is_plantable = models.BooleanField(
        "Ekiladigan gul / Plantable",
        default=False,
        help_text="Agar gul ekiladigan bo'lsa belgilang",
    )
    planting_fee = models.DecimalField(
        "Ekish narxi / Planting fee",
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Faqat ekiladigan gullar uchun / Only for plantable flowers",
    )
    description = models.TextField(blank=True)
    description_uz = models.TextField("Tavsif (O'zbekcha)", blank=True, default="")
    description_ru = models.TextField("Описание (Русский)", blank=True, default="")
    description_en = models.TextField("Description (English)", blank=True, default="")
    image = models.ImageField(upload_to='flowers/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Gul / Flower'
        verbose_name_plural = 'Gullar / Flowers'

    def __str__(self):
        flower_type = "🌱" if self.is_plantable else "💐"
        return f"{flower_type} {self.name} — {self.price} so'm"

    def get_name(self, lang: str = "uz") -> str:
        """Get localized name."""
        if lang == "uz" and self.name_uz:
            return self.name_uz
        if lang == "ru" and self.name_ru:
            return self.name_ru
        if lang == "en" and self.name_en:
            return self.name_en
        return self.name

    def get_description(self, lang: str = "uz") -> str:
        """Get localized description."""
        if lang == "uz" and self.description_uz:
            return self.description_uz
        if lang == "ru" and self.description_ru:
            return self.description_ru
        if lang == "en" and self.description_en:
            return self.description_en
        return self.description

    @property
    def total_price(self):
        """Jami: narx + dastafka + ekish (agar ekiladigan bo'lsa)"""
        total = self.price + (self.delivery_fee or 0)
        if self.is_plantable:
            total += (self.planting_fee or 0)
        return total
