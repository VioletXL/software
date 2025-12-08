import os
import pandas as pd
from django.core.wsgi import get_wsgi_application

# 配置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bool_project.settings')
application = get_wsgi_application()

# 导入Book模型
from book.models import Book


def import_books_from_excel():
    print("开始读取数据文件...")
    try:
        df = pd.read_csv('item.csv', encoding='utf-8')
        print(f"文件读取成功，共 {len(df)} 行数据")

        success_count = 0  # 记录成功导入的数量
        duplicate_count = 0  # 记录重复的数量

        for index, row in df.iterrows():
            if index == 0 and row['book_id'] == 'book_id':
                print("跳过表头行")
                continue

            # 检查当前 book_id 是否已存在
            current_book_id = row['book_id']
            if Book.objects.filter(book_id=current_book_id).exists():
                duplicate_count += 1
                print(f"第 {index + 1} 行：book_id={current_book_id} 已存在，跳过")
                continue

            # 保存新数据
            book = Book(
                book_id=current_book_id,
                title=row['题名'],
                author=row['作者'],
                publisher=row['出版社'],
                category_level1=row['一级分类'],
                category_level2=row['二级分类']
            )
            book.save()
            success_count += 1
            print(f"第 {index + 1} 行导入成功：{row['题名']}")

        print(f"导入完成：成功 {success_count} 条，跳过重复 {duplicate_count} 条")
    except Exception as e:
        print(f"发生错误：{str(e)}")
        print(f"发生错误：{str(e)}")  # 捕获并打印错误


if __name__ == '__main__':
    import_books_from_excel()


