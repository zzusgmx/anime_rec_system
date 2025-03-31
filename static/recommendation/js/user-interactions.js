// 量子级动漫推荐系统 - 用户互动功能
// 处理用户互动页面的逻辑和可视化

class UserInteractionManager {
  constructor() {
    this.apiEndpoints = {
      recentInteractions: '/recommendations/api/interactions/recent/',
      myInteractions: '/recommendations/api/interactions/summary/',
      activeUsers: '/recommendations/api/interactions/top-users/',
      interactionStats: '/recommendations/api/visualization/interaction-stats/',
      userNetwork: '/recommendations/api/visualization/user-network/',
      interactionTimeline: '/recommendations/api/visualization/interaction-timeline/'
    };

    // 初始化状态
    this.isLoading = false;
    this.currentPanel = 'recent-interactions';

    console.log('[QUANTUM-INTERACTION] 用户互动管理器初始化完成');

    // 在DOM加载完成后绑定事件
    this.bindEvents();
    // 初始加载数据
    this.initialize();
  }

  // 绑定所有事件处理器
  bindEvents() {
    document.addEventListener('DOMContentLoaded', () => {
      // 面板切换按钮
      document.querySelectorAll('.quantum-nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          this.switchPanel(e.currentTarget.dataset.panelTarget);
        });
      });

      // 互动详情点击
      document.addEventListener('click', (e) => {
        if (e.target.closest('.user-interaction-item')) {
          const item = e.target.closest('.user-interaction-item');
          const interactionId = item.dataset.interactionId;
          if (interactionId) {
            this.showInteractionDetail(interactionId);
          }
        }
      });

      // 刷新按钮
      document.querySelectorAll('.refresh-interactions').forEach(btn => {
        btn.addEventListener('click', () => {
          this.refreshCurrentPanel();
        });
      });
    });
  }

  // 初始化加载
  initialize() {
    // 加载初始面板数据
    this.loadRecentInteractions();
    // 加载用户互动统计
    this.loadInteractionSummary();
  }

  // 切换面板
  switchPanel(panelId) {
    if (this.isLoading) return;

    this.currentPanel = panelId;

    // 更新按钮状态
    document.querySelectorAll('.quantum-nav-btn').forEach(btn => {
      if (btn.dataset.panelTarget === panelId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // 更新面板显示
    document.querySelectorAll('.interaction-panel').forEach(panel => {
      if (panel.id === panelId) {
        panel.classList.remove('d-none');
      } else {
        panel.classList.add('d-none');
      }
    });

    // 加载对应面板数据
    switch (panelId) {
      case 'recent-interactions':
        this.loadRecentInteractions();
        break;
      case 'my-interactions':
        this.loadMyInteractions();
        break;
      case 'active-users':
        this.loadActiveUsers();
        break;
    }
  }

  // 刷新当前面板
  refreshCurrentPanel() {
    switch (this.currentPanel) {
      case 'recent-interactions':
        this.loadRecentInteractions();
        break;
      case 'my-interactions':
        this.loadMyInteractions();
        break;
      case 'active-users':
        this.loadActiveUsers();
        break;
    }
  }

  // 获取CSRF令牌
  getCsrfToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
           document.cookie.split('; ')
               .find(row => row.startsWith('csrftoken='))
               ?.split('=')[1];
  }

  // API请求辅助函数 - 修复"throw of exception caught locally"警告
  async fetchData(url) {
    this.isLoading = true;

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': this.getCsrfToken()
        },
        credentials: 'same-origin'
      });

      // 不在try块内抛出异常，而是直接返回错误Promise
      if (!response.ok) {
        console.error(`[QUANTUM-INTERACTION] API错误 (${response.status}): ${response.statusText}`);
        return Promise.reject(new Error(`API错误 (${response.status}): ${response.statusText}`));
      }

      const data = await response.json();

      // 同样不在try块内抛出异常
      if (!data.success) {
        console.error('[QUANTUM-INTERACTION] 数据获取失败:', data.error || '获取数据失败');
        return Promise.reject(new Error(data.error || '获取数据失败'));
      }

      return data;
    } finally {
      this.isLoading = false;
    }
  }

  // 显示加载状态
  showLoading(container) {
    // 修复：确保container参数是DOM元素或ID字符串
    const containerElement = typeof container === 'string'
      ? document.getElementById(container) || document.querySelector(container)
      : container;

    if (!containerElement) {
      console.error('[QUANTUM-INTERACTION] 找不到容器元素:', container);
      return;
    }

    containerElement.innerHTML = `
      <div class="loading-container text-center py-5">
        <div class="quantum-spinner"></div>
        <p class="mt-3">量子数据加载中...</p>
      </div>
    `;
  }

  // 显示错误状态
  showError(container, message) {
    // 修复：确保container参数是DOM元素或ID字符串
    const containerElement = typeof container === 'string'
      ? document.getElementById(container) || document.querySelector(container)
      : container;

    if (!containerElement) {
      console.error('[QUANTUM-INTERACTION] 找不到容器元素:', container);
      return;
    }

    containerElement.innerHTML = `
      <div class="error-container text-center py-5">
        <div class="error-icon">
          <i class="fas fa-exclamation-triangle text-warning fa-3x"></i>
        </div>
        <p class="mt-3">${message || '加载数据失败，请稍后再试'}</p>
        <button class="btn btn-sm btn-primary mt-2 refresh-interactions">
          <i class="fas fa-sync-alt me-1"></i>重试
        </button>
      </div>
    `;

    // 绑定重试按钮
    containerElement.querySelector('.refresh-interactions')?.addEventListener('click', () => {
      this.refreshCurrentPanel();
    });
  }

  // 加载最近互动
  async loadRecentInteractions() {
    // 修复：确保使用正确的容器选择器
    const container = document.querySelector('#recent-interactions .interaction-list');

    if (!container) {
      console.error('[QUANTUM-INTERACTION] 找不到最近互动容器');
      return;
    }

    this.showLoading(container);

    try {
      const data = await this.fetchData(this.apiEndpoints.recentInteractions);

      // 修复：添加调试日志
      console.log('[QUANTUM-INTERACTION] 获取最近互动数据:', data);

      if (!data.interactions || data.interactions.length === 0) {
        container.innerHTML = `
          <div class="empty-state text-center py-5">
            <div class="empty-icon">
              <i class="fas fa-users text-muted fa-3x"></i>
            </div>
            <p class="mt-3">暂无社区互动记录</p>
          </div>
        `;
        return;
      }

      // 渲染互动列表
      this.renderInteractionList(container, data.interactions);

    } catch (error) {
      // 修复：确保错误信息显示在正确的容器中
      console.error('[QUANTUM-INTERACTION] 加载最近互动失败:', error);
      this.showError(container, error.message);

      // 错误时展示调试信息
      container.innerHTML += `
        <div class="debug-info mt-3 p-3 border border-warning" style="background: #fff8e1; border-radius: 8px;">
          <h6>调试信息 (请联系管理员)</h6>
          <p>${error.message}</p>
          <code>${error.stack}</code>
        </div>
      `;
    }
  }

  // 加载我的互动
  async loadMyInteractions() {
    // 修复：确保使用正确的容器选择器
    const container = document.querySelector('#my-interactions .my-interactions-list');

    if (!container) {
      console.error('[QUANTUM-INTERACTION] 找不到我的互动容器');
      return;
    }

    this.showLoading(container);

    try {
      const data = await this.fetchData(this.apiEndpoints.myInteractions);

      // 修复：添加调试日志
      console.log('[QUANTUM-INTERACTION] 获取我的互动数据:', data);

      if (!data.interactions || data.interactions.length === 0) {
        container.innerHTML = `
          <div class="empty-state text-center py-5">
            <div class="empty-icon">
              <i class="fas fa-user-clock text-muted fa-3x"></i>
            </div>
            <p class="mt-3">您暂无互动记录</p>
            <p class="text-muted">尝试对他人的评论点赞或回复，增加您的互动</p>
          </div>
        `;
        return;
      }

      // 渲染互动列表
      this.renderInteractionList(container, data.interactions);

    } catch (error) {
      // 修复：确保错误信息显示在正确的容器中
      console.error('[QUANTUM-INTERACTION] 加载我的互动失败:', error);
      this.showError(container, error.message);
    }
  }

  // 加载活跃用户
  async loadActiveUsers() {
    // 修复：确保使用正确的容器选择器
    const container = document.querySelector('#active-users .active-users-list');

    if (!container) {
      console.error('[QUANTUM-INTERACTION] 找不到活跃用户容器');
      return;
    }

    this.showLoading(container);

    try {
      const data = await this.fetchData(this.apiEndpoints.activeUsers);

      // 修复：添加调试日志
      console.log('[QUANTUM-INTERACTION] 获取活跃用户数据:', data);

      if (!data.users || data.users.length === 0) {
        container.innerHTML = `
          <div class="empty-state text-center py-5">
            <div class="empty-icon">
              <i class="fas fa-user-friends text-muted fa-3x"></i>
            </div>
            <p class="mt-3">暂无活跃用户数据</p>
          </div>
        `;
        return;
      }

      // 渲染活跃用户列表
      this.renderActiveUsersList(container, data.users);

    } catch (error) {
      // 修复：确保错误信息显示在正确的容器中
      console.error('[QUANTUM-INTERACTION] 加载活跃用户失败:', error);
      this.showError(container, error.message);
    }
  }

  // 加载互动统计摘要
  async loadInteractionSummary() {
    const container = document.getElementById('interactionSummary');

    if (!container) {
      console.error('[QUANTUM-INTERACTION] 找不到互动统计容器');
      return;
    }

    this.showLoading(container);

    try {
      const data = await this.fetchData(this.apiEndpoints.myInteractions);

      // 修复：添加调试日志
      console.log('[QUANTUM-INTERACTION] 获取互动统计数据:', data);

      if (!data.summary) {
        container.innerHTML = `
          <div class="empty-state text-center py-3">
            <p>暂无互动统计数据</p>
          </div>
        `;
        return;
      }

      // 渲染互动统计摘要
      this.renderInteractionSummary(container, data.summary);

    } catch (error) {
      // 修复：确保错误信息显示在正确的容器中
      console.error('[QUANTUM-INTERACTION] 加载互动统计失败:', error);
      this.showError(container, error.message);
    }
  }

  // 显示互动详情
  async showInteractionDetail(interactionId) {
    const modal = document.getElementById('interactionDetailModal');
    const modalTitle = document.getElementById('interactionModalTitle');
    const modalContent = document.getElementById('interactionModalContent');
    const viewContentBtn = document.getElementById('viewContentBtn');

    if (!modal || !modalTitle || !modalContent) {
      console.error('[QUANTUM-INTERACTION] 找不到互动详情模态框元素');
      return;
    }

    // 显示加载状态
    modalContent.innerHTML = `
      <div class="loading-container text-center py-3">
        <div class="quantum-spinner"></div>
        <p class="mt-2">加载详情...</p>
      </div>
    `;

    // 显示模态框
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();

    try {
      // 这里应该是请求详情的API
      const url = `/recommendations/api/interactions/detail/${interactionId}/`;
      const data = await this.fetchData(url);

      if (!data.interaction) {
        modalContent.innerHTML = '<p class="text-center">无法加载互动详情</p>';
        return;
      }

      // 更新模态框标题
      modalTitle.textContent = this.getInteractionTypeText(data.interaction.type) + '详情';

      // 渲染互动详情
      modalContent.innerHTML = this.createInteractionDetailHTML(data.interaction);

      // 更新内容链接
      if (data.interaction.content_url) {
        viewContentBtn.href = data.interaction.content_url;
        viewContentBtn.classList.remove('d-none');
      } else {
        viewContentBtn.classList.add('d-none');
      }

    } catch (error) {
      console.error('[QUANTUM-INTERACTION] 加载互动详情失败:', error);
      modalContent.innerHTML = `
        <div class="error-container text-center">
          <i class="fas fa-exclamation-triangle text-warning mb-2"></i>
          <p>${error.message || '加载详情失败'}</p>
        </div>
      `;
    }
  }

  // 渲染互动列表
  renderInteractionList(container, interactions) {
    // 修复：处理interactions为undefined或不是数组的情况
    if (!Array.isArray(interactions)) {
      console.error('[QUANTUM-INTERACTION] interactions不是有效数组:', interactions);
      container.innerHTML = `
        <div class="error-container text-center py-3">
          <p>数据格式错误，请联系管理员</p>
        </div>
      `;
      return;
    }

    let html = '';

    interactions.forEach(interaction => {
      html += this.createInteractionItemHTML(interaction);
    });

    container.innerHTML = html || `
      <div class="empty-state text-center py-3">
        <p>暂无互动数据</p>
      </div>
    `;

    // 添加淡入动画效果
    container.querySelectorAll('.user-interaction-item').forEach((item, index) => {
      item.style.opacity = '0';
      item.style.transform = 'translateY(20px)';

      setTimeout(() => {
        item.style.transition = 'all 0.3s ease';
        item.style.opacity = '1';
        item.style.transform = 'translateY(0)';
      }, index * 100);
    });
  }

  // 创建互动项HTML
  createInteractionItemHTML(interaction) {
    if (!interaction || !interaction.from_user || !interaction.to_user) {
      console.error('[QUANTUM-INTERACTION] 互动数据缺少必要字段:', interaction);
      return '';
    }

    const interactionTypeClass = {
      'like': 'like',
      'reply': 'reply',
      'mention': 'mention'
    }[interaction.type] || 'like';

    const interactionTypeIcon = {
      'like': 'heart',
      'reply': 'reply',
      'mention': 'at'
    }[interaction.type] || 'heart';

    const timeAgo = this.timeAgo(new Date(interaction.timestamp));

    let html = `
      <div class="user-interaction-item" data-interaction-id="${interaction.id}">
        <div class="interaction-avatar">
          <img src="${interaction.from_user.avatar || '/static/images/default-avatar.jpg'}" 
               alt="${interaction.from_user.username}">
        </div>
        <div class="interaction-content">
          <div class="interaction-header">
            <span class="interaction-username">${interaction.from_user.username}</span>
            <span class="interaction-type ${interactionTypeClass}">
              <i class="fas fa-${interactionTypeIcon} me-1"></i>
              ${this.getInteractionTypeText(interaction.type)}
            </span>
            <span class="interaction-timestamp ms-auto">${timeAgo}</span>
          </div>
    `;

    // 互动目标用户
    html += `
      <div class="interaction-text">
        ${interaction.from_user.username} 
        ${this.getInteractionVerbText(interaction.type)} 
        <strong>${interaction.to_user.username}</strong>
    `;

    // 如果有评论内容
    if (interaction.comment_content) {
      html += `
        <div class="interaction-target">
          <i class="fas fa-quote-left me-1 text-muted"></i>
          ${interaction.comment_content}
        </div>
      `;
    }

    html += `
          </div>
          <div class="interaction-footer">
            <a href="${interaction.anime_url || '#'}" class="text-muted">
              <i class="fas fa-film me-1"></i>${interaction.anime_title || '查看动漫'}
            </a>
          </div>
        </div>
      </div>
    `;

    return html;
  }

  // 创建互动详情HTML
  createInteractionDetailHTML(interaction) {
    if (!interaction || !interaction.from_user || !interaction.to_user) {
      return '<p class="text-center text-danger">互动数据格式不正确</p>';
    }

    let html = `
      <div class="interaction-detail">
        <div class="d-flex align-items-center mb-3">
          <div class="me-3">
            <img src="${interaction.from_user.avatar || '/static/images/default-avatar.jpg'}" 
                 alt="${interaction.from_user.username}" 
                 class="rounded-circle" 
                 width="50" height="50">
          </div>
          <div>
            <h5 class="mb-0">${interaction.from_user.username}</h5>
            <span class="text-muted">${new Date(interaction.timestamp).toLocaleString()}</span>
          </div>
        </div>
        
        <div class="interaction-detail-type mb-3">
          <span class="badge bg-primary">
            <i class="fas fa-${this.getInteractionTypeIcon(interaction.type)} me-1"></i>
            ${this.getInteractionTypeText(interaction.type)}
          </span>
          <span class="ms-2">→</span>
          <div class="ms-2 d-inline-block">
            <img src="${interaction.to_user.avatar || '/static/images/default-avatar.jpg'}" 
                 alt="${interaction.to_user.username}" 
                 class="rounded-circle" 
                 width="24" height="24">
            <span class="ms-1">${interaction.to_user.username}</span>
          </div>
        </div>
    `;

    // 内容部分
    if (interaction.comment_content) {
      html += `
        <div class="card mb-3">
          <div class="card-header">
            <i class="fas fa-comment me-1"></i> 评论内容
          </div>
          <div class="card-body">
            <p class="card-text">${interaction.comment_content}</p>
          </div>
        </div>
      `;
    }

    // 动漫信息
    if (interaction.anime_title) {
      html += `
        <div class="d-flex align-items-center">
          <i class="fas fa-film me-2 text-muted"></i>
          <span>动漫: <a href="${interaction.anime_url || '#'}">${interaction.anime_title}</a></span>
        </div>
      `;
    }

    html += `</div>`;

    return html;
  }

  // 渲染活跃用户列表
  renderActiveUsersList(container, users) {
    if (!Array.isArray(users)) {
      console.error('[QUANTUM-INTERACTION] users不是有效数组:', users);
      container.innerHTML = `
        <div class="error-container text-center py-3">
          <p>数据格式错误，请联系管理员</p>
        </div>
      `;
      return;
    }

    let html = '';

    users.forEach(user => {
      if (!user || !user.username) {
        console.warn('[QUANTUM-INTERACTION] 跳过无效用户数据:', user);
        return;
      }

      html += `
        <div class="user-card mb-3">
          <img src="${user.avatar || '/static/images/default-avatar.jpg'}" 
               alt="${user.username}" class="user-avatar">
          <div class="user-info">
            <h5 class="user-name">${user.username}</h5>
            <div>
              <span class="interaction-badge badge-${user.influence_score > 50 ? 'reply' : 'like'}">
                ${user.influence_score || 0} 影响力
              </span>
              <span class="interaction-badge badge-${user.social_activity_score > 50 ? 'reply' : 'mention'}">
                ${user.social_activity_score || 0} 活跃度
              </span>
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html || `
      <div class="empty-state text-center py-3">
        <p>暂无活跃用户数据</p>
      </div>
    `;
  }

  // 渲染互动统计摘要 - 修复"Local variable html is redundant"警告
  renderInteractionSummary(container, summary) {
    // 防止summary为undefined
    const data = summary || {};

    // 直接将模板字符串赋值给container.innerHTML，不使用多余的中间变量
    container.innerHTML = `
      <div class="stats-container">
        <div class="stat-item">
          <div class="stat-value">${data.likes_given || 0}</div>
          <div class="stat-label">点赞他人</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${data.likes_received || 0}</div>
          <div class="stat-label">获得点赞</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${data.replies_given || 0}</div>
          <div class="stat-label">回复他人</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${data.replies_received || 0}</div>
          <div class="stat-label">获得回复</div>
        </div>
      </div>
      <div class="influence-score">
        <div class="influence-value">${data.influence_score || 0}</div>
        <div class="influence-label">社区影响力</div>
      </div>
    `;
  }

  // 辅助方法：获取互动类型文本
  getInteractionTypeText(type) {
    const typeTexts = {
      'like': '点赞',
      'reply': '回复',
      'mention': '提及'
    };
    return typeTexts[type] || '互动';
  }

  // 辅助方法：获取互动类型图标
  getInteractionTypeIcon(type) {
    const typeIcons = {
      'like': 'heart',
      'reply': 'reply',
      'mention': 'at'
    };
    return typeIcons[type] || 'comment';
  }

  // 辅助方法：获取互动动词文本
  getInteractionVerbText(type) {
    const verbTexts = {
      'like': '点赞了',
      'reply': '回复了',
      'mention': '提及了'
    };
    return verbTexts[type] || '互动了';
  }

  // 辅助方法：时间格式化为几分钟前、几小时前等
  timeAgo(date) {
    if (!date || isNaN(date.getTime())) return '未知时间';

    const seconds = Math.floor((new Date() - date) / 1000);

    let interval = Math.floor(seconds / 31536000);
    if (interval >= 1) {
      return `${interval}年前`;
    }

    interval = Math.floor(seconds / 2592000);
    if (interval >= 1) {
      return `${interval}个月前`;
    }

    interval = Math.floor(seconds / 86400);
    if (interval >= 1) {
      return `${interval}天前`;
    }

    interval = Math.floor(seconds / 3600);
    if (interval >= 1) {
      return `${interval}小时前`;
    }

    interval = Math.floor(seconds / 60);
    if (interval >= 1) {
      return `${interval}分钟前`;
    }

    if (seconds < 10) return '刚刚';

    return `${Math.floor(seconds)}秒前`;
  }
}

// 初始化用户互动管理器
window.interactionManager = new UserInteractionManager();