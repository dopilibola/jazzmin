from django import forms
from django.contrib.auth.models import User
from .models import Qabristonmap, Qabristonmap_image



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

class LoginForm(forms.Form):
    # Kirish uchun login va parol
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class ForgotPasswordForm(forms.Form):
    # Parolni tiklash uchun telefon raqami
    phone_number = forms.CharField()

class ResetPasswordForm(forms.Form):
    # Yangi parol (kamida 6 belgi)
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)



class QabristonmapForm(forms.ModelForm):
    class Meta:
        model = Qabristonmap
        # product foydalanuvchi tomonidan tanlanmaydi — view'da avtomatik biriktiramiz
        fields = [
            "ism_familiyasi_marhum",
            "years_old",
            "years_new",
            "qator",
            "qabr_soni",
            "status",
        ]

class QabristonmapImageForm(forms.ModelForm):
    class Meta:
        model = Qabristonmap_image
        fields = ["product", "image"]  # 'product' bu yerda Qabristonmap FK (tanlash uchun)
        widgets = {
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"})
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Faqat userga ruxsat berilgan Product ichidagi Qabristonmaplar ro'yxatini ko'rsatamiz
        if user and hasattr(user, "profile") and user.profile.product:
            self.fields["product"].queryset = Qabristonmap.objects.filter(
                product=user.profile.product
            )
        else:
            # Hech narsa ko'rsatmaymiz — ruxsat yo'q
            self.fields["product"].queryset = Qabristonmap.objects.none()