from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.utils.timesince import timesince

register = template.Library()


@register.filter
def percentage_of(value, max_value):
    """
    计算百分比
    用法: {{ value|percentage_of:max_value }}
    """
    if max_value == 0:
        return 0
    return min(100, int((value / max_value) * 100))


@register.filter
def multiply(value, arg):
    """
    将值乘以参数
    用法: {{ value|multiply:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def star_rating(value):
    """
    将数值转换为星级评分显示
    用法: {{ anime.rating_avg|star_rating }}
    """
    try:
        value = float(value)
        full_stars = int(value)
        fraction = value - full_stars

        result = '<span class="star-rating">'
        # 添加完整星星
        result += '<i class="fas fa-star"></i>' * full_stars

        # 添加半星
        if fraction >= 0.5:
            result += '<i class="fas fa-star-half-alt"></i>'
            fraction = 0

        # 添加空星
        result += '<i class="far fa-star"></i>' * (5 - full_stars - (1 if fraction >= 0.5 else 0))

        result += '</span>'
        return mark_safe(result)
    except (ValueError, TypeError):
        return value


# 新增的函数，用于支持更多用户交互功能

@register.filter
def friendly_timesince(value):
    """
    将时间转换为友好的'多久前'格式
    用法: {{ comment.timestamp|friendly_timesince }}
    """
    if not value:
        return ''

    now = timezone.now()

    if value > now:
        return '刚刚'

    time_diff = timesince(value, now)

    # 转换英文时间描述为中文
    translations = {
        'year': '年',
        'years': '年',
        'month': '个月',
        'months': '个月',
        'week': '周',
        'weeks': '周',
        'day': '天',
        'days': '天',
        'hour': '小时',
        'hours': '小时',
        'minute': '分钟',
        'minutes': '分钟',
        'second': '秒',
        'seconds': '秒',
    }

    for eng, chn in translations.items():
        time_diff = time_diff.replace(eng, chn)

    # 去掉逗号后面的内容，只保留最大单位
    if ',' in time_diff:
        time_diff = time_diff.split(',')[0]

    return f'{time_diff}前'


@register.filter
def get_anime_user_status(anime, user):
    """
    获取用户对动漫的状态（已评分、已收藏等）
    用法: {{ anime|get_anime_user_status:user }}
    """
    if not user.is_authenticated:
        return []

    from recommendation.models import UserRating, UserFavorite, UserComment

    statuses = []

    # 检查是否已评分
    if UserRating.objects.filter(user=user, anime=anime).exists():
        statuses.append({
            'type': 'rated',
            'icon': 'fas fa-heart',
            'text': '已评分'
        })

    # 检查是否已收藏
    if UserFavorite.objects.filter(user=user, anime=anime).exists():
        statuses.append({
            'type': 'favorited',
            'icon': 'fas fa-bookmark',
            'text': '已收藏'
        })

    # 检查是否已评论
    if UserComment.objects.filter(user=user, anime=anime).exists():
        statuses.append({
            'type': 'commented',
            'icon': 'fas fa-comment',
            'text': '已评论'
        })

    return statuses


@register.simple_tag
def anime_popularity_percentage(anime):
    """
    将热门度转换为百分比
    用法: {% anime_popularity_percentage anime %}
    """
    try:
        popularity = float(anime.popularity)
        return min(100, int(popularity * 10))  # 0-10转化为0-100%
    except (ValueError, TypeError, AttributeError):
        return 0


@register.filter
def format_rating(value):
    """
    格式化评分显示
    用法: {{ anime.rating_avg|format_rating }}
    """
    try:
        return f"{float(value or 0):.1f}"
    except (ValueError, TypeError):
        return "0.0"


@register.filter
def heart_rating(value):
    """
    将数值转换为心形评分显示
    用法: {{ anime.rating_avg|heart_rating }}
    """
    try:
        value = float(value or 0)
        full_hearts = int(value)

        result = '<span class="rating-hearts">'
        # 添加实心心形
        result += '<i class="fas fa-heart heart active"></i>' * full_hearts

        # 添加空心
        result += '<i class="far fa-heart heart"></i>' * (5 - full_hearts)

        result += '</span>'
        return mark_safe(result)
    except (ValueError, TypeError):
        return value