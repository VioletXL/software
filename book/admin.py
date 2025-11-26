from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Book

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'publish_date', 'price', 'is_available']
    list_filter = ['author', 'publish_date', 'is_available']
    search_fields = ['title', 'author']