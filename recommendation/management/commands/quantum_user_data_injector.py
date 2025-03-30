from django.core.management.base import BaseCommand
from django.db import transaction
import random
import os
import django
from faker import Faker
from django.contrib.auth.models import User
from anime.models import Anime, AnimeType
from recommendation.models import UserRating, UserFavorite, UserComment


class QuantumUserDataInjector:
    def __init__(self, total_interactions=500):
        self.faker = Faker('zh_CN')
        self.total_interactions = total_interactions
        self.anime_pool = list(Anime.objects.all())

    def generate_quantum_user(self):
        """
        量子用户生成器：创建高度个性化的用户档案
        """
        username = f"quantum_user_{self.faker.user_name()}_{random.randint(1000, 9999)}"
        email = f"{username}@quantumanime.tech"

        user = User.objects.create_user(
            username=username,
            email=email,
            password='QuantumAnime2025!'
        )

        # 完善用户 Profile
        profile = user.profile
        profile.bio = self.faker.sentence()
        profile.birth_date = self.faker.date_of_birth(minimum_age=15, maximum_age=35)
        profile.gender = random.choice(['male', 'female', 'other'])

        # 随机选择偏好类型
        preferred_types = AnimeType.objects.order_by('?')[:random.randint(1, 3)]
        profile.preferred_types.set(preferred_types)

        profile.save()

        return user

    def create_specified_user(self):
        """
        量子精确用户注入器 - 专门为指定用户创建
        """
        user, created = User.objects.get_or_create(
            username='zzuxcm',
            defaults={
                'email': 'zzuxcm@quantumanime.tech',
                'is_active': True
            }
        )

        if created:
            user.set_password('zzuxcm123456')
            user.save()

        # 完善用户 Profile
        profile = user.profile
        profile.bio = "量子动漫推荐系统的首席测试官，热爱技术与动漫的跨界极客 🚀"
        profile.birth_date = self.faker.date_of_birth(minimum_age=25, maximum_age=35)
        profile.gender = 'male'

        preferred_types = AnimeType.objects.filter(name__in=['Movie', 'ONA', 'TV'])
        profile.preferred_types.set(preferred_types)

        profile.save()

        # 为指定用户生成高度个性化的交互
        self.generate_interactions(user, is_specified_user=True)

        return user

    def generate_interactions(self, user, is_specified_user=False):
        """
        量子交互生成器
        """
        if is_specified_user:
            interacted_animes = Anime.objects.filter(
                type__name__in=['Movie', 'ONA', 'TV']
            ).order_by('-popularity')[:50]
        else:
            interacted_animes = random.sample(self.anime_pool, random.randint(20, 80))

        interactions = []

        for anime in interacted_animes:
            # 评分逻辑
            if is_specified_user:
                rating = max(3.5, min(5, round(random.gauss(4.5, 0.5), 1)))
            else:
                rating = max(1, min(5, round(random.gauss(3.5, 1), 1)))

            user_rating, _ = UserRating.objects.get_or_create(
                user=user,
                anime=anime,
                defaults={'rating': rating}
            )
            interactions.append(user_rating)

            # 收藏逻辑
            if is_specified_user or random.random() < 0.4:
                user_favorite, _ = UserFavorite.objects.get_or_create(
                    user=user,
                    anime=anime
                )
                interactions.append(user_favorite)

            # 评论逻辑
            if is_specified_user or random.random() < 0.3:
                comment_text = self.generate_intelligent_comment(
                    anime,
                    rating,
                    is_specified_user=is_specified_user
                )
                user_comment = UserComment.objects.create(
                    user=user,
                    anime=anime,
                    content=comment_text
                )
                interactions.append(user_comment)

        return interactions

    def generate_intelligent_comment(self, anime, rating, is_specified_user=False):
        """
        量子级智能评论生成器
        """
        tech_comment_templates = [
            "从架构和叙事角度看，{title}简直是{type}类型的技术奇点！🚀",
            "{title}不仅是部动漫，更像是一个复杂的技术系统，层次感极其丰富 💻",
            "用计算机科学的视角审视{title}，其世界观构建堪比分布式系统的优雅设计 🔬"
        ]

        if is_specified_user:
            comment = random.choice(tech_comment_templates).format(
                type=anime.type.name,
                title=anime.title
            )
        else:
            comment_templates = {
                'high_rating': [
                    "这部{type}真的太棒了！{title}完全超出了我的期待！",
                    "{title}简直是{type}的天花板，强烈推荐！",
                ],
                'mid_rating': [
                    "{title}还不错，{type}类型的作品总体表现中等。",
                    "一般般的{type}动漫，但有些亮点值得一看。",
                ],
                'low_rating': [
                    "{title}让我有点失望，{type}类型有更好的作品。",
                    "这部{type}略显平庸，没有太多惊喜。",
                ]
            }

            if rating >= 4:
                template_group = 'high_rating'
            elif rating >= 2.5:
                template_group = 'mid_rating'
            else:
                template_group = 'low_rating'

            comment = random.choice(comment_templates[template_group]).format(
                type=anime.type.name,
                title=anime.title
            )

        return comment

    def execute_quantum_injection(self):
        """
        量子数据注入执行器
        """
        with transaction.atomic():
            # 首先注入指定用户
            specified_user = self.create_specified_user()
            print(f"🎯 注入目标用户: {specified_user.username}")

            # 继续注入随机用户
            for _ in range(self.total_interactions):
                user = self.generate_quantum_user()
                self.generate_interactions(user)
                print(f"🚀 注入量子用户: {user.username}")


class Command(BaseCommand):
    help = '量子级用户数据注入器'

    def handle(self, *args, **kwargs):
        injector = QuantumUserDataInjector(total_interactions=300)
        injector.execute_quantum_injection()

        self.stdout.write(self.style.SUCCESS('🚀 量子用户数据注入完成'))