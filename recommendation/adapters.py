# recommendation/adapters.py - 创建这个新文件

import pandas as pd
import numpy as np
from django.db import models
from typing import List, Dict, Tuple, Optional, Any, Union
import logging

logger = logging.getLogger('django')


class QuantumDataAdapter:
    """
    量子数据适配器 - 双通道训练数据融合系统

    支持两种数据源:
    1. 数据库通道 - 从Django ORM中提取训练数据
    2. 原始数据通道 - 直接从CSV/DataFrame处理数据

    实现了训练/特征的统一视图，无论数据来源
    """

    def __init__(self):
        self.db_data = None
        self.raw_data = None
        self.fusion_mode = "concat"  # 可选: concat, merge, weighted

    def load_from_database(self, queryset, value_fields) -> None:
        """从数据库加载训练数据"""
        self.db_data = pd.DataFrame(list(queryset.values(*value_fields)))
        logger.info(f"从数据库加载了 {len(self.db_data)} 条记录")

    def load_from_dataframe(self, df: pd.DataFrame) -> None:
        """直接加载DataFrame数据"""
        self.raw_data = df
        logger.info(f"从原始数据加载了 {len(self.raw_data)} 条记录")

    def load_from_csv(self, filepath: str,
                      rating_col: str = 'rating',
                      user_col: str = 'user_id',
                      item_col: str = 'anime_id') -> None:
        """从CSV文件加载训练数据"""
        try:
            # 关键修复：更强的路径处理
            import os
            normalized_path = os.path.abspath(os.path.expanduser(filepath))

            # 输出更详细的路径信息
            logger.info(f"CSV路径诊断:")
            logger.info(f" - 原始路径: {filepath}")
            logger.info(f" - 规范化路径: {normalized_path}")
            logger.info(f" - 当前工作目录: {os.getcwd()}")

            # 验证文件存在
            if not os.path.exists(normalized_path):
                logger.error(f"文件不存在: {normalized_path}")
                raise FileNotFoundError(f"找不到文件: {normalized_path}")

            # 尝试读取CSV
            df = pd.read_csv(normalized_path)
            logger.info(f"成功读取CSV，列名: {list(df.columns)}")

            # 更健壮的列映射逻辑
            column_mapping = {
                'userId': user_col,
                'itemId': item_col,
                'movieId': item_col,
                'score': rating_col,
            }

            # 只映射存在的列
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df.rename(columns={old_col: new_col}, inplace=True)

            # 验证必要的列是否存在
            required_cols = [user_col, item_col, rating_col]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                # 尝试从类似列推断
                similar_cols = {
                    'user_id': ['user', 'uid', 'userid'],
                    'anime_id': ['anime', 'animeid', 'item_id', 'item'],
                    'rating': ['rate', 'score', 'stars']
                }

                for req_col in missing_cols:
                    for df_col in df.columns:
                        if df_col.lower() in similar_cols.get(req_col, []):
                            df.rename(columns={df_col: req_col}, inplace=True)
                            logger.info(f"推断列映射: {df_col} → {req_col}")

                # 再次检查
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    raise ValueError(f"CSV文件缺少必要列: {missing_cols}")

            self.raw_data = df
            logger.info(f"成功加载 {len(df)} 条记录")
        except Exception as e:
            logger.error(f"CSV加载异常: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def set_fusion_mode(self, mode: str) -> None:
        """设置数据融合模式"""
        valid_modes = ["concat", "merge", "weighted"]
        if mode not in valid_modes:
            raise ValueError(f"不支持的融合模式: {mode}. 请使用: {valid_modes}")
        self.fusion_mode = mode

    def get_fused_data(self) -> pd.DataFrame:
        """获取融合后的训练数据"""
        if self.db_data is None and self.raw_data is None:
            raise ValueError("无可用数据源 - 请先加载数据")

        if self.db_data is None:
            return self.raw_data

        if self.raw_data is None:
            return self.db_data

        # 执行数据融合 - 根据选择的模式
        if self.fusion_mode == "concat":
            # 简单连接 - 所有记录合并
            return pd.concat([self.db_data, self.raw_data], ignore_index=True)

        elif self.fusion_mode == "merge":
            # 根据用户和物品ID合并 - 有重复时使用原始数据
            return pd.concat([self.db_data, self.raw_data]).drop_duplicates(
                subset=['user_id', 'anime_id'], keep='first')

        elif self.fusion_mode == "weighted":
            # 高级加权融合 - 数据库数据权重更高
            merged = pd.concat([self.db_data, self.raw_data])
            # 标记来源
            self.db_data['source'] = 'db'
            self.raw_data['source'] = 'raw'
            # 按用户和动漫分组，优先保留数据库记录
            return merged.sort_values('source').drop_duplicates(
                subset=['user_id', 'anime_id'], keep='first').drop('source', axis=1)

        return None

    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """准备训练数据并进行特征工程"""
        data = self.get_fused_data()

        if data is None or len(data) < 50:  # 保留最小数据量检查
            logger.warning("训练数据不足，模型性能将受限")
            return None, None

        # 基本特征提取 - 可根据需要扩展
        X = data[['user_id', 'anime_id']].values
        y = data['rating'].values

        logger.info(f"准备了 {len(X)} 条训练记录，特征维度: {X.shape[1]}")
        return X, y


# 使用示例:
"""
adapter = QuantumDataAdapter()

# 从数据库加载数据
from recommendation.models import UserRating
adapter.load_from_database(UserRating.objects.all(), 
                          ['user_id', 'anime_id', 'rating'])

# 从Kaggle加载数据
adapter.load_from_csv('kaggle_anime_ratings.csv')

# 设置融合模式
adapter.set_fusion_mode('concat')

# 获取训练数据
X, y = adapter.prepare_training_data()
"""