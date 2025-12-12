# book/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
import json
from .models import Book
from .forms import CustomUserCreationForm, CustomAuthenticationForm


# 首页视图
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


# 推荐API接口
@csrf_exempt
def recommend_api(request):
    """推荐API接口"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id', 'anonymous')
            top_n = data.get('top_n', 6)

            print(f"收到推荐请求 - 用户: {user_id}, 数量: {top_n}")

            # 方法1：按借阅次数降序（最热门）
            books = Book.objects.filter(is_available=True).order_by('-borrow_count')[:top_n]

            # 如果热门图书不够，补充随机图书
            if books.count() < top_n:
                remaining = top_n - books.count()
                extra_books = Book.objects.filter(
                    is_available=True
                ).exclude(
                    id__in=[b.id for b in books]
                ).order_by('?')[:remaining]
                books = list(books) + list(extra_books)

            book_list = []
            for book in books:
                # 确定分类显示
                if book.category_level1:
                    category = book.category_level1
                elif book.category_level2:
                    category = book.category_level2
                else:
                    category = '未分类'

                # 确定状态
                status = '可借阅' if book.is_available else '已借出'

                # 如果有评分，显示评分
                rating_text = ''
                if book.rating > 0:
                    rating_text = f'{book.rating:.1f}'

                book_list.append({
                    'title': book.title,
                    'author': book.author or '未知',
                    'publisher': book.publisher or '未知',
                    'category': category,
                    'status': status,
                    'rating': rating_text,
                    'description': book.description or '',
                    'borrow_count': book.borrow_count,
                    'book_id': book.book_id or str(book.id)
                })

            print(f"成功返回 {len(book_list)} 条推荐")

            return JsonResponse({
                'success': True,
                'user_id': user_id,
                'recommendations': book_list
            })

        except Exception as e:
            print(f"推荐API错误: {e}")
            import traceback
            traceback.print_exc()

            # 返回示例数据作为备用
            return JsonResponse({
                'success': True,
                'user_id': user_id,
                'recommendations': get_fallback_recommendations(top_n)
            })

    return JsonResponse({'error': '只支持POST'}, status=405)


def get_fallback_recommendations(n):
    """备选推荐数据"""
    sample_books = [
        {
            'title': '马克思恩格斯全集',
            'author': '中共中央马克思恩格斯列宁斯大林著作编译局',
            'publisher': '人民出版社',
            'category': '马克思主义',
            'status': '可借阅',
            'rating': '4.8',
            'description': '马克思和恩格斯的经典著作全集',
            'borrow_count': 120,
            'book_id': 'fallback_1'
        },
        {
            'title': '恩格斯反杜林论',
            'author': '恩格斯',
            'publisher': '人民出版社',
            'category': '马克思主义',
            'status': '可借阅',
            'rating': '4.7',
            'description': '恩格斯批判杜林错误观点的经典著作',
            'borrow_count': 85,
            'book_id': 'fallback_2'
        },
        {
            'title': 'Python编程：从入门到实践',
            'author': 'Eric Matthes',
            'publisher': '人民邮电出版社',
            'category': '计算机科学',
            'status': '可借阅',
            'rating': '4.9',
            'description': 'Python编程入门经典教程',
            'borrow_count': 200,
            'book_id': 'fallback_3'
        },
        {
            'title': '机器学习',
            'author': '周志华',
            'publisher': '清华大学出版社',
            'category': '计算机科学',
            'status': '可借阅',
            'rating': '4.8',
            'description': '机器学习领域经典教材',
            'borrow_count': 150,
            'book_id': 'fallback_4'
        }
    ]
    return sample_books[:min(n, len(sample_books))]


# 猜你喜欢推荐页面
def recommendations_page(request):
    """猜你喜欢推荐页面"""
    return render(request, 'book/recommendations.html')


# 用户注册视图
def register_view(request):
    """用户注册视图"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '注册成功！欢迎来到图书分享系统。')
            return redirect('home')
        else:
            messages.error(request, '注册失败，请检查表单信息。')
    else:
        form = CustomUserCreationForm()

    return render(request, 'book/register.html', {'form': form})


# 用户登录视图
def login_view(request):
    """用户登录视图"""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)

                # 获取next参数（登录后重定向）
                next_url = request.GET.get('next', 'home')
                messages.success(request, f'欢迎回来，{user.username}！')
                return redirect(next_url)
        else:
            messages.error(request, '用户名或密码错误，请重试。')
    else:
        form = CustomAuthenticationForm()

    return render(request, 'book/login.html', {'form': form})


# 用户登出视图
@login_required
def logout_view(request):
    """用户登出视图"""
    logout(request)
    messages.success(request, '您已成功登出。')
    return redirect('home')


# 用户个人资料页面
@login_required
def profile_view(request):
    """用户个人资料页面"""
    user = request.user
    # 这里可以添加用户的借阅记录、收藏等信息
    return render(request, 'book/profile.html', {'user': user})