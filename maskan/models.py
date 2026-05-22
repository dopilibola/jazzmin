from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission


class User(AbstractUser):
    """Loyihaning autentifikatsiya modeli (AUTH_USER_MODEL = 'maskan.User')."""
    phone_number = models.CharField(max_length=15, unique=True)
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)

    # Guruh va ruxsatlar uchun related_name larni to'g'ri qo'yamiz
    groups = models.ManyToManyField(
        Group,
        related_name='custom_users',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_users',
        blank=True
    )

    def __str__(self):
        return self.username
