from django.contrib import admin
from .models import Book  # 导入你的Book模型


class BookAdmin(admin.ModelAdmin):
    # 后台列表页显示的字段（使用当前模型中存在的字段）
    list_display = ['book_id', 'title', 'author', 'publisher', 'category_level1', 'is_available']

    # 可筛选的字段（使用当前模型中存在的字段）
    list_filter = ['category_level1', 'category_level2', 'is_available']

    # 可搜索的字段
    search_fields = ['title', 'author', 'publisher']


# 注册模型和管理类
admin.site.register(Book, BookAdmin)