// 量子态推荐引擎 - 分页增强版
// 重构核心API通信层，支持分页参数传递和状态维护

class QuantumRecommendationEngine {
  constructor() {
    // 核心配置
    this.apiEndpoint = '/recommendations/api/recommendations/';
    this.cache = new Map();
    this.pendingRequests = new Map();
    this.fallbackRecommendations = {}; // 备用数据存储

    // 分页状态存储
    this.paginationState = {
      currentPage: 1,
      totalPages: 1,
      totalItems: 0,
      itemsPerPage: 12, // 默认每页12项
      strategy: 'hybrid' // 默认策略
    };

    this.initializeFallbackData();
    console.log("[QUANTUM-ENGINE] 量子态推荐引擎初始化完成，分页模块已激活");
  }

  initializeFallbackData() {
    // 预填充备用推荐数据，以防API失败时使用
    this.fallbackRecommendations = {
      'hybrid': this.generateFallbackData('hybrid'),
      'cf': this.generateFallbackData('cf'),
      'content': this.generateFallbackData('content'),
      'ml': this.generateFallbackData('ml'),
      'popular': this.generateFallbackData('popular')
    };
  }

  generateFallbackData(strategy) {
    // 根据策略生成相应类型的备用数据
    const baseTitles = {
      'hybrid': ['多维度推荐动漫', '混合算法精选', '量子推荐热门作品', '个性化精选'],
      'cf': ['猜你喜欢', '相似用户也在看', '基于你的口味', '协同算法推荐'],
      'content': ['相似内容推荐', '同类型精选', '风格相似作品', '主题相关作品'],
      'ml': ['AI精选', '深度学习推荐', '智能算法发现', 'GBDT模型推荐'],
      'popular': ['本周热门', '大家都在看', '最受欢迎', '流行趋势']
    };

    const titles = baseTitles[strategy] || baseTitles.hybrid;

    return titles.map((title, index) => ({
      id: 1000 + index,
      title: title,
      cover_url: `/static/images/default-cover.jpg`,
      rating: (4 + Math.random()).toFixed(1),
      score: Math.floor(70 + Math.random() * 25),
      url: '/anime/list/'
    }));
  }

  /**
   * 获取指定策略和页码的动漫推荐
   * @param {string} strategy - 推荐策略: hybrid|cf|content|ml|popular
   * @param {number} page - 页码
   * @param {number} limit - 每页显示数量
   * @returns {Promise<Object>} 包含推荐结果和分页信息的对象
   */
  async getRecommendations(strategy = 'hybrid', page = 1, limit = 12) {
    // 参数验证和标准化
    if (!strategy || strategy === 'undefined') {
      console.warn('[QUANTUM-WARNING] 策略参数无效，量子回退至默认hybrid策略');
      strategy = 'hybrid';
    }

    page = parseInt(page) || 1;
    limit = parseInt(limit) || 12;

    if (page < 1) page = 1;
    if (limit > 50) limit = 50; // 防止过载查询

    // 构建缓存键 - 包含分页信息
    const cacheKey = `${strategy}:${page}:${limit}`;

    // 检查是否有相同请求正在进行中
    if (this.pendingRequests.has(cacheKey)) {
      return this.pendingRequests.get(cacheKey);
    }

    // 检查缓存
    if (this.cache.has(cacheKey)) {
      return Promise.resolve(this.cache.get(cacheKey));
    }

    // 创建新请求
    const requestPromise = new Promise(async (resolve, reject) => {
      try {
        const params = new URLSearchParams({
          strategy: strategy,
          page: page,
          limit: limit
        });

        console.log(`[QUANTUM-REQUEST] 发起分页量子请求: ${this.apiEndpoint}?${params.toString()}`);

        const response = await fetch(`${this.apiEndpoint}?${params.toString()}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          },
          credentials: 'same-origin'
        });

        if (!response.ok) {
          console.warn(`[QUANTUM-ERROR] API请求失败 (${response.status}): ${response.statusText}`);
          // 构建应急响应
          return resolve(this._buildFallbackResponse(strategy, page, limit));
        }

        const data = await response.json();

        if (!data.success) {
          console.warn(`[QUANTUM-ERROR] API返回错误: ${data.message || '未知错误'}`);
          return resolve(this._buildFallbackResponse(strategy, page, limit));
        }

        // 保存分页状态
        this.paginationState = {
          currentPage: page,
          totalPages: data.pagination?.total_pages || 1,
          totalItems: data.pagination?.total_items || 0,
          itemsPerPage: limit,
          strategy: strategy
        };

        // 构建完整响应
        const result = {
          recommendations: data.recommendations || [],
          pagination: {
            current_page: page,
            total_pages: data.pagination?.total_pages || 1,
            total_items: data.pagination?.total_items || 0,
            items_per_page: limit,
            has_next: page < (data.pagination?.total_pages || 1),
            has_previous: page > 1
          }
        };

        // 缓存结果 (5分钟过期)
        this.cache.set(cacheKey, result);
        setTimeout(() => this.cache.delete(cacheKey), 5 * 60 * 1000);

        resolve(result);
      } catch (error) {
        console.error('[QUANTUM-CRITICAL] 推荐引擎故障:', error);
        // 错误恢复: 使用备用数据
        resolve(this._buildFallbackResponse(strategy, page, limit));
      } finally {
        this.pendingRequests.delete(cacheKey);
      }
    });

    // 存储到pending请求
    this.pendingRequests.set(cacheKey, requestPromise);

    return requestPromise;
  }

  /**
   * 构建备用响应数据
   * @private
   */
  _buildFallbackResponse(strategy, page, limit) {
    const fallbackItems = this.fallbackRecommendations[strategy] || this.fallbackRecommendations.hybrid;
    // 假设总共有50项可分页内容
    const totalItems = 50;
    const totalPages = Math.ceil(totalItems / limit);

    // 模拟分页
    const start = (page - 1) * limit;
    const end = Math.min(start + limit, totalItems);

    // 循环使用有限的备用数据
    const recommendations = [];
    for (let i = start; i < end; i++) {
      const index = i % fallbackItems.length;
      const item = {...fallbackItems[index]};
      item.id = 1000 + i; // 确保ID唯一
      item.title = `${item.title} #${i + 1}`; // 确保标题唯一
      recommendations.push(item);
    }

    return {
      recommendations: recommendations,
      pagination: {
        current_page: page,
        total_pages: totalPages,
        total_items: totalItems,
        items_per_page: limit,
        has_next: page < totalPages,
        has_previous: page > 1
      }
    };
  }

  /**
   * 清除引擎缓存
   */
  clearCache() {
    this.cache.clear();
    console.log("[QUANTUM-CACHE] 量子缓存已重置");
  }

  /**
   * 获取当前分页状态
   */
  getPaginationState() {
    return {...this.paginationState};
  }

  /**
   * 获取推荐策略描述
   */
  // 在recommendation-engine.js文件中，修改getStrategyDescription方法
getStrategyDescription(strategy) {
  const descriptions = {
    'hybrid': {
      title: '混合推荐',
      icon: 'fa-magic',
      description: '量子混合算法结合了多种推荐策略，综合考虑用户偏好和内容相似性，提供最全面的推荐结果。',
      className: 'icon-hybrid'
    },
    'cf': {
      title: '协同过滤',
      icon: 'fa-users',
      description: '协同过滤基于"相似的用户喜欢相似的动漫"原理，通过分析用户行为模式发现隐藏的关联。',
      className: 'icon-cf'
    },
    'content': {
      title: '基于内容推荐',
      icon: 'fa-tags',
      description: '内容推荐基于动漫的特征相似度，分析类型、风格、制作公司等元数据，推荐风格相似的作品。',
      className: 'icon-content'
    },
    'ml': {
      title: '机器学习增强推荐',
      icon: 'fa-brain',
      description: '使用模型对比选出的最佳模型（包括GBDT/XGBoost/LightGBM/神经网络），从复杂的用户-动漫交互数据中学习深层次模式。',
      className: 'icon-ml'
    },
    'popular': {
      title: '热门推荐',
      icon: 'fa-fire',
      description: '热门推荐基于全网用户的集体智慧，展示当前最受欢迎的动漫作品。',
      className: 'icon-popular'
    }
  };

  return descriptions[strategy] || descriptions['hybrid'];
}
}

// 创建单例实例
window.recommendationEngine = new QuantumRecommendationEngine();