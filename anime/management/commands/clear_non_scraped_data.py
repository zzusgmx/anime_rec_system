from django.core.management.base import BaseCommand
from anime.models import Anime


class Command(BaseCommand):
    help = '清理非爬虫爬取的数据'

    def handle(self, *args, **options):
        # 定义识别爬虫数据的条件
        # 例如：爬虫数据的描述可能包含特定的标记
        non_scraped = Anime.objects.exclude(description__contains="MyAnimeList")
        count = non_scraped.count()

        # 执行删除
        if count > 0:
            self.stdout.write(f"发现 {count} 条非爬虫数据，准备删除...")
            non_scraped.delete()
            self.stdout.write(self.style.SUCCESS(f"成功删除 {count} 条非爬虫数据"))
        else:
            self.stdout.write("未发现非爬虫数据")