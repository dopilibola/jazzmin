from django.urls import path
from . import views

urlpatterns = [
    path('info_data/', views.add_infodata, name='add_infodata'),
    path('contact_success/', views.contact_success, name='contact_success'),
    path('qabr', views.qabr, name='qabr'),
    path('upload/', views.upload_image, name='upload_image'),
    path('images/', views.image_list, name='image_list'),    
    
]








# urlpatterns = [
#     path('info_data/', views.add_infodata, name='add_infodata'),
#     path('contact_success/', views.contact_success, name='contact_success'),
#     path('qabr', views.qabr, name='qabr'),

# ]
