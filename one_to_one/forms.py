from django import forms
from .models import Infodata, Qabriston, Image
from django.contrib.auth.models import User

class InfodataForm(forms.ModelForm):
    class Meta:
        model = Infodata
        fields = ['idname', 'ism_familiyasi_marhum', 'yoshi', 'karta_number', 'qabr_soni', 'royhatga_olingan_joy', 'malumotnoma_num', 'uy_manzili', 'olim_sababi', 'qarindoshligi', 'ism_familiyasi_ishonchlivakil', 'telefon_numeri', 'gorkov_bilanmi', 'created_by'   ]
class QabristonForm(forms.ModelForm):
    class Meta:
        model = Qabriston
        fields = ['karta_number', 'qator', 'qabr_soni', 'created_by']  
        
            


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
        fields = ['image', 'malumotnoma_nomeri']