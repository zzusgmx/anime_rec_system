# recommendation/management/commands/init_recommendation_system.py

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
import os
import sys
import time
import logging

logger = logging.getLogger('django')


class Command(BaseCommand):
    help = '推荐系统初始化: 爬虫数据获取 + 模型训练的一体化流程'

    def add_arguments(self, parser):
        parser.add_argument('--skip-crawl', action='store_true',
                            help='跳过爬虫阶段')
        parser.add_argument('--skip-train', action='store_true',
                            help='跳过模型训练阶段')
        parser.add_argument('--crawl-pages', type=int, default=5,
                            help='爬虫页数')
        parser.add_argument('--test', action='store_true',
                            help='测试模式')

    def handle(self, *args, **options):
        skip_crawl = options.get('skip_crawl')
        skip_train = options.get('skip_train')
        crawl_pages = options.get('crawl_pages')
        test_mode = options.get('test')

        # 命令头信息
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS(f'推荐系统一体化初始化工具 v1.0.0 - {timezone.now()}'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        start_time = time.time()

        try:
            # 阶段1: 爬虫获取数据
            if not skip_crawl:
                self._crawl_data(crawl_pages, test_mode)
            else:
                self.stdout.write(self.style.WARNING('根据参数跳过爬虫阶段'))

            # 阶段2: 模型训练
            if not skip_train:
                self._train_model(test_mode)
            else:
                self.stdout.write(self.style.WARNING('根据参数跳过模型训练阶段'))

            # 完成
            elapsed_time = time.time() - start_time
            self.stdout.write(self.style.SUCCESS('=' * 80))
            self.stdout.write(self.style.SUCCESS(f'推荐系统初始化完成! 总耗时: {elapsed_time:.2f}秒'))
            self.stdout.write(self.style.SUCCESS('=' * 80))

        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR('用户中断操作'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'初始化过程发生异常: {str(e)}'))

    def _crawl_data(self, pages, test_mode):
        """执行爬虫阶段"""
        self.stdout.write(self.style.SUCCESS('\n[阶段 1/2] 爬虫数据获取'))
        self.stdout.write('-' * 50)

        # 构建爬虫命令参数
        crawl_args = [
            '--pages', str(pages),
        ]

        if test_mode:
            crawl_args.append('--debug')

        # 测试模式下减少页数
        if test_mode:
            crawl_args = ['--pages', '2']  # 测试模式只爬取2页

        # 执行爬虫命令
        self.stdout.write(self.style.WARNING('启动爬虫获取新数据...'))
        call_command('crawl_anime', *crawl_args)

    def _train_model(self, test_mode):
        """执行模型训练阶段"""
        self.stdout.write(self.style.SUCCESS('\n[阶段 2/2] 推荐模型训练'))
        self.stdout.write('-' * 50)

        # 构建训练命令参数
        train_args = ['--force']

        if test_mode:
            train_args.extend(['--trees', '50'])  # 测试模式使用较小的模型
            train_args.append('--debug')

        # 执行训练命令
        self.stdout.write(self.style.WARNING('开始训练推荐模型...'))
        call_command('train_ml_model', *train_args)