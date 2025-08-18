from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Product, Category, ProductImage, Location,
    Qabristonmap, Qabristonmap_image, User, Profile
)


# --- Category ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


# --- Location ---
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "latitude", "longitude")
    search_fields = ("name",)


# --- ProductImage inline ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    min_num = 1
    max_num = 10


# --- Product ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "location_link", "category")
    search_fields = ("name", "category__name")
    list_filter = ("category",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, "profile") and request.user.profile.product:
            return qs.filter(category=request.user.profile.product.category)
        return qs.none()

    def location_link(self, obj):
        if obj.location:
            return format_html(
                '<a href="https://www.google.com/maps/search/?api=1&query={},{}" target="_blank">{}</a>',
                obj.location.latitude, obj.location.longitude, obj.location.name
            )
        return "-"
    location_link.short_description = "Lokatsiya (Google Maps)"


# --- ProductImage ---
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "image_preview", "uploaded_at")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
                obj.image.url
            )
        return "Rasm yo‘q"
    image_preview.short_description = "Rasm"


# --- Qabristonmap ---
@admin.register(Qabristonmap)
class QabristonmapAdmin(admin.ModelAdmin):
    list_display = ("ism_familiyasi_marhum", "product", "status", "yosh")
    list_filter = ("status", "product")
    search_fields = ("ism_familiyasi_marhum", "qator", "qabr_soni")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, "profile") and request.user.profile.product:
            return qs.filter(product=request.user.profile.product)
        return qs.none()

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj and hasattr(request.user, "profile") and request.user.profile.product:
            return obj.product == request.user.profile.product
        return False

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return hasattr(request.user, "profile") and request.user.profile.product is not None

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj and hasattr(request.user, "profile") and request.user.profile.product:
            return obj.product == request.user.profile.product
        return False


# --- QabristonmapImage ---
@admin.register(Qabristonmap_image)
class QabristonmapImageAdmin(admin.ModelAdmin):
    list_display = ("image_preview", "product_name", "cemetery_name", "uploaded_at")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;" />',
                obj.image.url
            )
        return "Rasm yo‘q"
    image_preview.short_description = "Rasm"

    def product_name(self, obj):
        return obj.product.ism_familiyasi_marhum
    product_name.short_description = "Marhum Ismi"

    def cemetery_name(self, obj):
        return obj.product.product.name if obj.product.product else "Nomaʼlum qabriston"
    cemetery_name.short_description = "Qabriston nomi"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, "profile") and request.user.profile.product:
            return qs.filter(product__product=request.user.profile.product)
        return qs.none()

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj and hasattr(request.user, "profile") and request.user.profile.product:
            return obj.product.product == request.user.profile.product
        return False

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return hasattr(request.user, "profile") and request.user.profile.product is not None

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj and hasattr(request.user, "profile") and request.user.profile.product:
            return obj.product.product == request.user.profile.product
        return False


# --- CustomUser ---
@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "phone_number", "is_verified")
    search_fields = ("username", "phone_number")
    list_filter = ("is_active", "is_verified", "is_staff")


# --- Profile ---
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user_username",
        "full_name",
        "home_address",
        "phone_number",
        "chat_id",
        "temp_pin",
        "telegram_verified",
    )
    search_fields = ("phone_number", "full_name", "chat_id", "user__username")
    list_filter = ("telegram_verified",)

    def user_username(self, obj):
        return obj.user.username if obj.user else "-"
    user_username.short_description = "Username"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, "profile") and request.user.profile.product:
            return qs.filter(product=request.user.profile.product)
        return qs.none()

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj and hasattr(request.user, "profile") and request.user.profile.product:
            return obj.product == request.user.profile.product
        return False

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return hasattr(request.user, "profile") and request.user.profile.product is not None

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj and hasattr(request.user, "profile") and request.user.profile.product:
            return obj.product == request.user.profile.product
        return False
