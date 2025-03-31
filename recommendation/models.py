from django.db import models
from django.contrib.auth.models import User
from anime.models import TimeStampedModel, Anime
from django.utils import timezone

# recommendation/models.py 中添加或修改以下代码
# 修改 recommendation/models.py 中的AnimeLike模型
class AnimeLike(models.Model):
    """
    动漫点赞模型：记录用户对动漫的点赞
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anime_likes')
    anime = models.ForeignKey('anime.Anime', on_delete=models.CASCADE, related_name='anime_likes')
    timestamp = models.DateTimeField(auto_now_add=True)

    # 添加这两个字段并设置默认值，解决迁移问题
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "动漫点赞"
        verbose_name_plural = "动漫点赞列表"
        unique_together = ['user', 'anime']  # 确保用户对每个动漫只有一条点赞记录
        indexes = [
            models.Index(fields=['user', '-timestamp'], name='user_anime_like_idx'),
            models.Index(fields=['anime'], name='anime_likes_idx'),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} 点赞 {self.anime.title}"

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

    class EncodingFixMixin:
        """编码修复混入类 - 在保存前修复编码问题"""

        def save(self, *args, **kwargs):
            """重写保存方法，在保存前修复编码"""
            # 执行字符字段的编码修复
            for field in self._meta.fields:
                if isinstance(field, models.CharField) or isinstance(field, models.TextField):
                    value = getattr(self, field.name)
                    if value and isinstance(value, str):
                        # 应用编码修复
                        fixed_value = self._fix_encoding(value)
                        setattr(self, field.name, fixed_value)

            # 调用原始保存方法
            super().save(*args, **kwargs)

        def _fix_encoding(self, text):
            """编码修复函数"""
            if not text:
                return text

            # 尝试修复双重编码问题
            try:
                # 将字符串反向编码为latin1字节数组
                temp_bytes = text.encode('latin1')
                # 尝试作为UTF-8解析
                return temp_bytes.decode('utf-8', errors='replace')
            except:
                return text

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
    # 添加回复计数
    reply_count = models.PositiveIntegerField(default=0, verbose_name="回复数")
    # 识别评论类型：原始评论或回复
    is_reply = models.BooleanField(default=False, verbose_name="是否为回复")

    # 新增：关联到父评论（如果这是一个回复）
    parent_comment = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name="父评论"
    )

    class Meta:
        verbose_name = "用户评论"
        verbose_name_plural = "用户评论列表"
        indexes = [
            models.Index(fields=['anime', '-timestamp'], name='anime_comment_time_idx'),
            models.Index(fields=['user', '-timestamp'], name='user_comment_time_idx'),
            models.Index(fields=['parent_comment', '-timestamp'], name='reply_time_idx'),
        ]
        ordering = ['-timestamp']  # 默认按时间降序排列

    def __str__(self):
        # 显示评论内容的前20个字符
        preview = self.content[:20] + "..." if len(self.content) > 20 else self.content
        if self.is_reply and self.parent_comment:
            return f"{self.user.username} 回复了 {self.parent_comment.user.username}: {preview}"
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
            models.Index(fields=['user', '-timestamp'], name='user_like_time_idx'),
        ]

    def __str__(self):
        if self.comment.is_reply:
            return f"{self.user.username} 点赞了 {self.comment.user.username} 对 {self.comment.parent_comment.user.username} 的回复"
        return f"{self.user.username} 点赞了 {self.comment.user.username} 的评论"


class UserInteraction(TimeStampedModel):
    """
    用户互动：记录用户之间的互动数据
    用于分析和可视化用户社交网络
    """
    # 互动发起者
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='interactions_initiated',
        verbose_name="互动发起者"
    )
    # 互动接收者
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='interactions_received',
        verbose_name="互动接收者"
    )
    # 互动类型
    INTERACTION_TYPES = [
        ('reply', '评论回复'),
        ('like', '点赞评论'),
        ('mention', '提及用户'),
    ]
    interaction_type = models.CharField(
        max_length=10,
        choices=INTERACTION_TYPES,
        verbose_name="互动类型"
    )
    # 关联的评论（如果有）
    comment = models.ForeignKey(
        UserComment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='interactions',
        verbose_name="相关评论"
    )
    # 关联的点赞（如果有）
    like = models.ForeignKey(
        UserLike,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='interactions',
        verbose_name="相关点赞"
    )
    # 互动时间
    timestamp = models.DateTimeField(auto_now_add=True)
    # 是否已读
    is_read = models.BooleanField(default=False, verbose_name="是否已读")
    # 互动强度（用于分析）
    strength = models.FloatField(default=1.0, verbose_name="互动强度")

    class Meta:
        verbose_name = "用户互动"
        verbose_name_plural = "用户互动列表"
        indexes = [
            models.Index(fields=['from_user', '-timestamp'], name='from_user_time_idx'),
            models.Index(fields=['to_user', '-timestamp'], name='to_user_time_idx'),
            models.Index(fields=['to_user', 'is_read'], name='user_unread_idx'),
            models.Index(fields=['interaction_type'], name='interaction_type_idx'),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        action = {
            'reply': '回复了',
            'like': '点赞了',
            'mention': '提及了'
        }.get(self.interaction_type, '互动了')

        return f"{self.from_user.username} {action} {self.to_user.username}"
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

    expires_at = models.DateTimeField(verbose_name="过期时间")
