from django.shortcuts import render

# Create your views here.
def home_selle(request):
    return render(request, 'sell_home.html')
