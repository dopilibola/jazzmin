from django.urls import path, include
from .import views
# from ..one_to_one import views, url

urlpatterns = [
    path('', views.home, name='home' ),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout' ),
    path('register/', views.register_user, name='register'),
    path('update_password/', views.update_password, name='update_password' ),
    path('/one-to-one/', include('one_to_one.urls')),
]
