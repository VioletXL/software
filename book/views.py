# book/views.py
from django.db.models import Count
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
    model_files_exist = os.path.exists('lightfm_model.npz') and os.path.exists('lightfm_model.mappings.json')

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
def search_books(request):
    query = request.GET.get('q', '')
    if query:
        books = Book.objects.filter(title__icontains=query)
    else:
        books = Book.objects.all()
    return render(request, 'book/search.html', {'books': books, 'query': query})


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

            # 如果是已登录用户且推荐系统可用，使用模型推荐
            if user_id != 'anonymous' and RECOMMENDER_AVAILABLE:
                try:
                    # 尝试将用户ID转换为整数
                    try:
                        user_id_int = int(user_id)
                    except:
                        user_id_int = user_id

                    recommended_book_id = recommender.recommend(user_id_int)

                    if recommended_book_id:
                        try:
                            # 获取推荐图书
                            recommended_book = Book.objects.get(book_id=recommended_book_id)
                            # 基于推荐图书获取相似图书
                            from django.db.models import Q
                            similar_books = Book.objects.filter(
                                Q(category_level1=recommended_book.category_level1) |
                                Q(category_level2=recommended_book.category_level2) |
                                Q(author=recommended_book.author)
                            ).exclude(id=recommended_book.id).distinct()[:top_n - 1]

                            books = [recommended_book] + list(similar_books)

                            # 如果不够，用热门书籍补充
                            if len(books) < top_n:
                                remaining = top_n - len(books)
                                popular_books = Book.objects.annotate(
                                    borrow_count=Count('borrowrecord')
                                ).order_by('-borrow_count')[:remaining]
                                books.extend(popular_books)

                        except Book.DoesNotExist:
                            # 推荐图书不存在，回退到热门书籍
                            books = Book.objects.annotate(
                                borrow_count=Count('borrowrecord')
                            ).order_by('-borrow_count')[:top_n]
                    else:
                        # 模型没有推荐结果，使用热门书籍
                        books = Book.objects.annotate(
                            borrow_count=Count('borrowrecord')
                        ).order_by('-borrow_count')[:top_n]

                except Exception as e:
                    print(f"模型推荐失败: {e}")
                    # 出错时使用热门书籍
                    books = Book.objects.annotate(
                        borrow_count=Count('borrowrecord')
                    ).order_by('-borrow_count')[:top_n]
            else:
                # 未登录用户或推荐系统不可用，使用热门书籍
                books = Book.objects.annotate(
                    borrow_count=Count('borrowrecord')
                ).order_by('-borrow_count')[:top_n]

            # 构建返回数据
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
                    'book_id': book.book_id or str(book.id),
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

            # 返回真实的备选推荐数据
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
    """归还图书"""
    book = get_object_or_404(Book, id=book_id)

    # 检查是否是当前借阅者
    if book.current_borrower != request.user:
        messages.error(request, '您没有借阅此图书')
        return redirect('my_borrow_records')

    book.return_book()
    messages.success(request, f'已归还《{book.title}》')
    return redirect('my_borrow_records')