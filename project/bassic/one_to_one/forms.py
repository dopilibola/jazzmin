from django import forms
from .models import Infodata

class InfodataForm(forms.ModelForm):
    class Meta:
        model = Infodata
        fields = ['first_name', 'last_name', 'idname', 'passportdata', 'data']