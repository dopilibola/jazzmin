
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from maskan import views as maskan_views
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('front.urls')),
    path('maskan/', include('maskan.urls')),
    path('userdata/', include('one_to_one.urls')),
    
    # API endpoints accessible at root to match clients posting to /api/... paths
    path('api/bot-register/', maskan_views.api_bot_register, name='api_bot_register'),
    path('api/bot-start/', maskan_views.api_bot_start, name='api_bot_start'),

]

# Error handlerlarni maskan/views.py dan ulash
handler400 = maskan_views.custom_error_view
handler403 = maskan_views.custom_error_view
handler404 = maskan_views.custom_error_view
handler500 = maskan_views.custom_error_view


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



