from django.db import models
from django.core.validators import RegexValidator
from django.utils.html import format_html
from django.contrib.auth.models import User, AbstractUser, Group, Permission





class User(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True)
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)

    # Guruh va ruxsatlar uchun related_name larni to‘g‘ri qo‘yamiz
    groups = models.ManyToManyField(
        Group,
        related_name='custom_users',  # eski user_set bilan to‘qnashmaydi
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_users',  # eski user_set bilan to‘qnashmaydi
        blank=True
    )

    def __str__(self):
        return self.username


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True)
    temp_pin = models.CharField(max_length=12, blank=True, null=True)
    telegram_verified = models.BooleanField(default=False)
    full_name = models.CharField(max_length=150, blank=True)
    home_address = models.CharField(max_length=255, blank=True)
    chat_id = models.CharField(max_length=50, blank=True, null=True)

    product = models.ForeignKey(
        'Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Ruxsat berilgan qabriston"
    )


    def __str__(self):
        return self.phone_number or (self.user.username if self.user else "No User")






class Category(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Tuman Shahar"
        verbose_name_plural = "Tumanlar Shaharlar"


class Location(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Lokatsiya"
        verbose_name_plural = "Lokatsiyalar"




class Product(models.Model):  # Qabriston
    name = models.CharField("Qabriston nomi", max_length=100)
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Lokatsiya"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name="Tuman/Shahar"
    )
    description = models.TextField("Izoh", blank=True, default='')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Qabriston"
        verbose_name_plural = "Qabristonlar"



class ProductImage(models.Model):
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="Qabriston"
    )
    image = models.ImageField("Rasm", upload_to='uploads/products/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} rasmi"

    def image_preview(self):
        if self.image:
            return format_html('<a href="{}" target="_blank"><img src="{}" width="100" /></a>', self.image.url, self.image.url)
        return "Rasm mavjud emas"

    image_preview.short_description = "Ko‘rinish"

    class Meta:
        verbose_name = "Qabriston rasmi"
        verbose_name_plural = "Qabriston rasmlari"


only_year_validator = RegexValidator(
    regex=r'^\d{4}$',
    message='Faqat 4 xonali yil kiriting, masalan: 1990 yoki 2023'
)

class Qabristonmap(models.Model):
    STATUS_CHOICES = [
        ('green', 'Yashil'),
        ('yellow', 'Sariq'),
        ('red', 'Qizil'),
    ]

    ism_familiyasi_marhum = models.CharField(max_length=20, blank=True)
    years_old = models.CharField(
        max_length=4,
        blank=True,
        validators=[only_year_validator],
        verbose_name='Tug‘ilgan yil'
    )
    years_new = models.CharField(
        max_length=4,
        blank=True,
        validators=[only_year_validator],
        verbose_name='Vafot yili'
    )
    years = models.CharField(max_length=20, blank=True, verbose_name='Yil oraliği')
    yosh = models.PositiveIntegerField(null=True, blank=True, verbose_name='Yosh')
    qator = models.CharField(max_length=20, blank=True)
    qabr_soni = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='green')

    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='qabristonmaps',
        verbose_name="Qabriston"
    )

    def save(self, *args, **kwargs):
        if self.years_old and self.years_new:
            try:
                old_year = int(self.years_old)
                new_year = int(self.years_new)
                self.years = f"{old_year} - {new_year}"
                self.yosh = (new_year - old_year) + 1 if new_year >= old_year else None
            except ValueError:
                self.years = ""
                self.yosh = None
        else:
            self.years = ""
            self.yosh = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ism_familiyasi_marhum} ({self.status})"

    class Meta:
        verbose_name = "Marhum"
        verbose_name_plural = "Marhumlar"


        


class Qabristonmap_image(models.Model):
    product = models.ForeignKey(Qabristonmap, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='uploads/cam/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.ism_familiyasi_marhum} image"
 
    class Meta:
        verbose_name = "qabrnig rasmi"
        verbose_name_plural = "Qabrning rasmlari"