"""Bot/sayt ma'lumotlarini Django admin panelida ko'rsatish."""
from django.contrib import admin

from .models import BotGrave, BotOrder, BotOrderItem, BotUser


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "phone_number", "telegram_id", "language", "created_at")
    search_fields = ("full_name", "phone_number")
    list_filter = ("language",)
    ordering = ("-id",)

    def has_add_permission(self, request):
        return False  # foydalanuvchi faqat bot/sayt orqali qo'shiladi

    def has_delete_permission(self, request, obj=None):
        return False  # xavfsizlik uchun (bog'liq ma'lumotlar o'chib ketmasligi uchun)


@admin.register(BotGrave)
class BotGraveAdmin(admin.ModelAdmin):
    list_display = ("id", "deceased_full_name", "user", "cemetery", "district",
                    "relationship_status")
    search_fields = ("deceased_full_name", "cemetery", "district")
    ordering = ("-id",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class BotOrderItemInline(admin.TabularInline):
    model = BotOrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("item_type", "item_id", "title", "quantity", "price")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(BotOrder)
class BotOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "full_name", "phone_number", "status",
                    "total_price", "created_at")
    search_fields = ("full_name", "phone_number", "deceased_full_name")
    list_filter = ("status",)
    ordering = ("-id",)
    inlines = [BotOrderItemInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
