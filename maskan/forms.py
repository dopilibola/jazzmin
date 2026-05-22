from django import forms
from django.contrib.auth.models import User



class RegisterPhoneForm(forms.Form):
    phone_number = forms.CharField(max_length=15)

class VerifyCodeForm(forms.Form):
    phone_number = forms.CharField(max_length=15)
    code = forms.CharField(max_length=4)

class SetPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)




class RegisterForm(forms.ModelForm):
    # Parol kamida 6 belgidan iborat bo‘lishi kerak
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)
    class Meta:
        model = User
        fields = ['username', 'password']

class ForgotPasswordForm(forms.Form):
    # Parolni tiklash uchun telefon raqami
    phone_number = forms.CharField()

class ResetPasswordForm(forms.Form):
    # Yangi parol (kamida 6 belgi)
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)