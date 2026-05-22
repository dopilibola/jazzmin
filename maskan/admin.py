from django.contrib import admin
from .models import User


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "phone_number", "is_verified")
    search_fields = ("username", "phone_number")
    list_filter = ("is_active", "is_verified", "is_staff")
