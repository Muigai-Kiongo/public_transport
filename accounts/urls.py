from django.urls import path
from .import views


urlpatterns = [
    path('register/',views.signUp , name ='register' ),
    path('profile/', views.profile, name='profile'),
]