from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import InfodataForm, QabristonForm, ImageForm
from .models import Image
import requests
from decouple import config


BOT_TOKEN = config('BOT_TOKEN')
CHAT_ID = config('CHAT_ID')
# Create your views here
# @login_required(login_url='/login/')
# def add_infodata(request):
#     if not request.user.is_authenticated:
#         return render(request, 'login.html')
    
#     else:

#         if request.method == 'POST':
#             form = InfodataForm(request.POST)
#             if form.is_valid():
#                 infodata = form.save(commit=False)
#                 infodata.created_by = request.user
#                 infodata.save()
#                 form.save()
#                 return redirect('contact_success') 
#         else:
#             form = InfodataForm()
#         return render(request, 'infodata.html', {'form':form})





def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {
        'chat_id': CHAT_ID,
        'text': message
    }
    requests.post(url, data=data)

@login_required(login_url='/login/')
def add_infodata(request):
    if not request.user.is_authenticated:
        return render(request, 'login.html')
    else:
        if request.method == 'POST':
            form = InfodataForm(request.POST)
            if form.is_valid():
                infodata = form.save(commit=False)
                infodata.created_by = request.user
                infodata.save()

                # 🔔 Telegramga xabar yuborish
                message = f"Yangi infodata qo‘shildi!\nUser: {request.user.username}\nID: {infodata.id}"
                send_telegram_message(message)

                return redirect('contact_success') 
        else:
            form = InfodataForm()
        return render(request, 'infodata.html', {'form': form})
# views.py


def qabr(request):
    if request.method == 'POST':  
        form = QabristonForm(request.POST)  
        if form.is_valid():  
            form.save()  
            return redirect('contact_success')  
    else:
        form = QabristonForm()  
    return render(request, 'qabr.html', {'form': form})  




def contact_success(request):
    return render(request, 'success.html')




def upload_image(request):
    if request.method == 'POST' and request.FILES['image']:
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('image_list')  # Rasm saqlangandan so'ng rasm ro'yxatiga qaytish
    else:
        form = ImageForm()
    return render(request, 'upload_image.html', {'form': form})




# Rasm ro'yxatini ko'rsatish
def image_list(request):
    images = Image.objects.all()
    return render(request, 'image_list.html', {'images': images})
