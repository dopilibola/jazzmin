from django.shortcuts import render
import requests
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from decouple import config
BOT_TOKEN = config('BOT_TOKEN')
CHAT_ID = config('CHAT_ID')


def index(request):
    return render(request, 'index.html')

def login2(request):
    return render(request, 'login2.html')



@csrf_exempt  # (Agar JSdan POST bo‘lsa, CSRF tokeni bo'lmasa)
def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')

        if not name or not phone:
            return JsonResponse({'ok': False, 'error': 'Maʼlumot to‘liq emas'})

        message = f"🆕 Yangi murojaat:\n\n👤 Ismi: {name}\n📞 Telefon: {phone}"
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': CHAT_ID,
            'text': message
        }

        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return JsonResponse({'ok': True, 'message': 'Yuborildi'})
        else:
            return JsonResponse({'ok': False, 'message': 'Telegramga yuborib bo‘lmadi'})

    return JsonResponse({'ok': False, 'error': 'Faqat POST so‘rovi qabul qilinadi'})
