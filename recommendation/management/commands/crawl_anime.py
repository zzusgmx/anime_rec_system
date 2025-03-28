from django.core.management.base import BaseCommand
from recommendation.scrapers.myanimelist_scraper import MyAnimeListScraper
import logging

logger = logging.getLogger('django')


class Command(BaseCommand):
    help = '从外部源抓取动漫数据'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, default='myanimelist',
                            help='数据源 (目前仅支持 myanimelist)')
        parser.add_argument('--mode', type=str, default='top',
                            help='抓取模式 (top, search, id)')
        parser.add_argument('--query', type=str, help='搜索查询（当mode=search时使用）')
        parser.add_argument('--id', type=int, help='抓取特定ID（当mode=id时使用）')
        parser.add_argument('--start-page', type=int, default=1,
                            help='开始爬取的页数')
        parser.add_argument('--count', type=int, default=1,
                            help='爬取页数')
        parser.add_argument('--import', action='store_true',
                            help='导入抓取的数据到数据库')
        parser.add_argument('--delay', type=float, default=4.0,
                            help='请求间隔时间（秒）')
        parser.add_argument('--retries', type=int, default=3,
                            help='最大重试次数')
        parser.add_argument('--force', action='store_true',
                            help='强制导入已存在的动漫')

    def handle(self, *args, **options):
        source = options['source']
        mode = options['mode']
        query = options['query']
        anime_id = options['id']
        start_page = options['start_page']
        count = options['count']
        import_data = options['import']
        delay = options['delay']
        retries = options['retries']
        force = options['force']

        self.stdout.write(f"开始从 {source} 抓取动漫数据...")

        # 实例化爬虫
        if source == 'myanimelist':
            scraper = MyAnimeListScraper(delay=delay, max_retries=retries)
        else:
            self.stderr.write(f"不支持的数据源: {source}")
            return

        # 根据模式执行不同的抓取逻辑
        if mode == 'top':
            self.stdout.write(f"抓取热门动漫排行榜 (从第{start_page}页开始，共{count}页)")

            # 始终导入数据，但除非force参数为True，否则跳过已存在的动漫
            incremental = not force

            if not import_data:
                self.stdout.write(self.style.WARNING("警告: 未指定--import参数，将只抓取但不导入数据"))

            added = scraper.run(start_page=start_page, max_pages=count, incremental=incremental, do_import=import_data)

            self.stdout.write(f"成功抓取并添加 {added} 部动漫")

        elif mode == 'search' and query:
            self.stdout.write(f"搜索动漫: {query}")
            self.stderr.write("搜索模式尚未实现")
            return

        elif mode == 'id' and anime_id:
            self.stdout.write(f"抓取特定ID: {anime_id}")
            self.stderr.write("ID抓取模式尚未实现")
            return

        else:
            self.stderr.write("无效的模式或参数组合")
            return

        self.stdout.write(self.style.SUCCESS("抓取完成"))