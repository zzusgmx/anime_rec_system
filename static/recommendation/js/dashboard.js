// █████████████████████████████████████████████
// ████ 量子态动漫仪表盘控制器 - QUANTUM FORK ████
// █████████████████████████████████████████████

// ======== [STRATUM-0] TOKEN管理层 ========
// 获取CSRF Token - 安全通信基础设施
function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
         document.cookie.split('; ')
             .find(row => row.startsWith('csrftoken='))
             ?.split('=')[1];
}

// 确保所有fetch请求都包含CSRF令牌 - 基于零信任架构
function fetchWithCSRF(url, options = {}) {
  const headers = options.headers || {};
  headers['X-CSRFToken'] = getCsrfToken();
  headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  headers['X-Requested-With'] = 'XMLHttpRequest';

  return fetch(url, {
    ...options,
    headers,
    credentials: 'same-origin'
  });
}

class DashboardController {
  constructor() {
    this.currentStrategy = 'hybrid';
    this.userData = null;
    this.isLoading = {
      recommendations: false,
      ratings: false,
      comments: false
    };

    // API端点映射表 - 服务发现层
    this.apiEndpoints = {
      recommendations: '/recommendations/api/dashboard/recommendations/',
      ratings: '/recommendations/api/dashboard/ratings/',
      comments: '/recommendations/api/dashboard/comments/',
      userStats: '/recommendations/api/dashboard/user-stats/'
    };

    console.log("[QUANTUM] 量子态仪表盘控制器初始化完成");
    this.initEventListeners();
  }

  // ======== [STRATUM-1] 事件监听层 ========
  // 初始化事件监听器 - 反应式架构核心
  initEventListeners() {
    // 推荐策略选择器
    document.querySelectorAll('.strategy-selector').forEach(selector => {
      selector.addEventListener('click', (event) => {
        event.preventDefault();
        const strategy = selector.dataset.strategy;
        this.loadRecommendations(strategy);
      });
    });

    // 确保DOM中有userStats元素才初始化统计数据动画
    if (document.getElementById('userStats')) {
      this.initStatsAnimation();
    }
  }

  // 初始化用户统计动画 - 视觉反馈系统
  initStatsAnimation() {
    const statItems = document.querySelectorAll('#userStats .stat-item');

    statItems.forEach(item => {
      const type = item.dataset.type;
      const display = item.querySelector('.stat-number');
      const targetValue = parseInt(display.textContent, 10);

      if (!isNaN(targetValue) && targetValue > 0) {
        // 保存目标值
        display.dataset.target = targetValue;
        // 重置显示值
        display.textContent = '0';

        // 延迟执行动画
        setTimeout(() => {
          this.animateNumber(display, targetValue);
        }, 500);
      }
    });
  }

  // 数字增长动画 - 平滑的视觉转换
  animateNumber(element, target, duration = 1500) {
    const start = parseInt(element.textContent, 10) || 0;
    const increment = Math.max(1, Math.floor((target - start) / (duration / 50)));
    let current = start;

    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        element.textContent = target;
        clearInterval(timer);
      } else {
        element.textContent = current;
      }
    }, 50);
  }

  // ======== [STRATUM-2] 数据获取层 ========
  // 加载推荐数据 - 量子推荐引擎接口
  loadRecommendations(strategy = 'hybrid') {
    if (this.isLoading.recommendations) return;

    this.currentStrategy = strategy;
    this.isLoading.recommendations = true;

    // 更新活动策略
    this.updateActiveStrategy(strategy);

    // 显示加载状态
    const container = document.getElementById('recommendationContainer');
    if (!container) {
      console.error('[QUANTUM-ERROR] 推荐容器节点不存在');
      this.isLoading.recommendations = false;
      return;
    }

    container.innerHTML = `
      <div class="loading-container">
        <div class="quantum-spinner"></div>
        <p class="mt-3">量子态计算中...</p>
      </div>
    `;

    // 构建API URL
    const url = `${this.apiEndpoints.recommendations}?strategy=${strategy}&limit=4`;

    // 发起API请求
    fetchWithCSRF(url, {
      method: 'GET'
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`API错误 (${response.status}): ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.success) {
        this.renderRecommendations(data.recommendations);
      } else {
        throw new Error(data.error || '获取推荐失败');
      }
    })
    .catch(error => {
      console.error('[QUANTUM-ERROR] 加载推荐失败:', error);
      this.showRecommendationError(error.message);
    })
    .finally(() => {
      this.isLoading.recommendations = false;
    });
  }

  // 更新活动策略 - UI状态同步
  updateActiveStrategy(strategy) {
    document.querySelectorAll('.strategy-selector').forEach(selector => {
      if (selector.dataset.strategy === strategy) {
        selector.classList.add('active');
      } else {
        selector.classList.remove('active');
      }
    });
  }

  // ======== [STRATUM-3] 渲染层 ========
  // 渲染推荐 - 高性能UI映射
  renderRecommendations(recommendations) {
    const container = document.getElementById('recommendationContainer');
    if (!container) {
      console.error('[QUANTUM-ERROR] 推荐容器节点不存在');
      return;
    }

    if (!recommendations || recommendations.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">
            <i class="fas fa-film"></i>
          </div>
          <h5>暂无推荐</h5>
          <p>随着您观看更多动漫并进行评分，我们的推荐系统将为您提供更精准的个性化推荐</p>
          <a href="${window.URLS?.animeList || '/anime/list/'}" class="btn btn-primary mt-2 rounded-pill">
            <i class="fas fa-play me-1"></i>浏览动漫
          </a>
        </div>
      `;
      return;
    }

    // 构建推荐卡片
    let html = '';
    recommendations.forEach(anime => {
      // 安全的URL构建 - 防止XSS和undefined值
      const coverUrl = anime.image || `/static/images/default-cover.jpg`;

      // 应用路由解析树进行URL构建
      const animeUrl = this._resolveAnimeUrl(anime);

      html += `
        <div class="rec-card">
          <a href="${animeUrl}">
            <div class="rec-img-container">
              <img src="${coverUrl}" alt="${anime.title}" onerror="this.src='/static/images/no-image.jpg'">
            </div>
          </a>
          <div class="rec-content">
            <h5 class="rec-title" title="${anime.title}">${anime.title}</h5>
            <div class="rec-confidence">
              <div class="d-flex justify-content-between small mb-1">
                <span>匹配度</span>
                <span>${anime.confidence || 0}%</span>
              </div>
              <div class="confidence-bar">
                <div class="confidence-level" style="width: 0%" data-value="${anime.confidence || 0}"></div>
              </div>
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // 添加动画效果
    setTimeout(() => {
      container.querySelectorAll('.confidence-level').forEach((bar) => {
        const confidence = bar.dataset.value;
        bar.style.width = `${confidence}%`;
      });
    }, 100);
  }

  // 显示推荐错误 - 故障恢复机制
  showRecommendationError(message) {
    const container = document.getElementById('recommendationContainer');
    if (!container) return;

    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">
          <i class="fas fa-exclamation-triangle text-warning"></i>
        </div>
        <h5>获取推荐失败</h5>
        <p>${message || '请稍后再试'}</p>
        <button class="btn btn-primary mt-2 rounded-pill" onclick="dashboardController.loadRecommendations('${this.currentStrategy}')">
          <i class="fas fa-sync-alt me-1"></i>重新加载
        </button>
      </div>
    `;
  }

  // 加载用户评分 - 数据聚合层
  loadRatings() {
    if (this.isLoading.ratings) return;

    this.isLoading.ratings = true;
    const container = document.getElementById('ratingsContainer');
    if (!container) {
      console.error('[QUANTUM-ERROR] 评分容器节点不存在');
      this.isLoading.ratings = false;
      return;
    }

    // 显示加载状态
    container.innerHTML = `
      <div class="loading-container">
        <div class="quantum-spinner"></div>
        <p class="mt-3">加载评分记录中...</p>
      </div>
    `;

    // 如果有初始数据，直接使用
    if (typeof initialRatings !== 'undefined' && initialRatings.length > 0) {
      this.renderRatings(initialRatings);
      this.isLoading.ratings = false;
      return;
    }

    // 发起API请求
    fetchWithCSRF(this.apiEndpoints.ratings, {
      method: 'GET'
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`API错误 (${response.status}): ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.success) {
        this.renderRatings(data.ratings);
      } else {
        throw new Error(data.error || '获取评分记录失败');
      }
    })
    .catch(error => {
      console.error('[QUANTUM-ERROR] 加载评分失败:', error);
      this.showRatingsError(error.message);
    })
    .finally(() => {
      this.isLoading.ratings = false;
    });
  }

  // 渲染评分 - 核心修复
  renderRatings(ratings) {
    const container = document.getElementById('ratingsContainer');
    if (!container) {
      console.error('[QUANTUM-ERROR] 评分容器节点不存在');
      return;
    }

    if (!ratings || ratings.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">
            <i class="fas fa-star"></i>
          </div>
          <h5>暂无评分记录</h5>
          <p>您还没有给任何动漫评分，开始评分将帮助我们为您提供更准确的推荐</p>
          <a href="${window.URLS?.animeList || '/anime/list/'}" class="btn btn-primary mt-2 rounded-pill">
            <i class="fas fa-play me-1"></i>开始评分
          </a>
        </div>
      `;
      return;
    }

    // 构建评分列表
    let html = '<div class="activities-list">';
    ratings.forEach(rating => {
      // 构建ID锚点链接
      const ratingAnchor = rating.ratingId ? `#rating-${rating.ratingId}` : '#ratings-section';

      // 【核心修复】使用路由解析树构建URL
      const animeUrl = this._resolveAnimeUrl(rating, ratingAnchor);

      // 生成星级HTML
      let starsHtml = '';
      for (let i = 1; i <= 5; i++) {
        if (i <= Math.floor(rating.rating)) {
          starsHtml += '<i class="fas fa-star text-warning"></i>';
        } else if (i - 0.5 <= rating.rating) {
          starsHtml += '<i class="fas fa-star-half-alt text-warning"></i>';
        } else {
          starsHtml += '<i class="far fa-star text-warning"></i>';
        }
      }

      html += `
        <div class="activity-item">
          <div class="activity-header">
            <div class="activity-title">
              <a href="${animeUrl}">${rating.animeTitle || '未知动漫'}</a>
            </div>
            <div class="activity-date">${rating.date || '未知日期'}</div>
          </div>
          <div class="activity-content">
            评分: ${starsHtml} <span class="ms-1">${rating.rating ? rating.rating.toFixed(1) : '0.0'}</span>
          </div>
          <div class="mt-2">
            <a href="${animeUrl}" class="btn btn-sm btn-outline-primary">
              <i class="fas fa-external-link-alt me-1"></i> 查看动漫
            </a>
          </div>
        </div>
      `;
    });
    html += '</div>';

    container.innerHTML = html;
  }

  // 显示评分错误 - 用户反馈系统
  showRatingsError(message) {
    const container = document.getElementById('ratingsContainer');
    if (!container) return;

    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">
          <i class="fas fa-exclamation-triangle text-warning"></i>
        </div>
        <h5>获取评分记录失败</h5>
        <p>${message || '请稍后再试'}</p>
        <button class="btn btn-primary mt-2 rounded-pill" onclick="dashboardController.loadRatings()">
          <i class="fas fa-sync-alt me-1"></i>重新加载
        </button>
      </div>
    `;
  }

  // 加载用户评论 - 社交层功能
  loadComments() {
    if (this.isLoading.comments) return;

    this.isLoading.comments = true;
    const container = document.getElementById('commentsContainer');
    if (!container) {
      console.error('[QUANTUM-ERROR] 评论容器节点不存在');
      this.isLoading.comments = false;
      return;
    }

    // 显示加载状态
    container.innerHTML = `
      <div class="loading-container">
        <div class="quantum-spinner"></div>
        <p class="mt-3">加载评论记录中...</p>
      </div>
    `;

    // 如果有初始数据，直接使用
    if (typeof initialComments !== 'undefined' && initialComments.length > 0) {
      this.renderComments(initialComments);
      this.isLoading.comments = false;
      return;
    }

    // 发起API请求
    fetchWithCSRF(this.apiEndpoints.comments, {
      method: 'GET'
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`API错误 (${response.status}): ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.success) {
        this.renderComments(data.comments);
      } else {
        throw new Error(data.error || '获取评论记录失败');
      }
    })
    .catch(error => {
      console.error('[QUANTUM-ERROR] 加载评论失败:', error);
      this.showCommentsError(error.message);
    })
    .finally(() => {
      this.isLoading.comments = false;
    });
  }

  // 渲染评论
  renderComments(comments) {
    const container = document.getElementById('commentsContainer');
    if (!container) {
      console.error('[QUANTUM-ERROR] 评论容器节点不存在');
      return;
    }

    if (!comments || comments.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">
            <i class="fas fa-comment"></i>
          </div>
          <h5>暂无评论记录</h5>
          <p>您还没有发表任何评论</p>
        </div>
      `;
      return;
    }

    // 构建评论列表
    let html = '<div class="activities-list">';
    comments.forEach(comment => {
      // 【核心修复】使用与评分相同的路由解析树
      const animeUrl = this._resolveAnimeUrl(comment);

      html += `
        <div class="activity-item">
          <div class="activity-header">
            <div class="activity-title">
              <a href="${animeUrl}" class="anime-link">${comment.animeTitle || '未知动漫'}</a>
            </div>
            <div class="activity-date">${comment.date || '未知日期'}</div>
          </div>
          <div class="activity-content">
            ${comment.content || ''}
          </div>
          <div class="mt-2">
            <span class="badge bg-light text-dark">
              <i class="fas fa-heart text-danger me-1"></i> ${comment.like_count || 0}
            </span>
            <a href="${animeUrl}" class="btn btn-sm btn-outline-primary ms-2">
              <i class="fas fa-external-link-alt me-1"></i> 查看动漫
            </a>
          </div>
        </div>
      `;
    });
    html += '</div>';

    container.innerHTML = html;
  }

  // 显示评论错误
  showCommentsError(message) {
    const container = document.getElementById('commentsContainer');
    if (!container) return;

    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">
          <i class="fas fa-exclamation-triangle text-warning"></i>
        </div>
        <h5>获取评论记录失败</h5>
        <p>${message || '请稍后再试'}</p>
        <button class="btn btn-primary mt-2 rounded-pill" onclick="dashboardController.loadComments()">
          <i class="fas fa-sync-alt me-1"></i>重新加载
        </button>
      </div>
    `;
  }

  // ======== [STRATUM-4] 工具库 ========

  /**
   * 量子路由解析树 - 多维度路由坍缩算法
   * 将任意数据模型解析为有效的动漫页面URL
   * @param {Object} entity - 包含路由数据的实体
   * @param {string} [anchor=''] - 可选的页内锚点
   * @returns {string} - 解析后的URL
   */
  _resolveAnimeUrl(entity, anchor = '') {
  // 日志级跟踪（开发环境）
  if (window.DEBUG_ROUTER) {
    console.log('[QUANTUM-ROUTER] 解析实体:', entity, '锚点:', anchor);
  }

  // Tier 1: 优先使用slug（SEO友好的URL）
  if (entity.animeSlug || entity.slug) {
    const slug = entity.animeSlug || entity.slug;
    return `${window.URLS?.animeDetail || '/anime/'}${slug}/${anchor}`;
  }
  // Tier 2: 如果没有slug但有ID，直接以ID作为slug参数传递
  // 修复: 不使用id/前缀，因为URL配置中没有这种匹配模式
  else if (entity.animeId || entity.id) {
    const id = entity.animeId || entity.id;
    return `${window.URLS?.animeDetail || '/anime/'}${id}/${anchor}`; // 移除了'id/'前缀
  }
  // Tier 3: 终极降级 - 这种情况理论上不应该发生
  else {
    console.warn('[QUANTUM-ROUTER] 路由降级:', entity);
    return window.URLS?.animeList || '/anime/list/';
  }
}

  // 初始化仪表盘 - 启动系统
  initDashboard() {
    console.log('[QUANTUM] 启动量子态仪表盘...');
    // 加载推荐数据
    this.loadRecommendations(this.currentStrategy);
    // 加载用户评分记录
    this.loadRatings();
    // 加载用户评论记录
    this.loadComments();
    console.log('[QUANTUM] 量子态仪表盘初始化完成');
  }
}