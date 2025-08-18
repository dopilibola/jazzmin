# yourapp/validators.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_password_length(value):
    if len(value) < 8:
        raise ValidationError(_("Parol kamida 8 ta belgidan iborat bo'lishi kerak."))

def validate_password_not_numeric(value):
    if value.isdigit():
        raise ValidationError(_("Parol faqat raqamlardan iborat bo'lmasligi kerak."))

def validate_common_password(value):
    common_passwords = ['12345678', 'password', 'qwerty', '123456']
    if value.lower() in common_passwords:
        raise ValidationError(_("Bu parol juda ommabop va xavfsiz emas."))
