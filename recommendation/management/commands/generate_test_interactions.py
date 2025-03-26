# recommendation/management/commands/generate_test_interactions.py
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from anime.models import Anime
from recommendation.models import (
    UserRating, UserComment, UserLike, UserFavorite, BrowsingHistory
)


class Command(BaseCommand):
    help = "生成用户交互测试数据"

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=5, help='要生成数据的用户数量')
        parser.add_argument('--ratings', type=int, default=50, help='要生成的评分数量')
        parser.add_argument('--comments', type=int, default=30, help='要生成的评论数量')
        parser.add_argument('--likes', type=int, default=60, help='要生成的点赞数量')
        parser.add_argument('--favorites', type=int, default=40, help='要生成的收藏数量')
        parser.add_argument('--browsing', type=int, default=80, help='要生成的浏览记录数量')

    def handle(self, *args, **options):
        # 检查所需数据是否存在
        users_count = User.objects.count()
        anime_count = Anime.objects.count()

        if users_count < 2 or anime_count < 5:
            self.stdout.write(self.style.ERROR('数据库中需要至少2个用户和5个动漫才能生成测试数据'))
            return

        # 获取参数
        users_limit = options['users']
        ratings_count = options['ratings']
        comments_count = options['comments']
        likes_count = options['likes']
        favorites_count = options['favorites']
        browsing_count = options['browsing']

        # 获取数据模型
        users = list(User.objects.all()[:users_limit])
        animes = list(Anime.objects.all())

        self.stdout.write(self.style.SUCCESS(f'开始生成测试数据'))

        # 生成评分数据
        existing_ratings = set(UserRating.objects.values_list('user_id', 'anime_id'))
        ratings_created = 0

        while ratings_created < ratings_count:
            user = random.choice(users)
            anime = random.choice(animes)

            if (user.id, anime.id) not in existing_ratings:
                rating = round(random.uniform(1.0, 5.0), 1)
                UserRating.objects.create(user=user, anime=anime, rating=rating)
                existing_ratings.add((user.id, anime.id))
                ratings_created += 1

        self.stdout.write(self.style.SUCCESS(f'已生成 {ratings_created} 条评分数据'))

        # 生成评论数据
        comments_created = 0
        for _ in range(comments_count):
            user = random.choice(users)
            anime = random.choice(animes)

            # 生成随机评论内容
            comments = [
                f"这部动漫真的很棒，特别喜欢{anime.title}的剧情设计！",
                f"个人觉得{anime.title}的角色塑造非常成功，给五星好评。",
                f"画风精美，音乐出色，情节紧凑，{anime.title}值得推荐！",
                f"看完{anime.title}后久久不能平静，真是神作。",
                f"虽然{anime.title}有些地方不太完美，但整体还是很不错的。",
                f"追完{anime.title}感觉有点空虚，希望能有第二季。",
                f"{anime.title}剧情节奏有点慢，但是角色魅力十足。",
                f"冲着声优阵容来看的{anime.title}，没有让我失望。"
            ]

            content = random.choice(comments)
            # 随机添加一些额外内容使评论更加多样化
            if random.random() > 0.7:
                extras = [
                    "强烈推荐给所有动漫爱好者！",
                    "期待作者的下一部作品。",
                    "不知道为什么很多人不喜欢，我个人觉得很赞。",
                    "配乐简直神了，单曲循环中...",
                    "男/女主角太可爱了，已经入坑。"
                ]
                content += " " + random.choice(extras)

            comment = UserComment.objects.create(
                user=user,
                anime=anime,
                content=content,
                timestamp=timezone.now() - timedelta(days=random.randint(0, 30))
            )
            comments_created += 1

        self.stdout.write(self.style.SUCCESS(f'已生成 {comments_created} 条评论数据'))

        # 生成点赞数据
        if comments_created > 0:
            existing_likes = set(UserLike.objects.values_list('user_id', 'comment_id'))
            likes_created = 0
            comments = list(UserComment.objects.all())

            while likes_created < likes_count and comments:
                user = random.choice(users)
                comment = random.choice(comments)

                if (user.id, comment.id) not in existing_likes:
                    UserLike.objects.create(user=user, comment=comment)
                    existing_likes.add((user.id, comment.id))
                    likes_created += 1

            self.stdout.write(self.style.SUCCESS(f'已生成 {likes_created} 条点赞数据'))

        # 生成收藏数据
        existing_favorites = set(UserFavorite.objects.values_list('user_id', 'anime_id'))
        favorites_created = 0

        while favorites_created < favorites_count:
            user = random.choice(users)
            anime = random.choice(animes)

            if (user.id, anime.id) not in existing_favorites:
                UserFavorite.objects.create(user=user, anime=anime)
                existing_favorites.add((user.id, anime.id))
                favorites_created += 1

        self.stdout.write(self.style.SUCCESS(f'已生成 {favorites_created} 条收藏数据'))

        # 生成浏览历史
        existing_browsing = set(BrowsingHistory.objects.values_list('user_id', 'anime_id'))
        browsing_created = 0

        while browsing_created < browsing_count:
            user = random.choice(users)
            anime = random.choice(animes)

            browse_count = random.randint(1, 10)
            last_time = timezone.now() - timedelta(days=random.randint(0, 14))

            if (user.id, anime.id) in existing_browsing:
                # 更新已有记录
                history = BrowsingHistory.objects.get(user=user, anime=anime)
                history.browse_count += browse_count
                history.last_browse_time = last_time
                history.save()
            else:
                # 创建新记录
                BrowsingHistory.objects.create(
                    user=user,
                    anime=anime,
                    browse_count=browse_count,
                    last_browse_time=last_time
                )
                existing_browsing.add((user.id, anime.id))
                browsing_created += 1

        self.stdout.write(self.style.SUCCESS(f'已生成 {browsing_created} 条浏览历史数据'))

        # 更新动漫浏览计数
        for anime in animes:
            browse_count = BrowsingHistory.objects.filter(anime=anime).count()
            if browse_count > 0:
                anime.view_count = browse_count * random.randint(5, 20)  # 模拟实际访问量会更大
                anime.save(update_fields=['view_count'])

        self.stdout.write(self.style.SUCCESS('测试数据生成完成！'))