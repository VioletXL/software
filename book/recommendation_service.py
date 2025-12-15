# book/recommendation_service.py
import os
import json
import numpy as np
import pandas as pd
from django.conf import settings
from collections import defaultdict


class HybridRecommender:
    """Django版本的混合推荐系统"""

    def __init__(self):
        self.user_history = defaultdict(list)
        self.author_pref = defaultdict(lambda: defaultdict(float))
        self.press_pref = defaultdict(lambda: defaultdict(float))
        self.category1_pref = defaultdict(lambda: defaultdict(float))
        self.category2_pref = defaultdict(lambda: defaultdict(float))
        self.book_features = {}
        self.user_info = {}
        self.stats = {
            'user_borrow_counts': defaultdict(int),
            'book_borrow_counts': defaultdict(int),
        }
        self.lightfm_enabled = False
        self.lightfm_user_embeddings = None
        self.lightfm_item_embeddings = None
        self.lightfm_user_biases = None
        self.lightfm_item_biases = None
        self.lightfm_user_index = {}
        self.lightfm_item_index = {}
        self.lightfm_item_ids = []
        self.book_id_to_str = {}
        self.str_to_book_id = {}

    @staticmethod
    def _id_to_str(value):
        if isinstance(value, float) and float(value).is_integer():
            value = int(value)
        return str(value)

    def load_book_features(self):
        """加载图书特征"""
        try:
            items_df = pd.read_csv('item.csv')
            for _, row in items_df.iterrows():
                bid = row['book_id']
                self.book_features[bid] = {
                    'title': row['题名'],
                    'author': row['作者'],
                    'press': row['出版社'],
                    'category1': row['一级分类'],
                    'category2': row['二级分类']
                }
                bid_str = self._id_to_str(bid)
                self.book_id_to_str[bid] = bid_str
                self.str_to_book_id[bid_str] = bid
            print(f"加载了 {len(self.book_features)} 本图书的特征")
        except Exception as e:
            print(f"加载图书特征失败: {e}")

    def load_lightfm_model(self):
        """加载LightFM模型"""
        try:
            model_path = 'lightfm_model.npz'
            mapping_path = 'lightfm_model_mappings.json'

            if not os.path.exists(model_path) or not os.path.exists(mapping_path):
                print("未找到LightFM模型文件")
                return

            data = np.load(model_path)
            with open(mapping_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)

            self.lightfm_user_embeddings = data.get('user_embeddings')
            self.lightfm_item_embeddings = data.get('item_embeddings')
            self.lightfm_user_biases = data.get('user_biases')
            self.lightfm_item_biases = data.get('item_biases')

            user_ids = [self._id_to_str(uid) for uid in mapping.get('user_ids', [])]
            item_ids = [self._id_to_str(iid) for iid in mapping.get('item_ids', [])]

            self.lightfm_user_index = {uid: idx for idx, uid in enumerate(user_ids)}
            self.lightfm_item_index = {iid: idx for idx, iid in enumerate(item_ids)}
            self.lightfm_item_ids = item_ids

            if (self.lightfm_item_embeddings is not None and
                    self.lightfm_user_embeddings is not None):
                self.lightfm_enabled = True
                print("LightFM模型加载成功")
        except Exception as e:
            print(f"加载LightFM模型失败: {e}")

    def load_user_borrow_history(self, user_id):
        """从数据库加载用户借阅历史"""
        from .models import BorrowRecord

        borrows = BorrowRecord.objects.filter(user_id=user_id).select_related('book')

        for borrow in borrows:
            book_id = borrow.book_id
            borrow_time = borrow.borrow_date

            # 计算时间衰减分数（最近借阅的权重更高）
            reference_time = borrows.last().borrow_date if borrows else borrow_time
            time_diff = (reference_time - borrow_time).days
            time_score = np.exp(-time_diff / 120)  # 120天衰减

            self.user_history[user_id].append((book_id, time_score, borrow_time))
            self.stats['user_borrow_counts'][user_id] += 1
            self.stats['book_borrow_counts'][book_id] += 1

            # 更新特征偏好
            if book_id in self.book_features:
                features = self.book_features[book_id]
                author = features['author']
                press = features['press']
                category1 = features['category1']
                category2 = features['category2']

                self.author_pref[user_id][author] += time_score
                self.press_pref[user_id][press] += time_score
                if pd.notna(category1):
                    self.category1_pref[user_id][category1] += time_score
                if pd.notna(category2):
                    self.category2_pref[user_id][category2] += time_score

    def recommend(self, user_id, topk=1):
        """为用户生成推荐"""
        # 加载用户历史
        self.load_user_borrow_history(user_id)

        history = self.user_history.get(user_id, [])
        if not history:
            # 新用户：返回热门书籍
            popular_books = sorted(
                self.stats['book_borrow_counts'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            return popular_books[0][0] if popular_books else None

        # 生成候选书籍
        candidates = self.get_candidates(user_id, history)

        if not candidates:
            candidates = [book_id for book_id, _, _ in history]

        # 为候选书籍打分
        scores = {}
        for book_id in candidates:
            if book_id not in self.book_features:
                continue

            score = self.calculate_score(user_id, book_id, history)
            scores[book_id] = score

        if not scores:
            return None

        # 返回最高分的书籍
        return max(scores.items(), key=lambda x: x[1])[0]

    def get_candidates(self, user_id, history, topk=50):
        """生成候选书籍"""
        candidates = set()

        # 1. 用户历史书籍
        history_books = [book_id for book_id, _, _ in history][-topk:]
        candidates.update(history_books)

        # 2. 基于作者/分类的相似书籍
        for book_id in history_books:
            if book_id in self.book_features:
                features = self.book_features[book_id]
                author = features.get('author')
                cat1 = features.get('category1')
                cat2 = features.get('category2')

                # 查找相同作者的书籍
                if author:
                    for bid, feat in self.book_features.items():
                        if feat.get('author') == author and bid != book_id:
                            candidates.add(bid)

        # 3. LightFM推荐（如果可用）
        if self.lightfm_enabled:
            lf_candidates = self._lightfm_top_items(user_id, topk=20)
            candidates.update(lf_candidates)

        return list(candidates)[:100]  # 限制候选数量

    def calculate_score(self, user_id, book_id, history):
        """计算书籍得分"""
        if book_id not in self.book_features:
            return 0

        features = self.book_features[book_id]
        author = features.get('author')
        press = features.get('press')
        category1 = features.get('category1')
        category2 = features.get('category2')

        # 基础分数
        base_score = 0.1

        # 检查是否借阅过
        borrow_count = sum(1 for bid, _, _ in history if bid == book_id)
        if borrow_count > 0:
            base_score = 1.0 + 0.2 * borrow_count

        # 特征偏好加分
        if author in self.author_pref[user_id]:
            base_score += 0.3 * self.author_pref[user_id][author]

        if press in self.press_pref[user_id]:
            base_score += 0.2 * self.press_pref[user_id][press]

        if category1 and category1 in self.category1_pref[user_id]:
            base_score += 0.2 * self.category1_pref[user_id][category1]

        if category2 and category2 in self.category2_pref[user_id]:
            base_score += 0.1 * self.category2_pref[user_id][category2]

        # LightFM分数（如果可用）
        if self.lightfm_enabled:
            lf_score = self._lightfm_score(user_id, book_id)
            if lf_score is not None:
                lf_prob = 1.0 / (1.0 + np.exp(-lf_score))
                base_score += 0.3 * lf_prob

        # 全局热度加分
        global_pop = self.stats['book_borrow_counts'].get(book_id, 0)
        base_score += 0.01 * min(global_pop / 100.0, 1.0)

        return base_score

    def _lightfm_score(self, user_id, book_id):
        """计算LightFM分数"""
        if not self.lightfm_enabled:
            return None

        user_key = self._id_to_str(user_id)
        item_key = self._id_to_str(book_id)

        u_idx = self.lightfm_user_index.get(user_key)
        i_idx = self.lightfm_item_index.get(item_key)

        if u_idx is None or i_idx is None:
            return None

        user_vec = self.lightfm_user_embeddings[u_idx]
        item_vec = self.lightfm_item_embeddings[i_idx]

        score = float(np.dot(user_vec, item_vec))

        if self.lightfm_user_biases is not None:
            score += float(self.lightfm_user_biases[u_idx])
        if self.lightfm_item_biases is not None:
            score += float(self.lightfm_item_biases[i_idx])

        return score

    def _lightfm_top_items(self, user_id, topk=20):
        """获取LightFM推荐的top物品"""
        if not self.lightfm_enabled:
            return []

        user_key = self._id_to_str(user_id)
        u_idx = self.lightfm_user_index.get(user_key)

        if u_idx is None:
            return []

        user_vec = self.lightfm_user_embeddings[u_idx]
        item_scores = np.dot(self.lightfm_item_embeddings, user_vec)

        if self.lightfm_item_biases is not None:
            item_scores += self.lightfm_item_biases
        if self.lightfm_user_biases is not None:
            item_scores += self.lightfm_user_biases[u_idx]

        max_items = min(len(self.lightfm_item_ids), len(item_scores))
        if max_items <= 0:
            return []

        topk = min(topk, max_items)
        top_indices = np.argpartition(-item_scores, topk - 1)[:topk]
        top_indices = top_indices[np.argsort(-item_scores[top_indices])]

        candidates = []
        for idx in top_indices:
            if idx < len(self.lightfm_item_ids):
                bid = self.str_to_book_id.get(self.lightfm_item_ids[idx])
                if bid and bid in self.book_features:
                    candidates.append(bid)

        return candidates


# 创建全局推荐器实例
recommender = HybridRecommender()


def initialize_recommender():
    """初始化推荐系统（在Django启动时调用）"""
    recommender.load_book_features()
    recommender.load_lightfm_model()
    print("推荐系统初始化完成")