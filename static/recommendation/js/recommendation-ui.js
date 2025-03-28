// 量子态推荐UI - 完全重构版
// 增强错误处理、用户反馈和动画效果

class RecommendationUI {
  constructor(containerId = 'recommendationContainer') {
    this.containerId = containerId;
    this.container = document.getElementById(containerId);
    this.currentStrategy = 'hybrid';
    this.isLoading = false;
    this.retryCount = 0;
    this.maxRetries = 3;

    console.log("量子态推荐UI组件初始化完成");
  }

  /**
   * 显示加载状态
   */
  showLoading() {
    if (!this.container) return;
    this.isLoading = true;

    this.container.innerHTML = `
      <div class="col-12 text-center my-5">
        <div class="loading-container">
          <div class="quantum-spinner"></div>
          <p class="mt-3">量子态计算中...</p>
          <small class="text-muted">正在应用 ${this.getStrategyName(this.currentStrategy)} 算法</small>
        </div>
      </div>
    `;
  }

  /**
   * 显示错误状态
   * @param {string} message - 错误消息
   */
  showError(message) {
    if (!this.container) return;
    this.isLoading = false;

    this.container.innerHTML = `
      <div class="col-12">
        <div class="empty-state">
          <div class="empty-icon">
            <i class="fas fa-exclamation-triangle text-warning"></i>
          </div>
          <h5>量子算法异常</h5>
          <p>${message || '推荐引擎遇到意外错误，请稍后再试'}</p>
          <button class="btn btn-primary mt-2 rounded-pill retry-btn">
            <i class="fas fa-sync-alt me-1"></i>重试
          </button>
        </div>
      </div>
    `;

    // 添加重试按钮事件
    const retryBtn = this.container.querySelector('.retry-btn');
    if (retryBtn) {
      retryBtn.addEventListener('click', () => {
        this.loadRecommendations(this.currentStrategy);
      });
    }
  }

  /**
   * 显示空状态
   */
  showEmpty() {
    if (!this.container) return;
    this.isLoading = false;

    this.container.innerHTML = `
      <div class="col-12">
        <div class="empty-state">
          <div class="empty-icon">
            <i class="fas fa-film"></i>
          </div>
          <h5>暂无推荐</h5>
          <p>随着您观看更多动漫并进行评分，我们的推荐系统将为您提供更精准的个性化推荐</p>
          <a href="/anime/list/" class="btn btn-primary mt-2 rounded-pill">
            <i class="fas fa-list me-2"></i>浏览所有动漫
          </a>
        </div>
      </div>
    `;
  }

  /**
   * 获取策略名称
   * @private
   */
  getStrategyName(strategy) {
    const names = {
      'hybrid': '混合推荐',
      'cf': '协同过滤',
      'content': '基于内容',
      'ml': '基于GBDT',
      'popular': '热门推荐'
    };
    return names[strategy] || names['hybrid'];
  }

  /**
   * 渲染推荐项目
   * @param {Array} recommendations - 推荐数据
   */
  renderRecommendations(recommendations) {
    if (!this.container) return;
    this.isLoading = false;

    if (!recommendations || recommendations.length === 0) {
      this.showEmpty();
      return;
    }

    // 构建网格布局HTML
    let html = '<div class="row recommendation-grid">';

    recommendations.forEach(anime => {
      const coverUrl = anime.cover_url || `/static/images/default-cover.jpg`; // 使用默认图片
      const score = anime.score || 0;

      html += `
        <div class="col-md-3 col-sm-6 mb-4">
          <div class="card recommendation-card h-100">
            <div class="card-img-container">
              <img src="${coverUrl}" alt="${anime.title}" class="card-img-top" onerror="this.src='/static/images/no-image.jpg'">
              <div class="confidence-badge ${this._getConfidenceClass(score)}">
                ${score}% 匹配
              </div>
            </div>

            <div class="card-body">
              <h5 class="card-title" title="${anime.title}">${anime.title}</h5>
              ${anime.rating ? `
              <div class="mb-2">
                <span class="rating-stars">
                  ${this._generateStarRating(anime.rating)}
                </span>
                <span class="text-muted ms-1">${parseFloat(anime.rating).toFixed(1)}</span>
              </div>
              ` : ''}
            </div>

            <div class="card-footer">
              <a href="${anime.url || '/anime/' + anime.id + '/'}" class="btn btn-sm btn-primary w-100">
                <i class="fas fa-info-circle me-1"></i> 查看详情
              </a>
            </div>
          </div>
        </div>
      `;
    });

    html += '</div>';
    this.container.innerHTML = html;

    // 添加动画效果
    this._animateItems();
  }

  /**
   * 加载并显示推荐
   * @param {string} strategy - 推荐策略
   */
  async loadRecommendations(strategy) {
    // 确保策略是有效的
    if (!strategy || strategy === 'undefined') {
      console.warn('策略参数无效，使用默认hybrid策略');
      strategy = 'hybrid';
    }

    this.currentStrategy = strategy;
    this.showLoading();

    try {
      // 更新活动策略视觉效果
      this._updateActiveStrategy(strategy);

      // 更新URL以反映当前策略
      this._updateUrlStrategy(strategy);

      // 更新策略描述
      this._updateStrategyDescription(strategy);

      // 使用推荐引擎获取数据
      const recommendations = await recommendationEngine.getRecommendations(strategy);
      this.renderRecommendations(recommendations);

      // 重置重试计数
      this.retryCount = 0;
    } catch (error) {
      console.error('加载推荐失败:', error);

      // 实现渐进式重试
      if (this.retryCount < this.maxRetries) {
        this.retryCount++;
        console.log(`尝试重试 (${this.retryCount}/${this.maxRetries})...`);

        // 显示重试状态
        if (this.container) {
          this.container.innerHTML = `
            <div class="col-12 text-center my-5">
              <div class="loading-container">
                <div class="quantum-spinner"></div>
                <p class="mt-3">重新连接中 (${this.retryCount}/${this.maxRetries})...</p>
              </div>
            </div>
          `;
        }

        // 增加延迟时间进行重试
        setTimeout(() => {
          this.loadRecommendations(strategy);
        }, 1000 * this.retryCount);
      } else {
        this.showError(error.message);
      }
    }
  }

  /**
   * 更新URL以反映当前策略
   * @private
   */
  _updateUrlStrategy(strategy) {
    try {
      const url = new URL(window.location);
      url.searchParams.set('strategy', strategy);
      window.history.pushState({}, '', url);
    } catch (e) {
      console.warn('更新URL参数失败:', e);
    }
  }

  /**
   * 更新活动策略按钮状态
   * @private
   */
  _updateActiveStrategy(strategy) {
    document.querySelectorAll('.strategy-selector').forEach(btn => {
      if (btn.dataset.strategy === strategy) {
        btn.classList.add('active');
        if (btn.classList.contains('btn-outline-primary')) {
          btn.classList.remove('btn-outline-primary');
          btn.classList.add('btn-primary');
        }
      } else {
        btn.classList.remove('active');
        if (btn.classList.contains('btn-primary')) {
          btn.classList.remove('btn-primary');
          btn.classList.add('btn-outline-primary');
        }
      }
    });
  }

  /**
   * 更新策略描述
   * @private
   */
  _updateStrategyDescription(strategy) {
    const descContainer = document.querySelector('.algo-header');
    if (!descContainer) return;

    const stratDesc = recommendationEngine.getStrategyDescription(strategy);

    descContainer.innerHTML = `
      <i class="fas ${stratDesc.icon} algo-icon ${stratDesc.className}"></i>
      <h2 class="algo-title">${stratDesc.title}</h2>
      <p class="algo-description">${stratDesc.description}</p>
    `;
  }

  /**
   * 添加项目动画效果
   * @private
   */
  _animateItems() {
    const cards = this.container.querySelectorAll('.recommendation-card');

    cards.forEach((card, index) => {
      // 设置初始状态
      card.style.opacity = '0';
      card.style.transform = 'translateY(20px)';
      card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';

      // 添加延迟入场动画
      setTimeout(() => {
        card.style.opacity = '1';
        card.style.transform = 'translateY(0)';
      }, index * 100);

      // 确保信心指示条动画
      const confidenceBar = card.querySelector('.confidence-level');
      if (confidenceBar) {
        setTimeout(() => {
          confidenceBar.style.width = `${confidenceBar.dataset.value}%`;
        }, 500 + index * 100);
      }
    });
  }

  /**
   * 根据分数获取置信度类名
   * @private
   */
  _getConfidenceClass(score) {
    if (score >= 80) return 'confidence-high';
    if (score >= 50) return 'confidence-medium';
    return 'confidence-low';
  }

  /**
   * 生成星级评分HTML
   * @private
   */
  _generateStarRating(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating - fullStars >= 0.5;
    let html = '';

    // 全星
    for (let i = 0; i < fullStars; i++) {
      html += '<i class="fas fa-star"></i>';
    }

    // 半星
    if (hasHalfStar) {
      html += '<i class="fas fa-star-half-alt"></i>';
    }

    // 空星
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    for (let i = 0; i < emptyStars; i++) {
      html += '<i class="far fa-star"></i>';
    }

    return html;
  }
}

// 创建全局实例
window.recommendationUI = new RecommendationUI('recommendationContainer');