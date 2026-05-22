"""
Bot va veb-sayt ma'lumotlarini Django admin panelida ko'rsatish.

Bu modellar SQLAlchemy jadvallariga (`users`, `graves`, `orders`,
`order_items`) bog'langan — bot va sayt aynan shu jadvallardan foydalanadi.
`managed = False` — Django bu jadvallarni YARATMAYDI/o'chirmaydi, faqat
o'qiydi va ko'rsatadi.
"""
from django.db import models


class BotUser(models.Model):
    """Bot/sayt foydalanuvchisi — `users` jadvali."""

    id = models.AutoField(primary_key=True)
    telegram_id = models.BigIntegerField("Telegram ID", null=True, blank=True)
    full_name = models.CharField("Ism-familiya", max_length=200, blank=True)
    phone_number = models.CharField("Telefon", max_length=30, blank=True)
    language = models.CharField("Til", max_length=5, blank=True)
    created_at = models.DateTimeField("Ro'yxatdan o'tgan sana", null=True, blank=True)

    class Meta:
        managed = False
        db_table = "users"
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering = ["-id"]

    def __str__(self):
        return self.full_name or self.phone_number or f"Foydalanuvchi #{self.pk}"


class BotGrave(models.Model):
    """Foydalanuvchi qabri — `graves` jadvali."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        BotUser, on_delete=models.DO_NOTHING, db_column="user_id",
        related_name="graves", verbose_name="Foydalanuvchi",
    )
    region = models.CharField("Viloyat", max_length=100, blank=True)
    district = models.CharField("Tuman", max_length=100, blank=True)
    cemetery = models.CharField("Qabriston", max_length=200, blank=True)
    deceased_full_name = models.CharField("Marhum", max_length=200, blank=True)
    birth_year = models.IntegerField("Tug'ilgan yili", null=True, blank=True)
    death_year = models.IntegerField("Vafot yili", null=True, blank=True)
    birth_approximate = models.BooleanField("Tug'ilish taxminiy", default=False)
    death_approximate = models.BooleanField("Vafot taxminiy", default=False)
    relationship_status = models.CharField("Qarindoshlik", max_length=50, blank=True)

    class Meta:
        managed = False
        db_table = "graves"
        verbose_name = "Qabr"
        verbose_name_plural = "Qabrlar"
        ordering = ["-id"]

    def __str__(self):
        return self.deceased_full_name or f"Qabr #{self.pk}"


class BotOrder(models.Model):
    """Buyurtma — `orders` jadvali."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        BotUser, on_delete=models.DO_NOTHING, db_column="user_id",
        related_name="orders", verbose_name="Foydalanuvchi",
    )
    full_name = models.CharField("Ism-familiya", max_length=200, blank=True)
    phone_number = models.CharField("Telefon", max_length=30, blank=True)
    deceased_full_name = models.CharField("Marhum", max_length=200, null=True, blank=True)
    total_price = models.IntegerField("Summa", default=0)
    status = models.CharField("Holat", max_length=50, blank=True)
    payment_method = models.CharField("To'lov usuli", max_length=50, null=True, blank=True)
    comment = models.TextField("Izoh", null=True, blank=True)
    created_at = models.DateTimeField("Sana", null=True, blank=True)
    assigned_username = models.CharField("Ishchi", max_length=100, null=True, blank=True)
    assigned_at = models.DateTimeField("Qabul qilingan", null=True, blank=True)
    feedback = models.CharField("Baho", max_length=20, null=True, blank=True)
    feedback_reason = models.TextField("Baho izohi", null=True, blank=True)

    class Meta:
        managed = False
        db_table = "orders"
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        ordering = ["-id"]

    def __str__(self):
        return f"Buyurtma #{self.pk}"


class BotOrderItem(models.Model):
    """Buyurtma elementi — `order_items` jadvali."""

    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(
        BotOrder, on_delete=models.DO_NOTHING, db_column="order_id",
        related_name="items", verbose_name="Buyurtma",
    )
    item_type = models.CharField("Turi", max_length=30, blank=True)
    item_id = models.IntegerField(default=0)
    title = models.CharField("Nomi", max_length=200, blank=True)
    quantity = models.IntegerField("Soni", default=1)
    price = models.IntegerField("Narxi", default=0)

    class Meta:
        managed = False
        db_table = "order_items"
        verbose_name = "Buyurtma elementi"
        verbose_name_plural = "Buyurtma elementlari"

    def __str__(self):
        return self.title or f"Element #{self.pk}"
