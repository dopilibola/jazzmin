
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from maskan import views as maskan_views
from apps.botapp.views import analytics_view, analytics_api, users_tracking_view, user_detail_view
from apps.botapp.order_analytics_views import (
    order_analytics_dashboard,
    order_analytics_orders,
    order_analytics_order_detail,
    order_analytics_workers,
    order_analytics_worker_detail,
    order_analytics_api,
    order_analytics_salary,
    order_analytics_salary_export,
)

urlpatterns = [
    # User Analytics (existing)
    path('admin/analytics/', analytics_view, name='admin_analytics'),
    path('admin/analytics/api/', analytics_api, name='admin_analytics_api'),
    path('admin/analytics/users/', users_tracking_view, name='admin_analytics_users'),
    path('admin/analytics/users/<int:telegram_id>/', user_detail_view, name='admin_user_detail'),

    # Order Analytics (NEW - separate module)
    path('admin/order-analytics/', order_analytics_dashboard, name='order_analytics_dashboard'),
    path('admin/order-analytics/orders/', order_analytics_orders, name='order_analytics_orders'),
    path('admin/order-analytics/orders/<int:order_id>/', order_analytics_order_detail, name='order_analytics_order_detail'),
    path('admin/order-analytics/workers/', order_analytics_workers, name='order_analytics_workers'),
    path('admin/order-analytics/workers/<int:telegram_id>/', order_analytics_worker_detail, name='order_analytics_worker_detail'),
    path('admin/order-analytics/salary/', order_analytics_salary, name='order_analytics_salary'),
    path('admin/order-analytics/salary/export/', order_analytics_salary_export, name='order_analytics_salary_export'),
    path('admin/order-analytics/api/', order_analytics_api, name='order_analytics_api'),

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



