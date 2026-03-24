from django.contrib import admin

from apps.botapp.models import (
    CatalogFlowerCategory,
    CatalogFlowerProduct,
    CatalogService,
    TelegramUser,
)


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ("chat_id", "full_name", "phone_number", "username", "language", "created_at", "updated_at")
    list_filter = ("language",)
    search_fields = ("chat_id", "full_name", "phone_number", "username")
    list_editable = ("language",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Telegram", {"fields": ("chat_id", "username", "language")}),
        ("Profil", {"fields": ("full_name", "phone_number")}),
        ("Sanalar", {"fields": ("created_at", "updated_at")}),
    )


# ---------------------------------------------------------------------------
# Catalog: Services
# ---------------------------------------------------------------------------


@admin.register(CatalogService)
class CatalogServiceAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_uz", "category", "price", "is_active", "updated_at")
    list_filter = ("is_active", "category")
    search_fields = ("name_en", "name_ru", "name_uz")
    list_editable = ("price", "is_active")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("category", "is_active", "price", "image")}),
        ("Name", {"fields": ("name_uz", "name_ru", "name_en")}),
        ("Description", {"fields": ("description_uz", "description_ru", "description_en")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )


# ---------------------------------------------------------------------------
# Catalog: Flower categories & products
# ---------------------------------------------------------------------------


class FlowerProductInline(admin.TabularInline):
    model = CatalogFlowerProduct
    extra = 1
    fields = ("name_uz", "name_ru", "name_en", "price", "is_active")


@admin.register(CatalogFlowerCategory)
class CatalogFlowerCategoryAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_uz", "sort_order", "is_active", "product_count")
    list_filter = ("is_active",)
    search_fields = ("name_en", "name_ru", "name_uz")
    list_editable = ("sort_order", "is_active")
    inlines = [FlowerProductInline]

    @admin.display(description="Products")
    def product_count(self, obj):
        return obj.products.count()


@admin.register(CatalogFlowerProduct)
class CatalogFlowerProductAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_uz", "category", "price", "is_active", "updated_at")
    list_filter = ("is_active", "category")
    search_fields = ("name_en", "name_ru", "name_uz")
    list_editable = ("price", "is_active")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("category", "is_active", "price", "image")}),
        ("Name", {"fields": ("name_uz", "name_ru", "name_en")}),
        ("Description", {"fields": ("description_uz", "description_ru", "description_en")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )
