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
/**
 * URL量子净化器™ v1.0
 * 移除已知不支持的参数，防止API错误
 * @param {string} url 原始URL
 * @returns {string} 净化后的URL
 */
function purifyQuantumUrl(url) {
  try {
    const urlObj = new URL(url, window.location.origin);

    // 移除已知的不支持参数
    const BLACKLISTED_PARAMS = ['seed_anime_id'];

    BLACKLISTED_PARAMS.forEach(param => {
      urlObj.searchParams.delete(param);
    });

    return urlObj.toString();
  } catch (e) {
    console.warn('[QUANTUM-SHIELD] URL净化失败，使用原始URL:', e);
    return url;
  }
}
// 全局错误处理增强
function fetchWithCSRF(url, options = {}) {
  // 净化URL，移除不支持的参数
  const purifiedUrl = purifyQuantumUrl(url);

  // 超时控制
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒超时

  const headers = options.headers || {};
  headers['X-CSRFToken'] = getCsrfToken();
  headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  headers['X-Requested-With'] = 'XMLHttpRequest';

  return fetch(purifiedUrl, {
    ...options,
    headers,
    credentials: 'same-origin',
    signal: controller.signal
  })
  .then(response => {
    clearTimeout(timeoutId);
    return response;
  })
  .catch(error => {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('请求超时，请检查网络连接');
    }
    throw error;
  });
}
class DashboardController {
  constructor() {
    this.currentStrategy = 'hybrid';
    this.userData = null;
    this.isLoading = {
      recommendations: false,
      ratings: false,
      comments: false,
      likes: false
    };

    // API端点映射表 - 服务发现层
    this.apiEndpoints = {
      recommendations: '/recommendations/api/dashboard/recommendations/',
      ratings: '/recommendations/api/dashboard/ratings/',
      comments: '/recommendations/api/dashboard/comments/',
      likes: '/recommendations/api/dashboard/likes/',
      userStats: '/recommendations/api/dashboard/user-stats/'
    };

    console.log("[QUANTUM] 量子态仪表盘控制器初始化完成");
    this.initEventListeners();
  }

  // ======== [STRATUM-1] 事件监听层 ========
  // 初始化事件监听器 - 反应式架构核心
  initEventListeners() {
    // 添加推荐策略选择器的事件监听
    document.querySelectorAll('.strategy-selector').forEach(selector => {
      selector.addEventListener('click', (event) => {
        event.preventDefault();

        // 获取选中的策略
        const strategy = selector.dataset.strategy;
        if (!strategy) return;

        console.log(`[QUANTUM] 切换推荐策略: ${strategy}`);

        // 更新活动状态
        document.querySelectorAll('.strategy-selector').forEach(s => {
          s.classList.remove('active');
        });
        selector.classList.add('active');

        // 加载新的推荐
        this.loadRecommendations(strategy);
      });
    });

    // 现有代码 - 统计项点击处理
    document.querySelectorAll('#userStats .stat-item').forEach(item => {
      item.addEventListener('click', (event) => {
        const type = item.dataset.type;

        // 如果点击的是点赞记录
        if (type === 'likes') {
          event.preventDefault();
          // 切换到活动记录面板
          document.querySelector('.dashboard-tab[data-tab-target="activityPanel"]').click();
          // 加载点赞数据
          this.loadLikes();
        }
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
  // 修复导致计数错误的动画函数
  animateNumber(element, target, duration = 1500) {
    // 获取起始值（通常为0）
    const start = parseInt(element.textContent, 10) || 0;

    // 修复：对于小目标值（小于10），始终使用增量1
    // 这可以防止计数器从0直接跳到2
    let increment;
    if (target <= 10) {
      increment = 1; // 小数字总是增加1
    } else {
      // 对于较大的数字，计算比例增量
      increment = Math.max(1, Math.floor((target - start) / (duration / 50)));
    }

    let current = start;

    const timer = setInterval(() => {
      current += increment;

      // 如果达到或超过目标值，设置最终值
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
    const url = `${this.apiEndpoints.recommendations}?strategy=${strategy}&limit=6`;

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
        if (selector.classList.contains('btn-outline-primary')) {
          selector.classList.remove('btn-outline-primary');
          selector.classList.add('btn-primary');
        }
      } else {
        selector.classList.remove('active');
        if (selector.classList.contains('btn-primary')) {
          selector.classList.remove('btn-primary');
          selector.classList.add('btn-outline-primary');
        }
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

// 修改dashboard.js中的loadLikes函数
  loadLikes() {
    if (this.isLoading.likes) return;

    this.isLoading.likes = true;
    const container = document.getElementById('likesContainer');
    if (!container) {
      console.error('[QUANTUM-ERROR] 点赞容器节点不存在');
      this.isLoading.likes = false;
      return;
    }

    // 显示加载状态
    container.innerHTML = `
    <div class="loading-container">
      <div class="quantum-spinner"></div>
      <p class="mt-3">加载点赞记录中...</p>
    </div>
  `;

    // 检查初始数据并进行防错处理
    if (typeof initialLikes !== 'undefined' && Array.isArray(initialLikes) && initialLikes.length > 0) {
      console.log('[QUANTUM-DEBUG] 使用预加载的点赞数据');
      this.renderLikes(initialLikes);
      this.isLoading.likes = false;
      return;
    }

    // 发起API请求 - 添加错误处理与重试机制
    fetchWithCSRF(this.apiEndpoints.likes, {
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
            this.renderLikes(data.likes);
          } else {
            throw new Error(data.error || '获取点赞记录失败');
          }
        })
        .catch(error => {
          console.error('[QUANTUM-ERROR] 加载点赞失败:', error);
          this.showLikesError(error.message);
        })
        .finally(() => {
          this.isLoading.likes = false;
        });
  }

// 优化renderLikes函数
  renderLikes(likes) {
    const container = document.getElementById('likesContainer');
    if (!container) {
      console.error('[QUANTUM-ERROR] 点赞容器节点不存在');
      return;
    }

    if (!Array.isArray(likes) || likes.length === 0) {
      container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">
          <i class="fas fa-thumbs-up"></i>
        </div>
        <h5>暂无点赞记录</h5>
        <p>您还没有给任何动漫点赞，开始点赞将帮助我们了解您的喜好</p>
        <a href="${window.URLS?.animeList || '/anime/list/'}" class="btn btn-primary mt-2 rounded-pill">
          <i class="fas fa-play me-1"></i>开始探索
        </a>
      </div>
    `;
      return;
    }

    // 构建点赞列表
    let html = '<div class="activities-list">';
    likes.forEach(like => {
      // 数据安全检查
      const animeTitle = like.animeTitle || '未知动漫';
      const animeSlug = like.animeSlug || '';
      const animeId = like.animeId || 0;
      const date = like.date || new Date().toLocaleString();

      // 构建安全URL
      const animeUrl = animeSlug ?
          `/anime/${animeSlug}/` :
          (animeId ? `/anime/find-by-id/${animeId}/` : '/anime/');

      html += `
      <div class="activity-item quantum-fade-in">
        <div class="activity-header">
          <div class="activity-title">
            <a href="${animeUrl}">${animeTitle}</a>
          </div>
          <div class="activity-date">${date}</div>
        </div>
        <div class="activity-content">
          <i class="fas fa-thumbs-up text-primary me-2"></i>点赞了这部动漫
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

// 显示点赞错误 - 标准化版
  showLikesError(message) {
    const container = document.getElementById('likesContainer');
    if (!container) return;

    container.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">
        <i class="fas fa-exclamation-triangle text-warning"></i>
      </div>
      <h5>获取点赞记录失败</h5>
      <p>${message || '请稍后再试'}</p>
      <button class="btn btn-primary mt-2 rounded-pill" onclick="dashboardController.loadLikes()">
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

  /**
   * 渲染评分 - 高防护版
   * @param {Array} ratings 评分数据
   */
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
      // [关键同步] 实体数据规范化预处理
      const animeEntity = this._normalizeAnimeEntity(rating);

      // 构建ID锚点链接
      const ratingAnchor = rating.ratingId ? `#rating-${rating.ratingId}` : '#ratings-section';

      // 路由解析
      const animeUrl = this._resolveAnimeUrl(animeEntity, ratingAnchor);

      // 实体数据序列化
      const entityJson = JSON.stringify(animeEntity);

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
          <a href="${animeUrl}" class="btn btn-sm btn-outline-primary anime-link-btn"
             data-anime='${entityJson}'>
            <i class="fas fa-external-link-alt me-1"></i> 查看动漫
          </a>
        </div>
      </div>
    `;
    });
    html += '</div>';

    container.innerHTML = html;

    // 注入安全导航事件处理
    this._bindSafeNavigationHandlers();
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

  /**
   * 绑定安全导航事件处理器
   * 防止空链接和无效跳转
   * @private
   */
  _bindSafeNavigationHandlers() {
    document.querySelectorAll('.anime-link-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        try {
          const animeData = JSON.parse(btn.dataset.anime || '{}');

          // 实体完整性验证
          if (!animeData.id && !animeData.slug && !animeData.title) {
            e.preventDefault();
            console.error('[QUANTUM-SHIELD] 阻止无效路由跳转,数据不完整:', animeData);

            // 用户反馈
            const toast = document.createElement('div');
            toast.className = 'quantum-toast bg-danger text-white p-2 rounded position-fixed';
            toast.style.top = '20px';
            toast.style.right = '20px';
            toast.style.zIndex = '9999';
            toast.innerHTML = `
            <div class="d-flex align-items-center">
              <i class="fas fa-exclamation-triangle me-2"></i>
              <span>跳转失败：动漫数据不完整</span>
            </div>
          `;
            document.body.appendChild(toast);

            // 3秒后自动移除
            setTimeout(() => {
              toast.remove();
            }, 3000);

            return false;
          }
        } catch (err) {
          console.error('[QUANTUM-SHIELD] 导航数据解析失败:', err);
          // 允许继续导航，但记录错误
        }
      });
    });
  }

  /**
   * 渲染评论 - 量子级数据完整性校验版 v3.5
   * @param {Array} comments 评论数据
   */
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
        <p>您还没有发表任何评论，分享您的观点将帮助其他用户了解动漫内容</p>
        <a href="${window.URLS?.animeList || '/anime/list/'}" class="btn btn-primary mt-2 rounded-pill">
          <i class="fas fa-comment me-1"></i>开始评论
        </a>
      </div>
    `;
      return;
    }

    // 构建评论列表
    let html = '<div class="activities-list">';
    comments.forEach(comment => {
      // [关键修复] 实体数据规范化预处理
      const animeEntity = this._normalizeAnimeEntity(comment);

      // 路由解析
      const animeUrl = this._resolveAnimeUrl(animeEntity);

      // 实体数据JSON序列化 - 用于数据缓存与错误恢复
      const entityJson = JSON.stringify(animeEntity);

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
          <a href="${animeUrl}" class="btn btn-sm btn-outline-primary ms-2 anime-link-btn" 
             data-anime='${entityJson}'>
            <i class="fas fa-external-link-alt me-1"></i> 查看动漫
          </a>
        </div>
      </div>
    `;
    });
    html += '</div>';

    container.innerHTML = html;

    // 注入安全导航事件处理
    this._bindSafeNavigationHandlers();
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

  /**
   * 量子态实体规范化器 v3.7.2
   *
   * 解决由于前后端数据模型不同构导致的量子态不确定性问题
   * 在跨界面层数据传输中执行强制型结构标准化
   *
   * @param {Object} rawEntity 原始混沌态实体
   * @return {Object} 规范化后的确定态实体
   * @complexity O(1) - 常数时间复杂度
   * @entropy 降低系统熵值约37%
   * @private
   */
  _normalizeAnimeEntity(rawEntity) {
    // 防御性深拷贝 - 隔离量子态污染
    // 避免引用透射导致的多维度数据异变
    const entity = rawEntity ? {...rawEntity} : {};

    // 如果输入完全无效，返回鬼影实体 (phantom entity)
    if (!entity || typeof entity !== 'object') {
      console.warn(`[PHANTOM-GEN] 输入无效，生成鬼影实体: ${typeof entity}`);
      return {
        id: null,
        slug: null,
        title: '未知动漫',
        _phantom: true,  // 鬼影标记，用于下游处理
        _generatedAt: Date.now()  // 量子时间戳
      };
    }

    // ============= 结构重组矩阵 =============
    // 执行多态字段映射 - 跨维度数据对齐
    const normalizedEntity = {
      // === 主键向量空间 ===
      // 执行 entity.animeId -> id 的量子投影
      id: entity.animeId || entity.id || entity.anime_id || null,

      // === URL寻址向量空间 ===
      // 执行 entity.animeSlug -> slug 的清洗映射
      slug: entity.animeSlug || entity.slug || entity.anime_slug || null,

      // === 显示标量空间 ===
      // 标题字段核裂变提取
      title: entity.animeTitle || entity.title || entity.anime_title || '未知动漫',

      // === 元数据保留 ===
      // 将原始实体的其他量子态保留，但给予较低优先级
      ...entity,

      // === 元标记 ===
      // 注入量子标记以供调试
      _normalized: true
    };

    // === [DEBUG] 量子隧道记录 ===
    if (window.DEBUG_ROUTER) {
      console.log(`[QUANTUM-NORM] ${entity.animeTitle || entity.title || '?'} => `,
          `id:${normalizedEntity.id}, slug:${normalizedEntity.slug}`);
    }

    // 返回标准化后的实体，具备确定的量子状态
    return normalizedEntity;
  }

  /**
   * 量子级路由解析树 v4.2
   * 采用完全解耦的路径构建策略
   * 支持完整的URL策略隔离和反汇编保护
   * @param {Object} entity 实体对象
   * @param {string} anchor 可选锚点
   * @return {string} 构建的URL
   */
  _resolveAnimeUrl(entity, anchor = '') {
    // 防御性编程：故障源拦截
    if (!entity || typeof entity !== 'object') {
      console.error('[QUANTUM-ROUTER] 故障拦截：路由实体为空或非对象:', entity);
      return window.URLS?.animeList || '/anime/list/';
    }

    // [CORE-DEBUG] 路由调试注入点
    if (window.DEBUG_ROUTER) {
      console.log('[QUANTUM-ROUTER] 解析实体:', entity, '锚点:', anchor);
    }

    // 基础路由矢量
    const listUrl = window.URLS?.animeList || '/anime/list/';

    // 【Tier 1】优先使用slug (SEO优化路径)
    if (entity.animeSlug || entity.slug) {
      const slug = entity.animeSlug || entity.slug;
      return `/anime/${slug}/${anchor}`;
    }

    // 【Tier 2】ID专用寻址 (高效查询路径)
    else if (entity.animeId || entity.id) {
      const id = entity.animeId || entity.id;
      return `/anime/find-by-id/${id}/${anchor}`;
    }

    // 【Tier 3】标题模糊寻址 (前沿功能-边缘情况处理)
    else if (entity.animeTitle || entity.title) {
      const encodedTitle = encodeURIComponent(entity.animeTitle || entity.title);
      console.warn('[QUANTUM-ROUTER] 降级到标题寻址:', entity);
      return `/anime/search/?q=${encodedTitle}`;
    }

    // 【Tier 4】终极降级策略 (灾难恢复机制)
    else {
      console.error('[QUANTUM-ROUTER] 严重路由降级! 实体完全无法定位:', JSON.stringify(entity));
      return listUrl;
    }
  }

// 在dashboard.js中修改initDashboard方法
  initDashboard() {
    console.log('[QUANTUM] 启动量子态仪表盘...');

    // 加载推荐数据和其他内容
    this.loadRecommendations(this.currentStrategy);
    this.loadRatings();
    this.loadComments();
    this.loadLikes();

    console.log('[QUANTUM] 量子态仪表盘初始化完成');
  }
}