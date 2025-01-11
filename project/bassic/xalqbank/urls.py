from django.urls import path
from .import views

urlpatterns = [
    path('ulganlik_puli/', views.ulganlik, name='ulganlik'),
    path('gur_data/', views.guardianship, name='guardianship'),
]
