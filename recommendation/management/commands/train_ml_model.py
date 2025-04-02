# recommendation/management/commands/train_ml_model.py

# 设置环境变量避免wmic问题，必须在所有其他导入之前
import os
os.environ['LOKY_MAX_CPU_COUNT'] = str(os.cpu_count() or 4)

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
import logging
import time
import traceback

logger = logging.getLogger('django')


class Command(BaseCommand):
    help = '训练或更新机器学习推荐模型 - 支持Kaggle数据集'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='强制重新训练模型')
        parser.add_argument('--trees', type=int, default=100,
                            help='决策树数量')
        parser.add_argument('--lr', type=float, default=0.1,
                            help='学习率')
        parser.add_argument('--depth', type=int, default=5,
                            help='树深度')
        parser.add_argument('--debug', action='store_true',
                            help='调试模式')
        parser.add_argument('--kaggle-data', type=str, default=None,
                            help='Kaggle数据集目录路径，默认查找D:/dmos/anime_rec_system/archive或项目archive目录')
        parser.add_argument('--anime-csv', type=str, default=None,
                            help='动漫CSV文件路径，如果不指定则查找{kaggle-data}/anime.csv')
        parser.add_argument('--rating-csv', type=str, default=None,
                            help='评分CSV文件路径，如果不指定则查找{kaggle-data}/rating.csv')
        parser.add_argument('--ensemble', action='store_true',
                            help='训练集成模型（同时使用本地和Kaggle数据）')
        parser.add_argument('--local-only', action='store_true',
                            help='仅使用本地数据训练')

    def handle(self, *args, **options):
        # 获取参数
        force = options['force']
        trees = options['trees']
        lr = options['lr']
        depth = options['depth']
        debug = options['debug']
        kaggle_data = options['kaggle_data']
        anime_csv = options['anime_csv']
        rating_csv = options['rating_csv']
        ensemble = options['ensemble']
        local_only = options['local_only']

        # 查找Kaggle数据集
        if not kaggle_data:
            # 尝试几个可能的位置
            possible_paths = [
                os.path.join(settings.BASE_DIR, 'archive'),
                os.path.join('D:', os.sep, 'dmos', 'anime_rec_system', 'archive'),
                os.path.join(settings.BASE_DIR, '..', 'archive')
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    kaggle_data = path
                    break

        # 如果指定了Kaggle数据目录，但没有指定具体文件，则查找默认文件
        if kaggle_data and not anime_csv:
            anime_csv = os.path.join(kaggle_data, 'anime.csv')

        if kaggle_data and not rating_csv:
            rating_csv = os.path.join(kaggle_data, 'rating.csv')

        # 检查文件是否存在
        if not local_only and (not os.path.exists(anime_csv) or not os.path.exists(rating_csv)):
            self.stdout.write(self.style.WARNING(f"❌ Kaggle数据文件不存在: {anime_csv} 或 {rating_csv}"))
            if not local_only:
                self.stdout.write(self.style.WARNING("⚠️ 将回退到仅使用本地数据训练"))
                local_only = True

        # 显示训练配置
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'🚀 推荐模型训练启动 [{timezone.now()}]'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'📊 训练配置:')
        self.stdout.write(f' - 模型参数: 树={trees}, 学习率={lr}, 深度={depth}')

        if local_only:
            self.stdout.write(f' - 数据源: 仅本地数据')
        elif ensemble:
            self.stdout.write(f' - 数据源: 集成模式 (本地 + Kaggle)')
            self.stdout.write(f' - Kaggle动漫数据: {anime_csv}')
            self.stdout.write(f' - Kaggle评分数据: {rating_csv}')
        else:
            self.stdout.write(f' - 数据源: 优先Kaggle数据')
            self.stdout.write(f' - Kaggle动漫数据: {anime_csv}')
            self.stdout.write(f' - Kaggle评分数据: {rating_csv}')

        # 训练计时
        start_time = time.time()

        try:
            if ensemble:
                # 训练集成模型
                self.stdout.write(self.style.SUCCESS('🧠 开始训练集成模型...'))
                from recommendation.engine.multi_source_trainer import QuantumEnsembleTrainer
                trainer = QuantumEnsembleTrainer(kaggle_data_dir=kaggle_data)
                success = trainer.train_ensemble_model()
            else:
                # 实例化推荐引擎
                from recommendation.engine.models.ml_engine import GBDTRecommender
                engine = GBDTRecommender(
                    n_estimators=trees,
                    learning_rate=lr,
                    max_depth=depth
                )

                # 检查模型是否存在
                if not force and engine.load_model():
                    self.stdout.write(self.style.WARNING('⚠️ 模型已存在，使用--force重新训练'))
                    return

                # 执行训练
                if local_only:
                    self.stdout.write(self.style.SUCCESS('🧠 开始训练本地数据模型...'))
                    success = engine.train_model()
                else:
                    self.stdout.write(self.style.SUCCESS(f'🧠 开始训练模型 (使用Kaggle数据)...'))
                    success = engine.train_model(anime_csv_path=anime_csv, rating_csv_path=rating_csv)

            if success:
                self.stdout.write(self.style.SUCCESS('✅ 模型训练成功 → 线性空间已量化'))
            else:
                self.stdout.write(self.style.ERROR('❌ 模型训练失败 → 量子退相干错误'))

            # 显示训练耗时
            training_time = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(f'⏱️ 训练耗时: {training_time:.2f}秒'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 训练异常: {str(e)}'))
            if debug:
                self.stdout.write(self.style.ERROR(traceback.format_exc()))