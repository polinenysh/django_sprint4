from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('about/', views.About.as_view(), name='about'),  # О сайте
    path('rules/', views.Rules.as_view(), name='rules'),  # Правила сообщества
]
