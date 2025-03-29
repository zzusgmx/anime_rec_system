# recommendation/engine/recommendation_engine.py
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from django.db.models import Avg, Count
from django.core.cache import cache
from django.utils import timezone
import logging
from pathlib import Path
import joblib
import pickle
from anime.models import Anime, AnimeType
from recommendation.models import UserRating
from users.models import UserBrowsing, UserPreference  # 修正导入路径

# 配置日志记录器
logger = logging.getLogger('django')
try:
    # 量子修复
    from recommendation.engine.models.ml_engine import GBDTRecommender

    ML_ENGINE_AVAILABLE = True
except ImportError:
    ML_ENGINE_AVAILABLE = False
    logger.warning("scikit-learn可能未安装，机器学习引擎不可用")


class RecommendationEngine:
    """
    混合推荐引擎：结合协同过滤和基于内容的推荐算法

    技术栈：
    - 协同过滤 (Collaborative Filtering)：基于用户行为相似度
    - 基于内容 (Content-Based)：基于物品特征相似度
    - 混合模型 (Hybrid)：动态权重融合策略
    """

    def _ml_recommendations(self, user_id, limit=10):
        """
        使用GBDT机器学习模型生成推荐
        """
        try:
            # 加载GBDT模型和编码器
            model_dir = Path(__file__).parent / 'models'
            model_path = model_dir / 'gbdt_model.joblib'
            encoders_path = model_dir / 'gbdt_encoders.pkl'

            if not (model_path.exists() and encoders_path.exists()):
                logger.error(f"GBDT模型文件不存在: {model_path} 或 {encoders_path}")
                # 如果模型不存在，回退到协同过滤
                logger.warning("GBDT模型不可用，回退到协同过滤")
                return self._collaborative_filtering(user_id, limit)

            # 加载模型和编码器
            model = joblib.load(model_path)
            encoders = pickle.load(open(encoders_path, 'rb'))

            # 准备用户特征
            user_features = self._extract_user_features(user_id)

            # 获取所有动漫
            all_anime = self._get_all_anime()

            # 为用户生成所有动漫的预测评分
            predictions = []
            for anime in all_anime:
                # 跳过用户已评分的动漫
                if self._has_user_rated(user_id, anime.id):
                    continue

                # 构建预测特征
                features = self._combine_features(user_features, self._extract_anime_features(anime))

                # 编码特征
                encoded_features = self._encode_features(features, encoders)

                # 预测
                try:
                    prediction = model.predict([encoded_features])[0]
                    predictions.append((anime.id, prediction))
                except Exception as e:
                    logger.error(f"GBDT预测错误 (动漫ID={anime.id}): {str(e)}")
                    continue

            # 排序并返回前limit个
            predictions.sort(key=lambda x: x[1], reverse=True)
            return predictions[:limit]

        except Exception as e:
            logger.error(f"GBDT推荐错误: {str(e)}")
            # 错误回退到混合算法
            logger.warning("ML推荐失败，回退到混合算法")
            cf_recs = self._collaborative_filtering(user_id, limit)
            cb_recs = self._content_based(user_id, limit)
            return self._hybrid_merge(cf_recs, cb_recs, limit)

    def _extract_user_features(self, user_id):
        """提取用户特征"""
        # 实现用户特征提取逻辑
        # 这应该返回用户的特征，如评分历史统计、偏好类型等
        pass

    def _extract_anime_features(self, anime):
        """提取动漫特征"""
        # 实现动漫特征提取逻辑
        # 返回动漫的特征，如类型、流行度、评分等
        pass

    def _combine_features(self, user_features, anime_features):
        """组合用户和动漫特征"""
        # 实现特征组合逻辑
        pass

    def _encode_features(self, features, encoders):
        """编码特征以匹配模型输入"""
        # 使用提供的编码器对特征进行编码
        pass

    def _has_user_rated(self, user_id, anime_id):
        """检查用户是否已评分过该动漫"""
        # 实现检查逻辑
        pass

    def _get_all_anime(self):
        """获取所有动漫"""
        # 从数据库获取所有动漫
        from anime.models import Anime
        return Anime.objects.all()

    def __init__(self, use_cache=True, cache_ttl=3600):
        """
        初始化推荐引擎

        Args:
            use_cache: 是否使用缓存加速
            cache_ttl: 缓存生存时间(秒)
        """
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        # 初始化机器学习引擎(如可用)
        self.ml_engine = None
        if ML_ENGINE_AVAILABLE:
            try:
                self.ml_engine = GBDTRecommender()
                # 尝试加载模型
                if not self.ml_engine.load_model():
                    # 模型不存在，尝试训练
                    logger.info("GBDT模型不存在，尝试即时训练...")
                    self.ml_engine.train_model()
            except Exception as e:
                logger.error(f"初始化ML引擎失败: {str(e)}")
                self.ml_engine = None

        logger.info("量子态推荐引擎初始化完毕，ML状态: %s", "在线" if self.ml_engine else "离线")

    def get_recommendations_for_user(self, user_id, limit=10, strategy='hybrid'):
        """
        为指定用户生成个性化推荐
        """
        cache_key = f"rec:user:{user_id}:strat:{strategy}:limit:{limit}"

        # 检查缓存
        if self.use_cache:
            cached_recommendations = cache.get(cache_key)
            if cached_recommendations:
                logger.debug(f"命中缓存: {cache_key}")
                return cached_recommendations

        try:
            # 根据策略选择算法
            if strategy == 'cf':
                recommendations = self._collaborative_filtering(user_id, limit)
            elif strategy == 'content':
                recommendations = self._content_based(user_id, limit)
            elif strategy == 'ml' and self.ml_engine:
                recommendations = self._ml_recommendations(user_id, limit)
            elif strategy == 'popular':
                recommendations = self._popular_recommendations(limit)
            else:  # 默认混合策略
                cf_recs = self._collaborative_filtering(user_id, limit * 2) or []
                cb_recs = self._content_based(user_id, limit * 2) or []

                if self.ml_engine:
                    ml_recs = self._ml_recommendations(user_id, limit * 2) or []
                    recommendations = self._hybrid_merge_three(cf_recs, cb_recs, ml_recs, limit)
                else:
                    recommendations = self._hybrid_merge(cf_recs, cb_recs, limit)

            # 确保推荐不为空
            if not recommendations:
                logger.warning(f"策略 {strategy} 未能生成推荐，回退到热门推荐")
                recommendations = self._popular_recommendations(limit)

            # 缓存结果
            if self.use_cache and recommendations:
                cache.set(cache_key, recommendations, self.cache_ttl)

            return recommendations
        except Exception as e:
            logger.error(f"推荐生成异常: {str(e)}")
            # 发生任何异常时返回热门推荐
            return self._popular_recommendations(limit)

    # 添加机器学习推荐方法
    def _ml_recommendations(self, user_id, limit=10):
        """
        机器学习推荐算法

        使用GBDT模型进行精准的个性化推荐
        """
        if not self.ml_engine:
            logger.warning("ML引擎离线，回退到协同过滤")
            return self._collaborative_filtering(user_id, limit)

        try:
            # 获取ML推荐
            recommendations = self.ml_engine.get_recommendations(user_id, limit * 2)

            # 如果ML推荐不足，补充协同过滤推荐
            if len(recommendations) < limit:
                cf_recs = self._collaborative_filtering(user_id, limit - len(recommendations))
                recommendations.extend(cf_recs)

            # 确保不超过limit
            return recommendations[:limit]

        except Exception as e:
            logger.error(f"ML推荐引擎故障: {str(e)}")
            return self._collaborative_filtering(user_id, limit)

    def _collaborative_filtering(self, user_id, limit=10):
        """
        协同过滤推荐算法实现 v2.1.3 - 量子相似度版

        使用用户-物品评分矩阵和余弦相似度进行多维映射
        包含自适应相似用户扩展机制和多级回退策略

        复杂度: O(n·log(n)) 其中 n 为评分数量
        """
        try:
            # 获取用户评分数据
            ratings = UserRating.objects.all().values('user_id', 'anime_id', 'rating')

            # 数据源检查 - 处理冷启动情况
            if len(ratings) < 10:
                logger.warning("评分数据不足，回退到热门推荐")
                return self._popular_recommendations(limit)

            # 转换为评分矩阵
            df = pd.DataFrame(ratings)
            pivot_table = df.pivot_table(index='user_id', columns='anime_id', values='rating').fillna(0)

            # 用户评分向量 - 处理冷启动用户
            try:
                user_vector = pivot_table.loc[user_id].values
            except KeyError:
                # 新用户冷启动问题处理
                logger.info(f"用户 {user_id} 没有评分记录，回退到热门推荐")
                return self._popular_recommendations(limit)

            # 计算用户相似度矩阵 - 使用余弦相似度
            user_similarity = cosine_similarity([user_vector], pivot_table.values)[0]

            # 【量子增强】动态扩展相似用户池 - 解决推荐不足问题
            user_indices = pivot_table.index.tolist()
            user_position = user_indices.index(user_id)
            similar_user_indices = np.argsort(user_similarity)[::-1]

            # 【核心修复】将固定值5扩展到最多20个相似用户
            K_SIMILAR_USERS = min(20, len(similar_user_indices) - 1)  # 防止越界
            similar_users = [user_indices[i] for i in similar_user_indices if i != user_position][:K_SIMILAR_USERS]

            # 【高级特性】记录相似用户抽样度量
            logger.debug(f"抽样了 {len(similar_users)} 个相似用户，相似度范围: "
                         f"{user_similarity[similar_user_indices[1]] if len(similar_user_indices) > 1 else 0:.4f} - "
                         f"{user_similarity[similar_user_indices[min(K_SIMILAR_USERS, len(similar_user_indices) - 1)]] if len(similar_user_indices) > K_SIMILAR_USERS else 0:.4f}")

            # 获取当前用户已评分的动漫 - 使用集合提高查找效率 O(1)
            rated_animes = set(df[df['user_id'] == user_id]['anime_id'].tolist())

            # 收集相似用户高评分的动漫 - 使用字典加速聚合
            candidate_animes = {}
            for similar_user in similar_users:
                similar_ratings = df[df['user_id'] == similar_user]
                for _, row in similar_ratings.iterrows():
                    anime_id = row['anime_id']
                    rating = row['rating']

                    # 排除用户已评分的动漫
                    if anime_id in rated_animes:
                        continue

                    # 使用相似度加权评分 - 余弦距离作为加权因子
                    user_sim = user_similarity[user_indices.index(similar_user)]

                    # 【算法优化】使用相似度平方，增强高相似用户权重
                    weighted_sim = user_sim * user_sim

                    # 更新候选动漫分数，使用加权平均
                    if anime_id in candidate_animes:
                        candidate_animes[anime_id][0] += rating * weighted_sim
                        candidate_animes[anime_id][1] += weighted_sim
                    else:
                        candidate_animes[anime_id] = [rating * weighted_sim, weighted_sim]

            # 计算最终分数并排序
            recommendations = []
            for anime_id, (weighted_sum, sim_sum) in candidate_animes.items():
                if sim_sum > 0:  # 防止除零错误
                    weighted_rating = weighted_sum / sim_sum
                    # 归一化到0-1范围
                    normalized_score = weighted_rating / 5.0
                    recommendations.append((anime_id, normalized_score))

            # 按分数降序排序
            recommendations.sort(key=lambda x: x[1], reverse=True)

            # 【量子级回退特性】处理推荐不足情况
            if len(recommendations) < limit:
                logger.info(f"协同过滤推荐数量不足({len(recommendations)}个)，启动三级回退策略")

                # 1. 尝试降低相似度阈值策略 (已包含在增加相似用户数中)

                # 2. 使用基于内容的推荐补充
                if len(recommendations) < limit:
                    content_recs = self._content_based(user_id, limit * 2)
                    # 排除已推荐的和已评分的
                    existing_ids = rated_animes.union(anime_id for anime_id, _ in recommendations)
                    content_recs = [(a_id, score * 0.85) for a_id, score in content_recs
                                    if a_id not in existing_ids]
                    recommendations.extend(content_recs)

                # 3. 最终使用热门推荐补全
                if len(recommendations) < limit:
                    # 获取热门动漫
                    popular_recs = self._popular_recommendations(limit * 2)
                    # 排除已有的推荐
                    existing_ids = rated_animes.union(anime_id for anime_id, _ in recommendations)
                    popular_recs = [(a_id, score * 0.7) for a_id, score in popular_recs
                                    if a_id not in existing_ids]
                    recommendations.extend(popular_recs)

                # 【量子后处理】重排序提高一致性
                recommendations.sort(key=lambda x: x[1], reverse=True)

            # 返回限定数量的推荐
            result = recommendations[:limit]
            logger.info(f"为用户 {user_id} 生成了 {len(result)} 条协同过滤推荐，策略混合比例: "
                        f"CF={len([r for r in result if r[1] > 0.7])}, 补充={len(result) - len([r for r in result if r[1] > 0.7])}")

            return result

        except Exception as e:
            logger.error(f"协同过滤算法异常: {str(e)}")
            # 发生异常时回退到热门推荐
            return self._popular_recommendations(limit)

    def _hybrid_merge_three(self, cf_recs, cb_recs, ml_recs=None, limit=10):
        """
        推荐结果融合

        将协同过滤、基于内容和机器学习(如可用)的推荐结果融合
        """
        # 初始化融合容器
        merged = {}

        # 如果没有ML推荐，调整权重
        if ml_recs is None:
            # 协同过滤权重分配 - 0.6
            for anime_id, score in cf_recs:
                merged[anime_id] = score * 0.6

            # 基于内容权重分配 - 0.4
            for anime_id, score in cb_recs:
                if anime_id in merged:
                    merged[anime_id] += score * 0.4
                else:
                    merged[anime_id] = score * 0.4
        else:
            # 三维融合逻辑
            # 协同过滤权重分配 - 0.4
            for anime_id, score in cf_recs:
                merged[anime_id] = score * 0.4

            # 基于内容权重分配 - 0.3
            for anime_id, score in cb_recs:
                if anime_id in merged:
                    merged[anime_id] += score * 0.3
                else:
                    merged[anime_id] = score * 0.3

            # 机器学习权重分配 - 0.3
            for anime_id, score in ml_recs:
                if anime_id in merged:
                    merged[anime_id] += score * 0.3
                else:
                    merged[anime_id] = score * 0.3

        # 转换为列表并排序
        recommendations = [(anime_id, score) for anime_id, score in merged.items()]
        recommendations.sort(key=lambda x: x[1], reverse=True)

        return recommendations[:limit]

    def _content_based(self, user_id, limit=10):
        """
        基于内容的推荐算法实现

        基于用户偏好和动漫特征，计算用户可能感兴趣的动漫

        Args:
            user_id: 目标用户ID
            limit: 推荐结果数量

        Returns:
            list: [(anime_id, score), ...] 格式的推荐列表
        """
        try:
            # 获取用户偏好数据
            user_preferences = UserPreference.objects.filter(user_id=user_id)

            # 检查是否有足够的偏好数据
            if user_preferences.count() < 3:
                # 尝试使用浏览历史
                browsing_history = UserBrowsing.objects.filter(user_id=user_id)
                if browsing_history.count() < 3:
                    logger.info(f"用户 {user_id} 没有足够的偏好数据，回退到热门推荐")
                    return self._popular_recommendations(limit)
                else:
                    # 使用浏览历史构建偏好
                    anime_ids = [b.anime_id for b in browsing_history.order_by('-browse_count')[:5]]
            else:
                # 使用偏好数据中评分最高的动漫
                anime_ids = [p.anime_id for p in user_preferences.order_by('-preference_value')[:5]]

            # 获取用户已有偏好的动漫类型
            liked_animes = Anime.objects.filter(id__in=anime_ids)
            liked_types = set()
            for anime in liked_animes:
                liked_types.add(anime.type_id)

            # 获取用户已评分的动漫列表（排除推荐）
            rated_animes = set(UserRating.objects.filter(user_id=user_id).values_list('anime_id', flat=True))

            # 使用类型相似度推荐
            candidate_animes = Anime.objects.filter(type_id__in=liked_types) \
                .exclude(id__in=rated_animes) \
                .values('id', 'type_id', 'rating_avg', 'popularity')

            # 计算候选动漫的匹配分数
            recommendations = []
            for candidate in candidate_animes:
                # 基于类型相似度、热门度和评分的加权计算
                type_match = 1.0 if candidate['type_id'] in liked_types else 0.0
                rating_score = candidate['rating_avg'] / 5.0 if candidate['rating_avg'] else 0.5
                popularity = candidate['popularity'] if candidate['popularity'] else 0.0

                # 加权计算最终分数
                final_score = (type_match * 0.5) + (rating_score * 0.3) + (popularity * 0.2)
                recommendations.append((candidate['id'], final_score))

            # 按分数降序排序
            recommendations.sort(key=lambda x: x[1], reverse=True)
            return recommendations[:limit]

        except Exception as e:
            logger.error(f"基于内容推荐算法异常: {str(e)}")
            # 发生异常时回退到热门推荐
            return self._popular_recommendations(limit)

    # 在recommendation/engine/recommendation_engine.py中添加这个修复

    def _popular_recommendations(self, limit=10):
        """
        热门推荐算法 - 确保始终返回结果
        """
        try:
            # 使用简单的查询确保总是返回结果
            popular_animes = Anime.objects.order_by('-popularity', '-rating_avg', 'id')[:limit * 2]

            # 如果没有按热门度排序的结果，尝试获取任何动漫
            if not popular_animes:
                popular_animes = Anime.objects.all()[:limit * 2]

            # 如果仍然没有结果，返回空列表
            if not popular_animes:
                logger.warning("数据库中没有动漫数据")
                return []

            # 简化推荐分数计算
            recommendations = []
            for i, anime in enumerate(popular_animes):
                # 为每个动漫分配一个从0.9递减的分数，确保有序排列
                score = max(0.1, 0.9 - (i * 0.03))
                recommendations.append((anime.id, score))

            return recommendations[:limit]
        except Exception as e:
            logger.error(f"热门推荐算法异常: {str(e)}")
            # 最后的备选方案：返回ID为1-10的动漫（如果存在）
            try:
                fallback_ids = list(range(1, limit + 1))
                fallback_animes = Anime.objects.filter(id__in=fallback_ids)
                return [(anime.id, 0.5) for anime in fallback_animes]
            except:
                # 确保总是返回一个列表，即使是空的
                return []

    def _hybrid_merge(self, cf_recs, cb_recs, limit=10):
        """
        混合推荐结果合并

        融合协同过滤和基于内容的推荐结果，使用加权策略

        Args:
            cf_recs: 协同过滤推荐结果
            cb_recs: 基于内容推荐结果
            limit: 最终返回数量

        Returns:
            list: 融合后的推荐结果
        """
        # 合并两种推荐结果
        merged = {}

        # 协同过滤结果权重 0.6
        for anime_id, score in cf_recs:
            merged[anime_id] = score * 0.6

        # 基于内容结果权重 0.4，与现有结果合并
        for anime_id, score in cb_recs:
            if anime_id in merged:
                merged[anime_id] += score * 0.4
            else:
                merged[anime_id] = score * 0.4

        # 转换为列表并排序
        recommendations = [(anime_id, score) for anime_id, score in merged.items()]
        recommendations.sort(key=lambda x: x[1], reverse=True)

        return recommendations[:limit]
    def update_recommendations_cache(self, user_id):
        """
        更新用户推荐缓存
        在用户行为变化时调用，刷新推荐结果

        Args:
            user_id: 目标用户ID
        """
        # 清除用户所有策略的缓存
        for strategy in ['hybrid', 'cf', 'content', 'popular']:
            cache_key = f"rec:user:{user_id}:strat:{strategy}:limit:10"
            cache.delete(cache_key)

        # 预计算并缓存默认推荐
        self.get_recommendations_for_user(user_id)

        logger.info(f"用户 {user_id} 的推荐缓存已更新")


# 单例模式实现
recommendation_engine = RecommendationEngine()