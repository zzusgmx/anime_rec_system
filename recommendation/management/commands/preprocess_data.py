# recommendation/management/commands/preprocess_data.py

from django.core.management.base import BaseCommand
from django.utils import timezone
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import logging

logger = logging.getLogger('django')


class PreprocessDataPipeline:
    """量子预处理管道 - 优化推荐系统输入矩阵"""

    def __init__(self):
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=0.95)  # 保留95%的方差

    def run(self):
        logger.info("🧠 启动量子预处理管道...")
        # 1. 特征提取
        raw_features = self._extract_features()

        # 2. 数据标准化
        normalized_features = self._normalize_data(raw_features)

        # 3. 维度约简
        reduced_features = self._reduce_dimensions(normalized_features)

        # 4. 特征向量化
        vectorized_features = self._vectorize_features(reduced_features)

        logger.info(
            f"✨ 量子预处理管道完成: {vectorized_features.shape[0]}行×{vectorized_features.shape[1]}列的特征矩阵")
        return vectorized_features

    def _extract_features(self):
        """从数据库提取原始特征"""
        from anime.models import Anime
        from recommendation.models import UserRating, UserComment, UserFavorite

        logger.info("🔍 执行特征提取...")
        # 这里实现你的特征提取逻辑
        # 例如，从模型中提取各种特征并组织成DataFrame

        # 示例代码
        anime_features = pd.DataFrame(
            list(Anime.objects.values('id', 'rating_avg', 'rating_count',
                                      'view_count', 'favorite_count', 'popularity'))
        )

        return anime_features

    def _normalize_data(self, features_df):
        """将数据标准化到相同量级"""
        logger.info("📊 执行数据标准化...")

        # 创建特征矩阵副本，避免修改原始数据
        df = features_df.copy()

        # 选择需要标准化的数值列
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        numeric_cols = [col for col in numeric_cols if col != 'id']

        # 应用标准化变换
        if numeric_cols:
            df[numeric_cols] = self.scaler.fit_transform(df[numeric_cols])

        return df

    def _reduce_dimensions(self, normalized_df):
        """使用PCA执行维度约简"""
        logger.info("🧩 执行维度约简...")

        # 创建数据副本
        df = normalized_df.copy()

        # 保存ID列
        ids = df['id'].values if 'id' in df.columns else None

        # 选择数值列进行降维
        numeric_cols = df.select_dtypes(include=['float64']).columns
        numeric_cols = [col for col in numeric_cols if col != 'id']

        if len(numeric_cols) > 2 and len(df) > 10:  # 至少需要3个特征和足够的样本量
            # 应用PCA
            reduced_data = self.pca.fit_transform(df[numeric_cols])

            # 创建新的DataFrame
            component_cols = [f'pc_{i + 1}' for i in range(reduced_data.shape[1])]
            reduced_df = pd.DataFrame(reduced_data, columns=component_cols)

            # 添加回ID列
            if ids is not None:
                reduced_df['id'] = ids

            logger.info(f"✂️ 维度从{len(numeric_cols)}降到{reduced_data.shape[1]}")
            return reduced_df
        else:
            logger.info("⚠️ 特征数量不足，跳过降维")
            return df

    def _vectorize_features(self, features_df):
        """将特征转换为向量形式，适合机器学习模型使用"""
        logger.info("🧮 执行特征向量化...")

        # 实现特征向量化逻辑
        # 例如，处理类别特征、文本特征等

        # 在这个简单示例中，我们只返回已经处理过的DataFrame
        return features_df


class Command(BaseCommand):
    help = '执行数据预处理流水线，优化推荐系统的输入矩阵'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, help='输出处理后特征矩阵的文件路径')
        parser.add_argument('--debug', action='store_true', help='启用调试模式')

    def handle(self, *args, **options):
        if options['debug']:
            logging.basicConfig(level=logging.DEBUG)

        self.stdout.write(self.style.SUCCESS('🚀 启动量子预处理管道'))

        try:
            # 实例化并运行预处理管道
            pipeline = PreprocessDataPipeline()
            processed_data = pipeline.run()

            # 如果指定了输出路径，保存结果
            if options['output']:
                processed_data.to_csv(options['output'], index=False)
                self.stdout.write(self.style.SUCCESS(
                    f'💾 特征矩阵已保存至: {options["output"]}'
                ))

            self.stdout.write(self.style.SUCCESS(
                f'✅ 预处理完成: 生成{processed_data.shape[0]}×{processed_data.shape[1]}特征矩阵'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 预处理失败: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))