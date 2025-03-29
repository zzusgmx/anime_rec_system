/**
 * QuantumExplorationController - 量子态探索引擎
 *
 * 新增：自主CSRF防御机制
 *
 * @version 2.3.8-quantum-autonomous
 */
class ExplorationController {
  constructor(dashboardController) {
    // 保存但不强依赖dashboardController
    this.dashboardController = dashboardController;

    // 量子缓存配置
    this.CACHE_TTL = 10 * 60 * 1000; // 缓存有效期: 10分钟
    this.CACHE_STALE_WHILE_REVALIDATE = true; // 过期缓存仍可使用并在后台刷新

    // API端点映射
    this.API_ENDPOINTS = {
      seasonal: '/recommendations/api/dashboard/seasonal/',
      similar: '/recommendations/api/dashboard/similar/',
      classics: '/recommendations/api/dashboard/classics/'
    };

    // 量子态管理 - 多层状态处理
    this.state = {
      seasonal: this._createInitialState(),
      similar: this._createInitialState(),
      classics: this._createInitialState()
    };

    // DOM节点引用缓存 - 修复映射关系
    this.DOM = {
      containers: {
        seasonal: document.getElementById('seasonal'),
        similar: document.getElementById('similar'),
        // 关键修复：保持键名与实际DOM ID映射一致
        classic: document.getElementById('classic')
      },
      tabs: {
        seasonal: document.getElementById('seasonal-tab'),
        similar: document.getElementById('similar-tab'),
        classic: document.getElementById('classic-tab')
      }
    };

    // 渲染配置
    this.renderConfig = {
      fadeInClass: 'quantum-fade-in',
      errorRetryDelay: 3000,
      parallelLoadThreshold: 3, // 并行加载阈值
      transitionDuration: 350,
      animationStaggerDelay: 50
    };

    // 请求状态控制
    this.requestController = {
      lock: false,
      queue: [],
      debounceTimeout: null,
      abortControllers: new Map(),
      maxRetries: 2
    };

    // 注入样式
    this._injectStyles();

    console.log(`[QUANTUM-EXPLORER] 初始化完成 | 构建版本: ${this.constructor.VERSION} [自主防御模式]`);
  }

  // 静态版本信息
  static get VERSION() { return '2.3.8-quantum-autonomous'; }

  /**
   * 获取CSRF令牌 - 自主模式
   * @returns {string} CSRF令牌
   * @private
   */
  _getCsrfToken() {
    // 方法1: 从隐藏字段获取
    const csrfElement = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (csrfElement) {
      return csrfElement.value;
    }

    // 方法2: 从cookie获取
    const csrfCookie = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='));

    if (csrfCookie) {
      return csrfCookie.split('=')[1];
    }

    // 如果无法获取，记录错误并返回空字符串
    console.error('[QUANTUM-ERROR] 无法获取CSRF令牌，请求可能会失败');
    return '';
  }
  _purifyUrl(url) {
  try {
    const urlObj = new URL(url, window.location.origin);

    // 移除已知的不支持参数
    const BLACKLISTED_PARAMS = ['seed_anime_id'];

    BLACKLISTED_PARAMS.forEach(param => {
      urlObj.searchParams.delete(param);
    });

    return urlObj.toString();
  } catch (e) {
    console.warn('[QUANTUM-EXPLORER] URL净化失败，使用原始URL:', e);
    return url;
  }
}
/**
 * 自主CSRF请求包装器
 * 不依赖外部控制器的安全请求方法
 * @param {string} url 请求URL
 * @param {Object} options 请求选项
 * @returns {Promise<Response>} Fetch响应Promise
 */
fetchWithCSRF(url, options = {}) {
  // 净化URL，移除已知不支持的参数
  const purifiedUrl = this._purifyUrl(url);

  // 构建请求头
  const headers = options.headers || {};
  headers['X-CSRFToken'] = this._getCsrfToken();
  headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  headers['X-Requested-With'] = 'XMLHttpRequest';

  // 发送请求
  return fetch(purifiedUrl, {
    ...options,
    headers,
    credentials: 'same-origin'
  });
}

  /**
   * 创建初始状态结构
   * @returns {Object} 初始状态对象
   * @private
   */
  _createInitialState() {
    return {
      // 数据状态
      data: null,
      metadata: null,
      error: null,

      // 加载状态
      loading: false,
      loaded: false,
      retryCount: 0,

      // 缓存状态
      lastFetched: null,
      cacheValid: false,

      // 渲染状态
      renderComplete: false,
      renderVersion: 0
    };
  }

  /**
   * 注入必要的CSS样式
   * @private
   */
  _injectStyles() {
    const styleId = 'quantum-exploration-styles';

    // 避免重复注入
    if (document.getElementById(styleId)) return;

    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
      /* 探索面板样式 */
      .anime-card {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        height: 100%;
      }
      
      .anime-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 20px rgba(0, 0, 0, 0.08);
      }
      
      .anime-card .card-img-top {
        height: 160px;
        object-fit: cover;
        transition: transform 0.5s ease;
        background-color: #f8f9fa;
      }
      
      .anime-card:hover .card-img-top {
        transform: scale(1.05);
      }
      
      .anime-card .card-title {
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        display: -webkit-box;
        -webkit-line-clamp: 1;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      
      .anime-card .card-footer {
        background-color: transparent;
        border-top: 1px solid rgba(0, 0, 0, 0.05);
        padding: 0.75rem;
      }
      
      /* 动画效果 */
      @keyframes quantumFadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      
      .quantum-fade-in {
        animation: quantumFadeIn 0.35s ease-out forwards;
      }
      
      /* 加载占位符效果 */
      .anime-card-placeholder {
        position: relative;
        overflow: hidden;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
        background-color: #f8f9fa;
      }
      
      .anime-card-placeholder::after {
        content: "";
        position: absolute;
        top: 0;
        right: 0;
        bottom: 0;
        left: 0;
        transform: translateX(-100%);
        background-image: linear-gradient(
          90deg,
          rgba(255, 255, 255, 0) 0,
          rgba(255, 255, 255, 0.2) 20%,
          rgba(255, 255, 255, 0.5) 60%,
          rgba(255, 255, 255, 0)
        );
        animation: shimmer 2s infinite;
      }
      
      @keyframes shimmer {
        100% { transform: translateX(100%); }
      }
      
      /* 引用动漫标签样式 */
      .reference-anime-badge {
        transition: all 0.3s ease;
        position: relative;
        z-index: 2;
      }
      
      .reference-anime-badge:hover {
        transform: translateY(-2px);
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
      }
    `;

    document.head.appendChild(style);
  }

  /**
   * 初始化探索控制器
   */
  init() {
    this._bindEvents();
    this._initialLoad();

    return this; // 链式调用支持
  }

  /**
   * 绑定事件监听器
   * @private
   */
  _bindEvents() {
    // 标签切换事件
    Object.entries(this.DOM.tabs).forEach(([type, tab]) => {
      if (!tab) return; // 跳过不存在的DOM元素

      tab.addEventListener('click', () => {
        this._handleTabActivation(type);
      });
    });

    // 监听窗口可见性变化，在用户回到页面时刷新数据
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        this._revalidateStaleCache();
      }
    });

    // 监听网络状态变化
    window.addEventListener('online', () => {
      console.log('[QUANTUM-EXPLORER] 网络连接恢复，重新加载数据');
      this._revalidateStaleCache();
    });
  }

  /**
   * 初始加载内容
   * @private
   */
  _initialLoad() {
    // 立即加载当前活动标签内容
    this._loadActiveTabContent();

    // 延迟预加载其他标签内容
    setTimeout(() => {
      this._preloadInactiveTabsContent();
    }, 2500);
  }

  /**
   * 加载当前活动标签内容
   * @private
   */
  _loadActiveTabContent() {
    // 获取当前活动标签
    const activeTabId = this._getActiveTabId();

    // 根据活动标签加载对应内容
    switch (activeTabId) {
      case 'seasonal-tab':
        this.loadSeasonalAnime();
        break;
      case 'similar-tab':
        this.loadSimilarAnime();
        break;
      case 'classic-tab':  // 修正：使用实际的tab ID
        this.loadClassicAnime();
        break;
      default:
        // 默认加载季节性动漫
        this.loadSeasonalAnime();
    }
  }

  /**
   * 获取当前活动标签ID
   * @returns {string} 活动标签ID
   * @private
   */
  _getActiveTabId() {
    for (const [type, tab] of Object.entries(this.DOM.tabs)) {
      if (tab && tab.classList.contains('active')) {
        return tab.id;
      }
    }

    // 默认返回seasonal标签
    return 'seasonal-tab';
  }

  /**
   * 预加载非活动标签内容
   * @private
   */
  _preloadInactiveTabsContent() {
    const activeTabId = this._getActiveTabId();

    // 按优先级预加载其他标签
    if (activeTabId !== 'seasonal-tab' && !this.state.seasonal.loaded) {
      this._fetchData('seasonal', true);
    }

    if (activeTabId !== 'similar-tab' && !this.state.similar.loaded) {
      this._fetchData('similar', true);
    }

    // 修复：如果classic不是活动标签，加载classics数据
    if (activeTabId !== 'classic-tab' && !this.state.classics.loaded) {
      this._fetchData('classics', true);
    }
  }

  /**
   * 处理标签激活
   * @param {string} type 内容类型
   * @private
   */
  _handleTabActivation(type) {
    // 根据类型加载内容
    switch (type) {
      case 'seasonal':
        this.loadSeasonalAnime();
        break;
      case 'similar':
        this.loadSimilarAnime();
        break;
      case 'classic': // 修复：匹配DOM键名
        this.loadClassicAnime();
        break;
    }
  }

  /**
   * 重新验证过期缓存
   * @private
   */
  _revalidateStaleCache() {
    Object.entries(this.state).forEach(([type, state]) => {
      // 仅对已加载但缓存可能过期的内容进行刷新
      if (state.loaded && this._isCacheStale(state)) {
        this._fetchData(type, true);
      }
    });
  }

  /**
   * 检查缓存是否过期
   * @param {Object} state 状态对象
   * @returns {boolean} 是否过期
   * @private
   */
  _isCacheStale(state) {
    if (!state.lastFetched) return true;

    const now = Date.now();
    return (now - state.lastFetched) > this.CACHE_TTL;
  }

  /**
   * 防抖执行函数
   * @param {Function} fn 要执行的函数
   * @param {number} delay 延迟时间
   * @private
   */
  _debounce(fn, delay = 300) {
    if (this.requestController.debounceTimeout) {
      clearTimeout(this.requestController.debounceTimeout);
    }

    this.requestController.debounceTimeout = setTimeout(() => {
      fn();
      this.requestController.debounceTimeout = null;
    }, delay);
  }

  /* ======== 公共 API 方法 ======== */

  /**
   * 加载季节性动漫
   */
  loadSeasonalAnime() {
    // 如果正在加载，则跳过
    if (this.state.seasonal.loading) return;

    // 如果已加载且缓存有效，直接使用缓存数据
    if (this.state.seasonal.loaded && !this._isCacheStale(this.state.seasonal)) {
      this._renderSeasonalAnime(this.state.seasonal.data);
      return;
    }

    // 如果已加载但缓存过期，使用缓存数据并在后台刷新
    if (this.state.seasonal.loaded && this.CACHE_STALE_WHILE_REVALIDATE) {
      this._renderSeasonalAnime(this.state.seasonal.data);
      this._fetchData('seasonal', true); // 静默刷新
      return;
    }

    // 防抖请求
    this._debounce(() => {
      this._fetchData('seasonal');
    }, 200);
  }

  /**
   * 加载相似动漫
   */
  loadSimilarAnime() {
    // 如果正在加载，则跳过
    if (this.state.similar.loading) return;

    // 如果已加载且缓存有效，直接使用缓存数据
    if (this.state.similar.loaded && !this._isCacheStale(this.state.similar)) {
      this._renderSimilarAnime(this.state.similar.data, this.state.similar.metadata);
      return;
    }

    // 如果已加载但缓存过期，使用缓存数据并在后台刷新
    if (this.state.similar.loaded && this.CACHE_STALE_WHILE_REVALIDATE) {
      this._renderSimilarAnime(this.state.similar.data, this.state.similar.metadata);
      this._fetchData('similar', true); // 静默刷新
      return;
    }

    // 防抖请求
    this._debounce(() => {
      this._fetchData('similar');
    }, 200);
  }

  /**
   * 加载经典动漫
   */
  loadClassicAnime() {
    // 如果正在加载，则跳过
    if (this.state.classics.loading) return;

    // 如果已加载且缓存有效，直接使用缓存数据
    if (this.state.classics.loaded && !this._isCacheStale(this.state.classics)) {
      this._renderClassicAnime(this.state.classics.data);
      return;
    }

    // 如果已加载但缓存过期，使用缓存数据并在后台刷新
    if (this.state.classics.loaded && this.CACHE_STALE_WHILE_REVALIDATE) {
      this._renderClassicAnime(this.state.classics.data);
      this._fetchData('classics', true); // 静默刷新
      return;
    }

    // 防抖请求
    this._debounce(() => {
      this._fetchData('classics');
    }, 200);
  }

/**
 * 获取数据 - v4.3 深度隔离防护版
 * @param {string} type 数据类型
 * @param {boolean} [silent=false] 是否静默加载
 * @private
 */
_fetchData(type, silent = false) {
  // 更新状态
  this.state[type].loading = true;
  this.state[type].error = null;

  // 非静默模式显示加载状态
  if (!silent) {
    // 修复：针对classics类型使用正确的DOM容器引用
    const containerKey = type === 'classics' ? 'classic' : type;
    this._showLoading(this.DOM.containers[containerKey]);
  }

  // 创建AbortController用于取消请求
  const controller = new AbortController();
  this.requestController.abortControllers.set(type, controller);

  // 获取API端点
  const endpoint = this._getApiEndpoint(type);

  // 构建请求参数
  const queryParams = new URLSearchParams();

  // 【量子参数隔离层】- 深度解耦
  switch(type) {
    case 'similar':
      // 使用引擎支持的参数形式
      queryParams.append('recommendation_type', 'similar');
      queryParams.append('strategy', 'content'); // 基于内容的推荐策略
      queryParams.append('limit', '8');
      break;
    case 'seasonal':
      queryParams.append('limit', '8');
      queryParams.append('type', 'seasonal');
      break;
    case 'classics':
      queryParams.append('limit', '8');
      queryParams.append('type', 'classic');
      break;
    default:
      // 默认参数，确保不传递seed_anime_id
      queryParams.append('limit', '8');
  }

  // 构建完整URL
  const requestUrl = endpoint + (queryParams.toString() ? `?${queryParams.toString()}` : '');

  // 使用自主CSRF方法
  this.fetchWithCSRF(requestUrl, {
    method: 'GET',
    signal: controller.signal
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`API错误 (${response.status}): ${response.statusText}`);
    }
    return response.json();
  })
  .then(data => {
    if (data.success) {
      // 清空重试计数
      this.state[type].retryCount = 0;

      // 更新状态
      this.state[type].data = data.data;
      this.state[type].loaded = true;
      this.state[type].lastFetched = Date.now();
      this.state[type].loading = false;

      // 保存元数据
      if (type === 'similar') {
        this.state[type].metadata = data.reference_anime || [];
      }

      // 非静默模式渲染数据
      if (!silent) {
        this._renderData(type, data.data, data.reference_anime);
      }
    } else {
      throw new Error(data.error || `获取${this._getTypeName(type)}失败`);
    }
  })
  .catch(error => {
    // 忽略取消的请求错误
    if (error.name === 'AbortError') {
      console.log(`[QUANTUM-EXPLORER] ${this._getTypeName(type)}请求已取消`);
      return;
    }

    console.error(`[QUANTUM-EXPLORER] 加载${this._getTypeName(type)}失败:`, error);

    // 更新状态
    this.state[type].loading = false;
    this.state[type].error = error.message;

    // 非静默模式显示错误
    if (!silent) {
      // 修复：针对classics类型使用正确的DOM容器引用
      const containerKey = type === 'classics' ? 'classic' : type;
      this._showError(this.DOM.containers[containerKey], error.message);
    }

    // 自动重试
    if (this.state[type].retryCount < this.requestController.maxRetries) {
      this.state[type].retryCount++;

      const retryDelay = Math.pow(2, this.state[type].retryCount) * 1000; // 指数退避
      console.log(`[QUANTUM-EXPLORER] 将在 ${retryDelay}ms 后重试 (${this.state[type].retryCount}/${this.requestController.maxRetries})`);

      setTimeout(() => {
        if (!this.state[type].loaded) {
          this._fetchData(type, silent);
        }
      }, retryDelay);
    }
  })
  .finally(() => {
    // 移除AbortController
    this.requestController.abortControllers.delete(type);
  });
}
  /**
   * 获取API端点
   * @param {string} type 数据类型
   * @returns {string} API端点
   * @private
   */
  _getApiEndpoint(type) {
    // 修复：直接使用API_ENDPOINTS对象，确保正确映射
    return this.API_ENDPOINTS[type];
  }

  /**
   * 获取类型名称
   * @param {string} type 数据类型
   * @returns {string} 类型名称
   * @private
   */
  _getTypeName(type) {
    const names = {
      seasonal: '本季新番',
      similar: '相似推荐',
      classics: '经典动漫'
    };

    return names[type] || type;
  }

  /**
   * 渲染数据
   * @param {string} type 数据类型
   * @param {Array} data 数据
   * @param {Array} [metadata] 元数据
   * @private
   */
  _renderData(type, data, metadata) {
    switch (type) {
      case 'seasonal':
        this._renderSeasonalAnime(data);
        break;
      case 'similar':
        this._renderSimilarAnime(data, metadata);
        break;
      case 'classics':
        this._renderClassicAnime(data);
        break;
    }
  }

  /* ======== 渲染方法 ======== */

  /**
   * 渲染季节性动漫
   * @param {Array} animes 季节性动漫数据
   * @private
   */
  _renderSeasonalAnime(animes) {
    const container = this.DOM.containers.seasonal;
    if (!container) return;

    // 增加渲染版本，防止竞态条件
    this.state.seasonal.renderVersion++;
    const currentVersion = this.state.seasonal.renderVersion;

    // 检查数据
    if (!animes || animes.length === 0) {
      this._showEmpty(container, '暂无本季新番');
      return;
    }

    let html = '<div class="row row-cols-1 row-cols-md-4 g-3">';

    animes.forEach((anime, index) => {
      // 构建安全URL
      const imageUrl = anime.image || '/static/images/default-cover.jpg';
      const animeUrl = anime.slug ? `/anime/${anime.slug}/` : `/anime/${anime.id}/`;

      html += `
        <div class="col ${this.renderConfig.fadeInClass}" style="animation-delay: ${index * this.renderConfig.animationStaggerDelay}ms">
          <div class="card h-100 anime-card">
            <div class="position-relative">
              <span class="position-absolute top-0 end-0 badge bg-primary m-2">新番</span>
              <img src="${imageUrl}" class="card-img-top" alt="${anime.title}" loading="lazy" 
                   onerror="this.src='/static/images/default-cover.jpg'">
            </div>
            <div class="card-body">
              <h5 class="card-title">${anime.title}</h5>
              <div class="text-muted small">类型: ${anime.type || '未分类'}</div>
              <div class="text-muted small">发布日期: ${anime.release_date || '未知'}</div>
            </div>
            <div class="card-footer">
              <a href="${animeUrl}" class="btn btn-sm btn-outline-primary w-100">
                <i class="fas fa-external-link-alt me-1"></i>查看详情
              </a>
            </div>
          </div>
        </div>
      `;
    });

    html += '</div>';

    // 更新DOM
    container.innerHTML = html;

    // 初始化延迟加载
    this._initLazyLoading(container);

    // 更新渲染状态
    this.state.seasonal.renderComplete = true;
  }

  /**
   * 渲染相似动漫
   * @param {Array} animes 相似动漫数据
   * @param {Array} referenceAnimes 参考动漫数据
   * @private
   */
  _renderSimilarAnime(animes, referenceAnimes) {
    const container = this.DOM.containers.similar;
    if (!container) return;

    // 增加渲染版本
    this.state.similar.renderVersion++;

    // 检查数据
    if (!animes || animes.length === 0) {
      let message = '暂无相似推荐';

      if (!referenceAnimes || referenceAnimes.length === 0) {
        message = '您需要先评分一些动漫才能获得相似推荐';
      } else {
        message = '没有找到相似的动漫，尝试评分更多动漫以获得推荐';
      }

      this._showEmpty(container, message);
      return;
    }

    // 首先展示参考动漫
    let referenceBadges = '';
    if (referenceAnimes && referenceAnimes.length > 0) {
      referenceBadges = `
        <div class="d-flex align-items-center mb-3 ${this.renderConfig.fadeInClass}">
          <div class="me-3">因为您喜欢:</div>
          <div class="d-flex flex-wrap gap-2">
      `;

      referenceAnimes.forEach(anime => {
        const animeUrl = anime.slug ? `/anime/${anime.slug}/` : `/anime/${anime.id}/`;
        referenceBadges += `<a href="${animeUrl}" class="badge bg-secondary text-decoration-none reference-anime-badge">${anime.title}</a>`;
      });

      referenceBadges += '</div></div>';
    }

    // 构建推荐动漫卡片
    let html = referenceBadges + '<div class="row row-cols-1 row-cols-md-4 g-3">';

    animes.forEach((anime, index) => {
      // 构建安全URL
      const imageUrl = anime.image || '/static/images/default-cover.jpg';
      const animeUrl = anime.slug ? `/anime/${anime.slug}/` : `/anime/${anime.id}/`;

      html += `
        <div class="col ${this.renderConfig.fadeInClass}" style="animation-delay: ${index * this.renderConfig.animationStaggerDelay}ms">
          <div class="card h-100 anime-card">
            <img src="${imageUrl}" class="card-img-top" alt="${anime.title}" loading="lazy"
                 onerror="this.src='/static/images/default-cover.jpg'">
            <div class="card-body">
              <h5 class="card-title">${anime.title}</h5>
              <div class="text-muted small">类型: ${anime.type || '未分类'}</div>
            </div>
            <div class="card-footer">
              <a href="${animeUrl}" class="btn btn-sm btn-outline-primary w-100">
                <i class="fas fa-external-link-alt me-1"></i>查看详情
              </a>
            </div>
          </div>
        </div>
      `;
    });

    html += '</div>';

    // 更新DOM
    container.innerHTML = html;

    // 初始化延迟加载
    this._initLazyLoading(container);

    // 更新渲染状态
    this.state.similar.renderComplete = true;
  }

  /**
   * 渲染经典动漫
   * @param {Array} animes 经典动漫数据
   * @private
   */
  _renderClassicAnime(animes) {
    // 修复：使用正确的DOM容器引用
    const container = this.DOM.containers.classic;
    if (!container) {
      console.error('[QUANTUM-ERROR] 经典动漫容器不存在，DOM量子状态异常');
      return;
    }

    // 增加渲染版本
    this.state.classics.renderVersion++;

    // 检查数据
    if (!animes || animes.length === 0) {
      this._showEmpty(container, '暂无经典动漫数据');
      return;
    }

    let html = '<div class="row row-cols-1 row-cols-md-4 g-3">';

    animes.forEach((anime, index) => {
      // 构建安全URL
      const imageUrl = anime.image || '/static/images/default-cover.jpg';
      const animeUrl = anime.slug ? `/anime/${anime.slug}/` : `/anime/${anime.id}/`;

      // 评分标签
      const ratingBadge = anime.rating ?
        `<span class="position-absolute top-0 end-0 badge bg-warning m-2">
          <i class="fas fa-star me-1"></i>${anime.rating.toFixed(1)}
        </span>` : '';

      html += `
        <div class="col ${this.renderConfig.fadeInClass}" style="animation-delay: ${index * this.renderConfig.animationStaggerDelay}ms">
          <div class="card h-100 anime-card">
            <div class="position-relative">
              ${ratingBadge}
              <img src="${imageUrl}" class="card-img-top" alt="${anime.title}" loading="lazy"
                   onerror="this.src='/static/images/default-cover.jpg'">
            </div>
            <div class="card-body">
              <h5 class="card-title">${anime.title}</h5>
              <div class="text-muted small">类型: ${anime.type || '未分类'}</div>
            </div>
            <div class="card-footer">
              <a href="${animeUrl}" class="btn btn-sm btn-outline-primary w-100">
                <i class="fas fa-external-link-alt me-1"></i>查看详情
              </a>
            </div>
          </div>
        </div>
      `;
    });

    html += '</div>';

    // 更新DOM
    container.innerHTML = html;

    // 初始化延迟加载
    this._initLazyLoading(container);

    // 更新渲染状态
    this.state.classics.renderComplete = true;
  }

  /**
   * 初始化图片懒加载
   * @param {Element} container DOM容器
   * @private
   */
  _initLazyLoading(container) {
    if (!container) return;

    const lazyImages = container.querySelectorAll('img[loading="lazy"]');

    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            const src = img.dataset.src || img.src;

            // 加载图片
            if (src) img.src = src;

            // 移除观察
            imageObserver.unobserve(img);
          }
        });
      }, {
        rootMargin: '50px 0px',
        threshold: 0.1
      });

      lazyImages.forEach(img => {
        imageObserver.observe(img);
      });
    } else {
      // 降级处理
      lazyImages.forEach(img => {
        const src = img.dataset.src || img.src;
        if (src) img.src = src;
      });
    }
  }

  /* ======== UI状态显示方法 ======== */

  /**
   * 显示加载状态
   * @param {Element} container DOM容器
   * @private
   */
  _showLoading(container) {
    if (!container) return;

    container.innerHTML = `
      <div class="text-center py-5">
        <div class="quantum-spinner"></div>
        <p class="mt-3">量子态同步中...</p>
      </div>
    `;
  }

  /**
   * 显示错误状态
   * @param {Element} container DOM容器
   * @param {string} message 错误信息
   * @private
   */
  _showError(container, message) {
    if (!container) return;

    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">
          <i class="fas fa-exclamation-triangle text-warning"></i>
        </div>
        <h5>数据获取失败</h5>
        <p>${message || '请稍后再试'}</p>
        <button class="btn btn-primary mt-2 rounded-pill reload-btn">
          <i class="fas fa-sync-alt me-1"></i>重新加载
        </button>
      </div>
    `;

    // 为重新加载按钮添加事件
    const reloadBtn = container.querySelector('.reload-btn');
    if (reloadBtn) {
      reloadBtn.addEventListener('click', () => {
        // 确定加载的内容类型
        for (const [type, cont] of Object.entries(this.DOM.containers)) {
          if (cont === container) {
            // 对应方法调用
            if (type === 'seasonal') this.loadSeasonalAnime();
            else if (type === 'similar') this.loadSimilarAnime();
            else if (type === 'classic') this.loadClassicAnime(); // 修复: 匹配DOM键名
            break;
          }
        }
      });
    }
  }

  /**
   * 显示空状态
   * @param {Element} container DOM容器
   * @param {string} message 提示信息
   * @private
   */
  _showEmpty(container, message) {
    if (!container) return;

    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">
          <i class="fas fa-film"></i>
        </div>
        <h5>暂无数据</h5>
        <p>${message || '暂无相关数据'}</p>
      </div>
    `;
  }
}