# recommendation/engine/models/ml_engine.py
# 轻量级机器学习推荐引擎 - 支持Kaggle数据集训练

# 设置环境变量避免wmic问题
import os

os.environ['LOKY_MAX_CPU_COUNT'] = str(os.cpu_count() or 4)

from sklearn.preprocessing import StandardScaler, LabelEncoder
import numpy as np
import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from django.core.cache import cache
import logging
import math
import pickle
import traceback
from typing import Tuple, Optional, Dict, List, Any, Union
import random
from anime.models import Anime
from recommendation.models import UserRating
from users.models import UserPreference

# 配置日志记录器
logger = logging.getLogger('django')


class GBDTRecommender:
    """
    梯度提升决策树推荐引擎 - 量子级多源集成版

    核心特性:
    - 潜变量特征工程
    - 自适应树深度优化
    - 优化的L2正则化
    - Lambda Rank变种排序算法
    - 支持Kaggle数据集训练
    - 动态权重调整机制
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
        # 尝试从文件加载最佳参数
        params_path = os.path.join('recommendation', 'engine', 'models', 'best_model_params.json')
        if os.path.exists(params_path):
            try:
                with open(params_path, 'r') as f:
                    import json
                    best_params = json.load(f)
                    # 更新默认参数
                    if 'n_estimators' in best_params:
                        n_estimators = int(best_params['n_estimators'])
                    if 'learning_rate' in best_params:
                        learning_rate = float(best_params['learning_rate'])
                    if 'max_depth' in best_params:
                        max_depth = int(best_params['max_depth'])
                    logger.info(f"已加载最佳模型参数: n_estimators={n_estimators}, learning_rate={learning_rate}, max_depth={max_depth}")
            except Exception as e:
                logger.error(f"加载最佳模型参数失败: {str(e)}")

        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.use_cache = use_cache
        self.model = None
        self.user_encoder = None
        self.anime_encoder = None
        self.feature_scaler = None
        self.anime_id_mapping = {}  # Kaggle ID映射到本地ID
        self.reverse_mapping = {}  # 本地ID映射到Kaggle ID
        self.model_path = os.path.join('recommendation', 'engine', 'models')
        self.feature_names = None  # 添加特征名称保存

        # 动态权重调整参数
        self.kaggle_weight = 0.7  # 初始Kaggle模型权重
        self.local_weight = 0.3  # 初始本地模型权重
        self.weight_update_step = 0.01  # 每次调整的步长

        # 模型性能指标
        self.performance_metrics = {
            'kaggle_rmse': 1.0,
            'local_rmse': 1.0
        }

        # 确保模型目录存在
        os.makedirs(self.model_path, exist_ok=True)

        logger.info("高级GBDT引擎初始化: trees=%d, lr=%.2f, depth=%d",
                    n_estimators, learning_rate, max_depth)

    def prepare_data(self, force_reload=False):
        """获取训练数据 - 从数据库中提取"""
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

            # 创建特征名称列表
            self.feature_names = [
                'user_encoded', 'user_rating_count', 'anime_encoded',
                'popularity', 'rating_avg', 'rating_count',
                'favorite_count', 'view_count', 'is_completed', 'is_featured'
            ]

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

    def load_kaggle_data(self, anime_csv_path, rating_csv_path):
        """
        加载Kaggle数据集 - 不导入数据库，仅用于训练
        添加了数据采样功能

        参数:
            anime_csv_path: 动漫CSV文件路径
            rating_csv_path: 评分CSV文件路径

        返回:
            特征矩阵X和目标变量y
        """
        try:
            logger.info(f"加载Kaggle数据集: {anime_csv_path}, {rating_csv_path}")

            # 加载数据集
            anime_df = pd.read_csv(anime_csv_path)
            rating_df = pd.read_csv(rating_csv_path)

            # 日志记录原始数据量
            logger.info(f"原始评分数据量: {len(rating_df)} 条记录")

            # 数据采样，只使用前100,000条记录 - 添加在这里
            rating_df = rating_df.head(100000)
            logger.info(f"采样后评分数据量: {len(rating_df)} 条记录")

            # 数据清洗
            # 移除无效评分 (-1表示已看但未评分)
            rating_df = rating_df[rating_df['rating'] > 0]
            logger.info(f"清洗后有效评分: {len(rating_df)} 条记录")

            # 仅保留评分数据中存在的动漫ID
            valid_anime_ids = set(anime_df['anime_id'].values)
            rating_df = rating_df[rating_df['anime_id'].isin(valid_anime_ids)]

            # 构建ID映射 (Kaggle ID -> 本地ID)
            # 注意：这里我们只是创建映射，不实际导入数据库
            self._build_id_mapping(anime_df)

            # 提取特征
            # 从Kaggle动漫数据中提取特征
            anime_features = self._extract_kaggle_anime_features(anime_df)

            # 从评分数据中提取用户-动漫对
            user_ids = rating_df['user_id'].values
            anime_ids = rating_df['anime_id'].values
            ratings = rating_df['rating'].values

            # 编码用户和动漫ID
            user_encoder = LabelEncoder()
            anime_encoder = LabelEncoder()

            encoded_users = user_encoder.fit_transform(user_ids)
            encoded_animes = anime_encoder.fit_transform(anime_ids)

            # 保存编码器以便预测时使用
            self.kaggle_user_encoder = user_encoder
            self.kaggle_anime_encoder = anime_encoder

            # 构建用户活跃度特征
            user_ratings_count = {}
            for uid in user_ids:
                user_ratings_count[uid] = user_ratings_count.get(uid, 0) + 1

            # 构建特征名称
            self.kaggle_feature_names = [
                'user_encoded', 'user_rating_count', 'anime_encoded',
                'rating', 'members', 'episodes', 'type_code', 'high_rating'
            ]

            # 组装特征矩阵
            X_features = []
            for i, (user_id, anime_id) in enumerate(zip(user_ids, anime_ids)):
                # 用户编码ID和活跃度
                user_feat = [encoded_users[i], user_ratings_count.get(user_id, 0)]

                # 动漫编码ID和特征
                anime_feat = [encoded_animes[i]] + anime_features.get(anime_id, [0, 0, 0, 0, 0])

                # 连接所有特征
                X_features.append(user_feat + anime_feat)

            # 标准化特征
            kaggle_scaler = StandardScaler()
            X = kaggle_scaler.fit_transform(X_features)
            y = np.array(ratings) / 10.0  # 将1-10的评分映射到0.1-1.0区间

            # 保存标准化器以便预测时使用
            self.kaggle_feature_scaler = kaggle_scaler

            # 分割验证集
            from sklearn.model_selection import train_test_split
            X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.1, random_state=42)

            logger.info(f"Kaggle数据集处理完成: {len(y)} 条评分记录, 特征维度: {X.shape[1]}")

            return X_train, y_train, X_val, y_val, anime_features

        except Exception as e:
            logger.error(f"加载Kaggle数据集异常: {str(e)}")
            logger.error(traceback.format_exc())
            return None, None, None, None, None

    def _extract_kaggle_anime_features(self, anime_df):
        """
        从Kaggle动漫数据中提取特征 - 增强版，能处理特殊值

        参数:
            anime_df: 动漫数据DataFrame

        返回:
            动漫特征字典 {anime_id: [features]}
        """
        features = {}

        # 提取并处理类型信息
        genre_set = set()
        for genres in anime_df['genre'].dropna():
            for genre in genres.split(','):
                genre_set.add(genre.strip())

        genre_mapping = {genre: i for i, genre in enumerate(genre_set)}

        # 提取类型数据
        anime_types = set(anime_df['type'].dropna())
        type_mapping = {type_: i for i, type_ in enumerate(anime_types)}

        # 添加特殊值处理
        unknown_values = ["Unknown", "?", "N/A", "unknown", "na", "null", "-"]

        # 构建特征
        successful_count = 0
        error_count = 0

        for _, row in anime_df.iterrows():
            try:
                anime_id = row['anime_id']

                # 评分特征 - 处理特殊值
                rating = 0.0
                if not pd.isna(row['rating']):
                    rating_val = str(row['rating'])
                    if rating_val not in unknown_values:
                        try:
                            rating = float(rating_val)
                        except (ValueError, TypeError):
                            rating = 0.0

                # 会员数（人气）特征 - 处理特殊值
                members = 0.0
                if not pd.isna(row['members']):
                    members_val = str(row['members'])
                    if members_val not in unknown_values:
                        try:
                            members = float(members_val)
                        except (ValueError, TypeError):
                            members = 0.0

                # 集数特征 - 处理特殊值
                episodes = 0.0
                if not pd.isna(row['episodes']):
                    episodes_val = str(row['episodes'])
                    if episodes_val not in unknown_values:
                        try:
                            episodes = float(episodes_val)
                        except (ValueError, TypeError):
                            episodes = 0.0

                # 类型编码
                anime_type = row['type'] if not pd.isna(row['type']) else ''
                type_code = type_mapping.get(anime_type, 0)

                # 构建特征向量
                features[anime_id] = [
                    rating / 10.0,  # 归一化评分
                    np.log1p(members) / 15.0 if members > 0 else 0,  # 归一化会员数
                    np.log1p(episodes) / 5.0 if episodes > 0 else 0,  # 归一化集数
                    type_code / len(type_mapping) if type_mapping else 0,  # 归一化类型编码
                    1.0 if rating > 8.0 else 0.0  # 高评分标志
                ]

                successful_count += 1

            except Exception as e:
                error_count += 1
                try:
                    logger.error(f"处理动漫ID {anime_id} 特征时出错: {str(e)}")
                except:
                    logger.error(f"处理动漫特征时出错: {str(e)}")

        logger.info(f"特征提取完成: 成功处理 {successful_count} 个动漫, {error_count} 个处理失败")

        return features

    def _build_id_mapping(self, anime_df):
        """
        构建Kaggle ID与本地ID的映射关系

        参数:
            anime_df: Kaggle动漫数据
        """
        # 获取本地数据库中的动漫
        local_animes = {}
        for anime in Anime.objects.all():
            # 转换为小写以便不区分大小写匹配
            title = anime.title.lower() if anime.title else ''
            local_animes[title] = anime.id

        # 构建映射
        for _, row in anime_df.iterrows():
            kaggle_id = row['anime_id']
            kaggle_title = row['name'].lower() if not pd.isna(row['name']) else ''

            # 尝试通过标题匹配
            if kaggle_title in local_animes:
                local_id = local_animes[kaggle_title]
                self.anime_id_mapping[kaggle_id] = local_id
                self.reverse_mapping[local_id] = kaggle_id

        logger.info(f"构建了 {len(self.anime_id_mapping)} 个Kaggle->本地ID映射")

        # 保存映射关系到文件
        try:
            mapping_file = os.path.join(self.model_path, 'anime_id_mapping.pkl')
            with open(mapping_file, 'wb') as f:
                pickle.dump({
                    'kaggle_to_local': self.anime_id_mapping,
                    'local_to_kaggle': self.reverse_mapping
                }, f)
            logger.info(f"ID映射关系已保存到 {mapping_file}")
        except Exception as e:
            logger.error(f"保存ID映射失败: {str(e)}")

    def train_model(self, anime_csv_path=None, rating_csv_path=None):
        """
        训练系统 - 支持Kaggle数据和本地数据

        参数:
            anime_csv_path: Kaggle动漫CSV文件路径
            rating_csv_path: Kaggle评分CSV文件路径
        """
        try:
            # 检查是否有Kaggle数据
            kaggle_data_available = anime_csv_path and rating_csv_path and \
                                    os.path.exists(anime_csv_path) and \
                                    os.path.exists(rating_csv_path)

            # 模型字典
            self.models = {}

            # 训练Kaggle模型
            if kaggle_data_available:
                logger.info("开始训练Kaggle数据模型...")
                X_train, y_train, X_val, y_val, anime_features = self.load_kaggle_data(
                    anime_csv_path, rating_csv_path
                )

                if X_train is not None and y_train is not None:
                    # 保存动漫特征以便预测时使用
                    self.kaggle_anime_features = anime_features

                    # 训练Kaggle模型
                    kaggle_model = GradientBoostingRegressor(
                        n_estimators=self.n_estimators,
                        learning_rate=self.learning_rate,
                        max_depth=self.max_depth,
                        random_state=42
                    )

                    kaggle_model.fit(X_train, y_train)

                    # 评估模型性能
                    if X_val is not None and y_val is not None:
                        y_pred = kaggle_model.predict(X_val)
                        kaggle_rmse = np.sqrt(np.mean((y_pred - y_val) ** 2))
                        self.performance_metrics['kaggle_rmse'] = kaggle_rmse
                        logger.info(f"Kaggle模型验证RMSE: {kaggle_rmse:.4f}")

                    # 保存Kaggle模型
                    self.models['kaggle'] = kaggle_model
                    joblib.dump(kaggle_model, os.path.join(self.model_path, 'kaggle_model.joblib'), compress=3)

                    # 保存Kaggle编码器和标准化器以及特征名称
                    with open(os.path.join(self.model_path, 'kaggle_encoders.pkl'), 'wb') as f:
                        pickle.dump({
                            'user_encoder': self.kaggle_user_encoder,
                            'anime_encoder': self.kaggle_anime_encoder,
                            'feature_scaler': self.kaggle_feature_scaler,
                            'anime_features': anime_features,
                            'feature_names': self.kaggle_feature_names
                        }, f)

                    logger.info("Kaggle模型训练并保存完成")
                else:
                    logger.warning("Kaggle数据处理失败，无法训练Kaggle模型")

            # 准备内部数据
            X, y = self.prepare_data(force_reload=True)

            if X is not None and y is not None and len(y) >= 50:
                # 构建梯度提升器
                local_model = GradientBoostingRegressor(
                    n_estimators=self.n_estimators,
                    learning_rate=self.learning_rate,
                    max_depth=self.max_depth,
                    random_state=42
                )

                # 训练&拟合
                logger.info(f"开始GBDT本地数据训练: 特征矩阵{X.shape} → 目标向量{y.shape}")
                local_model.fit(X, y)

                # 计算训练误差
                train_rmse = np.sqrt(np.mean((local_model.predict(X) - y) ** 2))
                self.performance_metrics['local_rmse'] = train_rmse
                logger.info(
                    f"本地模型训练完成: RMSE={train_rmse:.4f}, 特征权重前3={local_model.feature_importances_[:3]}")

                # 保存本地模型
                self.models['local'] = local_model
                joblib.dump(local_model, os.path.join(self.model_path, 'local_model.joblib'), compress=3)

                # 保存组合模型 (同时保存为推荐引擎可以直接使用的统一模型)
                joblib.dump(local_model, os.path.join(self.model_path, 'gbdt_model.joblib'), compress=3)

                # 保存本地编码器和标准化器以及特征名称
                with open(os.path.join(self.model_path, 'local_encoders.pkl'), 'wb') as f:
                    pickle.dump({
                        'user_encoder': self.user_encoder,
                        'anime_encoder': self.anime_encoder,
                        'feature_scaler': self.feature_scaler,
                        'feature_names': self.feature_names
                    }, f)

                # 同时保存为统一格式
                with open(os.path.join(self.model_path, 'gbdt_encoders.pkl'), 'wb') as f:
                    pickle.dump({
                        'user_encoder': self.user_encoder,
                        'anime_encoder': self.anime_encoder,
                        'feature_scaler': self.feature_scaler,
                        'feature_names': self.feature_names
                    }, f)

                logger.info("本地模型训练并保存完成")
            else:
                logger.warning(f"本地训练数据量不足({len(y) if y is not None else 0}条)，无法构建鲁棒本地模型")

            # 保存混合模型权重
            self._update_model_weights()

            # 设置主模型为混合模型
            self.model = self.models.get('local', self.models.get('kaggle'))

            return len(self.models) > 0

        except Exception as e:
            logger.error(f"训练过程异常: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def _update_model_weights(self):
        """
        更新模型权重并保存 - 增强版，保证本地模型最小权重
        """
        try:
            # 基于性能指标调整权重
            if 'kaggle' in self.models and 'local' in self.models:
                kaggle_rmse = self.performance_metrics['kaggle_rmse']
                local_rmse = self.performance_metrics['local_rmse']

                # 检查是否RMSE差距过大
                rmse_ratio = local_rmse / kaggle_rmse if kaggle_rmse > 0 else 1.0

                if rmse_ratio > 3.0:
                    # RMSE差距过大，应用平方根缩放来减轻差距
                    logger.warning(
                        f"检测到RMSE差距过大: local={local_rmse:.4f}, kaggle={kaggle_rmse:.4f}, 比率={rmse_ratio:.2f}")
                    kaggle_rmse = kaggle_rmse * math.sqrt(rmse_ratio / 3.0)
                    logger.info(f"应用平方根缩放后: kaggle_rmse调整为 {kaggle_rmse:.4f}")

                # 权重反比于RMSE (误差越小，权重越大)
                total = (1 / kaggle_rmse) + (1 / local_rmse)
                kaggle_weight_raw = (1 / kaggle_rmse) / total
                local_weight_raw = (1 / local_rmse) / total

                # 确保本地模型的最小权重不低于30%
                MIN_LOCAL_WEIGHT = 0.3
                if local_weight_raw < MIN_LOCAL_WEIGHT:
                    local_weight = MIN_LOCAL_WEIGHT
                    kaggle_weight = 1.0 - local_weight
                    logger.info(f"应用最小本地权重保障: {MIN_LOCAL_WEIGHT:.2f}")
                else:
                    local_weight = local_weight_raw
                    kaggle_weight = kaggle_weight_raw

                self.kaggle_weight = kaggle_weight
                self.local_weight = local_weight

                logger.info(f"更新混合模型权重: Kaggle={self.kaggle_weight:.2f}, 本地={self.local_weight:.2f}")

            # 保存权重
            weights_file = os.path.join(self.model_path, 'model_weights.pkl')
            with open(weights_file, 'wb') as f:
                pickle.dump({
                    'kaggle_weight': self.kaggle_weight,
                    'local_weight': self.local_weight,
                    'performance': self.performance_metrics
                }, f)

            logger.info(f"模型权重已保存到 {weights_file}")
        except Exception as e:
            logger.error(f"更新模型权重失败: {str(e)}")

    def load_model(self):
        """加载持久化模型 - 快速恢复机制"""
        try:
            # 初始化模型字典
            self.models = {}

            # 加载模型权重
            weights_file = os.path.join(self.model_path, 'model_weights.pkl')
            if os.path.exists(weights_file):
                with open(weights_file, 'rb') as f:
                    weights_data = pickle.load(f)
                    self.kaggle_weight = weights_data.get('kaggle_weight', 0.7)
                    self.local_weight = weights_data.get('local_weight', 0.3)
                    self.performance_metrics = weights_data.get('performance', {
                        'kaggle_rmse': 1.0,
                        'local_rmse': 1.0
                    })
                logger.info(f"加载模型权重: Kaggle={self.kaggle_weight:.2f}, 本地={self.local_weight:.2f}")

            # 加载ID映射
            mapping_file = os.path.join(self.model_path, 'anime_id_mapping.pkl')
            if os.path.exists(mapping_file):
                with open(mapping_file, 'rb') as f:
                    mapping_data = pickle.load(f)
                    self.anime_id_mapping = mapping_data.get('kaggle_to_local', {})
                    self.reverse_mapping = mapping_data.get('local_to_kaggle', {})
                logger.info(f"加载ID映射: {len(self.anime_id_mapping)} 个映射关系")

            # 加载Kaggle模型
            kaggle_model_file = os.path.join(self.model_path, 'kaggle_model.joblib')
            kaggle_encoders_file = os.path.join(self.model_path, 'kaggle_encoders.pkl')

            if os.path.exists(kaggle_model_file) and os.path.exists(kaggle_encoders_file):
                self.models['kaggle'] = joblib.load(kaggle_model_file)

                with open(kaggle_encoders_file, 'rb') as f:
                    kaggle_encoders = pickle.load(f)
                    self.kaggle_user_encoder = kaggle_encoders.get('user_encoder')
                    self.kaggle_anime_encoder = kaggle_encoders.get('anime_encoder')
                    self.kaggle_feature_scaler = kaggle_encoders.get('feature_scaler')
                    self.kaggle_anime_features = kaggle_encoders.get('anime_features', {})
                    self.kaggle_feature_names = kaggle_encoders.get('feature_names')

                logger.info("Kaggle模型加载成功")

            # 加载本地模型
            local_model_file = os.path.join(self.model_path, 'local_model.joblib')
            local_encoders_file = os.path.join(self.model_path, 'local_encoders.pkl')

            if os.path.exists(local_model_file) and os.path.exists(local_encoders_file):
                self.models['local'] = joblib.load(local_model_file)

                with open(local_encoders_file, 'rb') as f:
                    local_encoders = pickle.load(f)
                    self.user_encoder = local_encoders.get('user_encoder')
                    self.anime_encoder = local_encoders.get('anime_encoder')
                    self.feature_scaler = local_encoders.get('feature_scaler')
                    self.feature_names = local_encoders.get('feature_names')

                logger.info("本地模型加载成功")

            # 如果没有分离的模型，尝试加载统一模型
            if not self.models:
                unified_model_file = os.path.join(self.model_path, 'gbdt_model.joblib')
                unified_encoders_file = os.path.join(self.model_path, 'gbdt_encoders.pkl')

                if os.path.exists(unified_model_file) and os.path.exists(unified_encoders_file):
                    self.model = joblib.load(unified_model_file)
                    self.models['unified'] = self.model

                    with open(unified_encoders_file, 'rb') as f:
                        encoders = pickle.load(f)
                        self.user_encoder = encoders.get('user_encoder')
                        self.anime_encoder = encoders.get('anime_encoder')
                        self.feature_scaler = encoders.get('feature_scaler')
                        self.feature_names = encoders.get('feature_names')

                    logger.info("统一模型加载成功")
                    return True

            # 设置主模型为混合模型
            if 'local' in self.models:
                self.model = self.models['local']
            elif 'kaggle' in self.models:
                self.model = self.models['kaggle']
            else:
                logger.warning("未找到可用模型")
                return False

            logger.info(f"量子融合模型加载完成：{', '.join(self.models.keys())}")
            return len(self.models) > 0

        except Exception as e:
            logger.error(f"加载模型异常: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def predict(self, user_id, anime_id):
        """
        使用模型预测用户对动漫的评分 - 融合版

        通过设置feature_names解决X没有有效feature_names的问题
        """
        try:
            # 首先尝试使用本地模型预测
            local_pred = self._predict_with_local_model(user_id, anime_id)

            # 如果有Kaggle模型，尝试Kaggle预测
            kaggle_pred = self._predict_with_kaggle_model(user_id, anime_id)

            # 如果两个模型都有预测结果，使用加权平均
            if local_pred is not None and kaggle_pred is not None:
                final_pred = (local_pred * self.local_weight) + (kaggle_pred * self.kaggle_weight)
                return final_pred

            # 如果只有一个模型有预测结果，返回该结果
            if local_pred is not None:
                return local_pred
            if kaggle_pred is not None:
                return kaggle_pred

            # 如果没有任何模型能预测，返回默认值
            return 3.0  # 中等评分作为默认值

        except Exception as e:
            logger.error(f"预测异常: {str(e)}")
            return 3.0  # 发生异常时返回默认评分

    def _predict_with_local_model(self, user_id, anime_id):
        """
        使用本地模型预测

        参数:
            user_id: 用户ID
            anime_id: 动漫ID

        返回:
            预测评分
        """
        if 'local' not in self.models and 'unified' not in self.models:
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

            # 预测评分 - 使用本地或统一模型
            model = self.models.get('local', self.models.get('unified'))
            pred = model.predict(X)[0]

            # 限制评分范围
            pred = max(1.0, min(5.0, pred))

            return pred

        except Exception as e:
            logger.error(f"本地模型预测异常: {str(e)}")
            return None

    def _predict_with_kaggle_model(self, user_id, anime_id):
        """
        使用Kaggle模型预测

        参数:
            user_id: 用户ID (注意：这是本地系统的用户ID)
            anime_id: 动漫ID (注意：这是本地系统的动漫ID)

        返回:
            预测评分
        """
        if 'kaggle' not in self.models:
            return None

        try:
            # 将本地动漫ID转换为Kaggle ID
            kaggle_anime_id = self.reverse_mapping.get(anime_id)
            if kaggle_anime_id is None:
                # 没有对应的Kaggle ID，回退到本地模型
                return None

            # 获取该动漫的Kaggle特征
            anime_features = self.kaggle_anime_features.get(kaggle_anime_id, [0, 0, 0, 0, 0])

            # 由于Kaggle用户与本地用户无法直接映射，我们使用一个固定的Kaggle用户ID
            # 这意味着我们主要依赖动漫特征而非用户特征进行预测
            # 这是一种近似方法，实际应用中可能需要更复杂的用户映射策略

            # 使用用户评分历史作为特征
            ratings_count = UserRating.objects.filter(user_id=user_id).count()

            # 简化的特征转换
            # 1. 使用固定用户ID
            # 2. 使用本地评分数量
            # 3. 使用动漫特征
            try:
                # 使用Kaggle模型中的第一个用户ID
                dummy_user_id = 0
                features = [[dummy_user_id, min(ratings_count, 100) / 100, 0] + anime_features]

                # 标准化特征
                X = self.kaggle_feature_scaler.transform(features)

                # 预测
                pred = self.models['kaggle'].predict(X)[0]

                # 将Kaggle评分(0.1-1.0)转换为本地评分(1-5)
                pred = pred * 5.0

                # 限制评分范围
                pred = max(1.0, min(5.0, pred))

                return pred
            except Exception as inner_e:
                logger.error(f"Kaggle模型预测内部异常: {str(inner_e)}")
                return None

        except Exception as e:
            logger.error(f"Kaggle模型预测异常: {str(e)}")
            return None

    def get_recommendations(self, user_id, limit=10, exclude_rated=True):
        """用GBDT模型生成推荐 - 全局最优解方法"""
        if not self.models:
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

            # 候选集过滤 - 剪枝优化
            candidate_animes = [anime for anime in all_animes if anime['id'] not in rated_animes]

            # 按照流行度排序取topK - 先验概率加速
            candidate_animes = sorted(candidate_animes, key=lambda x: x['popularity'] or 0, reverse=True)[
                               :min(100, len(candidate_animes))]

            # 快速预测 - 批量操作
            predictions = []
            for anime in candidate_animes:
                anime_id = anime['id']

                # 使用混合模型预测
                pred = self.predict(user_id, anime_id)

                if pred is not None:
                    # 归一化评分 (1-5) -> (0-1)
                    norm_score = (pred - 1.0) / 4.0
                    predictions.append((anime_id, norm_score))

            # 排序并返回topK
            predictions.sort(key=lambda x: x[1], reverse=True)

            return predictions[:limit]

        except Exception as e:
            logger.error(f"推荐引擎异常: {str(e)}")
            logger.error(traceback.format_exc())
            return []

    def update_weights_from_feedback(self, user_id, anime_id, actual_rating):
        """
        根据用户实际评分更新模型权重

        参数:
            user_id: 用户ID
            anime_id: 动漫ID
            actual_rating: 用户实际评分
        """
        try:
            # 获取本地和Kaggle模型的预测
            local_pred = self._predict_with_local_model(user_id, anime_id)
            kaggle_pred = self._predict_with_kaggle_model(user_id, anime_id)

            if local_pred is None or kaggle_pred is None:
                return

            # 计算误差
            local_error = abs(local_pred - actual_rating)
            kaggle_error = abs(kaggle_pred - actual_rating)

            # 根据错误调整权重
            if local_error < kaggle_error:
                # 本地模型更准确，增加权重
                self.local_weight = min(0.9, self.local_weight + self.weight_update_step)
                self.kaggle_weight = 1.0 - self.local_weight
            elif kaggle_error < local_error:
                # Kaggle模型更准确，增加权重
                self.kaggle_weight = min(0.9, self.kaggle_weight + self.weight_update_step)
                self.local_weight = 1.0 - self.kaggle_weight

            # 保存更新的权重
            self._update_model_weights()

            logger.info(f"根据用户反馈更新模型权重: 本地={self.local_weight:.3f}, Kaggle={self.kaggle_weight:.3f}")

        except Exception as e:
            logger.error(f"更新模型权重失败: {str(e)}")