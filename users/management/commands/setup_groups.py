from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from anime.models import Anime, AnimeType
from recommendation.models import UserRating, UserComment, UserFavorite, UserLike
from users.models import Profile, UserBrowsing, UserPreference


class Command(BaseCommand):
    help = '创建预定义的用户组和权限'

    def handle(self, *args, **options):
        # 创建内容管理员组
        content_admin, created = Group.objects.get_or_create(name='ContentAdmins')
        if created:
            self.stdout.write(self.style.SUCCESS('成功创建内容管理员组'))
        else:
            self.stdout.write(self.style.WARNING('内容管理员组已存在'))

        # 创建内容编辑组
        content_editor, created = Group.objects.get_or_create(name='ContentEditors')
        if created:
            self.stdout.write(self.style.SUCCESS('成功创建内容编辑组'))
        else:
            self.stdout.write(self.style.WARNING('内容编辑组已存在'))

        # 创建内容审核员组
        moderator, created = Group.objects.get_or_create(name='Moderators')
        if created:
            self.stdout.write(self.style.SUCCESS('成功创建内容审核员组'))
        else:
            self.stdout.write(self.style.WARNING('内容审核员组已存在'))

        # 创建数据分析师组
        analyst, created = Group.objects.get_or_create(name='Analysts')
        if created:
            self.stdout.write(self.style.SUCCESS('成功创建数据分析师组'))
        else:
            self.stdout.write(self.style.WARNING('数据分析师组已存在'))

        # 获取内容类型
        anime_content_type = ContentType.objects.get_for_model(Anime)
        anime_type_content_type = ContentType.objects.get_for_model(AnimeType)
        rating_content_type = ContentType.objects.get_for_model(UserRating)
        comment_content_type = ContentType.objects.get_for_model(UserComment)
        favorite_content_type = ContentType.objects.get_for_model(UserFavorite)
        like_content_type = ContentType.objects.get_for_model(UserLike)
        profile_content_type = ContentType.objects.get_for_model(Profile)
        browsing_content_type = ContentType.objects.get_for_model(UserBrowsing)
        preference_content_type = ContentType.objects.get_for_model(UserPreference)

        # 内容管理员权限 - 可以管理所有内容
        content_admin_permissions = Permission.objects.filter(
            content_type__in=[
                anime_content_type,
                anime_type_content_type
            ]
        )
        content_admin.permissions.set(content_admin_permissions)
        self.stdout.write(self.style.SUCCESS(f'为内容管理员组分配了 {content_admin_permissions.count()} 个权限'))

        # 内容编辑权限 - 可以添加和编辑动漫，但不能删除
        content_editor_permissions = Permission.objects.filter(
            content_type__in=[anime_content_type, anime_type_content_type],
            codename__in=['add_anime', 'change_anime', 'view_anime',
                          'add_animetype', 'change_animetype', 'view_animetype']
        )
        content_editor.permissions.set(content_editor_permissions)
        self.stdout.write(self.style.SUCCESS(f'为内容编辑组分配了 {content_editor_permissions.count()} 个权限'))

        # 内容审核员权限 - 可以管理评论和评分
        moderator_permissions = Permission.objects.filter(
            content_type__in=[
                comment_content_type,
                rating_content_type,
                like_content_type
            ]
        )
        moderator.permissions.set(moderator_permissions)
        self.stdout.write(self.style.SUCCESS(f'为内容审核员组分配了 {moderator_permissions.count()} 个权限'))

        # 数据分析师权限 - 只能查看数据
        analyst_permissions = Permission.objects.filter(
            codename__startswith='view_'
        )
        analyst.permissions.set(analyst_permissions)
        self.stdout.write(self.style.SUCCESS(f'为数据分析师组分配了 {analyst_permissions.count()} 个权限'))

        self.stdout.write(self.style.SUCCESS('成功设置所有用户组和权限'))