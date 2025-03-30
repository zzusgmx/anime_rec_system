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
    量子级增强版动漫列表视图：添加异常处理和性能优化
    - 支持按标题、类型、评分等进行过滤
    - 实现分页功能
    - 展示推荐动漫
    - 量子增强：异常处理和性能优化
    """
    try:
        # 使用专用搜索表单处理搜索和过滤
        form = AnimeSearchForm(request.GET)

        # 性能优化：使用select_related减少数据库查询
        animes = Anime.objects.select_related('type').all()

        if form.is_valid():
            # 文本搜索（标题、原始标题、描述）
            query = form.cleaned_data.get('query')
            if query:
                # 优化搜索算法：使用全文搜索或更精确的匹配方式
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
            if is_completed:
                animes = animes.filter(is_completed=True)

            # 推荐过滤
            is_featured = form.cleaned_data.get('is_featured')
            if is_featured:
                animes = animes.filter(is_featured=True)

            # 排序
            sort_by = form.cleaned_data.get('sort_by')
            if sort_by:
                animes = animes.order_by(sort_by)
        else:
            # 默认排序：热门度降序
            animes = animes.order_by('-popularity')

        # 分页逻辑优化
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
        anime_types = AnimeType.objects.annotate(
            anime_count=Count('animes')
        ).order_by('name')

        context = {
            'animes': animes,
            'anime_types': anime_types,
            'search_form': form,
            'is_paginated': paginator.num_pages > 1,
            'page_obj': animes,
        }

        return render(request, 'anime/anime_list.html', context)

    except Exception as e:
        # 全局异常处理，量子态保护
        logger.error(f"动漫列表异常: {str(e)}\n{traceback.format_exc()}")

        # 降级显示
        messages.error(request, "加载动漫列表时发生错误，已启动降级保护模式")

        # 尝试获取类型列表用于最小化导航
        try:
            anime_types = AnimeType.objects.annotate(anime_count=Count('animes')).order_by('name')
        except:
            anime_types = []

        # 提供最小化上下文
        context = {
            'error': str(e) if settings.DEBUG else None,
            'search_form': AnimeSearchForm(),
            'anime_types': anime_types,
        }

        return render(request, 'anime/anime_list.html', context, status=500)

def anime_detail(request, slug):
    """
    量子态增强型动漫详情视图：支持多维度实体解析
    具备递归降级能力和自愈性错误处理
    """
    try:
        # ===== [内核] 量子级实体查找引擎 =====
        anime = None

        # 尝试路径1: 精确slug匹配 - O(1)复杂度
        try:
            anime = Anime.objects.get(slug=slug)
            logger.debug(f"通过精确slug匹配找到动漫: id={anime.id}, slug='{anime.slug}'")
        except Anime.DoesNotExist:
            pass

        # 尝试路径2: 数字ID回落 - 处理纯数字URL
        if anime is None and slug.isdigit():
            try:
                anime_id = int(slug)
                anime = Anime.objects.get(id=anime_id)
                logger.debug(f"通过ID回落找到动漫: id={anime.id}, slug='{anime.slug}'")

                # 执行URL规范化重定向
                if anime.slug and anime.slug != slug:
                    logger.info(f"从ID URL重定向到规范slug URL: {anime.slug}")
                    return redirect('anime:anime_detail', slug=anime.slug, permanent=True)
            except (ValueError, Anime.DoesNotExist):
                pass

        # 尝试路径3: 前缀模糊匹配 - 启发式搜索
        if anime is None:
            anime = Anime.objects.filter(slug__startswith=slug).first()
            if anime:
                logger.info(f"通过前缀模糊匹配找到动漫: id={anime.id}, slug='{anime.slug}'")
                # 重定向到规范URL
                return redirect('anime:anime_detail', slug=anime.slug, permanent=True)

        # 全维度搜索失败 - 引发404量子态
        if anime is None:
            logger.warning(f"全维度搜索失败: slug={slug}")
            raise Http404("动漫不存在")

        # ===== 记录用户浏览历史 =====
        if request.user.is_authenticated:
            try:
                # 引入事务管理
                from django.db import transaction

                # 使用原子事务确保浏览记录和计数的一致性
                with transaction.atomic():
                    # 更新或创建浏览记录
                    browse_record, created = UserBrowsing.objects.get_or_create(
                        user=request.user,
                        anime=anime,
                        defaults={'browse_count': 1}
                    )

                    logger.debug(f"浏览记录: user={request.user.id}, anime={anime.id}, created={created}, "
                                 f"当前browse_count={browse_record.browse_count if not created else 1}")

                    # 如果记录已存在，增加浏览次数
                    if not created:
                        # 直接使用F表达式进行原子更新，避免竞态条件
                        UserBrowsing.objects.filter(
                            user=request.user,
                            anime=anime
                        ).update(
                            browse_count=F('browse_count') + 1,
                            last_browsed=timezone.now()
                        )

                        # 重新获取更新后的记录，用于日志记录
                        browse_record.refresh_from_db()
                        logger.debug(f"更新后browse_count={browse_record.browse_count}")

                    # 增加动漫的总浏览次数
                    Anime.objects.filter(pk=anime.pk).update(view_count=F('view_count') + 1)

                # 刷新对象以获取更新的值
                anime.refresh_from_db()
                logger.debug(f"动漫'{anime.title}'总浏览次数更新为: {anime.view_count}")

            except Exception as e:
                # 浏览记录失败不影响主流程
                logger.error(f"记录浏览历史失败: {str(e)}\n{traceback.format_exc()}")

        # ===== 加载相关数据 =====
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

        # ===== [核心修复] 初始化上下文对象 =====
        # 这里是关键修复：确保context在所有执行路径上都被正确初始化
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
    - 实现多维级联删除破解外键约束锁
    - 采用原子事务保证数据完整性
    - 量子同步清除所有依赖实体
    """
    anime = get_object_or_404(Anime, slug=slug)

    if request.method == 'POST':
        anime_title = anime.title

        # 导入事务管理模块
        from django.db import transaction

        # 导入依赖实体模型
        from recommendation.models import UserRating, UserFavorite, UserComment, RecommendationCache
        from users.models import UserBrowsing, UserPreference

        try:
            # 启动原子事务锁 - 确保完全成功或完全失败
            with transaction.atomic():
                # 0x01: 高能反应堆 - 逆向清除所有依赖实体
                # 使用ORM批处理操作以达到最优性能
                UserPreference.objects.filter(anime=anime).delete()
                UserRating.objects.filter(anime=anime).delete()
                UserFavorite.objects.filter(anime=anime).delete()
                UserComment.objects.filter(anime=anime).delete()
                UserBrowsing.objects.filter(anime=anime).delete()
                RecommendationCache.objects.filter(anime=anime).delete()

                # 0x02: 核心实体销毁
                anime.delete()

            # 0x03: 成功信号传递
            messages.success(request, f'动漫《{anime_title}》已成功删除！')
            return redirect('anime:anime_list')

        except Exception as e:
            # 0x04: 异常捕获矩阵
            import traceback
            error_details = traceback.format_exc()
            messages.error(request, f'删除失败: {str(e)}')

            # 调试模式下透出完整量子轨迹
            if settings.DEBUG:
                messages.error(request, f'错误详情: {error_details}')

            return redirect('anime:anime_detail', slug=slug)

    # GET请求渲染确认页面
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


@cache_page(60 * 5)  # 缓存5分钟
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

    # 增强搜索范围和性能优化
    results = Anime.objects.filter(
        Q(title__icontains=query) |
        Q(original_title__icontains=query) |
        Q(description__icontains=query) |
        Q(type__name__icontains=query)  # 也搜索类型名称
    ).select_related('type').values(
        'id', 'title', 'slug', 'cover', 'type__name', 'rating_avg'
    )[:10]  # 限制结果数量为10个

    # 将QuerySet转换为列表，以便序列化
    results_list = []

    for item in results:
        # 构建搜索结果项
        result_item = {
            'id': item['id'],
            'title': item['title'],
            'url': reverse('anime:anime_detail', kwargs={'slug': item['slug']}),
            'type': item['type__name'],
            'rating': round(item['rating_avg'], 1) if item['rating_avg'] else None
        }

        # 处理封面图片URL
        if item['cover']:
            result_item['cover'] = f"{settings.MEDIA_URL}{item['cover']}"

        results_list.append(result_item)

    return JsonResponse({'results': results_list})


# anime/views.py
def anime_comments(request, slug):
    """
    量子化评论分页控制器 - 支持完整分页范式
    """
    anime = get_object_or_404(Anime, slug=slug)
    page = request.GET.get('page', 1)

    # 引入评论模型并优化查询性能
    from recommendation.models import UserComment, UserLike
    from django.db.models import Prefetch

    # 优化N+1查询问题 - 使用prefetch_related加载用户点赞
    user_likes_prefetch = None
    if request.user.is_authenticated:
        user_likes_prefetch = Prefetch(
            'likes',
            queryset=UserLike.objects.filter(user=request.user),
            to_attr='user_likes'
        )

    comments = UserComment.objects.filter(anime=anime) \
        .select_related('user', 'user__profile') \
        .prefetch_related(user_likes_prefetch) \
        .order_by('-timestamp')

    # 分页引擎
    paginator = Paginator(comments, 5)  # 每页10条评论
    try:
        page_obj = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    # 使用模板渲染（支持API/HTML双模式）
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX请求返回JSON
        from django.template.loader import render_to_string

        comments_html = ""
        for comment in page_obj:
            user_liked = False
            if request.user.is_authenticated and hasattr(comment, 'user_likes'):
                user_liked = len(comment.user_likes) > 0

            context = {'comment': comment, 'user': request.user, 'user_liked': user_liked}
            rendered = render_to_string('recommendation/partials/comment.html', context)
            comments_html += rendered

        # 构建分页元数据
        pagination_meta = {
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_comments': paginator.count
        }

        return JsonResponse({
            'html': comments_html,
            'pagination': pagination_meta
        })
    else:
        # 标准请求返回完整页面
        return render(request, 'anime/comments.html', {
            'comments': page_obj,
            'anime': anime
        })
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
    动漫类型删除视图：实现递归级联删除
    - 采用原子事务锁保证量子完整性
    - 实现多维度数据依赖清除
    - 高效批量操作优化
    """
    anime_type = get_object_or_404(AnimeType, slug=slug)

    if request.method == 'POST':
        anime_type_name = anime_type.name
        anime_count = anime_type.animes.count()

        # 导入事务管理和依赖实体
        from django.db import transaction
        from recommendation.models import UserRating, UserComment, UserFavorite, UserLike, RecommendationCache
        from users.models import UserBrowsing, UserPreference

        try:
            # 启动原子事务 - 确保完全成功或完全回滚
            with transaction.atomic():
                if anime_count > 0:
                    # 获取所有关联动漫ID - 使用列表强制执行查询
                    anime_ids = list(anime_type.animes.values_list('id', flat=True))

                    # 量子管道：多层次依赖实体清除 - 批量操作优化
                    # 第一层：用户偏好和浏览历史
                    UserPreference.objects.filter(anime_id__in=anime_ids).delete()
                    UserBrowsing.objects.filter(anime_id__in=anime_ids).delete()

                    # 第二层：社交互动数据
                    # 获取关联评论ID
                    comment_ids = list(UserComment.objects.filter(anime_id__in=anime_ids).values_list('id', flat=True))
                    # 清除评论点赞
                    if comment_ids:
                        UserLike.objects.filter(comment_id__in=comment_ids).delete()
                    # 清除评论本身
                    UserComment.objects.filter(anime_id__in=anime_ids).delete()

                    # 第三层：评分和收藏
                    UserRating.objects.filter(anime_id__in=anime_ids).delete()
                    UserFavorite.objects.filter(anime_id__in=anime_ids).delete()

                    # 第四层：推荐系统缓存
                    RecommendationCache.objects.filter(anime_id__in=anime_ids).delete()

                    # 最后：删除所有动漫实体
                    anime_type.animes.all().delete()

                # 终极操作：类型实体湮灭
                anime_type.delete()

            # 事务完成，提供反馈
            if anime_count > 0:
                messages.success(
                    request,
                    f'动漫类型【{anime_type_name}】已量子湮灭，同时级联删除了 {anime_count} 部动漫及相关数据。'
                )
            else:
                messages.success(request, f'动漫类型【{anime_type_name}】已删除！')

            return redirect('anime:anime_type_list')

        except Exception as e:
            # 异常处理：提供故障诊断信息
            import traceback
            error_details = traceback.format_exc()
            messages.error(request, f'删除失败: {str(e)}')

            # 调试模式输出完整堆栈
            if settings.DEBUG:
                messages.error(request, f'错误矩阵: {error_details}')

            return redirect('anime:anime_type_list')

    # GET请求：渲染确认页面
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


# 将此代码添加到 anime/views.py

def anime_search_redirect(request):
    """
    反向路由搜索适配器

    用于处理前端通过ID访问动漫详情的请求
    分析请求参数，查找对应的动漫记录，然后重定向到正确的URL

    这是一种高级的路由降级策略，解决URL配置与前端路由分发不匹配的问题
    """
    anime_id = request.GET.get('anime_id')

    if not anime_id:
        # 降级到普通搜索页面
        return anime_search(request)

    try:
        # 尝试通过ID查找动漫
        anime = Anime.objects.get(id=anime_id)
        # 重定向到正确的slug URL
        return redirect('anime:anime_detail', slug=anime.slug, permanent=False)
    except Anime.DoesNotExist:
        # 找不到动漫，返回404
        messages.error(request, f"找不到ID为 {anime_id} 的动漫")
        return redirect('anime:anime_not_found')
    except Exception as e:
        # 异常处理
        logger.error(f"搜索重定向异常: {str(e)}")
        messages.error(request, "查找动漫时发生错误")
        return redirect('anime:anime_list')

# 添加到 anime/views.py

def anime_find_by_id(request, anime_id):
    """
    通过ID直接查找动漫并重定向到详情页
    这是一个专用的查找器视图，避免和搜索视图冲突
    """
    try:
        anime = get_object_or_404(Anime, id=anime_id)
        # 重定向到基于slug的规范URL
        return redirect('anime:anime_detail', slug=anime.slug)
    except Exception as e:
        logger.error(f"通过ID查找动漫失败: {str(e)}")
        messages.error(request, "查找动漫时发生错误")
        return redirect('anime:anime_not_found')

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