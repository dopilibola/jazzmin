
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('maskan.urls')),
    path('userdata/', include('one_to_one.urls')),
    path('sale/', include('selle.urls')),
    path('xalqbank/', include('xalqbank.urls')),

]
