from django.contrib import admin
from .models import Infodata, Qabriston, Image
from django.utils.html import format_html


class InfodataAdmin(admin.ModelAdmin):
    list_display = ('malumotnoma_num', 'ism_familiyasi_marhum', 'qarindoshligi', 'ism_familiyasi_ishonchlivakil', 'telefon_numeri', 'JSHSHIR_ishonch_vakil', 'created_by')
    list_filter = ('telefon_numeri', 'ism_familiyasi_marhum')
    readonly_fields = ('created_by',)  # 'created_by' maydoni faqat o'qilishi mumkin

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user  # Agar 'created_by' maydoni bo'sh bo'lsa, joriy foydalanuvchini saqlash
        super().save_model(request, obj, form, change)

class QabristonAdmin(admin.ModelAdmin):
    list_display = ('karta_number', 'qator', 'qabr_soni', 'created_by')  # 'qabr_son' emas, 'qabr_soni' ishlatish kerak
    readonly_fields = ('created_by',)  # 'created_by' maydoni faqat o'qilishi mumkin

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user  # Agar 'created_by' maydoni bo'sh bo'lsa, joriy foydalanuvchini saqlash
        super().save_model(request, obj, form, change)





class ImageAdmin(admin.ModelAdmin):
    readonly_fields = ('created_by',)
    list_display = ('image', 'description', 'view_image_button', 'created_by')

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user  # Agar 'created_by' maydoni bo'sh bo'lsa, joriy foydalanuvchini saqlash
        super().save_model(request, obj, form, change)

    # Maxsus tugma yaratish
    def view_image_button(self, obj):
        return format_html(
            '<a class="button" href="{url}" target="_blank">Rasmni ko\'rish</a>',
            url=obj.image.url  # Rasmga to'liq URL
        )
    view_image_button.short_description = 'Rasmni ko\'rish'  # Tugmaning nomi




admin.site.register(Image, ImageAdmin)  
admin.site.register(Infodata, InfodataAdmin)
admin.site.register(Qabriston, QabristonAdmin)
