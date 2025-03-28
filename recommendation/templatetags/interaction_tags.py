from django import template
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from recommendation.models import UserRating, UserFavorite, UserLike

register = template.Library()


@register.simple_tag
def user_rating(user, anime):
    """
    获取用户对动漫的评分量子态
    用法: {% user_rating user anime %}
    """
    if not user.is_authenticated:
        return 0

    try:
        rating = UserRating.objects.get(user=user, anime=anime)
        return rating.rating
    except UserRating.DoesNotExist:
        return 0


@register.simple_tag
def user_has_favorited(user, anime):
    """
    检测用户收藏状态量子叠加
    用法: {% user_has_favorited user anime %}
    """
    if not user.is_authenticated:
        return False

    return UserFavorite.objects.filter(user=user, anime=anime).exists()


@register.simple_tag
def user_has_liked(user, comment):
    """
    检测用户点赞状态量子叠加
    用法: {% user_has_liked user comment %}
    """
    if not user.is_authenticated:
        return False

    return UserLike.objects.filter(user=user, comment=comment).exists()


@register.filter
def star_rating_html(value, max_stars=5):
    """
    渲染星级评分HTML
    用法: {{ anime.rating_avg|star_rating_html }}
    """
    html = '<div class="rating-display">'

    # 整星
    full_stars = int(value)
    for i in range(full_stars):
        html += '<i class="fas fa-star text-warning"></i>'

    # 半星
    if value - full_stars >= 0.5:
        html += '<i class="fas fa-star-half-alt text-warning"></i>'
        half_star = 1
    else:
        half_star = 0

    # 空星
    for i in range(max_stars - full_stars - half_star):
        html += '<i class="far fa-star text-warning"></i>'

    html += f'<span class="ms-2">{value:.1f}</span></div>'

    return mark_safe(html)


# 新增的函数，用于支持心形评分系统

@register.simple_tag(takes_context=True)
def render_comment(context, comment):
    """
    渲染评论组件
    用法: {% render_comment comment %}
    """
    # 获取当前用户
    user = context['user']

    # 检查用户是否已点赞该评论
    user_liked = False
    if user.is_authenticated:
        user_liked = UserLike.objects.filter(user=user, comment=comment).exists()

    # 创建上下文
    render_context = {
        'comment': comment,
        'user': user,
        'user_liked': user_liked
    }

    # 渲染评论模板
    return render_to_string('recommendation/partials/comment.html', render_context)


@register.simple_tag(takes_context=True)
def user_has_rated(context, anime):
    """
    检查用户是否已对指定动漫评分
    用法: {% user_has_rated anime %}
    """
    user = context['user']

    if not user.is_authenticated:
        return False

    return UserRating.objects.filter(user=user, anime=anime).exists()


@register.simple_tag(takes_context=True)
def user_rating_value(context, anime):
    """
    获取用户对指定动漫的评分
    用法: {% user_rating_value anime %}
    """
    user = context['user']

    if not user.is_authenticated:
        return 0

    try:
        rating = UserRating.objects.get(user=user, anime=anime)
        return rating.rating
    except UserRating.DoesNotExist:
        return 0


@register.filter
def heart_rating_html(value, max_hearts=5):
    """
    渲染心形评分HTML
    用法: {{ anime.rating_avg|heart_rating_html }}
    """
    html = '<div class="rating-hearts">'

    # 确保值在有效范围内
    value = max(0, min(float(value or 0), max_hearts))

    # 整颗心
    full_hearts = int(value)
    for i in range(full_hearts):
        html += '<i class="fas fa-heart heart active"></i>'

    # 空心
    for i in range(max_hearts - full_hearts):
        html += '<i class="far fa-heart heart"></i>'

    html += '</div>'

    return mark_safe(html)


@register.inclusion_tag('recommendation/partials/rating_hearts.html')
def rating_hearts_display(value, interactive=False, element_id=None):
    """
    显示评分心形
    用法: {% rating_hearts_display anime.rating_avg %}
    """
    return {
        'rating': float(value or 0),
        'range': range(1, 6),  # 1-5评分
        'interactive': interactive,
        'element_id': element_id
    }