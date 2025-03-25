from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count
from .models import UserRating, UserComment, UserLike, UserFavorite
from users.models import UserPreference, Profile
from anime.models import Anime


# =============== 评分信号处理 ===============

@receiver(post_save, sender=UserRating)
def update_anime_rating_stats(sender, instance, created, **kwargs):
    """
    当用户提交新评分或更新评分时：
    1. 更新动漫的平均评分和评分计数
    2. 更新用户档案的评分计数
    3. 更新或创建用户对该动漫的偏好记录
    """
    # 计算动漫的新平均评分和评分数量
    anime = instance.anime
    rating_stats = UserRating.objects.filter(anime=anime).aggregate(
        avg=Avg('rating'),
        count=Count('id')
    )

    # 更新动漫评分统计
    anime.rating_avg = rating_stats['avg'] or 0
    anime.rating_count = rating_stats['count'] or 0
    anime.save(update_fields=['rating_avg', 'rating_count'])

    # 更新用户评分计数
    user_profile = instance.user.profile
    rating_count = UserRating.objects.filter(user=instance.user).count()
    user_profile.rating_count = rating_count
    user_profile.save(update_fields=['rating_count'])

    # 更新用户偏好
    update_user_preference(instance.user, anime)


@receiver(post_delete, sender=UserRating)
def handle_rating_deletion(sender, instance, **kwargs):
    """处理评分删除事件"""
    # 重新计算动漫平均评分
    anime = instance.anime
    rating_stats = UserRating.objects.filter(anime=anime).aggregate(
        avg=Avg('rating'),
        count=Count('id')
    )

    anime.rating_avg = rating_stats['avg'] or 0
    anime.rating_count = rating_stats['count'] or 0
    anime.save(update_fields=['rating_avg', 'rating_count'])

    # 更新用户评分计数
    user_profile = instance.user.profile
    rating_count = UserRating.objects.filter(user=instance.user).count()
    user_profile.rating_count = rating_count
    user_profile.save(update_fields=['rating_count'])

    # 更新用户偏好
    update_user_preference(instance.user, anime)


# =============== 评论信号处理 ===============

@receiver(post_save, sender=UserComment)
def handle_comment_creation(sender, instance, created, **kwargs):
    """处理新评论创建事件"""
    if created:
        # 更新用户评论计数
        user_profile = instance.user.profile
        comment_count = UserComment.objects.filter(user=instance.user).count()
        user_profile.comment_count = comment_count
        user_profile.save(update_fields=['comment_count'])

        # 更新用户偏好
        update_user_preference(instance.user, instance.anime)


@receiver(post_delete, sender=UserComment)
def handle_comment_deletion(sender, instance, **kwargs):
    """处理评论删除事件"""
    # 更新用户评论计数
    user_profile = instance.user.profile
    comment_count = UserComment.objects.filter(user=instance.user).count()
    user_profile.comment_count = comment_count
    user_profile.save(update_fields=['comment_count'])

    # 更新用户偏好
    update_user_preference(instance.user, instance.anime)


# =============== 点赞信号处理 ===============

@receiver(post_save, sender=UserLike)
def handle_like_creation(sender, instance, created, **kwargs):
    """处理点赞创建事件"""
    if created:
        # 更新评论的点赞计数
        comment = instance.comment
        like_count = UserLike.objects.filter(comment=comment).count()
        comment.like_count = like_count
        comment.save(update_fields=['like_count'])

        # 更新用户偏好 (对评论所属动漫的偏好)
        update_user_preference(instance.user, comment.anime)


@receiver(post_delete, sender=UserLike)
def handle_like_deletion(sender, instance, **kwargs):
    """处理点赞删除事件"""
    # 更新评论的点赞计数
    comment = instance.comment
    like_count = UserLike.objects.filter(comment=comment).count()
    comment.like_count = like_count
    comment.save(update_fields=['like_count'])

    # 更新用户偏好
    update_user_preference(instance.user, comment.anime)


# =============== 收藏信号处理 ===============

@receiver(post_save, sender=UserFavorite)
def handle_favorite_creation(sender, instance, created, **kwargs):
    """处理收藏创建事件"""
    if created:
        # 更新动漫收藏计数
        anime = instance.anime
        favorite_count = UserFavorite.objects.filter(anime=anime).count()
        anime.favorite_count = favorite_count
        anime.save(update_fields=['favorite_count'])

        # 更新用户偏好
        update_user_preference(instance.user, anime)


@receiver(post_delete, sender=UserFavorite)
def handle_favorite_deletion(sender, instance, **kwargs):
    """处理收藏删除事件"""
    # 更新动漫收藏计数
    anime = instance.anime
    favorite_count = UserFavorite.objects.filter(anime=anime).count()
    anime.favorite_count = favorite_count
    anime.save(update_fields=['favorite_count'])

    # 更新用户偏好
    update_user_preference(instance.user, anime)


# =============== 辅助函数 ===============

def update_user_preference(user, anime):
    """
    计算并更新用户对特定动漫的偏好值
    综合考虑评分、评论、收藏、点赞等行为
    """
    # 获取用户对该动漫的各种交互数据
    try:
        rating = UserRating.objects.get(user=user, anime=anime).rating
        rating_weight = rating / 5 * 50  # 评分权重50%
    except UserRating.DoesNotExist:
        rating_weight = 0

    # 评论权重10%
    comment_count = UserComment.objects.filter(user=user, anime=anime).count()
    comment_weight = min(10, comment_count * 5)  # 最多10%

    # 收藏权重20%
    has_favorite = UserFavorite.objects.filter(user=user, anime=anime).exists()
    favorite_weight = 20 if has_favorite else 0

    # 浏览权重10%（需要从users应用导入）
    from users.models import UserBrowsing
    try:
        browsing = UserBrowsing.objects.get(user=user, anime=anime)
        browse_count = browsing.browse_count
        browse_weight = min(10, browse_count)  # 最多10%
    except UserBrowsing.DoesNotExist:
        browse_weight = 0

    # 点赞权重10% - 需要计算用户对该动漫相关评论的点赞数
    anime_comments = UserComment.objects.filter(anime=anime)
    like_count = UserLike.objects.filter(user=user, comment__in=anime_comments).count()
    like_weight = min(10, like_count * 2)  # 最多10%

    # 计算总偏好值 (0-100)
    preference_value = rating_weight + comment_weight + favorite_weight + browse_weight + like_weight

    # 更新或创建偏好记录
    UserPreference.objects.update_or_create(
        user=user,
        anime=anime,
        defaults={'preference_value': preference_value}
    )

    # 计算并更新动漫整体热门度
    update_anime_popularity(anime)


def update_anime_popularity(anime):
    """
    更新动漫热门度指数
    热门度 = 平均评分*0.4 + 标准化评分数*0.3 + 标准化浏览数*0.2 + 标准化收藏数*0.1
    """
    # 获取基础指标
    rating_avg = anime.rating_avg or 0
    rating_count = anime.rating_count or 0
    view_count = anime.view_count or 0
    favorite_count = anime.favorite_count or 0

    # 获取系统平均值作为归一化基准 (简化版，实际可能需要更复杂的计算)
    from django.db.models import Avg, Max
    metrics = Anime.objects.aggregate(
        avg_rating_count=Avg('rating_count'),
        max_rating_count=Max('rating_count'),
        avg_view_count=Avg('view_count'),
        max_view_count=Max('view_count'),
        avg_favorite_count=Avg('favorite_count'),
        max_favorite_count=Max('favorite_count'),
    )

    # 防止除零错误
    max_rating_count = max(1, metrics['max_rating_count'] or 1)
    max_view_count = max(1, metrics['max_view_count'] or 1)
    max_favorite_count = max(1, metrics['max_favorite_count'] or 1)

    # 归一化各指标 (0-1)
    norm_rating_count = rating_count / max_rating_count
    norm_view_count = view_count / max_view_count
    norm_favorite_count = favorite_count / max_favorite_count

    # 归一化评分 (0-1)
    norm_rating_avg = rating_avg / 5

    # 计算热门度 (0-1)
    popularity = (
            norm_rating_avg * 0.4 +
            norm_rating_count * 0.3 +
            norm_view_count * 0.2 +
            norm_favorite_count * 0.1
    )

    # 更新热门度
    anime.popularity = popularity
    anime.save(update_fields=['popularity'])