from django.db import models
from django.contrib.auth.models import User
from anime.models import TimeStampedModel, Anime


class UserRating(TimeStampedModel):
    """
    用户评分：记录用户对动漫的评分数据
    这是推荐系统的核心数据源之一
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name="用户"
    )
    anime = models.ForeignKey(
        Anime,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name="动漫"
    )
    # 评分范围1-5，支持小数点精度
    rating = models.FloatField(verbose_name="评分")
    # 评分操作时间戳
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "用户评分"
        verbose_name_plural = "用户评分列表"
        # 确保用户对每个动漫只有一条有效评分
        unique_together = ['user', 'anime']
        # 索引优化查询模式
        indexes = [
            models.Index(fields=['user', '-timestamp'], name='user_rating_time_idx'),
            models.Index(fields=['anime', '-rating'], name='anime_rating_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} 给 {self.anime.title} 评分 {self.rating}"


class UserComment(TimeStampedModel):
    """
    用户评论：记录用户对动漫的文字评价
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="用户"
    )
    anime = models.ForeignKey(
        Anime,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="动漫"
    )
    content = models.TextField(verbose_name="评论内容")
    # 评论时间戳
    timestamp = models.DateTimeField(auto_now_add=True)

    # 点赞计数器字段，避免每次查询都要计算关联表
    like_count = models.PositiveIntegerField(default=0, verbose_name="点赞数")

    class Meta:
        verbose_name = "用户评论"
        verbose_name_plural = "用户评论列表"
        indexes = [
            models.Index(fields=['anime', '-timestamp'], name='anime_comment_time_idx'),
            models.Index(fields=['user', '-timestamp'], name='user_comment_time_idx'),
        ]
        ordering = ['-timestamp']  # 默认按时间降序排列

    def __str__(self):
        # 显示评论内容的前20个字符
        preview = self.content[:20] + "..." if len(self.content) > 20 else self.content
        return f"{self.user.username}: {preview}"


class UserLike(TimeStampedModel):
    """
    用户点赞：记录用户对评论的点赞
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name="用户"
    )
    comment = models.ForeignKey(
        UserComment,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name="评论"
    )
    # 点赞时间
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "用户点赞"
        verbose_name_plural = "用户点赞列表"
        # 确保用户对一条评论只能点赞一次
        unique_together = ['user', 'comment']
        indexes = [
            models.Index(fields=['comment', '-timestamp'], name='comment_like_time_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} 点赞了 {self.comment.user.username} 的评论"


class UserFavorite(TimeStampedModel):
    """
    用户收藏：记录用户收藏的动漫
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name="用户"
    )
    anime = models.ForeignKey(
        Anime,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name="动漫"
    )
    # 收藏时间
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "用户收藏"
        verbose_name_plural = "用户收藏列表"
        # 确保用户对一个动漫只有一条收藏记录
        unique_together = ['user', 'anime']
        indexes = [
            models.Index(fields=['user', '-timestamp'], name='user_favorite_time_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} 收藏了 {self.anime.title}"


# 推荐结果缓存表 - 性能优化
class RecommendationCache(TimeStampedModel):
    """
    推荐结果缓存：存储预计算的推荐结果
    避免实时计算的性能开销
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cached_recommendations',
        verbose_name="用户"
    )
    anime = models.ForeignKey(
        Anime,
        on_delete=models.CASCADE,
        related_name='recommended_to',
        verbose_name="推荐动漫"
    )
    # 推荐分数：衡量推荐的强度
    score = models.FloatField(verbose_name="推荐分数")
    # 推荐类型：CF(协同过滤)、CB(基于内容)、POP(热门推荐)
    rec_type = models.CharField(
        max_length=3,
        choices=[('CF', '协同过滤'), ('CB', '基于内容'), ('POP', '热门推荐')],
        verbose_name="推荐类型"
    )
    # 过期时间：定期刷新推荐结果
    expires_at = models.DateTimeField(verbose_name="过期时间")

    class Meta:
        verbose_name = "推荐缓存"
        verbose_name_plural = "推荐缓存列表"
        # 索引优化查询
        indexes = [
            models.Index(fields=['user', '-score'], name='user_rec_score_idx'),
            models.Index(fields=['expires_at'], name='rec_expiry_idx'),
        ]
        ordering = ['-score']  # 默认按推荐分数排序

    def __str__(self):
        return f"{self.user.username} - {self.anime.title} ({self.rec_type})"
