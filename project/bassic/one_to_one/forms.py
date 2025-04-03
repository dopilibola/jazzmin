from django import forms
from .models import Infodata, Qabriston

class InfodataForm(forms.ModelForm):
    class Meta:
        model = Infodata
        fields = ['malumotnoma_num', 'ism_familiyasi_marhum', 'qarindoshligi', 'ism_familiyasi_ishonchlivakil', 'telefon_numeri', 'JSHSHIR_ishonch_vakil', 'viloyat', 'tuman', 'mahalla', 'JSHSHIR_olgan', 'gorkov_bilanmi', 'qabriston_joy', 'marhumning_qarindoshligi', 'ism_familiyasi', 'tibbiyot_muassasasi', 'royhatga_olingan_vaqt',]

class QabristonForm(forms.ModelForm):
    class Meta:
        model = Qabriston
        fields = ['karta_number', 'qator', 'qabr_soni']  