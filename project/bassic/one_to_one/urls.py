from django.urls import path
from . import views

urlpatterns = [
    path('info_data/', views.add_infodata, name='add_infodata'),
    path('contact_success/', views.contact_success, name='contact_success'),
    path('qabr', views.qabr, name='qabr'),
    
]
