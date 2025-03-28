// 量子态推荐引擎 - 完全重构版
// 增强错误处理、备用数据机制和缓存策略

class QuantumRecommendationEngine {
  constructor() {
    // 确保API端点路径正确
    this.apiEndpoint = '/recommendations/api/recommendations/';
    this.cache = new Map();
    this.pendingRequests = new Map();
    this.fallbackRecommendations = {}; // 为每种策略准备备用数据
    this.initializeFallbackData();

    console.log("量子态推荐引擎初始化完成");
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
      cover_url: `/static/images/default-cover.jpg`, // 使用确认存在的默认图片
      rating: (4 + Math.random()).toFixed(1),
      score: Math.floor(70 + Math.random() * 25),
      url: '/anime/list/'
    }));
  }

  /**
   * 获取指定策略的动漫推荐
   * @param {string} strategy - 推荐策略: hybrid|cf|content|ml|popular
   * @param {number} limit - 返回结果数量限制
   * @returns {Promise<Array>} 推荐结果数组
   */
  async getRecommendations(strategy = 'hybrid', limit = 8) {
    // 确保策略是有效的
    if (!strategy || strategy === 'undefined') {
      console.warn('策略参数无效，使用默认hybrid策略');
      strategy = 'hybrid';
    }

    // 构建缓存键
    const cacheKey = `${strategy}:${limit}`;

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
          limit: limit
        });

        console.log(`正在请求推荐API: ${this.apiEndpoint}?${params.toString()}`);

        const response = await fetch(`${this.apiEndpoint}?${params.toString()}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          },
          credentials: 'same-origin' // 确保发送认证cookies
        });

        if (!response.ok) {
          // 如果API请求失败，使用备用数据
          console.warn(`API请求失败 (${response.status}): ${response.statusText}`);
          console.log('使用备用推荐数据');
          return resolve(this.fallbackRecommendations[strategy] || this.fallbackRecommendations.hybrid);
        }

        const data = await response.json();

        if (!data.success) {
          console.warn(`API返回错误: ${data.message || '未知错误'}`);
          return resolve(this.fallbackRecommendations[strategy] || this.fallbackRecommendations.hybrid);
        }

        // 缓存结果 (5分钟过期)
        this.cache.set(cacheKey, data.recommendations);
        setTimeout(() => this.cache.delete(cacheKey), 5 * 60 * 1000);

        resolve(data.recommendations);
      } catch (error) {
        console.error('量子推荐引擎故障:', error);
        // 错误恢复: 使用备用数据而不是拒绝promise
        resolve(this.fallbackRecommendations[strategy] || this.fallbackRecommendations.hybrid);
      } finally {
        this.pendingRequests.delete(cacheKey);
      }
    });

    // 存储到pending请求
    this.pendingRequests.set(cacheKey, requestPromise);

    return requestPromise;
  }

  /**
   * 清除引擎缓存
   */
  clearCache() {
    this.cache.clear();
    console.log("推荐引擎缓存已清除");
  }

  /**
   * 获取推荐策略描述
   */
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
        title: '基于GBDT的机器学习推荐',
        icon: 'fa-brain',
        description: '梯度提升决策树(GBDT)是一种强大的机器学习算法，能够从复杂的用户-动漫交互数据中学习深层次模式。',
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
const recommendationEngine = new QuantumRecommendationEngine();