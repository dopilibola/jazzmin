from django import forms
from .models import Infodata, Qabriston, Image
from django.contrib.auth.models import User

class InfodataForm(forms.ModelForm):
    class Meta:
        model = Infodata
        fields = ['idname', 'malumotnoma_num', 'ism_familiyasi_marhum', 'qarindoshligi', 'ism_familiyasi_ishonchlivakil', 'telefon_numeri', 'JSHSHIR_ishonch_vakil', ]#'viloyat', 'tuman', 'mahalla', 'JSHSHIR_olgan', 'gorkov_bilanmi',]

class QabristonForm(forms.ModelForm):
    class Meta:
        model = Qabriston
        fields = ['karta_number', 'qator', 'qabr_soni']  
        
            


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super(UserUpdateForm, self).__init__(*args, **kwargs)

        for fieldname in ['username', 'email']:
            self.fields[fieldname].help_text = None


class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ['image', 'description']