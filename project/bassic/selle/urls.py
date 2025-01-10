from . import views
from django.urls import path

urlpatterns = [
    path('home_selle/', views.home_selle, name='home_selle'),
]
