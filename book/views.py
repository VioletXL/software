from django.shortcuts import render

# Create your views here.

from django.shortcuts import render
from .models import Book

def home(request):
    # 修改后：只查询前9本图书
    books = Book.objects.all()[:9]  # 切片[:9]表示取前9条数据
    return render(request, 'book/home.html', {'books': books})

# 搜索函数
def search_books(request):
    query = request.GET.get('q', '')
    if query:
        books = Book.objects.filter(title__icontains=query)
    else:
        books = Book.objects.all()
    return render(request, 'book/search.html', {'books': books, 'query': query})