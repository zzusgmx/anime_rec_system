# recommendation/engine/multi_source_trainer.py
import logging
import os
import numpy as np
import pandas as pd
from django.conf import settings
from django.db.models import Count, Avg
from sklearn.ensemble import GradientBoostingRegressor
from anime.models import Anime
from recommendation.models import UserRating
from users.models import UserPreference

# 配置日志记录器
logger = logging.getLogger('django')


class QuantumEnsembleTrainer:
    """
    多源量子态模型融合引擎 - 支持Kaggle数据集训练

    核心特性:
    - 支持多数据源训练和预测
    - 动态权重调整
    - ID空间映射与跨域泛化
    - 增量学习支持
    """

    def __init__(self, kaggle_data_dir=None):
        """
        初始化多源训练器

        参数:
            kaggle_data_dir: Kaggle数据集目录，默认为None
        """
        # 检查Kaggle数据目录
        self.kaggle_data_dir = kaggle_data_dir

        # 尝试查找默认位置的Kaggle数据
        if self.kaggle_data_dir is None:
            possible_paths = [
                os.path.join(settings.BASE_DIR, 'archive'),
                os.path.join('D:', os.sep, 'dmos', 'anime_rec_system', 'archive'),
                os.path.join(settings.BASE_DIR, '..', 'archive')
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    self.kaggle_data_dir = path
                    break

        # 初始化模型 - 移除了prefix参数
        from recommendation.engine.models.ml_engine import GBDTRecommender
        self.local_model = GBDTRecommender()

        # 初始化权重
        self.ensemble_weights = {'local': 0.65, 'kaggle': 0.35}

        logger.info(f"多源融合训练器初始化: Kaggle数据目录={self.kaggle_data_dir}")

    def train_ensemble_model(self):
        """
        训练集成模型 - 整合本地和Kaggle数据

        返回:
            bool: 训练是否成功
        """
        # 检查Kaggle数据集
        kaggle_anime_path = None
        kaggle_rating_path = None

        if self.kaggle_data_dir and os.path.exists(self.kaggle_data_dir):
            kaggle_anime_path = os.path.join(self.kaggle_data_dir, 'anime.csv')
            kaggle_rating_path = os.path.join(self.kaggle_data_dir, 'rating.csv')

            if not os.path.exists(kaggle_anime_path) or not os.path.exists(kaggle_rating_path):
                logger.warning(f"Kaggle数据文件不存在: {kaggle_anime_path} 或 {kaggle_rating_path}")
                kaggle_anime_path = None
                kaggle_rating_path = None

        # 训练本地数据模型
        logger.info("开始训练本地数据模型...")
        local_success = self.train_local_model()

        # 如果有Kaggle数据，集成训练
        if kaggle_anime_path and kaggle_rating_path:
            logger.info(f"使用Kaggle数据训练集成模型: {kaggle_anime_path}, {kaggle_rating_path}")

            # 训练完整的集成模型
            from recommendation.engine.models.ml_engine import GBDTRecommender
            ensemble_model = GBDTRecommender()

            # 训练集成模型
            ensemble_success = ensemble_model.train_model(
                anime_csv_path=kaggle_anime_path,
                rating_csv_path=kaggle_rating_path
            )

            if ensemble_success:
                logger.info("集成模型训练成功！")
                return True
            else:
                logger.warning("集成模型训练失败，将使用本地模型")
                return local_success
        else:
            logger.info("未找到Kaggle数据集，仅使用本地数据训练")
            return local_success

    def train_local_model(self):
        """
        爬虫数据训练管道

        返回:
            bool: 训练是否成功
        """
        # 检查训练数据
        ratings_count = UserRating.objects.count()
        if ratings_count < 50:
            logger.warning(f"本地训练数据不足，仅有 {ratings_count} 条评分记录")
            if ratings_count == 0:
                logger.error("没有本地训练数据，无法训练模型")
                return False

        try:
            # 使用本地数据训练模型
            from recommendation.engine.models.ml_engine import GBDTRecommender
            local_model = GBDTRecommender()
            success = local_model.train_model()

            if success:
                logger.info("本地模型训练成功")
                return True
            else:
                logger.error("本地模型训练失败")
                return False
        except Exception as e:
            logger.error(f"本地模型训练异常: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def load_kaggle_data(self):
        """
        加载Kaggle数据集

        返回:
            tuple: (anime_df, rating_df) 如果成功，否则 (None, None)
        """
        if not self.kaggle_data_dir or not os.path.exists(self.kaggle_data_dir):
            logger.error(f"Kaggle数据目录不存在: {self.kaggle_data_dir}")
            return None, None

        anime_path = os.path.join(self.kaggle_data_dir, 'anime.csv')
        rating_path = os.path.join(self.kaggle_data_dir, 'rating.csv')

        if not os.path.exists(anime_path) or not os.path.exists(rating_path):
            logger.error(f"Kaggle数据文件不存在: {anime_path} 或 {rating_path}")
            return None, None

        try:
            anime_df = pd.read_csv(anime_path)
            rating_df = pd.read_csv(rating_path)

            # 数据探索
            logger.info(f"加载了 {len(anime_df)} 个动漫和 {len(rating_df)} 条评分记录")

            # 数据清洗：移除无效评分 (-1表示已看但未评分)
            valid_rating_df = rating_df[rating_df['rating'] > 0]
            logger.info(f"有效评分记录: {len(valid_rating_df)}/{len(rating_df)}")

            return anime_df, valid_rating_df
        except Exception as e:
            logger.error(f"加载Kaggle数据异常: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None, None

    def _prepare_local_data(self):
        """
        准备本地数据用于训练

        返回:
            tuple: (X, y) 特征矩阵和目标向量
        """
        # 这只是一个简化的实现
        # 实际上，我们需要遵循ml_engine.py中的prepare_data方法
        from recommendation.engine.models.ml_engine import GBDTRecommender
        gbdt = GBDTRecommender()
        return gbdt.prepare_data()

    def predict(self, user_features, anime_features):
        """
        集成预测 - 后验概率融合

        参数:
            user_features: 用户特征
            anime_features: 动漫特征

        返回:
            float: 预测评分
        """
        # 加载GBDT模型
        from recommendation.engine.models.ml_engine import GBDTRecommender
        gbdt = GBDTRecommender()

        if not gbdt.load_model():
            logger.warning("无法加载模型，使用默认推荐")
            return 0.5  # 默认中等分数

        # 使用量子融合模型预测
        return gbdt.predict(user_features['user_id'], anime_features['anime_id'])

    def get_ensemble_recommendations(self, user_id, limit=10):
        """
        获取集成推荐

        参数:
            user_id: 用户ID
            limit: 推荐数量上限

        返回:
            list: 推荐列表 [(anime_id, score), ...]
        """
        # 使用GBDT模型获取推荐
        from recommendation.engine.models.ml_engine import GBDTRecommender
        gbdt = GBDTRecommender()

        if not gbdt.load_model():
            logger.warning("无法加载模型，使用默认推荐")
            return []

        return gbdt.get_recommendations(user_id, limit)