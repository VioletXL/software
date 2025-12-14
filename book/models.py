from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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

    # 添加新字段
    # 新增借阅相关字段
    current_borrower = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='borrowed_books'
    )
    borrow_count = models.IntegerField(default=0)  # 借阅次数

    def __str__(self):
        return self.title  # 后台显示书名

    class Meta:
        verbose_name = "图书"
        verbose_name_plural = "图书管理"
        ordering = ['book_id']  # 按书籍ID排序

    def borrow(self, user):
        """借阅图书"""
        if self.is_available:
            self.is_available = False
            self.current_borrower = user
            self.borrow_count += 1
            self.save()

            # 创建借阅记录
            BorrowRecord.objects.create(
                book=self,
                user=user,
                borrow_date=timezone.now()
            )
            return True
        return False

    def return_book(self):
        """归还图书"""
        self.is_available = True
        self.current_borrower = None
        self.save()

        # 更新借阅记录
        record = BorrowRecord.objects.filter(
            book=self,
            return_date__isnull=True
        ).first()
        if record:
            record.return_date = timezone.now()
            record.save()


class BorrowRecord(models.Model):
    """借阅记录模型"""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrow_records')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrow_records')
    borrow_date = models.DateTimeField(default=timezone.now)
    return_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-borrow_date']

    def __str__(self):
        return f"{self.user.username}借阅《{self.book.title}》"