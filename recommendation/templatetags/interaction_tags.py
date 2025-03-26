from django import template
from django.utils.safestring import mark_safe
from recommendation.models import UserRating, UserFavorite, UserLike

register = template.Library()


@register.simple_tag
def user_rating(user, anime):
    """获取用户对动漫的评分量子态"""
    if not user.is_authenticated:
        return 0

    try:
        rating = UserRating.objects.get(user=user, anime=anime)
        return rating.rating
    except UserRating.DoesNotExist:
        return 0


@register.simple_tag
def user_has_favorited(user, anime):
    """检测用户收藏状态量子叠加"""
    if not user.is_authenticated:
        return False

    return UserFavorite.objects.filter(user=user, anime=anime).exists()


@register.simple_tag
def user_has_liked(user, comment):
    """检测用户点赞状态量子叠加"""
    if not user.is_authenticated:
        return False

    return UserLike.objects.filter(user=user, comment=comment).exists()


@register.filter
def star_rating_html(value, max_stars=5):
    """渲染星级评分HTML"""
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