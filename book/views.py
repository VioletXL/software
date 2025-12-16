# book/views.py
from django.db.models import Count, Q
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
import json
from .models import Book
from .forms import CustomUserCreationForm, CustomAuthenticationForm
import os

# 尝试导入推荐服务
try:
    from .recommendation_service import recommender, initialize_recommender

    # 检查模型文件是否存在
    model_files_exist = os.path.exists('lightfm_model.npz') and os.path.exists('lightfm_model_mappings.json')

    if model_files_exist:
        print("检测到模型文件，正在初始化推荐系统...")
        try:
            initialize_recommender()
            RECOMMENDER_AVAILABLE = True
            print("推荐系统初始化成功")
        except Exception as e:
            print(f"推荐系统初始化失败: {e}")
            RECOMMENDER_AVAILABLE = False
    else:
        print("未找到模型文件，推荐系统不可用")
        RECOMMENDER_AVAILABLE = False

except ImportError as e:
    print(f"无法导入推荐服务: {e}")
    RECOMMENDER_AVAILABLE = False
except Exception as e:
    print(f"推荐系统初始化异常: {e}")
    RECOMMENDER_AVAILABLE = False



# 首页视图
def home(request):

    # 修改后：只查询前9本图书
    books = Book.objects.all()[:9]  # 切片[:9]表示取前9条数据
    return render(request, 'book/home.html', {'books': books})


# 搜索函数
# views.py
def search_books(request):
    """搜索图书"""
    query = request.GET.get('q', '')
    books = []

    if query:
        # 根据你的实际搜索逻辑修改
        books = Book.objects.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(publisher__icontains=query)
        )

        # 为每本书添加是否可借阅的状态
        for book in books:
            # 根据你的模型结构添加状态信息
            book.is_available = book.status == '可借阅' if hasattr(book, 'status') else True
            # 如果当前用户借阅了这本书
            if request.user.is_authenticated:
                book.current_borrower = book.current_borrower if hasattr(book, 'current_borrower') else None

    context = {
        'query': query,
        'books': books,
    }

    return render(request, 'book/search.html', context)

# 推荐API接口
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

            # 获取推荐书籍
            books = Book.objects.filter(is_available=True)[:top_n]

            book_list = []
            for book in books:
                # 确定分类显示
                category = book.category_level1 or book.category_level2 or '未分类'

                # 确定状态
                status = '可借阅' if book.is_available else '已借出'

                book_list.append({
                    'title': book.title,
                    'author': book.author or '未知',
                    'publisher': book.publisher or '未知',
                    'category': category,
                    'status': status,
                    'borrow_count': book.borrow_count,
                    'book_id': book.book_id,  # 使用 book.book_id，不是 book.id
                    'id': book.id
                })

            print(f"成功返回 {len(book_list)} 条推荐")

            return JsonResponse({
                'success': True,
                'user_id': user_id,
                'recommendations': book_list,
                'model_used': RECOMMENDER_AVAILABLE and user_id != 'anonymous'
            })

        except Exception as e:
            print(f"推荐API错误: {e}")
            import traceback
            traceback.print_exc()

            return JsonResponse({
                'success': True,
                'user_id': user_id,
                'recommendations': get_fallback_recommendations(top_n),
                'model_used': False
            })

    return JsonResponse({'error': '只支持POST'}, status=405)
def get_category_recommendations(user, num_books=9):
    """基于用户分类偏好的推荐"""
    # 获取用户借阅过的分类
    borrows = BorrowRecord.objects.filter(user=user).select_related('book')
    categories = set()

    for borrow in borrows:
        if borrow.book.category_level1:
            categories.add(borrow.book.category_level1)
        if borrow.book.category_level2:
            categories.add(borrow.book.category_level2)

    if categories:
        # 从用户偏好的分类中推荐书籍
        from django.db.models import Q
        return Book.objects.filter(
            Q(category_level1__in=categories) |
            Q(category_level2__in=categories)
        ).distinct()[:num_books]
    else:
        # 如果用户没有借阅历史，显示热门书籍
        return Book.objects.annotate(
            borrow_count=Count('borrowrecord')
        ).order_by('-borrow_count')[:num_books]

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
    messages.success(request, '您已成功退出。')
    return redirect('home')


# 用户个人资料页面
@login_required
def profile_view(request):
    """用户个人资料页面"""
    user = request.user
    # 这里可以添加用户的借阅记录、收藏等信息
    return render(request, 'book/profile.html', {'user': user})


from django.shortcuts import get_object_or_404
from .models import Book, BorrowRecord
@csrf_exempt
@login_required
def borrow_book(request):
    """处理借阅请求的API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            book_id = data.get('book_id')
            book_title = data.get('book_title')

            # 通过ID或标题查找图书
            if book_id:
                book = get_object_or_404(Book, id=book_id)
            elif book_title:
                book = get_object_or_404(Book, title=book_title)
            else:
                return JsonResponse({
                    'success': False,
                    'message': '请提供图书ID或书名'
                }, status=400)

            # 检查图书是否可借
            if not book.is_available:
                return JsonResponse({
                    'success': False,
                    'message': '该图书已被借出'
                })

            # 执行借阅
            if book.borrow(request.user):
                return JsonResponse({
                    'success': True,
                    'message': f'成功借阅《{book.title}》',
                    'book_id': book.id,
                    'book_title': book.title
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': '借阅失败'
                })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'服务器错误: {str(e)}'
            }, status=500)

    return JsonResponse({'error': '只支持POST请求'}, status=405)


@login_required
def my_borrow_records(request):
    """查看我的借阅记录"""
    borrow_records = BorrowRecord.objects.filter(user=request.user).select_related('book')

    context = {
        'borrow_records': borrow_records,
        'current_borrows': borrow_records.filter(return_date__isnull=True),
        'history_borrows': borrow_records.filter(return_date__isnull=False),
    }
    return render(request, 'book/my_borrows.html', context)


@login_required
def return_book(request, book_id):
    """归还图书 - 返回JSON格式"""
    book = get_object_or_404(Book, id=book_id)

    if request.method == 'POST':
        try:
            # 检查是否是当前借阅者
            if book.current_borrower != request.user:
                return JsonResponse({
                    'success': False,
                    'message': '您没有借阅此图书'
                }, status=400)

            # 执行归还
            book.return_book()

            return JsonResponse({
                'success': True,
                'message': f'已归还《{book.title}》'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'归还失败: {str(e)}'
            }, status=500)

    return JsonResponse({
        'success': False,
        'message': '无效的请求方法'
    }, status=405)


@login_required
def profile(request):
    """个人资料页面"""
    user = request.user

    # 获取用户的借阅记录
    borrow_records = BorrowRecord.objects.filter(user=user).order_by('-borrow_date')

    # 当前借阅（未归还）
    current_borrows = borrow_records.filter(return_date__isnull=True)

    # 历史借阅（已归还）
    history_borrows = borrow_records.filter(return_date__isnull=False)

    context = {
        'user': user,
        'current_borrows': current_borrows,
        'history_borrows': history_borrows,
        'current_borrows_count': current_borrows.count(),
        'total_borrows_count': borrow_records.count(),
    }

    return render(request, 'book/profile.html', context)


@login_required
def profile(request):
    """个人资料页面"""
    user = request.user

    # 获取用户的借阅记录
    borrow_records = BorrowRecord.objects.filter(user=user).order_by('-borrow_date')

    # 当前借阅和历史借阅
    current_borrows = borrow_records.filter(return_date__isnull=True)
    history_borrows = borrow_records.filter(return_date__isnull=False)

    # 为每条历史记录计算借阅时长
    for borrow in history_borrows:
        if borrow.return_date and borrow.borrow_date:
            delta = borrow.return_date - borrow.borrow_date
            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            # 构建友好的时长字符串
            if days > 0:
                borrow.duration_str = f"{days}天{hours}小时"
            elif hours > 0:
                borrow.duration_str = f"{hours}小时{minutes}分钟"
            elif minutes > 0:
                borrow.duration_str = f"{minutes}分钟{seconds}秒"
            else:
                borrow.duration_str = f"{seconds}秒"
        else:
            borrow.duration_str = "-"

    context = {
        'user': user,
        'current_borrows': current_borrows,
        'history_borrows': history_borrows,
        'current_borrows_count': current_borrows.count(),
        'total_borrows_count': borrow_records.count(),
    }

    return render(request, 'book/profile.html', context)