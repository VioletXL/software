# book/apps.py
from django.apps import AppConfig
import os


class BookConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'book'

    def ready(self):
        # 只在主进程中初始化，避免多进程重复初始化
        import sys

        # 检查是否在运行服务器
        is_running_server = 'runserver' in sys.argv
        is_testing = 'test' in sys.argv

        if is_running_server and not is_testing:
            try:
                # 检查模型文件是否存在
                model_files_exist = os.path.exists('lightfm_model.npz') and os.path.exists(
                    'lightfm_model_mappings.json')

                if model_files_exist:
                    print("检测到模型文件，正在初始化推荐系统...")
                    from .recommendation_service import initialize_recommender
                    initialize_recommender()
                    print("推荐系统初始化成功")
                else:
                    print("未找到模型文件，跳过推荐系统初始化")

            except ImportError as e:
                print(f"无法导入推荐服务: {e}")
            except Exception as e:
                print(f"推荐系统初始化失败: {e}")
                import traceback
                traceback.print_exc()