from django.contrib import admin
from .models import Infodata, Qabriston, Image
from django.utils.html import format_html


class InfodataAdmin(admin.ModelAdmin):
    list_display = ('idname', 'ism_familiyasi_marhum', 'yoshi', 'karta_number', 'qabr_soni', 'royhatga_olingan_joy', 'malumotnoma_num', 'uy_manzili', 'olim_sababi', 'qarindoshligi', 'ism_familiyasi_ishonchlivakil', 'telefon_numeri', 'gorkov_bilanmi', 'created_by')
    list_filter = ('telefon_numeri', 'ism_familiyasi_marhum', 'created_by')
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
    list_display = ('image', 'malumotnoma_nomeri', 'view_image_button', 'created_by')
    list_filter = ('malumotnoma_nomeri', 'created_by')
    search_fields = ('malumotnoma_nomeri',)  # Qidirish maydoni
    ordering = ('-id',)  # So'nggi qo'shilgan rasmni birinchi o'rinda ko'rsatish


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
    view_image_button.short_description = 'Rasmni korish'  # Tugmaning nomi




admin.site.register(Image, ImageAdmin)  
admin.site.register(Infodata, InfodataAdmin)
# admin.site.register(Qabriston, QabristonAdmin)
