from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def percentage_of(value, max_value):
    """计算百分比"""
    if max_value == 0:
        return 0
    return min(100, int((value / max_value) * 100))


@register.filter
def multiply(value, arg):
    """将值乘以参数"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def star_rating(value):
    """将数值转换为星级评分显示"""
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