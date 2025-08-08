from django.urls import path

from . import views

app_name = 'scorm'

urlpatterns = [
    # Package management
    path('', views.ScormPackageListView.as_view(), name='package_list'),
    path('upload/', views.ScormPackageCreateView.as_view(), name='package_create'),
    path('<slug:slug>/', views.ScormPackageDetailView.as_view(), name='package_detail'),
    path('<slug:slug>/edit/', views.ScormPackageUpdateView.as_view(), name='package_update'),
    path('<slug:slug>/delete/', views.ScormPackageDeleteView.as_view(), name='package_delete'),
    
    # Player and API
    path('<slug:slug>/launch/', views.launch_scorm_package, name='launch'),
    path('api/scorm/', views.scorm_api, name='api'),
    
    # User progress
    path('user/progress/', views.user_scorm_progress, name='user_progress'),
]