from django.contrib import admin
from .models import Infodata, Image
from django.utils.html import format_html


class InfodataAdmin(admin.ModelAdmin):
    list_display = (
        'idname', 'ism_familiyasi_marhum', 'yoshi', 'karta_number',
        'qabr_soni', 'royhatga_olingan_joy', 'malumotnoma_num',
        'uy_manzili', 'olim_sababi', 'qarindoshligi',
        'ism_familiyasi_ishonchlivakil', 'telefon_numeri', 'gorkov_bilanmi'
    )
    list_filter = ('telefon_numeri', 'ism_familiyasi_marhum')


class ImageAdmin(admin.ModelAdmin):
    list_display = ('image', 'malumotnoma_nomeri', 'view_image_button')
    list_filter = ('malumotnoma_nomeri',)
    search_fields = ('malumotnoma_nomeri',)
    ordering = ('-id',)

    def view_image_button(self, obj):
        return format_html(
            '<a class="button" href="{url}" target="_blank">Rasmni ko\'rish</a>',
            url=obj.image.url
        )
    view_image_button.short_description = 'Rasmni ko‘rish'


admin.site.register(Image, ImageAdmin)  
admin.site.register(Infodata, InfodataAdmin)
# admin.site.register(Qabriston, QabristonAdmin)  # Agar kerak bo'lsa, oching
