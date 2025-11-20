from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
# from .views import get_disease_data

urlpatterns = [
    # path('register/', views.register, name='register'),
    path('', views.landingpage, name='landingpage'),
    path('login/', views.login, name='login'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('report/', views.report, name='report'),
    path('report/add/', views.add_harvest, name='add_harvest'),
    path('api/harvest-data/', views.get_harvest_data, name='get_harvest_data'),
    path('scan/', views.scan, name='scan'),
    path('analyze/', views.analyze_image, name='analyze_image'),
    path('remote/', views.remote, name='remote'),
    path('add_mushroom_bag/', views.add_mushroom_bag, name='add_mushroom_bag'),
    path('logout/', views.logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('analyze/', views.analyze_image, name='analyze_image'),
    path('get-sensor-data/', views.get_sensor_data, name='get_sensor_data'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


