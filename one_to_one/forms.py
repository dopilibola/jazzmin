from django import forms
from .models import Infodata, Qabriston, Image


class InfodataForm(forms.ModelForm):
    class Meta:
        model = Infodata
        fields = ['idname', 'ism_familiyasi_marhum', 'yoshi', 'karta_number', 'qabr_soni', 'royhatga_olingan_joy', 'malumotnoma_num', 'uy_manzili', 'olim_sababi', 'qarindoshligi', 'ism_familiyasi_ishonchlivakil', 'telefon_numeri', 'gorkov_bilanmi']
class QabristonForm(forms.ModelForm):
    class Meta:
        model = Qabriston
        fields = ['karta_number', 'qator', 'qabr_soni']




class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ['image', 'malumotnoma_nomeri']