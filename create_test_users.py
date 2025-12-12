# create_test_users.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bool_project.settings')
django.setup()

from django.contrib.auth.models import User

# 创建测试用户
test_users = [
    {
        'username': 'demo_user',
        'email': 'demo@example.com',
        'password': 'demo1234',
        'first_name': '演示',
        'last_name': '用户'
    },
    {
        'username': 'book_lover',
        'email': 'booklover@example.com',
        'password': 'book1234',
        'first_name': '爱书',
        'last_name': '人士'
    },
    {
        'username': 'reader_2025',
        'email': 'reader@example.com',
        'password': 'read1234',
        'first_name': '阅读',
        'last_name': '爱好者'
    }
]

for user_data in test_users:
    if not User.objects.filter(username=user_data['username']).exists():
        user = User.objects.create_user(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name']
        )
        print(f"创建用户: {user.username}")
    else:
        print(f"用户已存在: {user_data['username']}")

print("测试用户创建完成！")