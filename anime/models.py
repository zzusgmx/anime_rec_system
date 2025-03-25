from django.db import models
from django.utils.text import slugify
import uuid


class TimeStampedModel(models.Model):
    """
    抽象基类：提供创建时间和更新时间追踪
    允许所有子模型继承时间戳功能但不创建实际表
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AnimeType(TimeStampedModel):
    """
    动漫类型模型
    例如：少年、少女、热血、悬疑等类型
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="类型名称")
    description = models.TextField(null=True, blank=True, verbose_name="类型描述")
    slug = models.SlugField(max_length=60, unique=True, blank=True, verbose_name="URL别名")

    class Meta:
        verbose_name = "动漫类型"
        verbose_name_plural = "动漫类型列表"
        ordering = ['name']  # 默认按名称排序

    def save(self, *args, **kwargs):
        # 自动生成slug用于URL友好化
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Anime(TimeStampedModel):
    """
    动漫核心模型：存储动漫的基本信息
    """
    # 基础信息
    title = models.CharField(max_length=100, verbose_name="标题")
    original_title = models.CharField(max_length=100, null=True, blank=True, verbose_name="原始标题")
    slug = models.SlugField(max_length=120, unique=True, blank=True, verbose_name="URL别名")
    # 使用UUID作为备用ID，避免ID暴露和顺序推测
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # 内容信息
    description = models.TextField(verbose_name="描述")
    cover = models.ImageField(upload_to='anime_covers/%Y/%m/', verbose_name="封面图")
    release_date = models.DateField(verbose_name="发布日期")
    episodes = models.PositiveSmallIntegerField(default=1, verbose_name="集数")
    duration = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="每集时长(分钟)")

    # 关联信息
    type = models.ForeignKey(
        AnimeType,
        on_delete=models.CASCADE,
        related_name='animes',
        verbose_name="类型"
    )

    # 统计数据字段 - 经常查询和排序的字段应该有索引
    popularity = models.FloatField(default=0, db_index=True, verbose_name="热门指数")
    rating_avg = models.FloatField(default=0, db_index=True, verbose_name="平均评分")
    rating_count = models.PositiveIntegerField(default=0, verbose_name="评分数量")
    view_count = models.PositiveIntegerField(default=0, verbose_name="浏览次数")
    favorite_count = models.PositiveIntegerField(default=0, verbose_name="收藏次数")

    # 内容标识
    is_featured = models.BooleanField(default=False, verbose_name="是否推荐")
    is_completed = models.BooleanField(default=True, verbose_name="是否完结")

    class Meta:
        verbose_name = "动漫"
        verbose_name_plural = "动漫列表"
        # 复合索引：同时使用类型和热门度排序的查询
        indexes = [
            models.Index(fields=['type', '-popularity'], name='anime_type_pop_idx'),
            models.Index(fields=['type', '-rating_avg'], name='anime_type_rating_idx'),
            models.Index(fields=['-release_date'], name='anime_release_idx'),
        ]
        ordering = ['-popularity', '-release_date']

    def save(self, *args, **kwargs):
        # 自动生成URL友好的slug
        if not self.slug:
            self.slug = slugify(f"{self.title}-{str(self.uuid)[:8]}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def update_popularity(self):
        """
        计算动漫热门指数
        热门指数 = 平均评分*0.4 + 标准化评分数*0.3 + 标准化浏览数*0.2 + 标准化收藏数*0.1
        """
        # 这里仅占位，实际计算将在信号或后台任务中完成
        # 避免高频更新导致的性能问题
        pass


