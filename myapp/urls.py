from django.urls import path
from .views import home, ajax_calls, download_file

urlpatterns = [
    path('', home, name='home'),
    path("ajax-calls/", ajax_calls, name='ajax_calls'),
    path('download/', download_file, name='download_file'),


]