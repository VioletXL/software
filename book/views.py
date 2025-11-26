from django.shortcuts import render

# Create your views here.

from django.shortcuts import render
from .models import Book

def home(request):
    books = Book.objects.all()  # 获取所有图书
    context = {
        'books': books
    }
    return render(request, 'book/home.html', context)

# 搜索函数
def search_books(request):
    query = request.GET.get('q', '')
    if query:
        books = Book.objects.filter(title__icontains=query)
    else:
        books = Book.objects.all()
    return render(request, 'book/search.html', {'books': books, 'query': query})