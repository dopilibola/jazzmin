from django.shortcuts import render, redirect
from .forms import InfodataForm, QabristonForm
# Create your views here

def add_infodata(request):
    if request.method == 'POST':
        form = InfodataForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('qabr') 
    else:
        form = InfodataForm()
    return render(request, 'infodata.html', {'form':form})

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