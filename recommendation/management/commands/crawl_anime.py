# recommendation/management/commands/crawl_anime.py

import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from recommendation.scrapers.myanimelist_scraper import MyAnimeListScraper
import logging

logger = logging.getLogger('django')


class Command(BaseCommand):
    help = '启动动漫爬虫以增量抓取新内容'

    def add_arguments(self, parser):
        parser.add_argument('--pages', type=int, default=5,
                            help='爬取的页数')
        parser.add_argument('--delay', type=float, default=2.5,
                            help='请求延迟(秒)')
        parser.add_argument('--full', action='store_true',
                            help='全量抓取模式(默认增量)')
        parser.add_argument('--debug', action='store_true',
                            help='调试模式，打印更多信息')
        parser.add_argument('--retries', type=int, default=3,
                            help='请求失败时的重试次数')
        parser.add_argument('--deep', action='store_true',
                            help='深度爬取模式，获取更多详细信息')

    def handle(self, *args, **options):
        pages = options['pages']
        delay = options['delay']
        incremental = not options['full']
        debug = options['debug']
        retries = options['retries']
        deep = options['deep']

        # 配置日志级别
        if debug:
            import logging
            logger.setLevel(logging.DEBUG)
            self.stdout.write(self.style.WARNING('调试模式已启用，日志级别设为DEBUG'))

        # 爬虫启动头信息
        self.stdout.write(self.style.SUCCESS(f'===== MyAnimeList爬虫启动于 {timezone.now()} ====='))
        self.stdout.write(self.style.SUCCESS(f'页数: {pages}'))
        self.stdout.write(self.style.SUCCESS(f'延迟: {delay}秒'))
        self.stdout.write(self.style.SUCCESS(f'模式: {"增量" if incremental else "全量"}'))
        self.stdout.write(self.style.SUCCESS(f'重试次数: {retries}'))
        self.stdout.write(self.style.SUCCESS(f'深度模式: {"开启" if deep else "关闭"}'))

        # 记录开始时间
        start_time = time.time()
        total_added = 0

        try:
            # 启动MyAnimeList爬虫
            self.stdout.write(self.style.WARNING('启动MyAnimeList爬虫...'))
            mal_scraper = MyAnimeListScraper(delay=delay, retries=retries)

            # 启用深度模式时，设置爬虫附加参数
            if deep:
                mal_scraper.set_deep_mode(True)

            added = mal_scraper.run(max_pages=pages, incremental=incremental)
            total_added += added
            self.stdout.write(self.style.SUCCESS(f'MyAnimeList爬虫完成，新增 {added} 部动漫'))

            # 计算总耗时
            elapsed_time = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(
                f'爬虫任务完成，总共新增 {total_added} 部动漫，耗时 {elapsed_time:.2f} 秒'))

            # 如果有新增内容，提示重建模型
            if total_added > 0:
                self.stdout.write(self.style.WARNING(
                    '检测到新增内容，正在自动重建推荐模型...'))

                # 自动调用模型训练
                from recommendation.engine.models.ml_engine import GBDTRecommender
                recommender = GBDTRecommender()
                if recommender.train_model():
                    self.stdout.write(self.style.SUCCESS('推荐模型重建成功!'))
                else:
                    self.stdout.write(self.style.ERROR('推荐模型重建失败，请手动执行 python manage.py train_ml_model'))

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('爬虫任务被用户中断'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'爬虫任务异常: {str(e)}'))