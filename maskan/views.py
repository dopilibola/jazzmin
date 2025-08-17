from django.shortcuts import render, redirect 

from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from .models import  Product, Category, Qabristonmap, Location, Profile
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from collections import defaultdict, OrderedDict
from django.db.models import Q
from .forms import LoginForm, QabristonmapForm, QabristonmapImageForm
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

import random
import json
import traceback


# ------------------------------------------
@csrf_exempt
def api_bot_register(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Faqat POST kerak'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'JSON xato'}, status=400)

    chat_id = data.get('chat_id', '').strip()
    full_name = data.get('full_name', '').strip()
    phone_number = data.get('phone_number', '').strip()
    home_address = data.get('home_address', '').strip()
    password = data.get('password', '').strip()

    if not phone_number or not password or not chat_id:
        return JsonResponse({'status': 'error', 'message': 'phone_number, password va chat_id kerak'}, status=400)

    User = get_user_model()

    # To'g'ri filter: Profile modelida chat_id va telegram_verified bor deb faraz qilamiz
    profile = Profile.objects.filter(
        user__isnull=False,
        telegram_verified=True,
        chat_id=chat_id
    ).first()
    if not profile:
        profile = Profile.objects.filter(
            phone_number=phone_number,
            telegram_verified=True,
            user__isnull=False
        ).first()

    if profile and profile.user:
        return JsonResponse({
            'status': 'exists',
            'username': profile.user.username,
            'password': profile.temp_pin or '',
            'message': "Foydalanuvchi allaqachon ro‘yxatdan o‘tgan"
        })

    # Yangi user yaratamiz
    username = phone_number
    if User.objects.filter(username=username).exists():
        username = f"{phone_number}_{random.randint(1000, 9999)}"

    try:
        user = User.objects.create_user(
            username=username,
            password=password,
            phone_number=phone_number
        )
        user.is_verified = True
        user.save()
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Foydalanuvchi yaratishda xatolik: {str(e)}'}, status=500)

    # Profile yaratishda xatolik bo'lishi mumkin, uni ham try-except bilan o'rab oling
    try:
        profile = Profile.objects.filter(phone_number=phone_number).first()
        if profile:
            # Agar profil boshqa userga biriktirilgan bo‘lsa, xatolik qaytaramiz
            if profile.user and profile.user != user:
                return JsonResponse({'status': 'error', 'message': 'Bu raqam boshqa foydalanuvchiga biriktirilgan.'}, status=400)
        else:
            profile = Profile(phone_number=phone_number)
        profile.user = user
        profile.full_name = full_name
        profile.home_address = home_address
        profile.telegram_verified = True
        profile.chat_id = chat_id
        profile.temp_pin = password
        profile.save()
        created = True
    except Exception as e:
        print("PROFILE ERROR:", e)
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Profile yaratishda xatolik: {str(e)}'}, status=500)

    return JsonResponse({
        'status': 'ok',
        'username': username,
        'password': password,
        'profile_created': created
    })


@csrf_exempt
def api_bot_start(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Faqat POST kerak'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'JSON xato'}, status=400)

    chat_id = (data.get('chat_id') or '').strip()
    if not chat_id:
        return JsonResponse({'status': 'error', 'message': 'chat_id kerak'}, status=400)

    profile = Profile.objects.filter(
        user__isnull=False,
        telegram_verified=True,
        chat_id=chat_id
    ).select_related('user').first()

    if not profile or not profile.user:
        return JsonResponse({'status': 'not_found', 'message': "Ro'yxatdan o'tmagansiz. Iltimos, ro'yxatdan o'tish uchun ma'lumotlarni yuboring."})

    user = profile.user
    # Agar oldindan saqlangan parol (temp_pin) bo'lsa, shu parolni qaytaramiz
    if profile.temp_pin:
        return JsonResponse({
            'status': 'ok',
            'username': user.username,
            'password': profile.temp_pin,
            'message': 'Hisob topildi. Mavjud parol qaytarildi.'
        })

    # Aks holda, bir marta parol yaratamiz va shu parolni keyin ham qaytaramiz
    new_password = str(random.randint(100000, 999999))
    try:
        user.set_password(new_password)
        user.save()
        profile.temp_pin = new_password
        profile.save()
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Parolni yaratishda xatolik: {str(e)}'}, status=500)

    return JsonResponse({
        'status': 'ok',
        'username': user.username,
        'password': new_password,
        'message': 'Hisob topildi. Yangi parol yaratildi.'
    })

# ============================
# Kirish va chiqish
# ============================
def login_user(request):
    # 🔹 Agar foydalanuvchi allaqachon login qilgan bo‘lsa → home sahifaga qaytadi
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user is not None:
                try:
                    profile = user.profile
                    if not profile.telegram_verified:
                        messages.error(request, "Iltimos, avval Telegram orqali tasdiqlang.")
                        return redirect('login')
                except Profile.DoesNotExist:
                    pass

                login(request, user)
                return redirect('home')
            else:
                messages.error(request, "Login yoki parol noto'g'ri.")
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

def logout_user(request):
    auth_logout(request)
    messages.success(request, "Tizimdan chiqildi.")
    return redirect('login')

def product(request, pk):
    product = Product.objects.get(id=pk)
    return render(request, 'product.html', {'product':product})



def qabristonmap_view(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # Faqat shu productga tegishli qabrlar
    qabrlar = Qabristonmap.objects.filter(product=product).prefetch_related('images')

    # Qator bo‘yicha guruhlash
    grouped_by_row = defaultdict(list)
    for qabr in qabrlar:
        grouped_by_row[qabr.qator].append(qabr)

    # Qator va qabr_soni bo‘yicha tartiblash
    grouped_qabrlar = OrderedDict()
    for qator in sorted(grouped_by_row, key=lambda x: int(x) if str(x).isdigit() else 999):
        sorted_qabrlar = sorted(
            grouped_by_row[qator],
            key=lambda q: int(q.qabr_soni) if str(q.qabr_soni).isdigit() else 999
        )
        grouped_qabrlar[qator] = sorted_qabrlar

    return render(request, 'qabristonmap.html', {
        'product': product,
        'grouped_qabrlar': grouped_qabrlar,
    })





def category(request, foo):
    # spaces
    foo = foo.replace('-', ' ')
    #category url 
    try:
        category = Category.objects.get(name=foo)
        products = Product.objects.filter(category=category)
        return render(request, 'category.html', {'products':products, 'category':category})

    except:
        messages.success(request, ("Category dosn't exist  "))
        return redirect('home')
    

def home(request):
    products = Product.objects.all()
    searched_products = []
    searched_graves = []
    query = None
    is_qabriston_egasi = False

    if request.user.is_authenticated:
        is_qabriston_egasi = request.user.groups.filter(name='Qabriston Egasi').exists()

    if request.method == "POST":
        query = request.POST.get("searched", "").strip()
        if query:
            searched_products = Product.objects.filter(name__icontains=query)
            (
                Q(ism_familiyasi_marhum__icontains=query) |
                Q(product__name__icontains=query)
            )

    locations = Location.objects.all()

    context = {
        'products': products,
        'is_qabriston_egasi': is_qabriston_egasi,
        'searched_products': searched_products,
        'searched_graves': searched_graves,
        'query': query,
        'locations': locations 
    }
    return render(request, 'home.html', context)



def qabristonmap_search_page(request, pk):
    qabriston = get_object_or_404(Qabristonmap, pk=pk)
    qidiruv = request.GET.get('qidiruv', '')

    # Qabrlarni faqat shu qabriston uchun
    all_qabrlar = Qabristonmap.objects.filter(qabriston=qabriston).select_related()
    
    # Qabrlarni qator bo‘yicha guruhlash
    grouped_qabrlar = {}
    for qabr in all_qabrlar:
        if str(qidiruv).lower() in str(qabr.ism_familiyasi_marhum).lower():
            grouped_qabrlar.setdefault(qabr.qator, []).append(qabr)
        elif not qidiruv:
            grouped_qabrlar.setdefault(qabr.qator, []).append(qabr)

    context = {
        'product': qabriston,  # modalda ishlatiladi
        'grouped_qabrlar': grouped_qabrlar,
    }
    return render(request, 'qabristonmap.html', context)

def qabristonmap_search_ajax(request, pk):
    # Qabriston ob'ektini olamiz
    qabriston = get_object_or_404(Product, pk=pk)
    qidiruv = request.GET.get('qidiruv', '')

    # Shu qabristonga tegishli qabrlar
    qabrlar = Qabristonmap.objects.filter(product=qabriston)

    # Qidiruv bo‘lsa — filter
    if qidiruv:
        qabrlar = qabrlar.filter(
            Q(ism_familiyasi_marhum__icontains=qidiruv) |
            Q(years_old__icontains=qidiruv) |
            Q(years_new__icontains=qidiruv) |
            Q(yosh__icontains=qidiruv)
        ) 

    # Json uchun natijalar
    result = []
    for qabr in qabrlar:
        result.append({
            'id': qabr.id,
            'ism_familiyasi': qabr.ism_familiyasi_marhum,
            'qator': qabr.qator,
            'qabr_soni': qabr.qabr_soni,
            'status': qabr.status,
        })

    return JsonResponse({'results': result})



def _get_assigned_product_or_403(user):
    """
    User'ga admin paneldan biriktirilgan bitta Product (qabriston) ni olib keladi.
    Bo'lmasa 403.
    """
    if not hasattr(user, "profile") or not user.profile.product:
        raise PermissionDenied("Sizga qabriston biriktirilmagan. Administrator bilan bog'laning.")
    return user.profile.product


@login_required(login_url="/login/")
def qabristonmap_list(request):
    """
    Foydalanuvchi faqat o'ziga biriktirilgan Product ichidagi marhumlar ro'yxatini ko'radi.
    """
    product = _get_assigned_product_or_403(request.user)
    items = Qabristonmap.objects.filter(product=product).order_by("-id")
    return render(request, "qabriston/qabristonmap_list.html", {"items": items, "product": product})


@login_required(login_url="/login/")
def qabristonmap_create(request):
    """
    Yangi Qabristonmap qo'shish (faqat o'ziga biriktirilgan Product ichida).
    """
    product = _get_assigned_product_or_403(request.user)

    if request.method == "POST":
        form = QabristonmapForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.product = product  # 🔒 muhim: user o'zi tanlamaydi, majburan biriktiramiz
            obj.save()
            messages.success(request, "Marhum ma'lumoti saqlandi.")
            return redirect("qabristonmap_list")
        else:
            messages.error(request, "Formada xatolik bor. Iltimos tekshirib qayta yuboring.")
    else:
        form = QabristonmapForm()

    return render(request, "qabriston/qabristonmap_form.html", {"form": form, "product": product})


@login_required(login_url="/login/")
def qabristonmap_image_create(request):
    """
    Qabriston rasmi yuklash. Foydalanuvchi faqat o'z Productiga tegishli Qabristonmap larni ko'radi.
    """
    _ = _get_assigned_product_or_403(request.user)

    if request.method == "POST":
        form = QabristonmapImageForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            img = form.save(commit=False)
            # Qo'shimcha xavfsizlik: tanlangan qabristonmap ham userga tegishli bo'lsin
            assigned_product = request.user.profile.product
            if img.product.product_id != assigned_product.id:
                raise PermissionDenied("Sizga tegishli bo'lmagan marhumga rasm yuklay olmaysiz.")
            img.save()
            messages.success(request, "Rasm yuklandi.")
            return redirect("qabristonmap_list")
        else:
            messages.error(request, "Formada xatolik bor. Iltimos tekshirib qayta yuboring.")
    else:
        form = QabristonmapImageForm(user=request.user)

    return render(request, "qabriston/qabristonmap_image_form.html", {"form": form})




def custom_error_view(request, exception=None):
    if request.user.is_authenticated:   # login bo'lganmi?
        messages.error(request, "Xatolik yuz berdi, siz Bosh sahifaga yo‘naltirildingiz.")
        return redirect('home')         
    else:
        messages.error(request, "Xatolik yuz berdi, tizimga kirishingiz kerak.")
        return redirect('login')     