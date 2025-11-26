from django.db import models

# Create your models here.

from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=200, verbose_name="书名")
    author = models.CharField(max_length=100, verbose_name="作者")
    publish_date = models.DateField(verbose_name="出版日期")
    price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="价格")
    is_available = models.BooleanField(default=True, verbose_name="是否可借")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "图书"  # 单数名称
        verbose_name_plural = "图书管理"  # 复数名称