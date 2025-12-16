# book/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # 基础页面

    #path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    #path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
path('login/',auth_views.LoginView.as_view(template_name='book/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # 功能页面
    path('search/', views.search_books, name='search'),
    path('recommendations/', views.recommendations_page, name='recommendations'),

    # API端点
    path('api/recommend/', views.recommend_api, name='api_recommend'),



    path('book/borrow/', views.borrow_book, name='book_borrow'),
path('my-borrows/', views.my_borrow_records, name='my_borrows'),
    path('book/return/<int:book_id>/', views.return_book, name='return_book'),





path('', views.home, name='home'),
]