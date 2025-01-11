from django import forms
from .models import Desnoot

class DesnootForm(forms.ModelForm):
    class Meta:
        model = Desnoot
        fields = ['name', 'surname', 'idname', 'patronymic', 'data_of_birth', 'cart_number', 'personal_number', 'mahalla_id', 'mahalla_name']


# class GuardianshipForm(forms.ModelForm):
#     class Meta:
#         model = Guardianship
#         fields = ['name', 'surname', 'idname', 'patronymic', 'data_of_birth', 'cart_number' 'personal_number' 'cart_number_p' ]