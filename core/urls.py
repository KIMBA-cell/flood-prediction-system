from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('api/locations/', views.locations_data, name='locations_data'),
    path('api/location/<int:location_id>/history/', views.location_history, name='location_history'),
    path('report/', views.report_flood, name='report_flood'),
    path('predict/', views.predict_flood, name='predict_flood'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/assign/<int:report_id>/', views.assign_response, name='assign_response'),
    path('dashboard/update/<int:response_id>/', views.update_response_status, name='update_response_status'),
    path('reset/', views.reset_system, name='reset_system'),
]