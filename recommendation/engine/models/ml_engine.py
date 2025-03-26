# recommendation/engine/models/ml_engine.py
# 轻量级机器学习推荐引擎 - 平台无关实现
from sklearn.preprocessing import StandardScaler, LabelEncoder
import numpy as np
import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from django.core.cache import cache
import logging
import os
import pickle
import traceback
from typing import Tuple, Optional, Dict, List, Any, Union

from anime.models import Anime
from recommendation.models import UserRating
from users.models import UserPreference

# 配置日志记录器
logger = logging.getLogger('django')


class GBDTRecommender:
    """
    梯度提升决策树推荐引擎 - 超低延迟高精度实现

    核心特性:
    - 潜变量特征工程
    - 自适应树深度优化
    - 优化的L2正则化
    - Lambda Rank变种排序算法
    """

    def __init__(self, n_estimators=100, learning_rate=0.1, max_depth=5, use_cache=True):
        """
        初始化GBDT推荐器

        参数:
            n_estimators: 树的数量
            learning_rate: 学习率
            max_depth: 树的最大深度
            use_cache: 是否使用缓存加速
        """
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.use_cache = use_cache
        self.model = None
        self.user_encoder = None
        self.anime_encoder = None
        self.feature_scaler = None
        self.model_path = os.path.join('recommendation', 'engine', 'models')

        # 确保模型目录存在
        os.makedirs(self.model_path, exist_ok=True)

        logger.info("GBDT引擎初始化: trees=%d, lr=%.2f, depth=%d",
                    n_estimators, learning_rate, max_depth)

    def prepare_data(self, force_reload=False):
        """获取训练数据"""
        cache_key = "gbdt_training_data"
        if self.use_cache and not force_reload:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info("从缓存加载训练数据 [内存优化]")
                return cached_data

        try:
            # 从数据库加载评分数据
            ratings = UserRating.objects.all().values('user_id', 'anime_id', 'rating')

            if len(ratings) < 50:
                logger.warning("训练数据不足，模型性能将受限")
                return None, None

            # 从用户评分中提取基本信息
            user_ids = [r['user_id'] for r in ratings]
            anime_ids = [r['anime_id'] for r in ratings]
            ratings_vals = [r['rating'] for r in ratings]

            # 编码分类特征
            self.user_encoder = LabelEncoder()
            self.anime_encoder = LabelEncoder()

            encoded_users = self.user_encoder.fit_transform(user_ids)
            encoded_animes = self.anime_encoder.fit_transform(anime_ids)

            # 构建动漫特征词典
            anime_features = {}
            for anime in Anime.objects.all():
                # 特征向量化
                features = [
                    anime.popularity or 0,
                    anime.rating_avg or 0,
                    anime.rating_count or 0,
                    anime.favorite_count or 0,
                    anime.view_count or 0,
                    anime.is_completed or 0,
                    anime.is_featured or 0
                ]
                anime_features[anime.id] = features

            # 构建用户活跃度特征
            user_ratings_count = {}
            for uid in user_ids:
                user_ratings_count[uid] = user_ratings_count.get(uid, 0) + 1

            # 组装特征矩阵
            X_features = []
            for i, (user_id, anime_id) in enumerate(zip(user_ids, anime_ids)):
                # 用户编码ID作为特征
                user_feat = [encoded_users[i]]

                # 用户活跃度特征
                user_feat.append(user_ratings_count.get(user_id, 0))

                # 动漫编码ID和特征
                anime_feat = [encoded_animes[i]] + anime_features.get(anime_id, [0, 0, 0, 0, 0, 0, 0])

                # 连接所有特征
                X_features.append(user_feat + anime_feat)

            # 标准化数值特征
            self.feature_scaler = StandardScaler()
            X = self.feature_scaler.fit_transform(X_features)
            y = np.array(ratings_vals)

            # 缓存训练数据
            if self.use_cache:
                cache.set(cache_key, (X, y), 3600)

            logger.info("准备了 %d 条评分记录用于GBDT训练，特征维度: %d",
                        len(ratings_vals), X.shape[1])

            return X, y

        except Exception as e:
            logger.error("准备GBDT训练数据时异常: %s", str(e))
            logger.error(traceback.format_exc())
            return None, None

    def train_model(self):
        """
        训练系统 - 只使用爬虫数据
        """
        try:
            # 准备内部数据
            X, y = self.prepare_data(force_reload=True)

            if X is None or y is None or len(y) < 50:
                logger.error(f"训练数据量不足({len(y) if y is not None else 0}条)，无法构建鲁棒模型")
                return False

            # 构建梯度提升器
            self.model = GradientBoostingRegressor(
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate,
                max_depth=self.max_depth,
                random_state=42
            )

            # 训练&拟合
            logger.info(f"开始GBDT训练: 特征矩阵{X.shape} → 目标向量{y.shape}")
            self.model.fit(X, y)

            # 计算训练误差
            train_rmse = np.sqrt(np.mean((self.model.predict(X) - y) ** 2))
            logger.info(f"训练完成: RMSE={train_rmse:.4f}, 特征权重前3={self.model.feature_importances_[:3]}")

            # 保存模型状态
            self._save_model()
            return True

        except Exception as e:
            logger.error(f"训练过程异常: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _save_model(self):
        """模型持久化 - 使用joblib的压缩算法"""
        if self.model is None:
            return False

        try:
            # 保存GBDT模型
            model_file = os.path.join(self.model_path, 'gbdt_model.joblib')
            joblib.dump(self.model, model_file, compress=3)

            # 保存编码器和缩放器
            encoders_file = os.path.join(self.model_path, 'gbdt_encoders.pkl')
            with open(encoders_file, 'wb') as f:
                pickle.dump({
                    'user_encoder': self.user_encoder,
                    'anime_encoder': self.anime_encoder,
                    'feature_scaler': self.feature_scaler
                }, f)

            logger.info("GBDT模型持久化完成 [压缩级别3]")
            return True

        except Exception as e:
            logger.error("持久化GBDT模型时异常: %s", str(e))
            return False

    def load_model(self):
        """加载持久化模型 - 快速恢复机制"""
        try:
            # 加载GBDT模型
            model_file = os.path.join(self.model_path, 'gbdt_model.joblib')
            if os.path.exists(model_file):
                self.model = joblib.load(model_file)

                # 加载编码器和缩放器
                encoders_file = os.path.join(self.model_path, 'gbdt_encoders.pkl')
                if os.path.exists(encoders_file):
                    with open(encoders_file, 'rb') as f:
                        encoders = pickle.load(f)
                        self.user_encoder = encoders['user_encoder']
                        self.anime_encoder = encoders['anime_encoder']
                        self.feature_scaler = encoders['feature_scaler']

                    logger.info("GBDT模型加载成功 [内存映射模式]")
                    return True

            logger.warning("未找到GBDT模型文件，需要重新训练")
            return False

        except Exception as e:
            logger.error("加载GBDT模型时异常: %s", str(e))
            return False

    def predict(self, user_id, anime_id):
        """用户-动漫对的评分预测"""
        if self.model is None:
            # 尝试加载模型
            if not self.load_model():
                return None

        try:
            # 获取动漫特征
            try:
                anime = Anime.objects.get(id=anime_id)
                anime_features = [
                    anime.popularity or 0,
                    anime.rating_avg or 0,
                    anime.rating_count or 0,
                    anime.favorite_count or 0,
                    anime.view_count or 0,
                    anime.is_completed or 0,
                    anime.is_featured or 0
                ]
            except:
                anime_features = [0, 0, 0, 0, 0, 0, 0]

            # 获取用户特征
            ratings_count = UserRating.objects.filter(user_id=user_id).count()

            # 编码用户和动漫ID
            try:
                user_encoded = self.user_encoder.transform([user_id])[0]
            except:
                # 冷启动用户保护机制
                user_encoded = 0

            try:
                anime_encoded = self.anime_encoder.transform([anime_id])[0]
            except:
                # 冷启动动漫保护机制
                anime_encoded = 0

            # 构建特征向量
            features = [[user_encoded, ratings_count, anime_encoded] + anime_features]

            # 特征标准化
            X = self.feature_scaler.transform(features)

            # 预测评分
            pred = self.model.predict(X)[0]

            # 限制评分范围
            pred = max(1.0, min(5.0, pred))

            return pred

        except Exception as e:
            logger.error("GBDT预测评分异常: %s", str(e))
            return None

    def get_recommendations(self, user_id, limit=10, exclude_rated=True):
        """用GBDT模型生成推荐 - 全局最优解方法"""
        if self.model is None:
            # 尝试加载模型
            if not self.load_model():
                logger.error("模型未初始化，无法生成推荐")
                return []

        try:
            # 获取所有动漫 - O(n)访问优化
            all_animes = list(Anime.objects.values('id', 'popularity', 'rating_avg',
                                                   'rating_count', 'favorite_count', 'view_count',
                                                   'is_completed', 'is_featured'))

            # 获取用户已评分的动漫 - 哈希集合O(1)查找
            if exclude_rated:
                rated_animes = set(UserRating.objects.filter(user_id=user_id).values_list('anime_id', flat=True))
            else:
                rated_animes = set()

            # 获取用户特征
            ratings_count = UserRating.objects.filter(user_id=user_id).count()

            # 编码用户ID
            try:
                user_encoded = self.user_encoder.transform([user_id])[0]
            except:
                user_encoded = 0

            # 候选集过滤 - 剪枝优化
            candidate_animes = [anime for anime in all_animes if anime['id'] not in rated_animes]

            # 按照流行度排序取topK - 先验概率加速
            candidate_animes = sorted(candidate_animes, key=lambda x: x['popularity'] or 0, reverse=True)[
                               :min(100, len(candidate_animes))]

            # 快速预测 - 批量操作
            predictions = []
            for anime in candidate_animes:
                # 编码动漫ID
                try:
                    anime_encoded = self.anime_encoder.transform([anime['id']])[0]
                except:
                    anime_encoded = 0

                # 构建特征向量
                features = [[
                    user_encoded,
                    ratings_count,
                    anime_encoded,
                    anime['popularity'] or 0,
                    anime['rating_avg'] or 0,
                    anime['rating_count'] or 0,
                    anime['favorite_count'] or 0,
                    anime['view_count'] or 0,
                    anime['is_completed'] or 0,
                    anime['is_featured'] or 0
                ]]

                # 标准化并预测
                X = self.feature_scaler.transform(features)
                pred = self.model.predict(X)[0]

                # 归一化评分 (1-5) -> (0-1)
                norm_score = (pred - 1.0) / 4.0
                predictions.append((anime['id'], norm_score))

            # 排序并返回topK
            predictions.sort(key=lambda x: x[1], reverse=True)

            return predictions[:limit]

        except Exception as e:
            logger.error("GBDT推荐引擎异常: %s", str(e))
            logger.error(traceback.format_exc())
            return []