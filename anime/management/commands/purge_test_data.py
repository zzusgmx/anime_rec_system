# anime/management/commands/purge_test_data.py
from django.core.management.base import BaseCommand
from anime.models import Anime, AnimeType
from django.db import transaction


class Command(BaseCommand):
    help = '清除所有实验性爬取的动漫数据'

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='确认执行删除操作')
        parser.add_argument('--keep-types', action='store_true', help='保留动漫类型数据')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING('警告: 此操作将删除所有动漫数据!'))
            self.stdout.write(self.style.WARNING('使用 --confirm 参数确认删除'))
            return

        # 量子交易锁 - 确保关联数据完整性
        with transaction.atomic():
            # 先删除依赖记录
            from recommendation.models import UserRating, UserComment, UserFavorite, RecommendationCache
            from users.models import UserBrowsing, UserPreference

            self.stdout.write('开始清理关联数据...')
            UserPreference.objects.all().delete()
            self.stdout.write('✓ 用户偏好数据已清除')

            UserBrowsing.objects.all().delete()
            self.stdout.write('✓ 浏览记录已清除')

            RecommendationCache.objects.all().delete()
            self.stdout.write('✓ 推荐缓存已清除')

            UserFavorite.objects.all().delete()
            self.stdout.write('✓ 收藏记录已清除')

            UserComment.objects.all().delete()
            self.stdout.write('✓ 评论数据已清除')

            UserRating.objects.all().delete()
            self.stdout.write('✓ 评分数据已清除')

            # 删除核心动漫数据
            anime_count = Anime.objects.count()
            Anime.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'✓ 成功删除 {anime_count} 部动漫数据'))

            # 根据参数决定是否保留类型数据
            if not options['keep_types']:
                type_count = AnimeType.objects.count()
                AnimeType.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'✓ 成功删除 {type_count} 个动漫类型'))
            else:
                self.stdout.write(self.style.SUCCESS('√ 已保留动漫类型数据'))

        self.stdout.write(self.style.SUCCESS('数据清理完成！系统已回到初始态'))