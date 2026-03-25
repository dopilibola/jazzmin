from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'full_name', 'phone_number', 'service',
        # 'flower',  # COMMENTED OUT
        'status', 'total_price', 'created_at',
    )
    list_filter = ('status', 'service', 'created_at')  # 'flower' removed
    search_fields = ('full_name', 'phone_number', 'cemetery_name', 'grave_owner_name')
    list_editable = ('status',)
    readonly_fields = ('user_telegram_id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Customer Info', {
            'fields': ('user_telegram_id', 'full_name', 'phone_number'),
        }),
        ('Order Details', {
            'fields': ('service', 'cemetery_name', 'grave_owner_name', 'order_notes'),  # 'flower' removed
        }),
        ('Status & Payment', {
            'fields': ('status', 'total_price'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
