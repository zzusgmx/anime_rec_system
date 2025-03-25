from django.db import models
<<<<<<< HEAD
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from anime.models import TimeStampedModel, Anime


class Profile(TimeStampedModel):
    """
    扩展Django默认用户模型
    与内置User模型保持一对一关系，存储额外的用户信息
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', null=True, blank=True, verbose_name="头像")
    bio = models.TextField(max_length=500, blank=True, verbose_name="个人简介")
    birth_date = models.DateField(null=True, blank=True, verbose_name="出生日期")
    gender = models.CharField(
        max_length=10,
        choices=[('male', '男'), ('female', '女'), ('other', '其他')],
        blank=True,
        verbose_name="性别"
    )

    # 用户偏好设置
    preferred_types = models.ManyToManyField(
        'anime.AnimeType',
        blank=True,
        related_name='preferred_by_users',
        verbose_name="喜好类型"
    )

    # 统计数据
    rating_count = models.PositiveIntegerField(default=0, verbose_name="评分次数")
    comment_count = models.PositiveIntegerField(default=0, verbose_name="评论次数")

    class Meta:
        verbose_name = "用户档案"
        verbose_name_plural = "用户档案列表"

    def __str__(self):
        return f"{self.user.username}的档案"


# 使用信号自动创建用户档案
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """当创建新用户时自动创建对应档案"""
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """当保存用户时自动保存对应档案"""
    instance.profile.save()


class UserBrowsing(TimeStampedModel):
    """
    用户浏览记录：追踪用户浏览动漫的历史
    用于分析用户兴趣和生成推荐
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='browsing_history')
    anime = models.ForeignKey('anime.Anime', on_delete=models.CASCADE, related_name='browsed_by')
    # 记录用户最近访问时间，用于时间衰减算法
    last_browsed = models.DateTimeField(auto_now=True)
    # 记录总浏览次数以衡量兴趣程度
    browse_count = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "浏览记录"
        verbose_name_plural = "浏览记录列表"
        unique_together = ['user', 'anime']  # 确保用户对每个动漫只有一条记录
        indexes = [
            models.Index(fields=['user', '-last_browsed'], name='user_browse_time_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.anime.title}"


class UserPreference(TimeStampedModel):
    """
    用户偏好：计算用户对特定动漫的综合兴趣度
    基于多种交互（评分、浏览、收藏等）的加权计算
    用于协同过滤推荐算法的核心输入
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='preferences')
    anime = models.ForeignKey('anime.Anime', on_delete=models.CASCADE, related_name='user_preferences')
    # 偏好值范围0-100，代表用户兴趣程度的百分比
    preference_value = models.FloatField(default=0, verbose_name="偏好值")
    # 最后计算时间
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "用户偏好"
        verbose_name_plural = "用户偏好列表"
        unique_together = ['user', 'anime']  # 每个用户对每个动漫只有一个偏好值
        indexes = [
            models.Index(fields=['user', '-preference_value'], name='user_pref_value_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.anime.title}: {self.preference_value:.2f}"

    def calculate_preference(self):
        """
        计算用户偏好值
        公式: rating*0.5 + comment*0.1 + favorite*0.2 + view*0.1 + like*0.1
        """
        # 占位方法，实际实现将在信号或管理命令中完成
        pass
=======

# Create your models here.
>>>>>>> d1322bd2ac3da5307a056d58f203a84a82102da1
