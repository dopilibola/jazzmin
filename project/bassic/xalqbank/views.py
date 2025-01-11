from django.shortcuts import render, redirect
from .forms import DesnootForm, GuardianshipForm


def ulganlik(request):
    if request.method == 'POST':
        form = DesnootForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('POST') 
    else:
        form = DesnootForm()
    return render(request, 'uliklik.html', {'form':form})


def guardianship(request):
    if request.method == 'POST1':
        form = GuardianshipForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('POST1') 
    else:
        form = GuardianshipForm()
    return render(request, 'gurdi.html', {'form':form})