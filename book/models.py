from django.db import models


class Book(models.Model):
    # 对应Excel中的字段：book_id（书籍ID）
    book_id = models.IntegerField(verbose_name="书籍ID", unique=True)  # unique确保ID不重复

    # 对应Excel中的“题名”（即书名）
    title = models.CharField(max_length=200, verbose_name="书名")

    # 对应Excel中的“作者”
    author = models.CharField(max_length=100, verbose_name="作者")

    # 新增：对应Excel中的“出版社”
    publisher = models.CharField(max_length=100, verbose_name="出版社")

    # 新增：对应Excel中的“一级分类”
    category_level1 = models.CharField(max_length=50, verbose_name="一级分类")

    # 新增：对应Excel中的“二级分类”
    category_level2 = models.CharField(max_length=50, verbose_name="二级分类")

    # 保留原模型中的“是否可借”（Excel中没有，用默认值True）
    is_available = models.BooleanField(default=True, verbose_name="是否可借")

    def __str__(self):
        return self.title  # 后台显示书名

    class Meta:
        verbose_name = "图书"
        verbose_name_plural = "图书管理"
        ordering = ['book_id']  # 按书籍ID排序