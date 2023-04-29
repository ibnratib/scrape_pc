from django.urls import path
from .views import home, ajax_calls

urlpatterns = [
    path('', home, name='home'),
    path("ajax-calls/", ajax_calls, name='ajax_calls'),


]