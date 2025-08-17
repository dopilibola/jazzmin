from django.urls import path, include
from .import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # Ro'yxatdan o'tish jarayoni

    
    # API endpoints are already exposed at root in project urls; keeping these under /maskan/ if used by clients
    path('api/bot-register/', views.api_bot_register, name='api_bot_register'),
    path('api/bot-start/', views.api_bot_start, name='api_bot_start'),

    
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('', views.home, name='home' ),
    
    path('/one-to-one/', include('one_to_one.urls')),
    path('product/<int:pk>', views.product, name='product' ),
    path('category/<str:foo>', views.category, name='category' ),
    path('qabristonmap/<int:pk>/', views.qabristonmap_view, name='qabristonmap'),
    path('qabristonmap/<int:pk>/search/', views.qabristonmap_search_page, name='qabristonmap_search'),
    path('qabristonmap/<int:pk>/search/ajax/', views.qabristonmap_search_ajax, name='qabristonmap_search_ajax'),

    path("qabriston/maps/", views.qabristonmap_list, name="qabristonmap_list"),
    path("qabriston/maps/create/", views.qabristonmap_create, name="qabristonmap_create"),
    path("qabriston/maps/image/create/", views.qabristonmap_image_create, name="qabristonmap_image_create"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)