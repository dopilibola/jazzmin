from django.shortcuts import redirect
from django.contrib import messages


def custom_error_view(request, exception=None):
    """Django xato sahifalari (400/403/404/500) uchun — bosh sahifaga qaytaradi."""
    messages.error(request, "Xatolik yuz berdi, siz bosh sahifaga yo'naltirildingiz.")
    return redirect('index')
