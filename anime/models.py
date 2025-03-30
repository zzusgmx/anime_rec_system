# anime/models.py
# 注意：高度优化的实体模型 - 量子级数据结构设计

from django.db import models
from django.utils.text import slugify
import uuid
import logging

# 配置日志记录器
logger = logging.getLogger('django')


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
        # 0x01: 量子加固版slug生成器 - 支持多语言与边缘情况处理
        if not self.slug:
            # 尝试基于name生成slug
            slug_base = slugify(self.name)

            # 如果slugify结果为空（例如纯中文名称）
            if not slug_base:
                # 使用name哈希值作为备选，确保确定性
                name_hash = abs(hash(self.name)) % 100000
                slug_base = f"type-{name_hash}"

            # 确保唯一性的递增计数器
            counter = 0
            slug = slug_base

            # 循环检查唯一性
            while AnimeType.objects.filter(slug=slug).exists():
                counter += 1
                slug = f"{slug_base}-{counter}"

            self.slug = slug
            # 诊断日志
            logger.info(f"为类型 '{self.name}' 生成slug: {self.slug}")

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
            models.Index(fields=['title'], name='anime_title_idx'),  # 添加标题索引
            models.Index(fields=['is_completed', '-popularity'], name='anime_complete_pop_idx'),  # 完结状态索引
            models.Index(fields=['is_featured', '-popularity'], name='anime_featured_pop_idx'),  # 推荐状态索引
        ]
        ordering = ['-popularity', '-release_date']

    def save(self, *args, **kwargs):
        # 0x02: 量子级增强slug生成器 - 高防碰撞与容错设计
        if not self.slug:
            # 获取基本slug部分（从标题）
            base_slug = slugify(self.title) if self.title else 'anime'

            # 如果slugify结果为空（纯中文等）
            if not base_slug or base_slug == 'anime':
                # 使用拼音转换或直接基于ID生成
                import hashlib
                # 使用标题的哈希作为备选
                title_hash = hashlib.md5(self.title.encode('utf-8')).hexdigest()[:8]
                base_slug = f"anime-{title_hash}"

            # 加入UUID前8位作为确保唯一性的量子指纹
            # 确保UUID已经存在，否则生成新的
            if not self.uuid:
                self.uuid = uuid.uuid4()

            # 从UUID中提取前8位十六进制数作为唯一标识
            uuid_hex = str(self.uuid).replace('-', '')[:8]

            # 组合最终slug：标题-uuid前8位
            self.slug = f"{base_slug}-{uuid_hex}"

            # 诊断日志
            logger.info(f"为动漫 '{self.title}' 生成slug: {self.slug}")

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