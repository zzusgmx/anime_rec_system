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
      document.querySelectorAll('.interaction-nav-btn').forEach(btn => {
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
    // 加载互动统计图表
    this.loadInteractionStatsChart();
    // 加载互动时间线
    this.loadInteractionTimeline();
  }

  // 切换面板
  switchPanel(panelId) {
    if (this.isLoading) return;

    this.currentPanel = panelId;

    // 更新按钮状态
    document.querySelectorAll('.interaction-nav-btn').forEach(btn => {
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
      case 'network-viz':
        this.loadNetworkVisualization();
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
      case 'network-viz':
        this.loadNetworkVisualization();
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

  // API请求辅助函数
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

      if (!response.ok) {
        throw new Error(`API错误 (${response.status}): ${response.statusText}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || '获取数据失败');
      }

      return data;
    } catch (error) {
      console.error('[QUANTUM-INTERACTION] 获取数据失败:', error);
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  // 显示加载状态
  showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="loading-container text-center py-5">
        <div class="quantum-spinner"></div>
        <p class="mt-3">量子数据加载中...</p>
      </div>
    `;
  }

  // 显示错误状态
  showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
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
    container.querySelector('.refresh-interactions')?.addEventListener('click', () => {
      this.refreshCurrentPanel();
    });
  }

  // 加载最近互动
  async loadRecentInteractions() {
    const containerId = 'recent-interactions';
    const container = document.querySelector(`#${containerId} .interaction-list`);

    if (!container) return;

    this.showLoading(container.id || containerId);

    try {
      const data = await this.fetchData(this.apiEndpoints.recentInteractions);

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
      this.showError(container.id || containerId, error.message);
    }
  }

  // 加载我的互动
  async loadMyInteractions() {
    const containerId = 'my-interactions';
    const container = document.querySelector(`#${containerId} .my-interactions-list`);

    if (!container) return;

    this.showLoading(container.id || containerId);

    try {
      const data = await this.fetchData(this.apiEndpoints.myInteractions);

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
      this.showError(container.id || containerId, error.message);
    }
  }

  // 加载活跃用户
  async loadActiveUsers() {
    const containerId = 'active-users';
    const container = document.querySelector(`#${containerId} .active-users-list`);

    if (!container) return;

    this.showLoading(container.id || containerId);

    try {
      const data = await this.fetchData(this.apiEndpoints.activeUsers);

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
      this.showError(container.id || containerId, error.message);
    }
  }

  // 加载互动网络可视化
  // 添加到loadNetworkVisualization方法中
async loadNetworkVisualization() {
  const chartContainer = document.getElementById('interactionNetworkChart');

  if (!chartContainer) return;

  this.showLoading('interactionNetworkChart');

  let retryCount = 0;
  const maxRetries = 3;

  const tryLoadNetwork = async () => {
    try {
      const data = await this.fetchData(this.apiEndpoints.userNetwork);

      if (!data.network || !data.network.nodes || data.network.nodes.length === 0) {
        chartContainer.innerHTML = `
          <div class="empty-state text-center py-5">
            <div class="empty-icon">
              <i class="fas fa-project-diagram text-muted fa-3x"></i>
            </div>
            <p class="mt-3">暂无足够的互动数据生成网络图</p>
            <p class="text-muted">当更多用户开始互动后，网络图将会生成</p>
          </div>
        `;
        return;
      }

      // 确保echarts已加载
      if (typeof echarts === 'undefined') {
        await this.loadEChartsLibrary();
      }

      // 使用ECharts渲染网络图
      this.renderNetworkChart(chartContainer, data.network);

    } catch (error) {
      console.error(`[QUANTUM-INTERACTION] 加载网络图失败 (尝试 ${retryCount+1}/${maxRetries}):`, error);

      if (retryCount < maxRetries) {
        retryCount++;
        chartContainer.innerHTML = `
          <div class="loading-container text-center py-4">
            <div class="quantum-spinner"></div>
            <p class="mt-3">加载中...再尝试 (${retryCount}/${maxRetries})</p>
          </div>
        `;

        // 等待1秒后重试
        setTimeout(() => {
          tryLoadNetwork();
        }, 1000);
      } else {
        this.showError('interactionNetworkChart', '无法加载互动网络图，请刷新页面重试');
      }
    }
  };

  await tryLoadNetwork();
}

// 添加加载ECharts库的方法
async loadEChartsLibrary() {
  return new Promise((resolve, reject) => {
    if (typeof echarts !== 'undefined') {
      resolve();
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/echarts/5.4.0/echarts.min.js';
    script.async = true;

    script.onload = () => {
      console.log('[QUANTUM-INTERACTION] ECharts库加载成功');
      resolve();
    };

    script.onerror = () => {
      console.error('[QUANTUM-INTERACTION] ECharts库加载失败');
      reject(new Error('无法加载图表库'));
    };

    document.head.appendChild(script);
  });
}

  // 加载互动统计摘要
  async loadInteractionSummary() {
    const container = document.getElementById('interactionSummary');

    if (!container) return;

    this.showLoading('interactionSummary');

    try {
      const data = await this.fetchData(this.apiEndpoints.myInteractions);

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
      this.showError('interactionSummary', error.message);
    }
  }

  // 加载互动统计图表
  async loadInteractionStatsChart() {
    const chartContainer = document.getElementById('interactionStatsChart');

    if (!chartContainer) return;

    this.showLoading('interactionStatsChart');

    try {
      const data = await this.fetchData(this.apiEndpoints.interactionStats);

      if (!data.stats || !data.stats.length) {
        chartContainer.innerHTML = `
          <div class="empty-state text-center py-3">
            <p>暂无互动统计数据</p>
          </div>
        `;
        return;
      }

      // 渲染互动统计图表
      this.renderInteractionStatsChart(chartContainer, data.stats);

    } catch (error) {
      this.showError('interactionStatsChart', error.message);
    }
  }

  // 加载互动时间线
  async loadInteractionTimeline() {
    const chartContainer = document.getElementById('interactionTimelineChart');

    if (!chartContainer) return;

    this.showLoading('interactionTimelineChart');

    try {
      const data = await this.fetchData(this.apiEndpoints.interactionTimeline);

      if (!data.timeline || !data.timeline.length) {
        chartContainer.innerHTML = `
          <div class="empty-state text-center py-3">
            <p>暂无互动时间线数据</p>
          </div>
        `;
        return;
      }

      // 渲染互动时间线图表
      this.renderInteractionTimelineChart(chartContainer, data.timeline);

    } catch (error) {
      this.showError('interactionTimelineChart', error.message);
    }
  }

  // 显示互动详情
  async showInteractionDetail(interactionId) {
    const modal = document.getElementById('interactionDetailModal');
    const modalTitle = document.getElementById('interactionModalTitle');
    const modalContent = document.getElementById('interactionModalContent');
    const viewContentBtn = document.getElementById('viewContentBtn');

    if (!modal || !modalTitle || !modalContent) return;

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
    let html = '';

    interactions.forEach(interaction => {
      html += this.createInteractionItemHTML(interaction);
    });

    container.innerHTML = html;

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
    let html = '';

    users.forEach(user => {
      html += `
        <div class="interaction-card">
          <div class="user-card">
            <img src="${user.avatar || '/static/images/default-avatar.jpg'}" 
                 alt="${user.username}" class="user-avatar">
            <div class="user-info">
              <h5 class="mb-1">${user.username}</h5>
              <div>
                <span class="badge bg-primary">${user.influence_score} 影响力</span>
                <span class="badge bg-info">${user.social_activity_score} 活跃度</span>
              </div>
            </div>
          </div>
          <div class="user-stats">
            <div class="stat-item">
              <div class="stat-value">${user.comment_count}</div>
              <div class="stat-label">评论</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">${user.replies_count}</div>
              <div class="stat-label">回复</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">${user.likes_received_count}</div>
              <div class="stat-label">获赞</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">${user.likes_given_count}</div>
              <div class="stat-label">点赞</div>
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  // 渲染互动统计摘要
  renderInteractionSummary(container, summary) {
    const html = `
      <div class="user-stats">
        <div class="stat-item">
          <div class="stat-value">${summary.likes_given || 0}</div>
          <div class="stat-label">点赞他人</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${summary.likes_received || 0}</div>
          <div class="stat-label">获得点赞</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${summary.replies_given || 0}</div>
          <div class="stat-label">回复他人</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${summary.replies_received || 0}</div>
          <div class="stat-label">获得回复</div>
        </div>
      </div>
      <div class="influence-score">
        <div class="influence-value">${summary.influence_score || 0}</div>
        <div class="influence-label">社区影响力</div>
      </div>
    `;

    container.innerHTML = html;
  }

  // 渲染互动统计图表
  renderInteractionStatsChart(container, stats) {
    if (!echarts) {
      container.innerHTML = '<p class="text-center">无法加载图表库</p>';
      return;
    }

    // 清空容器
    container.innerHTML = '';

    // 创建图表实例
    const chart = echarts.init(container);

    // 准备数据
    const data = stats.map(item => ({
      value: item.value,
      name: item.name
    }));

    // 图表配置
    const option = {
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        data: stats.map(item => item.name)
      },
      series: [
        {
          name: '互动类型',
          type: 'pie',
          radius: ['50%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 16,
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: false
          },
          data: data
        }
      ]
    };

    // 设置图表配置
    chart.setOption(option);

    // 窗口大小变化时重新调整图表
    window.addEventListener('resize', () => {
      chart.resize();
    });
  }

  // 渲染互动时间线图表
  renderInteractionTimelineChart(container, timeline) {
    if (!echarts) {
      container.innerHTML = '<p class="text-center">无法加载图表库</p>';
      return;
    }

    // 清空容器
    container.innerHTML = '';

    // 创建图表实例
    const chart = echarts.init(container);

    // 准备数据
    const dates = timeline.map(item => item.date);
    const likes = timeline.map(item => item.likes);
    const replies = timeline.map(item => item.replies);

    // 图表配置
    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#6a7985'
          }
        }
      },
      legend: {
        data: ['点赞', '回复']
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates
      },
      yAxis: {
        type: 'value'
      },
      series: [
        {
          name: '点赞',
          type: 'line',
          stack: 'Total',
          areaStyle: {},
          emphasis: {
            focus: 'series'
          },
          data: likes
        },
        {
          name: '回复',
          type: 'line',
          stack: 'Total',
          areaStyle: {},
          emphasis: {
            focus: 'series'
          },
          data: replies
        }
      ]
    };

    // 设置图表配置
    chart.setOption(option);

    // 窗口大小变化时重新调整图表
    window.addEventListener('resize', () => {
      chart.resize();
    });
  }

  // 渲染网络图
  renderNetworkChart(container, network) {
    if (!echarts) {
      container.innerHTML = '<p class="text-center">无法加载图表库</p>';
      return;
    }

    // 清空容器
    container.innerHTML = '';

    // 创建图表实例
    const chart = echarts.init(container);

    // 图表配置
    const option = {
      tooltip: {},
      legend: {
        data: ['用户', '互动']
      },
      series: [
        {
          name: '用户互动网络',
          type: 'graph',
          layout: 'force',
          data: network.nodes,
          links: network.links,
          categories: [
            { name: '用户' },
            { name: '互动' }
          ],
          roam: true,
          label: {
            show: true,
            position: 'right'
          },
          force: {
            repulsion: 100,
            edgeLength: 30
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: {
              width: 4
            }
          }
        }
      ]
    };

    // 设置图表配置
    chart.setOption(option);

    // 窗口大小变化时重新调整图表
    window.addEventListener('resize', () => {
      chart.resize();
    });
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
    if (!date) return '';

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