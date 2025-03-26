# anime/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, Avg, F
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.conf import settings
import json
import logging
import traceback

from .models import Anime, AnimeType
from .forms import AnimeForm, AnimeTypeForm, AnimeSearchForm
from users.models import UserBrowsing, UserPreference

# 配置日志记录器
logger = logging.getLogger('django')


def anime_list(request):
    """
    动漫列表视图：展示所有动漫，支持搜索和分页
    - 支持按标题、类型、评分等进行过滤
    - 实现分页功能
    - 展示推荐动漫
    """
    # 使用专用搜索表单处理搜索和过滤
    form = AnimeSearchForm(request.GET)
    animes = Anime.objects.select_related('type').all()

    if form.is_valid():
        # 文本搜索（标题、原始标题、描述）
        query = form.cleaned_data.get('query')
        if query:
            animes = animes.filter(
                Q(title__icontains=query) |
                Q(original_title__icontains=query) |
                Q(description__icontains=query)
            )

        # 类型过滤
        anime_type = form.cleaned_data.get('type')
        if anime_type:
            animes = animes.filter(type=anime_type)

        # 评分过滤
        min_rating = form.cleaned_data.get('min_rating')
        if min_rating:
            animes = animes.filter(rating_avg__gte=min_rating)

        # 状态过滤
        is_completed = form.cleaned_data.get('is_completed')
        if is_completed is not None:
            animes = animes.filter(is_completed=is_completed)

        # 推荐过滤
        is_featured = form.cleaned_data.get('is_featured')
        if is_featured is not None:
            animes = animes.filter(is_featured=is_featured)

        # 排序
        sort_by = form.cleaned_data.get('sort_by')
        if sort_by:
            animes = animes.order_by(sort_by)
    else:
        # 默认排序：热门度降序
        animes = animes.order_by('-popularity')

    # 分页逻辑
    paginator = Paginator(animes, 12)  # 每页12个动漫
    page = request.GET.get('page')

    try:
        animes = paginator.page(page)
    except PageNotAnInteger:
        # 如果页数不是整数，展示第一页
        animes = paginator.page(1)
    except EmptyPage:
        # 如果页数超出范围，展示最后一页
        animes = paginator.page(paginator.num_pages)

    # 获取所有类型供导航使用
    anime_types = AnimeType.objects.annotate(anime_count=Count('animes')).order_by('name')

    # 获取推荐动漫（用于侧边栏或轮播）
    featured_animes = Anime.objects.filter(is_featured=True).order_by('-rating_avg')[:6]

    context = {
        'animes': animes,
        'anime_types': anime_types,
        'featured_animes': featured_animes,
        'search_form': form,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': animes,
    }

    return render(request, 'anime/anime_list.html', context)


def anime_detail(request, slug):
    """
    动漫详情视图：展示单个动漫的详细信息
    - 记录用户浏览历史
    - 增加浏览计数
    - 提供相关推荐
    - 显示评论

    量子级错误处理：捕获所有可能异常并提供优雅降级
    """
    try:
        # ===== 诊断日志 =====
        logger.info(f"DEBUG: 尝试访问动漫slug={slug}")

        # ===== 查询策略：先精确匹配，再模糊匹配 =====
        try:
            # 尝试精确匹配
            anime = get_object_or_404(Anime, slug=slug)
            logger.info(f"DEBUG: 精确匹配找到动漫: {anime.id} - {anime.title}")
        except Http404:
            # 精确匹配失败，尝试前缀匹配
            try:
                anime = Anime.objects.filter(slug__startswith=slug).first()
                if anime:
                    logger.info(f"DEBUG: 前缀匹配找到动漫: {anime.id} - {anime.title}")
                    # 重定向到正确的URL，保持SEO和用户体验
                    return redirect('anime:anime_detail', slug=anime.slug, permanent=True)
                else:
                    # 所有匹配都失败，抛出404
                    logger.warning(f"DEBUG: 找不到匹配的动漫: slug={slug}")
                    raise Http404("动漫不存在")
            except Exception as e:
                logger.error(f"前缀匹配查询失败: {str(e)}")
                raise Http404("动漫查询失败")

        # 记录用户浏览历史（如果用户已登录）
        if request.user.is_authenticated:
            try:
                # 更新或创建浏览记录
                browse_record, created = UserBrowsing.objects.get_or_create(
                    user=request.user,
                    anime=anime,
                    defaults={'browse_count': 1}
                )

                # 如果记录已存在，增加浏览次数
                if not created:
                    browse_record.browse_count += 1
                    browse_record.save(update_fields=['browse_count', 'last_browsed'])

                # 增加动漫的总浏览次数
                Anime.objects.filter(pk=anime.pk).update(view_count=F('view_count') + 1)
                # 刷新对象以获取更新的值
                anime.refresh_from_db()
            except Exception as e:
                # 浏览记录失败不影响主流程
                logger.error(f"记录浏览历史失败: {str(e)}")

        # 获取同类型的相关推荐（排除当前动漫）
        try:
            related_animes = Anime.objects.filter(type=anime.type) \
                                 .exclude(id=anime.id) \
                                 .order_by('-popularity')[:6]
        except Exception as e:
            logger.error(f"获取相关推荐失败: {str(e)}")
            related_animes = []

        # 获取最新评论
        try:
            from recommendation.models import UserComment
            recent_comments = UserComment.objects.filter(anime=anime) \
                                  .select_related('user') \
                                  .order_by('-timestamp')[:5]
        except Exception as e:
            logger.error(f"获取评论失败: {str(e)}")
            recent_comments = []

        # 检查用户是否已收藏和评分（如果已登录）
        user_data = {}
        if request.user.is_authenticated:
            try:
                from recommendation.models import UserRating, UserFavorite

                # 检查是否已评分
                try:
                    user_rating = UserRating.objects.get(user=request.user, anime=anime)
                    user_data['rating'] = user_rating.rating
                except UserRating.DoesNotExist:
                    user_data['rating'] = 0

                # 检查是否已收藏
                user_data['has_favorited'] = UserFavorite.objects.filter(
                    user=request.user, anime=anime
                ).exists()
            except Exception as e:
                logger.error(f"获取用户数据失败: {str(e)}")
                user_data = {'rating': 0, 'has_favorited': False}

        context = {
            'anime': anime,
            'related_animes': related_animes,
            'recent_comments': recent_comments,
            'user_data': user_data,
        }

        return render(request, 'anime/anime_detail.html', context)

    except Http404:
        return anime_not_found(request)
    except Exception as e:
        # 捕获所有其他异常
        logger.error(f"动漫详情视图异常: {str(e)}")
        logger.error(traceback.format_exc())

        # 开发环境展示详细错误
        if settings.DEBUG:
            return HttpResponse(
                f"<pre>错误: {str(e)}\n\n{traceback.format_exc()}</pre>",
                content_type="text/html"
            )

        # 生产环境优雅降级
        messages.error(request, "获取动漫详情时遇到错误，请稍后再试")
        return redirect('anime:anime_list')


def anime_not_found(request):
    """
    404优雅降级处理：为找不到的动漫提供友好界面
    """
    context = {
        'title': '动漫未找到',
        'message': '您查找的动漫不存在或已被移除',
    }
    return render(request, 'anime/anime_not_found.html', context, status=404)


@login_required
@permission_required('anime.add_anime', raise_exception=True)
def anime_create(request):
    """
    动漫创建视图：添加新动漫
    - 需要用户登录且具有添加动漫的权限
    - 使用 AnimeForm 处理表单提交
    """
    if request.method == 'POST':
        form = AnimeForm(request.POST, request.FILES)
        if form.is_valid():
            anime = form.save(commit=False)

            # 将初始热门度设为0
            anime.popularity = 0
            anime.save()

            messages.success(request, f'动漫《{anime.title}》已成功添加！')
            return redirect('anime:anime_detail', slug=anime.slug)
        else:
            messages.error(request, '添加动漫失败，请检查表单错误。')
    else:
        # 预填充类型字段（如果URL中有）
        initial = {}
        type_id = request.GET.get('type')
        if type_id:
            try:
                initial['type'] = AnimeType.objects.get(id=type_id)
            except AnimeType.DoesNotExist:
                pass

        form = AnimeForm(initial=initial)

    context = {
        'form': form,
        'title': '添加新动漫',
        'submit_label': '保存',
        'is_create': True
    }

    return render(request, 'anime/anime_form.html', context)


@login_required
@permission_required('anime.change_anime', raise_exception=True)
def anime_edit(request, slug):
    """
    动漫编辑视图：更新现有动漫
    - 需要用户登录且具有编辑动漫的权限
    - 使用 AnimeForm 处理表单提交
    """
    anime = get_object_or_404(Anime, slug=slug)

    if request.method == 'POST':
        form = AnimeForm(request.POST, request.FILES, instance=anime)
        if form.is_valid():
            updated_anime = form.save()
            messages.success(request, f'动漫《{updated_anime.title}》已成功更新！')
            return redirect('anime:anime_detail', slug=updated_anime.slug)
        else:
            messages.error(request, '更新动漫失败，请检查表单错误。')
    else:
        form = AnimeForm(instance=anime)

    context = {
        'form': form,
        'anime': anime,
        'title': f'编辑动漫: {anime.title}',
        'submit_label': '更新',
        'is_create': False
    }

    return render(request, 'anime/anime_form.html', context)


@login_required
@permission_required('anime.delete_anime', raise_exception=True)
def anime_delete(request, slug):
    """
    动漫删除视图：删除现有动漫
    - 需要用户登录且具有删除动漫的权限
    - 支持确认页面
    """
    anime = get_object_or_404(Anime, slug=slug)

    if request.method == 'POST':
        anime_title = anime.title
        anime.delete()
        messages.success(request, f'动漫《{anime_title}》已成功删除！')
        return redirect('anime:anime_list')

    context = {
        'anime': anime,
    }

    return render(request, 'anime/anime_confirm_delete.html', context)


def anime_type_list(request):
    """
    动漫类型列表视图：展示所有动漫类型
    - 包含每个类型的动漫数量
    - 包含每个类型的平均评分
    """
    types = AnimeType.objects.annotate(
        anime_count=Count('animes'),
        avg_rating=Avg('animes__rating_avg')
    ).order_by('name')

    context = {
        'types': types,
    }

    return render(request, 'anime/anime_type_list.html', context)


def anime_by_type(request, slug):
    """
    按类型查看动漫：展示特定类型的所有动漫
    - 支持分页功能
    """
    anime_type = get_object_or_404(AnimeType, slug=slug)

    # 获取该类型下的所有动漫，按热门度排序
    animes = Anime.objects.filter(type=anime_type).order_by('-popularity')

    # 分页逻辑
    paginator = Paginator(animes, 12)  # 每页12个动漫
    page = request.GET.get('page')

    try:
        animes = paginator.page(page)
    except PageNotAnInteger:
        animes = paginator.page(1)
    except EmptyPage:
        animes = paginator.page(paginator.num_pages)

    context = {
        'anime_type': anime_type,
        'animes': animes,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': animes,
    }

    return render(request, 'anime/anime_by_type.html', context)


@cache_page(60 * 15)  # 缓存15分钟
def anime_search(request):
    """
    AJAX搜索视图：处理AJAX搜索请求
    - 返回JSON格式的搜索结果，用于实时搜索建议
    - 支持多字段搜索
    - 返回缩略图和链接
    """
    query = request.GET.get('query', '')

    if len(query) < 2:  # 至少输入两个字符才触发搜索
        return JsonResponse({'results': []})

    # 增强搜索范围
    results = Anime.objects.filter(
        Q(title__icontains=query) |
        Q(original_title__icontains=query) |
        Q(description__icontains=query) |
        Q(type__name__icontains=query)  # 也搜索类型名称
    ).select_related('type').values(
        'id', 'title', 'slug', 'cover', 'type__name', 'rating_avg'
    )[:10]  # 限制结果数量为10个

    # 将QuerySet转换为列表，以便序列化
    results_list = list(results)

    # 增强返回结果
    for item in results_list:
        # 添加完整URL
        item['url'] = reverse('anime:anime_detail', kwargs={'slug': item['slug']})

        # 处理封面图片URL
        if item['cover']:
            item['cover'] = request.build_absolute_uri(item['cover'])

        # 添加类型名称
        if 'type__name' in item:
            item['type'] = item.pop('type__name')

        # 格式化评分
        if 'rating_avg' in item and item['rating_avg']:
            item['rating'] = round(item['rating_avg'], 1)
            item.pop('rating_avg')

    return JsonResponse({'results': results_list})


@login_required
@permission_required('anime.add_animetype', raise_exception=True)
def anime_type_create(request):
    """
    动漫类型创建视图：添加新类型
    - 需要用户登录且具有添加类型的权限
    """
    if request.method == 'POST':
        form = AnimeTypeForm(request.POST)
        if form.is_valid():
            anime_type = form.save()
            messages.success(request, f'动漫类型【{anime_type.name}】已成功添加！')
            return redirect('anime:anime_type_list')
        else:
            messages.error(request, '创建动漫类型失败，请检查表单错误。')
    else:
        form = AnimeTypeForm()

    context = {
        'form': form,
        'title': '添加新类型',
        'submit_label': '保存'
    }

    return render(request, 'anime/anime_type_form.html', context)


@login_required
@permission_required('anime.change_animetype', raise_exception=True)
def anime_type_edit(request, slug):
    """
    动漫类型编辑视图：更新现有类型
    - 需要用户登录且具有编辑类型的权限
    """
    anime_type = get_object_or_404(AnimeType, slug=slug)

    if request.method == 'POST':
        form = AnimeTypeForm(request.POST, instance=anime_type)
        if form.is_valid():
            updated_type = form.save()
            messages.success(request, f'动漫类型【{updated_type.name}】已成功更新！')
            return redirect('anime:anime_type_list')
        else:
            messages.error(request, '更新动漫类型失败，请检查表单错误。')
    else:
        form = AnimeTypeForm(instance=anime_type)

    context = {
        'form': form,
        'anime_type': anime_type,
        'title': f'编辑类型: {anime_type.name}',
        'submit_label': '更新'
    }

    return render(request, 'anime/anime_type_form.html', context)


@login_required
@permission_required('anime.delete_animetype', raise_exception=True)
def anime_type_delete(request, slug):
    """
    动漫类型删除视图：删除现有类型
    - 需要用户登录且具有删除类型的权限
    - 防止删除已被动漫使用的类型
    """
    anime_type = get_object_or_404(AnimeType, slug=slug)

    # 检查是否有动漫使用此类型
    if anime_type.animes.exists():
        messages.error(request, f'无法删除类型【{anime_type.name}】，因为有动漫正在使用此类型。')
        return redirect('anime:anime_type_list')

    if request.method == 'POST':
        anime_type_name = anime_type.name
        anime_type.delete()
        messages.success(request, f'动漫类型【{anime_type_name}】已成功删除！')
        return redirect('anime:anime_type_list')

    context = {
        'anime_type': anime_type,
    }

    return render(request, 'anime/anime_type_confirm_delete.html', context)


# 添加异步评分和收藏处理视图
@login_required
@require_POST
def rate_anime(request, anime_id):
    """
    异步处理动漫评分
    - 使用AJAX请求处理
    - 需要用户登录
    """
    anime = get_object_or_404(Anime, id=anime_id)
    rating = float(request.POST.get('rating', 0))

    # 验证评分值
    if not (0 < rating <= 5):
        return JsonResponse({'status': 'error', 'message': '评分必须在1-5之间'}, status=400)

    # 更新或创建评分
    from recommendation.models import UserRating

    UserRating.objects.update_or_create(
        user=request.user,
        anime=anime,
        defaults={'rating': rating}
    )

    # 触发信号处理器更新动漫评分统计
    # 在signals.py中已实现

    return JsonResponse({
        'status': 'success',
        'message': f'成功为《{anime.title}》评分'
    })


@login_required
@require_POST
def toggle_favorite(request, anime_id):
    """
    异步处理动漫收藏
    - 使用AJAX请求处理
    - 需要用户登录
    """
    anime = get_object_or_404(Anime, id=anime_id)

    # 更新或创建收藏
    from recommendation.models import UserFavorite

    favorite, created = UserFavorite.objects.get_or_create(
        user=request.user,
        anime=anime,
    )

    # 如果已存在则删除（取消收藏）
    if not created:
        favorite.delete()
        action = 'removed'
        message = f'已取消收藏《{anime.title}》'
    else:
        action = 'added'
        message = f'已成功收藏《{anime.title}》'

    # 触发信号处理器更新动漫收藏统计
    # 在signals.py中已实现

    return JsonResponse({
        'status': 'success',
        'action': action,
        'message': message
    })


@require_POST
@login_required
@permission_required('anime.change_animetype', raise_exception=True)
def fix_type_slug(request):
    """
    AJAX端点：量子修复空slug的动漫类型记录
    使用模型的save()方法触发slug自动生成逻辑
    """
    try:
        data = json.loads(request.body)
        type_id = data.get('id')

        if not type_id:
            return JsonResponse({'success': False, 'error': '缺少类型ID'})

        # 获取类型并触发save()方法重新生成slug
        anime_type = get_object_or_404(AnimeType, id=type_id)
        # 强制清空slug以触发重新生成逻辑
        anime_type.slug = ''
        anime_type.save()  # 增强save()方法会处理slug生成

        return JsonResponse({
            'success': True,
            'message': f'成功修复 "{anime_type.name}" 的URL标识符',
            'slug': anime_type.slug
        })

    except Exception as e:
        logger.error(f"修复slug失败: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})