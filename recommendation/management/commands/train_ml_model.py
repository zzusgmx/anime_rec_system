# recommendation/management/commands/train_ml_model.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from recommendation.engine.models.ml_engine import GBDTRecommender
import logging

logger = logging.getLogger('django')


class Command(BaseCommand):
    help = '训练或更新机器学习推荐模型'

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

    def handle(self, *args, **options):
        # 获取参数
        force = options['force']
        trees = options['trees']
        lr = options['lr']
        depth = options['depth']
        debug = options['debug']

        # 初始化引擎和训练
        try:
            # 实例化推荐引擎
            engine = GBDTRecommender(
                n_estimators=trees,
                learning_rate=lr,
                max_depth=depth
            )

            # 检查模型是否存在
            if not force and engine.load_model():
                self.stdout.write(self.style.WARNING('模型已存在，使用--force重新训练'))
                return

            # 执行训练，仅使用系统内部数据
            self.stdout.write(self.style.SUCCESS(f'开始训练模型: 树数量={trees}, 学习率={lr}, 树深度={depth}'))
            success = engine.train_model()

            if success:
                self.stdout.write(self.style.SUCCESS('模型训练成功 → 线性空间已量化'))
            else:
                self.stdout.write(self.style.ERROR('模型训练失败 → 量子退相干错误'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'训练异常: {str(e)}'))
            if debug:
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))