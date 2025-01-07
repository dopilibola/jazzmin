from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignUpForm
from django.shortcuts import redirect 

# Create your views here.


def home(request):
    return render(request, 'home.html',)

def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user) 
            messages.success(request, ('Login successful'))
            return redirect('home')
        else:
            messages.success(request, ('error try again....'))
            return redirect('login')
    else: 
        return render(request, 'login.html', {})
    
def logout_user(request):
    logout(request)
    messages.success(request, 'Logged out succesfully')
    return redirect('home')
        
def register_user(request):
    form = SignUpForm()
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            # log in user
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, ('Username Creted - plesse fill out your user info below...'))
            return redirect('update_info')
        else:
            messages.error(request, ('Registration failed. Please try again.'))
            return redirect('register')
    else:
        return render(request, 'register.html', {'form':form })
    
def update_password(request):
    if request.user.is_authenticated:
        current_user = request.user

        if request.method == 'POST':
            form = ChangePasswordForm(current_user, request.POST)

            if form.is_valid():
                form.save()
                messages.success(request, "Your password has been update please log in agin")
                # login(request, current_user)
                return redirect('login')
            else: 
                for error in list(form.errors.values()):
                    messages.error(request, error)
                    return redirect('update_password')
        else:
            form = ChangePasswordForm(current_user)
            return render(request, "update_password.html", {'form':form})
    else:
        messages.success(request, "you must be logged in to view that page ! ")
        return redirect('home')