"""
可视化服务模块
包含数据处理和可视化生成服务
"""
import pandas as pd
import numpy as np
from django.db.models import Count, Avg, Sum, F, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta
import logging
import traceback
import json

from anime.models import Anime, AnimeType
from recommendation.models import UserRating, UserComment, UserFavorite, AnimeLike, UserInteraction
from users.models import UserBrowsing, Profile, UserPreference
from .models import DataCache

logger = logging.getLogger('django')


class DataProcessingService:
    """数据处理服务类"""

    @staticmethod
    def get_user_genre_preferences(user):
        """
        获取用户的动漫类型偏好数据
        返回适合可视化的数据结构
        """
        try:
            # 获取用户评分过的动漫的类型
            rated_anime_types = UserRating.objects.filter(user=user).select_related('anime__type')
            type_data = {}

            # 统计每个类型的评分情况
            for rating in rated_anime_types:
                if not rating.anime.type:
                    continue

                type_name = rating.anime.type.name
                if type_name not in type_data:
                    type_data[type_name] = {
                        'rating_count': 0,
                        'total_rating': 0,
                        'browse_count': 0,
                        'favorite_count': 0
                    }
                type_data[type_name]['rating_count'] += 1
                type_data[type_name]['total_rating'] += rating.rating

            # 获取用户浏览记录中的动漫类型
            browsed_anime_types = UserBrowsing.objects.filter(user=user).select_related('anime__type')
            for browsing in browsed_anime_types:
                if not browsing.anime.type:
                    continue

                type_name = browsing.anime.type.name
                if type_name not in type_data:
                    type_data[type_name] = {
                        'rating_count': 0,
                        'total_rating': 0,
                        'browse_count': 0,
                        'favorite_count': 0
                    }
                type_data[type_name]['browse_count'] += browsing.browse_count

            # 获取用户收藏的动漫类型
            favorite_anime_types = UserFavorite.objects.filter(user=user).select_related('anime__type')
            for favorite in favorite_anime_types:
                if not favorite.anime.type:
                    continue

                type_name = favorite.anime.type.name
                if type_name not in type_data:
                    type_data[type_name] = {
                        'rating_count': 0,
                        'total_rating': 0,
                        'browse_count': 0,
                        'favorite_count': 0
                    }
                type_data[type_name]['favorite_count'] += 1

            # 计算每个类型的偏好分数
            preference_scores = []
            for type_name, data in type_data.items():
                # 偏好分数计算逻辑
                avg_rating = data['total_rating'] / data['rating_count'] if data['rating_count'] > 0 else 0

                # 权重设置
                rating_weight = 2.0
                browse_weight = 0.2
                favorite_weight = 3.0

                # 计算偏好分数
                preference_score = (
                        rating_weight * avg_rating * data['rating_count'] +
                        browse_weight * data['browse_count'] +
                        favorite_weight * data['favorite_count']
                )

                preference_scores.append({
                    'name': type_name,
                    'value': round(preference_score, 2),
                    'avg_rating': round(avg_rating, 1) if data['rating_count'] > 0 else 0,
                    'rating_count': data['rating_count'],
                    'browse_count': data['browse_count'],
                    'favorite_count': data['favorite_count']
                })

            # 按偏好分数降序排序
            preference_scores.sort(key=lambda x: x['value'], reverse=True)

            # 取前8个类型
            return preference_scores[:8]
        except Exception as e:
            logger.error(f"获取用户类型偏好数据失败: {str(e)}\n{traceback.format_exc()}")
            return []

    @staticmethod
    def get_user_rating_trends(user):
        """获取用户评分趋势数据"""
        try:
            # 获取过去12个月的评分数据
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=365)

            # 按月聚合评分数据
            rating_by_month = (
                UserRating.objects.filter(
                    user=user,
                    timestamp__date__gte=start_date,
                    timestamp__date__lte=end_date
                )
                .annotate(month=TruncMonth('timestamp'))
                .values('month')
                .annotate(
                    count=Count('id'),
                    avg_rating=Avg('rating')
                )
                .order_by('month')
            )

            # 构建完整的月份序列
            months = []
            current = start_date.replace(day=1)
            while current <= end_date:
                months.append(current)
                # 移至下个月
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

            # 将查询结果转换为字典，以月份为键
            rating_dict = {item['month'].date().isoformat(): {
                'count': item['count'],
                'avg_rating': round(item['avg_rating'], 1)
            } for item in rating_by_month}

            # 构建完整的月份序列数据
            result = []
            for month in months:
                month_str = month.isoformat()
                if month_str in rating_dict:
                    result.append({
                        'month': month_str,
                        'count': rating_dict[month_str]['count'],
                        'avg_rating': rating_dict[month_str]['avg_rating']
                    })
                else:
                    result.append({
                        'month': month_str,
                        'count': 0,
                        'avg_rating': 0
                    })

            return result
        except Exception as e:
            logger.error(f"获取用户评分趋势数据失败: {str(e)}\n{traceback.format_exc()}")
            return []


class VisualizationService:
    """可视化服务类"""

    @staticmethod
    def generate_rating_distribution(user):
        """生成评分分布数据"""
        try:
            # 查询用户的评分记录
            ratings = UserRating.objects.filter(user=user)

            # 如果没有评分记录，返回空数据
            if not ratings.exists():
                return []

            # 统计每个评分的次数
            rating_distribution = {}
            for r in range(1, 6):  # 1-5分
                # 计算四舍五入到每个整数分数的评分数量
                count = ratings.filter(rating__gte=r - 0.25, rating__lt=r + 0.75).count()
                rating_distribution[r] = count

            # 构建数据
            data = [
                {'rating': r, 'count': rating_distribution[r]}
                for r in range(1, 6)
            ]

            return data
        except Exception as e:
            logger.error(f"生成评分分布数据失败: {str(e)}\n{traceback.format_exc()}")
            return []

    @staticmethod
    def generate_genre_preference(user):
        """生成类型偏好数据"""
        try:
            # 使用DataProcessingService获取偏好数据
            return DataProcessingService.get_user_genre_preferences(user)
        except Exception as e:
            logger.error(f"生成类型偏好数据失败: {str(e)}\n{traceback.format_exc()}")
            return []

    @staticmethod
    def generate_viewing_trends(user):
        """生成观看趋势数据"""
        try:
            # 获取过去14天的日期范围
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=13)
            date_range = [start_date + timedelta(days=i) for i in range(14)]

            # 查询用户在这段时间内的浏览记录
            browsing_data = (
                UserBrowsing.objects
                .filter(
                    user=user,
                    last_browsed__date__gte=start_date,
                    last_browsed__date__lte=end_date
                )
                .annotate(date=TruncDate('last_browsed'))
                .values('date')
                .annotate(views=Count('id'))
                .order_by('date')
            )

            # 查询用户在这段时间内的评分记录
            rating_data = (
                UserRating.objects
                .filter(
                    user=user,
                    timestamp__date__gte=start_date,
                    timestamp__date__lte=end_date
                )
                .annotate(date=TruncDate('timestamp'))
                .values('date')
                .annotate(ratings=Count('id'))
                .order_by('date')
            )

            # 将查询结果转换为字典，以日期为键
            browsing_dict = {item['date'].isoformat(): item['views'] for item in browsing_data}
            rating_dict = {item['date'].isoformat(): item['ratings'] for item in rating_data}

            # 构建完整的日期序列数据
            result = []
            for d in date_range:
                date_str = d.isoformat()
                result.append({
                    'date': date_str,
                    'views': browsing_dict.get(date_str, 0),
                    'ratings': rating_dict.get(date_str, 0)
                })

            return result
        except Exception as e:
            logger.error(f"生成观看趋势数据失败: {str(e)}\n{traceback.format_exc()}")
            return []

    @staticmethod
    def generate_activity_summary(user):
        """生成活动摘要数据"""
        try:
            # 获取用户的浏览记录数
            browsing_count = UserBrowsing.objects.filter(user=user).count()

            # 获取用户的评分记录数
            rating_count = UserRating.objects.filter(user=user).count()

            # 获取用户的评论记录数
            comment_count = UserComment.objects.filter(user=user).count()

            # 获取用户的收藏记录数
            favorite_count = UserFavorite.objects.filter(user=user).count()

            # 构建数据
            data = [
                {
                    'name': '浏览记录',
                    'value': browsing_count,
                    'color': '#6d28d9'  # 紫色
                },
                {
                    'name': '评分记录',
                    'value': rating_count,
                    'color': '#10b981'  # 绿色
                },
                {
                    'name': '评论记录',
                    'value': comment_count,
                    'color': '#f97316'  # 橙色
                },
                {
                    'name': '收藏记录',
                    'value': favorite_count,
                    'color': '#2563eb'  # 蓝色
                }
            ]

            return data
        except Exception as e:
            logger.error(f"生成活动摘要数据失败: {str(e)}\n{traceback.format_exc()}")
            return []

    @staticmethod
    def generate_network_data(user=None):
        """生成关系网络数据"""
        try:
            # 定义最大节点数
            max_nodes = 50

            if user:
                # 特定用户的交互网络
                interactions = UserInteraction.objects.filter(
                    Q(from_user=user) | Q(to_user=user)
                ).select_related('from_user', 'to_user').order_by('-timestamp')[:100]

                # 收集节点
                users = set([user.id])
                for interaction in interactions:
                    users.add(interaction.from_user.id)
                    users.add(interaction.to_user.id)
                    if len(users) >= max_nodes:
                        break

                # 限制总节点数
                users = list(users)[:max_nodes]

                # 过滤关联的交互
                filtered_interactions = [i for i in interactions
                                         if i.from_user.id in users and i.to_user.id in users]
            else:
                # 全局交互网络
                interactions = UserInteraction.objects.all().select_related(
                    'from_user', 'to_user'
                ).order_by('-timestamp')[:500]

                # 计算每个用户的交互总数
                user_interaction_count = {}
                for interaction in interactions:
                    user_interaction_count[interaction.from_user.id] = user_interaction_count.get(
                        interaction.from_user.id, 0) + 1
                    user_interaction_count[interaction.to_user.id] = user_interaction_count.get(interaction.to_user.id,
                                                                                                0) + 1

                # 选择交互最多的用户
                sorted_users = sorted(user_interaction_count.items(), key=lambda x: x[1], reverse=True)
                top_users = [user_id for user_id, _ in sorted_users[:max_nodes]]

                # 过滤关联的交互
                filtered_interactions = [i for i in interactions
                                         if i.from_user.id in top_users and i.to_user.id in top_users]

            # 构建节点数据
            nodes = []
            user_profiles = {}

            for user_id in sorted(list(set([i.from_user.id for i in filtered_interactions] +
                                           [i.to_user.id for i in filtered_interactions]))):
                try:
                    profile = Profile.objects.get(user_id=user_id)
                    user_profiles[user_id] = profile

                    nodes.append({
                        'id': user_id,
                        'username': profile.user.username,
                        'influence': profile.influence_score,
                        'activity': profile.social_activity_score,
                        'size': 10 + (profile.influence_score + profile.social_activity_score) / 10
                    })
                except Profile.DoesNotExist:
                    pass

            # 构建连接数据
            links = []
            for interaction in filtered_interactions:
                links.append({
                    'source': interaction.from_user.id,
                    'target': interaction.to_user.id,
                    'type': interaction.interaction_type,
                    'strength': interaction.strength,
                    'width': interaction.strength * 2  # 线宽基于交互强度
                })

            return {
                'nodes': nodes,
                'links': links
            }
        except Exception as e:
            logger.error(f"生成网络数据失败: {str(e)}\n{traceback.format_exc()}")
            return {'nodes': [], 'links': []}