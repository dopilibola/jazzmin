from django import forms
from .models import Infodata

class InfodataForm(forms.ModelForm):
    class Meta:
        model = Infodata
        fields = ['malumotnoma_num', 'full_name', 'vafot_etgan_sana', 'dalolatnoma_sanasi', 'dalolatnoma_raqami', 'olim_sababi', 'qayt_qilingan_FHDY_bolim', 'tugilgan_vaqti', 'yosh', 'vafot_etgan_joy', 'malumot_berilgan_sana', 'vafot_etgan_shaxsning_JSHIR', 'tibbiyot_muassasasi']