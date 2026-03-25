from django.contrib import admin
from .models import Service  # , Flower  # COMMENTED OUT


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_active', 'updated_at')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active', 'price', 'category')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'price', 'description', 'image', 'is_active'),
        }),
        ("Tarjimalar / Translations", {
            'fields': ('name_uz', 'name_ru', 'name_en', 'description_uz', 'description_ru', 'description_en'),
            'classes': ('collapse',),
            'description': "Har bir til uchun nom va tavsif kiriting",
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


# ---------------------------------------------------------------------------
# Flower Admin (COMMENTED OUT)
# ---------------------------------------------------------------------------

# @admin.register(Flower)
# class FlowerAdmin(admin.ModelAdmin):
#     list_display = (
#         'flower_image_preview',
#         'name',
#         'is_plantable',
#         'price',
#         'delivery_fee',
#         'planting_fee',
#         'total_price_display',
#         'is_active',
#     )
#     list_filter = ('is_active', 'is_plantable')
#     search_fields = ('name', 'description')
#     prepopulated_fields = {'slug': ('name',)}
#     list_editable = ('is_plantable', 'price', 'delivery_fee', 'planting_fee', 'is_active')
#     readonly_fields = ('created_at', 'updated_at', 'flower_image_preview_large')
#     list_per_page = 20
#
#     fieldsets = (
#         ("Asosiy ma'lumotlar / Basic Info", {
#             'fields': ('name', 'slug', 'image', 'flower_image_preview_large', 'description', 'is_active'),
#         }),
#         ("Tarjimalar / Translations", {
#             'fields': ('name_uz', 'name_ru', 'name_en', 'description_uz', 'description_ru', 'description_en'),
#             'classes': ('collapse',),
#             'description': "Har bir til uchun nom va tavsif kiriting",
#         }),
#         ("Narxlar / Prices", {
#             'fields': ('price', 'delivery_fee'),
#             'description': "Gul narxi va yetkazib berish narxi",
#         }),
#         ("Ekish sozlamalari / Planting Settings", {
#             'fields': ('is_plantable', 'planting_fee'),
#             'description': "Agar gul ekiladigan bo'lsa, ekish narxini kiriting",
#         }),
#         ('Vaqtlar / Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',),
#         }),
#     )
#
#     @admin.display(description="Rasm")
#     def flower_image_preview(self, obj):
#         from django.utils.html import format_html
#         from django.templatetags.static import static
#         if obj.image:
#             return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.image.url)
#         # Default logo.jpg
#         default_url = static('logo.jpg')
#         return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px; opacity: 0.5;" title="Default rasm" />', default_url)
#
#     @admin.display(description="Katta rasm")
#     def flower_image_preview_large(self, obj):
#         from django.utils.html import format_html
#         from django.templatetags.static import static
#         if obj.image:
#             return format_html('<img src="{}" width="200" style="border-radius: 10px;" />', obj.image.url)
#         # Default logo.jpg
#         default_url = static('logo.jpg')
#         return format_html(
#             '<img src="{}" width="200" style="border-radius: 10px; opacity: 0.5;" />'
#             '<br><small style="color: #999;">⚠️ Rasm yuklanmagan - default logo ko\'rsatilmoqda</small>',
#             default_url
#         )
#
#     @admin.display(description="Turi")
#     def flower_type_icon(self, obj):
#         from django.utils.html import format_html
#         if obj.is_plantable:
#             return format_html('<span title="Ekiladigan gul" style="font-size: 1.2em;">🌱</span>')
#         return format_html('<span title="Qo\'yiladigan gul" style="font-size: 1.2em;">💐</span>')
#
#     @admin.display(description="Ekish narxi")
#     def planting_fee_display(self, obj):
#         if obj.is_plantable and obj.planting_fee:
#             return f"{obj.planting_fee:,.0f} so'm"
#         return "—"
#
#     @admin.display(description="Jami narx")
#     def total_price_display(self, obj):
#         from django.utils.html import format_html
#         price = float(obj.total_price) if obj.total_price else 0
#         return format_html('<strong>{} so\'m</strong>', f"{price:,.0f}")
