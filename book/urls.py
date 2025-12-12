# book/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # 基础页面
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # 功能页面
    path('search/', views.search_books, name='search'),
    path('recommendations/', views.recommendations_page, name='recommendations'),

    # API端点
    path('api/recommend/', views.recommend_api, name='api_recommend'),
]