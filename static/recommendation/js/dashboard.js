// 量子态动漫仪表盘控制器
// 负责仪表盘页面的所有交互和数据加载

// 获取CSRF Token
function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
         document.cookie.split('; ')
             .find(row => row.startsWith('csrftoken='))
             ?.split('=')[1];
}

// 确保所有fetch请求都包含CSRF令牌
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

    // API端点
    this.apiEndpoints = {
      recommendations: '/recommendations/api/dashboard/recommendations/',
      ratings: '/recommendations/api/dashboard/ratings/',
      comments: '/recommendations/api/dashboard/comments/',
      userStats: '/recommendations/api/dashboard/user-stats/'
    };

    console.log("量子态仪表盘控制器初始化完成");
    this.initEventListeners();
  }

  // 初始化事件监听器
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

  // 初始化用户统计动画
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

  // 数字增长动画
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

  // 加载推荐数据
  loadRecommendations(strategy = 'hybrid') {
    if (this.isLoading.recommendations) return;

    this.currentStrategy = strategy;
    this.isLoading.recommendations = true;

    // 更新活动策略
    this.updateActiveStrategy(strategy);

    // 显示加载状态
    const container = document.getElementById('recommendationContainer');
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
      console.error('加载推荐失败:', error);
      this.showRecommendationError(error.message);
    })
    .finally(() => {
      this.isLoading.recommendations = false;
    });
  }

  // 更新活动策略
  updateActiveStrategy(strategy) {
    document.querySelectorAll('.strategy-selector').forEach(selector => {
      if (selector.dataset.strategy === strategy) {
        selector.classList.add('active');
      } else {
        selector.classList.remove('active');
      }
    });
  }

  // 渲染推荐
  renderRecommendations(recommendations) {
    const container = document.getElementById('recommendationContainer');

    if (!recommendations || recommendations.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">
            <i class="fas fa-film"></i>
          </div>
          <h5>暂无推荐</h5>
          <p>随着您观看更多动漫并进行评分，我们的推荐系统将为您提供更精准的个性化推荐</p>
          <a href="/anime/list/" class="btn btn-primary mt-2 rounded-pill">
            <i class="fas fa-play me-1"></i>浏览动漫
          </a>
        </div>
      `;
      return;
    }

    // 构建推荐卡片
    let html = '';
    recommendations.forEach(anime => {
      const coverUrl = anime.image || `/static/images/default-cover.jpg`;
      html += `
        <div class="rec-card">
          <a href="${anime.url || '/anime/' + anime.id + '/'}">
            <div class="rec-img-container">
              <img src="${coverUrl}" alt="${anime.title}" onerror="this.src='/static/images/no-image.jpg'">
            </div>
          </a>
          <div class="rec-content">
            <h5 class="rec-title" title="${anime.title}">${anime.title}</h5>
            <div class="rec-confidence">
              <div class="d-flex justify-content-between small mb-1">
                <span>匹配度</span>
                <span>${anime.confidence}%</span>
              </div>
              <div class="confidence-bar">
                <div class="confidence-level" style="width: 0%" data-value="${anime.confidence}"></div>
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

  // 显示推荐错误
  showRecommendationError(message) {
    const container = document.getElementById('recommendationContainer');
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

  // 加载用户评分
  loadRatings() {
    if (this.isLoading.ratings) return;

    this.isLoading.ratings = true;
    const container = document.getElementById('ratingsContainer');

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
      console.error('加载评分失败:', error);
      this.showRatingsError(error.message);
    })
    .finally(() => {
      this.isLoading.ratings = false;
    });
  }

  // 渲染评分
  // 渲染评分
renderRatings(ratings) {
  const container = document.getElementById('ratingsContainer');

  if (!ratings || ratings.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">
          <i class="fas fa-star"></i>
        </div>
        <h5>暂无评分记录</h5>
        <p>您还没有给任何动漫评分，开始评分将帮助我们为您提供更准确的推荐</p>
        <a href="${URLS.animeList}" class="btn btn-primary mt-2 rounded-pill">
          <i class="fas fa-play me-1"></i>开始评分
        </a>
      </div>
    `;
    return;
  }

  // 构建评分列表
  let html = '<div class="activities-list">';
  ratings.forEach(rating => {
    // 构建URL时添加评分区锚点
    // 如果有特定评分ID则定位到特定评分，否则定位到评分区域
    const ratingAnchor = rating.ratingId ? `#rating-${rating.ratingId}` : '#ratings-section';

    // 使用animeSlug构建URL
    const animeUrl = rating.animeSlug
      ? `/anime/${rating.animeSlug}/${ratingAnchor}`
      : `/anime/${rating.animeId}/${ratingAnchor}`;

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
            <a href="${animeUrl}">${rating.animeTitle}</a>
          </div>
          <div class="activity-date">${rating.date}</div>
        </div>
        <div class="activity-content">
          评分: ${starsHtml} <span class="ms-1">${rating.rating.toFixed(1)}</span>
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

  // 显示评分错误
  showRatingsError(message) {
    const container = document.getElementById('ratingsContainer');
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

  // 加载用户评论
  loadComments() {
    if (this.isLoading.comments) return;

    this.isLoading.comments = true;
    const container = document.getElementById('commentsContainer');

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
      console.error('加载评论失败:', error);
      this.showCommentsError(error.message);
    })
    .finally(() => {
      this.isLoading.comments = false;
    });
  }

  // 渲染评论
  // 在dashboard.js文件中找到renderComments方法，修改如下

// 渲染评论
renderComments(comments) {
  const container = document.getElementById('commentsContainer');

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
    // Use animeSlug if available, otherwise construct URL with animeId
    const animeUrl = comment.animeSlug
      ? `/anime/${comment.animeSlug}/`
      : `/anime/${comment.animeId}/`;

    html += `
      <div class="activity-item">
        <div class="activity-header">
          <div class="activity-title">
            <a href="${animeUrl}" class="anime-link">${comment.animeTitle}</a>
          </div>
          <div class="activity-date">${comment.date}</div>
        </div>
        <div class="activity-content">
          ${comment.content}
        </div>
        <div class="mt-2">
          <span class="badge bg-light text-dark">
            <i class="fas fa-heart text-danger me-1"></i> ${comment.like_count}
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

  // 初始化仪表盘
  initDashboard() {
    // 加载推荐数据
    this.loadRecommendations(this.currentStrategy);
    // 加载用户评分记录
    this.loadRatings();
    // 加载用户评论记录
    this.loadComments();
  }
}