from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count
from .models import UserRating, UserComment, UserLike, UserFavorite, UserInteraction, AnimeLike
from users.models import UserPreference, Profile
from anime.models import Anime
# =============== 评分信号处理 ===============
@receiver(post_save, sender=UserRating)
def update_model_weights_on_rating(sender, instance, created, **kwargs):
    """
    当用户提交新评分时，更新模型权重
    """
    try:
        # 避免递归调用
        if getattr(instance, '_skip_weight_update', False):
            return

        # 获取推荐引擎
        from recommendation.engine.recommendation_engine import recommendation_engine

        # 更新模型权重
        recommendation_engine.update_model_weights_from_feedback(
            instance.user.id,
            instance.anime.id,
            instance.rating
        )

        logger.info(f"用户 {instance.user.id} 对动漫 {instance.anime.id} 的评分已用于更新模型权重")

    except Exception as e:
        logger.error(f"更新模型权重失败: {str(e)}")
@receiver(post_save, sender=UserComment)
def handle_comment_reply(sender, instance, created, **kwargs):
    """处理评论回复创建事件"""
    if created and instance.is_reply and instance.parent_comment:
        # 更新父评论的回复计数
        parent_comment = instance.parent_comment
        parent_comment.reply_count = UserComment.objects.filter(parent_comment=parent_comment).count()
        parent_comment.save(update_fields=['reply_count'])

        # 更新用户的回复计数
        user_profile = instance.user.profile
        user_profile.replies_count = UserComment.objects.filter(user=instance.user, is_reply=True).count()
        user_profile.save(update_fields=['replies_count'])

        # 更新用户社交活跃度
        user_profile.calculate_social_activity()
        user_profile.save(update_fields=['social_activity_score'])

        # 创建用户互动记录
        UserInteraction.objects.create(
            from_user=instance.user,
            to_user=parent_comment.user,
            interaction_type='reply',
            comment=instance,
            strength=1.2  # 回复互动强度较高
        )


@receiver(post_delete, sender=UserComment)
def handle_comment_reply_deletion(sender, instance, **kwargs):
    """处理评论回复删除事件"""
    if instance.is_reply and instance.parent_comment:
        # 更新父评论的回复计数
        parent_comment = instance.parent_comment
        parent_comment.reply_count = UserComment.objects.filter(parent_comment=parent_comment).count()
        parent_comment.save(update_fields=['reply_count'])

        # 更新用户的回复计数
        user_profile = instance.user.profile
        user_profile.replies_count = UserComment.objects.filter(user=instance.user, is_reply=True).count()
        user_profile.save(update_fields=['replies_count'])

        # 更新用户社交活跃度
        user_profile.calculate_social_activity()
        user_profile.save(update_fields=['social_activity_score'])

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
    if not getattr(instance, '_skip_profile_update', False):
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
# 添加到 recommendation/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import AnimeLike
@receiver(post_save, sender=AnimeLike)
def handle_anime_like_creation(sender, instance, created, **kwargs):
    """处理动漫点赞创建事件"""
    if created:
        # 更新动漫点赞计数
        anime = instance.anime
        like_count = AnimeLike.objects.filter(anime=anime).count()
        anime.like_count = like_count
        anime.save(update_fields=['like_count'])

        # 更新用户偏好 (对点赞动漫的偏好)
        update_user_preference(instance.user, anime)
@receiver(post_delete, sender=AnimeLike)
def handle_anime_like_deletion(sender, instance, **kwargs):
    """处理动漫点赞删除事件"""
    # 更新动漫点赞计数
    anime = instance.anime
    like_count = AnimeLike.objects.filter(anime=anime).count()
    anime.like_count = like_count
    anime.save(update_fields=['like_count'])

    # 更新用户偏好
    update_user_preference(instance.user, anime)


# 修改点赞信号处理
@receiver(post_save, sender=UserLike)
def handle_like_creation(sender, instance, created, **kwargs):
    """处理点赞创建事件"""
    if created:
        # 更新评论的点赞计数
        comment = instance.comment
        like_count = UserLike.objects.filter(comment=comment).count()
        comment.like_count = like_count
        comment.save(update_fields=['like_count'])

        # 更新点赞用户的统计
        liker_profile = instance.user.profile
        liker_profile.likes_given_count = UserLike.objects.filter(user=instance.user).count()
        liker_profile.save(update_fields=['likes_given_count'])

        # 更新被点赞用户的统计
        liked_user_profile = comment.user.profile
        liked_user_profile.likes_received_count = UserLike.objects.filter(comment__user=comment.user).count()
        liked_user_profile.save(update_fields=['likes_received_count'])

        # 更新两位用户的分数
        liker_profile.calculate_social_activity()
        liked_user_profile.calculate_influence()
        liker_profile.save(update_fields=['social_activity_score'])
        liked_user_profile.save(update_fields=['influence_score'])

        # 创建用户互动记录
        UserInteraction.objects.create(
            from_user=instance.user,
            to_user=comment.user,
            interaction_type='like',
            comment=comment,
            like=instance,
            strength=0.8  # 点赞互动强度适中
        )


@receiver(post_delete, sender=UserLike)
def handle_like_deletion(sender, instance, **kwargs):
    """处理点赞删除事件"""
    # 更新评论的点赞计数
    comment = instance.comment
    like_count = UserLike.objects.filter(comment=comment).count()
    comment.like_count = like_count
    comment.save(update_fields=['like_count'])

    # 更新点赞用户的统计
    liker_profile = instance.user.profile
    liker_profile.likes_given_count = UserLike.objects.filter(user=instance.user).count()
    liker_profile.save(update_fields=['likes_given_count'])

    # 更新被点赞用户的统计
    liked_user_profile = comment.user.profile
    liked_user_profile.likes_received_count = UserLike.objects.filter(comment__user=comment.user).count()
    liked_user_profile.save(update_fields=['likes_received_count'])

    # 更新两位用户的分数
    liker_profile.calculate_social_activity()
    liked_user_profile.calculate_influence()
    liker_profile.save(update_fields=['social_activity_score'])
    liked_user_profile.save(update_fields=['influence_score'])
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

    # 浏览权重10%
    try:
        from users.models import UserBrowsing
        browsing = UserBrowsing.objects.get(user=user, anime=anime)
        browse_count = browsing.browse_count
        browse_weight = min(10, browse_count)  # 最多10%
    except:
        browse_weight = 0

    # 动漫点赞权重10%
    has_anime_like = AnimeLike.objects.filter(user=user, anime=anime).exists()
    anime_like_weight = 10 if has_anime_like else 0

    # 评论点赞权重5%
    anime_comments = UserComment.objects.filter(anime=anime)
    like_count = UserLike.objects.filter(user=user, comment__in=anime_comments).count()
    like_weight = min(5, like_count * 1)  # 最多5%

    # 计算总偏好值 (0-100)
    preference_value = rating_weight + comment_weight + favorite_weight + browse_weight + anime_like_weight + like_weight

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