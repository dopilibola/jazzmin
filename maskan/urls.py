from django.urls import path, include
from .import views
# from django.conf import settings
# from django.conf.urls.static import static



urlpatterns = [
    path('', views.home, name='home' ),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout' ),
    path('register/', views.register_user, name='register'),
    path('update_password/', views.update_password, name='update_password' ),
    path('/one-to-one/', include('one_to_one.urls')),
    path('profile/', views.edit_profile, name='profile'),
    path('profiledet/', views.profile_detail, name='profile_detail'),

]
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)