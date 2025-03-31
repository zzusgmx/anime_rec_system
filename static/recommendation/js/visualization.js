// 量子态数据可视化引擎 - ECharts集成
// 用于生成用户行为和动漫偏好的可视化图表

class QuantumVisualizationEngine {
  constructor() {
    this.apiEndpoints = {
      userActivity: '/recommendations/api/visualization/user-activity/',
      genrePreference: '/recommendations/api/visualization/genre-preference/',
      ratingDistribution: '/recommendations/api/visualization/rating-distribution/',
      viewingTrends: '/recommendations/api/visualization/viewing-trends/',
      likesAnalysis: '/recommendations/api/visualization/likes-analysis/',
      genreHeatmap: '/recommendations/api/visualization/genre-heatmap/'
    };

    this.charts = new Map();
    this.pendingRenders = new Map();
    this.colors = {
      primary: '#6d28d9',
      secondary: '#10b981',
      accent: '#f97316',
      background: 'rgba(255, 255, 255, 0.8)',
      gradients: [
        ['#6d28d9', '#8b5cf6'],  // 紫色渐变
        ['#10b981', '#34d399'],  // 绿色渐变
        ['#f97316', '#fb923c'],  // 橙色渐变
        ['#2563eb', '#60a5fa'],   // 蓝色渐变
        ['#ef4444', '#f87171']   // 红色渐变
      ]
    };

    // 注册自身到全局作用域，确保可被其他脚本访问
    window.vizEngine = this;

    console.log('[QUANTUM-VIZ] 量子态可视化引擎初始化完成');

    // 设置观察器以检测面板可见性变化
    this.setupObservers();

    // 为图表容器标签切换添加事件监听
    this.setupTabEventListeners();
  }

  fetchData(url) {
    console.log(`[QUANTUM-VIZ] 正在获取数据: ${url}`);

    // 获取CSRF令牌
    const csrfToken = this.getCsrfToken();

    // 添加超时处理
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒超时

    return fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrfToken
      },
      credentials: 'same-origin',
      signal: controller.signal
    })
    .then(response => {
      clearTimeout(timeoutId);
      if (!response.ok) {
        throw new Error(`API错误 (${response.status}): ${response.statusText}`);
      }
      return response.json();
    })
    .catch(error => {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('请求超时，请检查网络连接');
      }
      throw error;
    });
  }

  // 创建渐变色
  createGradient(ctx, colors) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, colors[0]);
    gradient.addColorStop(1, colors[1]);
    return gradient;
  }

  // 格式化大数字
  formatNumber(num) {
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'k';
    }
    return num.toString();
  }

  // 设置观察器来检测DOM变化和元素可见性
  setupObservers() {
    // 1. 设置IntersectionObserver来检测元素何时进入视口
    this.visibilityObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const container = entry.target;
          console.log(`[QUANTUM-VIZ] 容器 #${container.id} 现在可见，尝试渲染`);

          // 如果有待渲染的数据，立即渲染
          if (this.pendingRenders.has(container.id)) {
            this.renderDeferredChart(container.id);
          } else if (!this.charts.has(container.id)) {
            // 如果没有待渲染数据且图表未渲染，则请求新数据
            this.renderChartById(container.id);
          }
        }
      });
    }, { threshold: 0.1 });

    // 2. 设置MutationObserver来检测DOM变化
    this.mutationObserver = new MutationObserver((mutations) => {
      mutations.forEach(mutation => {
        if (mutation.type === 'attributes' &&
            (mutation.attributeName === 'class' || mutation.attributeName === 'style')) {
          const panel = mutation.target;

          // 检查是否是可视化面板且变为可见
          if (panel.classList.contains('viz-panel') &&
              panel.classList.contains('active') &&
              panel.style.display !== 'none') {

            console.log(`[QUANTUM-VIZ] 检测到面板激活: ${panel.id}`);

            // 查找此面板中的图表容器
            const container = panel.querySelector('.chart-container');
            if (container && container.id) {
              // 确保容器可见并有尺寸
              this.ensureContainerReady(container);

              // 渲染或调整图表
              if (!this.charts.has(container.id)) {
                this.renderChartById(container.id);
              } else {
                const chart = this.charts.get(container.id);
                if (chart) setTimeout(() => chart.resize(), 50);
              }
            }
          }
        }
      });
    });

    // 页面加载后开始观察所有相关元素
    document.addEventListener('DOMContentLoaded', () => {
      this.observeAllPanelsAndContainers();
    });

    // 也立即开始观察，以防DOMContentLoaded已经触发
    if (document.readyState === 'interactive' || document.readyState === 'complete') {
      this.observeAllPanelsAndContainers();
    }
  }

  // 观察所有面板和图表容器
  observeAllPanelsAndContainers() {
    // 观察所有可视化面板元素
    document.querySelectorAll('.viz-panel').forEach(panel => {
      this.mutationObserver.observe(panel, {
        attributes: true,
        attributeFilter: ['class', 'style']
      });

      // 也观察面板中的图表容器
      const container = panel.querySelector('.chart-container');
      if (container) {
        this.visibilityObserver.observe(container);
      }
    });

    // 观察所有图表容器
    document.querySelectorAll('.chart-container').forEach(container => {
      this.visibilityObserver.observe(container);
    });

    console.log('[QUANTUM-VIZ] 已开始观察所有面板和容器');
  }

  // 设置标签切换事件监听器
  setupTabEventListeners() {
    document.addEventListener('DOMContentLoaded', () => {
      // 为可视化导航按钮添加点击事件
      document.querySelectorAll('.viz-nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const targetId = btn.dataset.vizTarget;

          // 延迟渲染，确保DOM更新
          setTimeout(() => {
            const panel = document.getElementById(targetId);
            if (panel) {
              const container = panel.querySelector('.chart-container');
              if (container && container.id) {
                this.ensureContainerReady(container);
                this.renderChartById(container.id);
              }
            }
          }, 100);
        });
      });

      // 为仪表板标签添加点击事件
      document.querySelectorAll('.dashboard-tab').forEach(tab => {
        tab.addEventListener('click', () => {
          if (tab.dataset.tabTarget === 'visualizationPanel') {
            // 如果切换到可视化面板，延迟初始化
            setTimeout(() => {
              this.initializeCharts();
            }, 200);
          }
        });
      });
    });
  }

  // 确保容器准备好渲染图表
  ensureContainerReady(container) {
    if (!container) return false;

    const rect = container.getBoundingClientRect();
    console.log(`[QUANTUM-VIZ] 容器 #${container.id} 当前尺寸: ${rect.width}x${rect.height}`);

    // 如果容器不可见或尺寸为零，则强制设置
    if (rect.height < 100 || rect.width < 100 ||
        container.offsetParent === null ||
        window.getComputedStyle(container).display === 'none') {

      // 强制设置尺寸和可见性
      container.style.height = '400px';
      container.style.width = '100%';
      container.style.minHeight = '300px';
      container.style.display = 'block';
      container.style.visibility = 'visible';
      container.style.opacity = '1';

      // 确保父面板也可见
      const parentPanel = container.closest('.viz-panel');
      if (parentPanel) {
        parentPanel.style.display = 'block';
        parentPanel.style.visibility = 'visible';
        parentPanel.style.opacity = '1';
      }

      console.log(`[QUANTUM-VIZ] 已强制设置容器 #${container.id} 尺寸和可见性`);

      // 强制浏览器重新计算布局
      void container.offsetHeight;
      return true;
    }

    return false;
  }

  /**
   * 根据ID渲染特定图表
   * 完整重构版 - 修复渲染方法调用错误、增强错误处理
   *
   * @param {string} chartId 图表容器的ID
   */
  renderChartById(chartId) {
    console.log(`[QUANTUM-VIZ] 请求渲染图表: ${chartId}`);

    const container = document.getElementById(chartId);
    if (!container) {
      console.error(`[QUANTUM-VIZ] 找不到图表容器: #${chartId}`);
      return;
    }

    // ===== 第1步: 强制设置容器尺寸和可见性 =====
    container.style.height = '400px';
    container.style.width = '100%';
    container.style.minHeight = '300px';
    container.style.display = 'block';
    container.style.visibility = 'visible';
    container.style.opacity = '1';

    // ===== 第2步: 确保容器所在面板可见 =====
    const panel = container.closest('.viz-panel');
    if (panel) {
      // 检查面板是否已激活
      if (!panel.classList.contains('active')) {
        console.log(`[QUANTUM-VIZ] 容器 #${chartId} 所在面板未激活，尝试激活`);

        // 获取所有面板并重置状态
        const allPanels = document.querySelectorAll('.viz-panel');
        allPanels.forEach(p => {
          p.classList.remove('active');
          p.style.display = 'none';
          p.style.visibility = 'hidden';
          p.style.opacity = '0';
        });

        // 激活当前面板
        panel.classList.add('active');
        panel.style.display = 'block';
        panel.style.visibility = 'visible';
        panel.style.opacity = '1';

        // 同步激活对应的导航按钮
        if (panel.id) {
          const navBtns = document.querySelectorAll('.viz-nav-btn');
          navBtns.forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.vizTarget === panel.id) {
              btn.classList.add('active');
            }
          });
        }
      }
    }

    // ===== 第3步: 显示加载状态 =====
    this.showLoading(chartId);

    // ===== 第4步: 确定图表类型并获取数据 =====
    let apiEndpoint = '';
    let optionCreator = null;

    // 修复: 使用正确的方法名 (_createXXXChartOption 而不是 _renderXXXChart)
    switch (chartId) {
      case 'activityChart':
        apiEndpoint = this.apiEndpoints.userActivity;
        optionCreator = this._createActivityChartOption;
        break;
      case 'genreChart':
        apiEndpoint = this.apiEndpoints.genrePreference;
        optionCreator = this._createGenreChartOption;
        break;
      case 'ratingChart':
        apiEndpoint = this.apiEndpoints.ratingDistribution;
        optionCreator = this._createRatingChartOption;
        break;
      case 'trendChart':
        apiEndpoint = this.apiEndpoints.viewingTrends;
        optionCreator = this._createTrendChartOption;
        break;
      case 'likesAnalysisChart':
        apiEndpoint = this.apiEndpoints.likesAnalysis;
        optionCreator = this._createLikesAnalysisChartOption;
        break;
      case 'radarChart':
        apiEndpoint = this.apiEndpoints.genrePreference;
        optionCreator = this._createRadarChartOption;
        break;
      case 'heatmapChart':
        apiEndpoint = this.apiEndpoints.genreHeatmap;
        optionCreator = this._createHeatmapChartOption;
        break;
      default:
        console.error(`[QUANTUM-VIZ] 未知图表ID: ${chartId}`);
        this.showError(chartId, '未知的图表类型，请检查配置');
        return;
    }

    // 安全检查: 确保选项创建器存在
    if (!optionCreator || typeof optionCreator !== 'function') {
      console.error(`[QUANTUM-VIZ] 图表 ${chartId} 的配置创建器未定义`);
      this.showError(chartId, `图表配置创建器未定义: ${chartId}`);
      return;
    }

    // ===== 第5步: 使用Promise链处理数据获取和渲染 =====
    // 添加请求超时控制
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('请求超时，请检查网络连接')), 10000);
    });

    // 发送API请求并设置超时
    Promise.race([
      this.fetchData(apiEndpoint),
      timeoutPromise
    ])
    .then(response => {
      // 验证API响应
      if (!response.success || !response.data) {
        throw new Error(response.error || '服务器返回的数据无效');
      }

      // 检查容器是否仍然存在
      const container = document.getElementById(chartId);
      if (!container) {
        throw new Error('图表容器已不存在');
      }

      // 清除加载状态
      container.innerHTML = '';

      // 创建ECharts实例
      let chart;
      try {
        chart = echarts.init(container);
        this.charts.set(chartId, chart);
      } catch (err) {
        throw new Error(`ECharts初始化失败: ${err.message}`);
      }

      // 调用对应的选项创建方法生成图表配置
      // 修复: 使用bind确保this上下文，然后调用函数
      const optionMethod = optionCreator.bind(this);
      const option = optionMethod(response.data);

      if (!option) {
        throw new Error('图表配置生成失败');
      }

      // 设置图表配置
      try {
        chart.setOption(option);
      } catch (err) {
        throw new Error(`图表渲染失败: ${err.message}`);
      }

      // 延迟调整图表大小，确保渲染完成
      setTimeout(() => {
        if (chart && typeof chart.resize === 'function') {
          chart.resize();
          console.log(`[QUANTUM-VIZ] ${chartId} 图表大小已调整`);
        }
      }, 200);

      // 添加窗口大小变化监听
      const resizeHandler = () => {
        if (chart && typeof chart.resize === 'function') {
          chart.resize();
        }
      };

      // 移除旧的监听器（如果有）并添加新的
      window.removeEventListener('resize', resizeHandler);
      window.addEventListener('resize', resizeHandler);

      console.log(`[QUANTUM-VIZ] ${chartId} 图表渲染成功`);
    })
    .catch(error => {
      console.error(`[QUANTUM-VIZ] ${chartId} 图表渲染失败:`, error);

      // 错误分类和处理
      let errorMessage = error.message || '未知错误';
      let errorAction = null;

      if (errorMessage.includes('超时')) {
        errorMessage = '获取数据超时，请检查网络连接';
        errorAction = '重试';
      } else if (errorMessage.includes('初始化失败')) {
        errorMessage = 'ECharts组件初始化失败，请刷新页面';
        errorAction = '刷新页面';
      } else if (errorMessage.includes('服务器')) {
        errorMessage = '服务器数据异常或格式错误';
        errorAction = '报告问题';
      }

      // 显示友好的错误消息
      this.showEnhancedError(chartId, errorMessage, errorAction);

      // 如果是ECharts问题，尝试重新加载库
      if (errorMessage.includes('ECharts') && typeof echarts === 'undefined') {
        this._loadEChartsLibrary();
      }
    });
  }

  /**
   * 显示增强的错误信息，带有操作按钮
   * @param {string} containerId 容器ID
   * @param {string} message 错误消息
   * @param {string} action 建议操作
   */
  showEnhancedError(containerId, message, action) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="chart-error">
        <div class="empty-icon">
          <i class="fas fa-exclamation-triangle text-warning"></i>
        </div>
        <h5 class="mt-3">图表加载失败</h5>
        <p class="text-muted">${message || '请稍后再试'}</p>
        <div class="mt-3">
          <button class="btn btn-sm btn-primary" onclick="window.vizEngine.refreshChart('${containerId}')">
            <i class="fas fa-sync-alt me-1"></i>${action || '重试'}
          </button>
          <button class="btn btn-sm btn-outline-secondary ms-2" onclick="window.vizEngine.showDummyData('${containerId}')">
            <i class="fas fa-chart-bar me-1"></i>显示示例数据
          </button>
        </div>
      </div>
    `;
  }

  /**
   * 显示简单错误信息
   * @param {string} containerId 容器ID
   * @param {string} message 错误消息
   */
  showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="chart-error">
        <div class="empty-icon">
          <i class="fas fa-exclamation-triangle text-warning"></i>
        </div>
        <h5 class="mt-3">图表加载失败</h5>
        <p class="text-muted">${message || '请稍后再试'}</p>
        <button class="btn btn-sm btn-primary mt-2" onclick="window.vizEngine.refreshChart('${containerId}')">
          <i class="fas fa-sync-alt me-1"></i>重试
        </button>
      </div>
    `;
  }

  /**
   * 刷新指定图表
   * @param {string} containerId 容器ID
   */
  refreshChart(containerId) {
    console.log(`[QUANTUM-VIZ] 刷新图表: ${containerId}`);
    this.renderChartById(containerId);
  }

  /**
   * 显示示例数据（降级策略）
   * @param {string} containerId 容器ID
   */
  showDummyData(containerId) {
    console.log(`[QUANTUM-VIZ] 为 ${containerId} 显示示例数据`);

    const container = document.getElementById(containerId);
    if (!container) return;

    // 清除容器内容
    container.innerHTML = '';

    // 创建ECharts实例
    try {
      const chart = echarts.init(container);

      // 根据图表类型显示不同的示例数据
      let option;

      switch(containerId) {
        case 'activityChart':
          option = this._createDummyActivityChart();
          break;
        case 'genreChart':
          option = this._createDummyGenreChart();
          break;
        case 'ratingChart':
          option = this._createDummyRatingChart();
          break;
        case 'trendChart':
          option = this._createDummyTrendChart();
          break;
        case 'likesAnalysisChart':
          option = this._createDummyLikesAnalysisChart();
          break;
        case 'radarChart':
          option = this._createDummyRadarChart();
          break;
        case 'heatmapChart':
          option = this._createDummyHeatmapChart();
          break;
        default:
          option = this._createDummyActivityChart();
      }

      // 设置图表配置
      chart.setOption(option);

      // 保存图表实例
      this.charts.set(containerId, chart);

      // 添加提示信息
      container.insertAdjacentHTML('beforeend', `
        <div class="text-center mt-2" style="position: absolute; bottom: 5px; width: 100%;">
          <span class="badge bg-warning text-dark">示例数据</span>
        </div>
      `);

      // 调整图表大小
      setTimeout(() => chart.resize(), 100);

    } catch (error) {
      console.error(`[QUANTUM-VIZ] 显示示例数据失败:`, error);
      container.innerHTML = `
        <div class="chart-error">
          <p class="text-muted">无法显示示例数据，请刷新页面</p>
        </div>
      `;
    }
  }

  /**
   * 创建示例活动图表
   * @returns {Object} ECharts配置
   */
  _createDummyActivityChart() {
    return {
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        data: ['浏览记录', '评分记录', '评论记录', '收藏记录', '点赞记录']
      },
      series: [
        {
          name: '用户活动',
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
          data: [
            { value: 35, name: '浏览记录', itemStyle: { color: '#6d28d9' } },
            { value: 20, name: '评分记录', itemStyle: { color: '#10b981' } },
            { value: 12, name: '评论记录', itemStyle: { color: '#f97316' } },
            { value: 18, name: '收藏记录', itemStyle: { color: '#2563eb' } },
            { value: 15, name: '点赞记录', itemStyle: { color: '#ef4444' } }
          ]
        }
      ]
    };
  }

  /**
   * 创建示例类型偏好图表
   * @returns {Object} ECharts配置
   */
  _createDummyGenreChart() {
    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'value',
        boundaryGap: [0, 0.01]
      },
      yAxis: {
        type: 'category',
        data: ['科幻', '冒险', '恋爱', '校园', '悬疑', '日常']
      },
      series: [
        {
          name: '偏好程度',
          type: 'bar',
          data: [
            {value: 85, itemStyle: {color: '#6d28d9'}},
            {value: 72, itemStyle: {color: '#10b981'}},
            {value: 63, itemStyle: {color: '#f97316'}},
            {value: 52, itemStyle: {color: '#2563eb'}},
            {value: 38, itemStyle: {color: '#ef4444'}},
            {value: 24, itemStyle: {color: '#8b5cf6'}}
          ]
        }
      ]
    };
  }

  /**
   * 创建示例评分分布图表
   * @returns {Object} ECharts配置
   */
  _createDummyRatingChart() {
    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: ['1', '2', '3', '4', '5']
      },
      yAxis: {
        type: 'value',
        name: '评分次数',
        minInterval: 1
      },
      series: [
        {
          name: '评分分布',
          type: 'bar',
          data: [3, 8, 15, 25, 18],
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#6d28d9' },
              { offset: 1, color: '#8b5cf6' }
            ])
          }
        }
      ]
    };
  }

  /**
   * 创建示例趋势图表
   * @returns {Object} ECharts配置
   */
  _createDummyTrendChart() {
    // 生成过去14天的日期
    const dates = [];
    const today = new Date();
    for (let i = 13; i >= 0; i--) {
      const date = new Date();
      date.setDate(today.getDate() - i);
      dates.push(date.toISOString().split('T')[0]);
    }

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: ['浏览次数', '评分次数']
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
          name: '浏览次数',
          type: 'line',
          stack: 'Total',
          areaStyle: {},
          data: [5, 3, 8, 4, 6, 3, 5, 7, 4, 6, 9, 5, 8, 7],
          itemStyle: { color: '#6d28d9' }
        },
        {
          name: '评分次数',
          type: 'line',
          stack: 'Total',
          areaStyle: {},
          data: [2, 1, 3, 1, 2, 0, 1, 2, 1, 3, 2, 1, 3, 2],
          itemStyle: { color: '#10b981' }
        }
      ]
    };
  }

  /**
   * 创建示例点赞分析图表
   * @returns {Object} ECharts配置
   */
  _createDummyLikesAnalysisChart() {
    return {
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        data: ['动漫点赞', '评论点赞', '评分', '收藏']
      },
      series: [
        {
          name: '点赞分析',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
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
          data: [
            { value: 42, name: '动漫点赞', itemStyle: { color: '#ef4444' } },
            { value: 28, name: '评论点赞', itemStyle: { color: '#f97316' } },
            { value: 35, name: '评分', itemStyle: { color: '#10b981' } },
            { value: 25, name: '收藏', itemStyle: { color: '#2563eb' } }
          ]
        }
      ]
    };
  }

  /**
   * 创建示例雷达图
   * @returns {Object} ECharts配置
   */
  _createDummyRadarChart() {
    return {
      tooltip: {
        trigger: 'item'
      },
      radar: {
        indicator: [
          { name: '科幻', max: 100 },
          { name: '冒险', max: 100 },
          { name: '恋爱', max: 100 },
          { name: '校园', max: 100 },
          { name: '悬疑', max: 100 },
          { name: '日常', max: 100 }
        ]
      },
      series: [
        {
          name: '类型偏好',
          type: 'radar',
          areaStyle: {
            opacity: 0.6
          },
          data: [
            {
              value: [85, 70, 45, 65, 78, 32],
              name: '偏好程度'
            }
          ]
        }
      ]
    };
  }

  /**
   * 创建示例热力图
   * @returns {Object} ECharts配置
   */
  _createDummyHeatmapChart() {
    const genres = ['科幻', '冒险', '恋爱', '校园', '悬疑', '日常', '治愈', '运动'];
    const dimensions = ['浏览量', '评分', '收藏'];
    const data = [];

    // 生成随机数据
    for (let i = 0; i < dimensions.length; i++) {
      for (let j = 0; j < genres.length; j++) {
        data.push([i, j, Math.floor(Math.random() * 90 + 10)]);
      }
    }

    return {
      tooltip: {
        position: 'top',
        formatter: function(params) {
          return `${dimensions[params.value[0]]} - ${genres[params.value[1]]}: ${params.value[2]}`;
        }
      },
      grid: {
        left: '3%',
        right: '7%',
        bottom: '13%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: dimensions
      },
      yAxis: {
        type: 'category',
        data: genres
      },
      visualMap: {
        min: 0,
        max: 100,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '5%'
      },
      series: [
        {
          name: '类型热度',
          type: 'heatmap',
          data: data,
          label: {
            show: true
          }
        }
      ]
    };
  }

  // 渲染延迟的图表
  renderDeferredChart(chartId) {
    console.log(`[QUANTUM-VIZ] 渲染延迟图表: ${chartId}`);

    // 检查是否有预加载的数据
    const data = this.pendingRenders.get(chartId);
    if (data) {
      // 有预加载数据，直接使用
      this.pendingRenders.delete(chartId);

      const container = document.getElementById(chartId);
      if (!container) return;

      this.ensureContainerReady(container);

      // 根据图表类型和数据渲染
      try {
        console.log(`[QUANTUM-VIZ] 使用预加载数据渲染 ${chartId}`);

        // 清除加载状态
        container.innerHTML = '';

        // 创建图表实例
        const chart = echarts.init(container);
        this.charts.set(chartId, chart);

        // 根据图表类型设置选项
        let option;
        switch (chartId) {
          case 'activityChart':
            option = this._createActivityChartOption(data);
            break;
          case 'genreChart':
            option = this._createGenreChartOption(data);
            break;
          case 'ratingChart':
            option = this._createRatingChartOption(data);
            break;
          case 'trendChart':
            option = this._createTrendChartOption(data);
            break;
          case 'likesAnalysisChart':
            option = this._createLikesAnalysisChartOption(data);
            break;
          case 'radarChart':
            option = this._createRadarChartOption(data);
            break;
          case 'heatmapChart':
            option = this._createHeatmapChartOption(data);
            break;
        }

        if (option) {
          chart.setOption(option);

          // 强制触发resize以确保正确渲染
          setTimeout(() => {
            if (chart && typeof chart.resize === 'function') {
              chart.resize();
              console.log(`[QUANTUM-VIZ] ${chartId}图表大小已调整`);
            }
          }, 100);
        }
      } catch (error) {
        console.error(`[QUANTUM-VIZ] 延迟渲染 ${chartId} 失败:`, error);
        this.showError(chartId, error.message);
      }
    } else {
      // 没有预加载数据，直接渲染
      this.pendingRenders.delete(chartId);
      this.renderChartById(chartId);
    }
  }

  // 获取CSRF令牌
  getCsrfToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
           document.cookie.split('; ')
               .find(row => row.startsWith('csrftoken='))
               ?.split('=')[1];
  }

  // 显示加载状态
  showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="text-center py-5">
        <div class="quantum-spinner"></div>
        <p class="mt-3">量子数据分析中...</p>
      </div>
    `;
  }

  // 初始化所有图表 - 改进版本
  initializeCharts() {
    console.log('[QUANTUM-VIZ] 开始初始化可视化系统...');

    try {
      // 检查ECharts是否可用
      if (typeof echarts === 'undefined') {
        console.error('[QUANTUM-VIZ] ECharts库未加载，尝试动态加载');
        this._loadEChartsLibrary();
        return;
      }

      // 寻找当前激活的面板
      const activePanel = document.querySelector('.viz-panel.active');
      if (activePanel) {
        console.log(`[QUANTUM-VIZ] 找到激活面板: ${activePanel.id}`);

        // 确保激活面板可见
        activePanel.style.display = 'block';
        activePanel.style.visibility = 'visible';
        activePanel.style.opacity = '1';

        // 寻找此面板中的图表容器
        const container = activePanel.querySelector('.chart-container');
        if (container && container.id) {
          console.log(`[QUANTUM-VIZ] 初始化激活面板中的图表: ${container.id}`);

          // 强制设置容器尺寸
          this.ensureContainerReady(container);

          // 仅渲染激活面板中的图表
          this.renderChartById(container.id);
        }
      } else {
        console.warn('[QUANTUM-VIZ] 未找到激活面板，将渲染第一个面板');

        // 如果没有激活面板，激活第一个面板
        const firstPanel = document.querySelector('.viz-panel');
        if (firstPanel) {
          firstPanel.classList.add('active');
          firstPanel.style.display = 'block';
          firstPanel.style.visibility = 'visible';
          firstPanel.style.opacity = '1';

          const container = firstPanel.querySelector('.chart-container');
          if (container && container.id) {
            // 强制设置容器尺寸
            this.ensureContainerReady(container);

            // 渲染此图表
            this.renderChartById(container.id);
          }
        }
      }

      console.log('[QUANTUM-VIZ] 初始化完成，将在切换标签时按需渲染其他图表');

    } catch (error) {
      console.error('[QUANTUM-VIZ] 图表初始化过程中发生严重错误:', error);
    }
  }

  // 动态加载ECharts库
  _loadEChartsLibrary() {
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/echarts/5.4.0/echarts.min.js';
    script.async = true;

    script.onload = () => {
      console.log('[QUANTUM-VIZ] ECharts库加载成功，重新初始化图表');
      setTimeout(() => this.initializeCharts(), 500);
    };

    script.onerror = () => {
      console.error('[QUANTUM-VIZ] ECharts库加载失败');
      this._showGlobalError();
    };

    document.head.appendChild(script);
  }

  // 显示全局错误
  _showGlobalError() {
    const panels = document.querySelectorAll('.viz-panel');
    panels.forEach(panel => {
      const container = panel.querySelector('.chart-container');
      if (container) {
        container.innerHTML = `
          <div class="chart-error">
            <div class="empty-icon">
              <i class="fas fa-exclamation-triangle text-danger"></i>
            </div>
            <h5 class="mt-3">可视化组件加载失败</h5>
            <p class="text-muted">无法加载必要的可视化库，请检查网络连接或刷新页面重试</p>
            <button class="btn btn-primary mt-2" onclick="location.reload()">
              <i class="fas fa-sync-alt me-1"></i>刷新页面
            </button>
          </div>
        `;
      }
    });
  }

  // ======== 图表选项创建方法 - 全部直接作为类方法实现 ========

  // 创建活动图表选项
  _createActivityChartOption(data) {
    return {
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        data: data.map(item => item.name)
      },
      series: [
        {
          name: '用户活动',
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
          data: data.map(item => ({
            value: item.value,
            name: item.name,
            itemStyle: {
              color: item.color
            }
          }))
        }
      ]
    };
  }

  // 创建类型偏好图表选项
  _createGenreChartOption(data) {
    const genres = data.map(item => item.name);
    const values = data.map(item => item.value);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'value',
        boundaryGap: [0, 0.01]
      },
      yAxis: {
        type: 'category',
        data: genres,
        axisLabel: {
          interval: 0,
          rotate: 30
        }
      },
      series: [
        {
          name: '偏好程度',
          type: 'bar',
          data: values.map((value, index) => ({
            value: value,
            itemStyle: {
              color: this.colors.gradients[index % this.colors.gradients.length][0]
            }
          })),
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    };
  }

  // 创建评分分布图表选项
  _createRatingChartOption(data) {
    const ratings = data.map(item => item.rating.toString());
    const counts = data.map(item => item.count);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          crossStyle: {
            color: '#999'
          }
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: ratings,
        axisPointer: {
          type: 'shadow'
        }
      },
      yAxis: {
        type: 'value',
        name: '评分次数',
        minInterval: 1
      },
      series: [
        {
          name: '评分分布',
          type: 'bar',
          data: counts,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#6d28d9' },
              { offset: 1, color: '#8b5cf6' }
            ])
          },
          emphasis: {
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#5b21b6' },
                { offset: 1, color: '#7c3aed' }
              ])
            }
          }
        }
      ]
    };
  }

  // 创建点赞分析图表选项
  _createLikesAnalysisChartOption(data) {
    return {
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        data: data.map(item => item.name)
      },
      series: [
        {
          name: '点赞分析',
          type: 'pie',
          radius: ['40%', '70%'],
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
          data: data.map(item => ({
            value: item.value,
            name: item.name,
            itemStyle: {
              color: item.color || this.colors.gradients[0][0]
            }
          }))
        }
      ]
    };
  }

  // 创建观看趋势图表选项
  _createTrendChartOption(data) {
    const dates = data.map(item => item.date);
    const viewCounts = data.map(item => item.views);
    const ratingCounts = data.map(item => item.ratings);

    return {
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
        data: ['浏览次数', '评分次数']
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
          name: '浏览次数',
          type: 'line',
          stack: 'Total',
          areaStyle: {
            opacity: 0.3,
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(128, 90, 213, 0.8)' },
              { offset: 1, color: 'rgba(128, 90, 213, 0.1)' }
            ])
          },
          emphasis: {
            focus: 'series'
          },
          lineStyle: {
            width: 2
          },
          showSymbol: false,
          smooth: true,
          itemStyle: {
            color: '#6d28d9'
          },
          data: viewCounts
        },
        {
          name: '评分次数',
          type: 'line',
          stack: 'Total',
          areaStyle: {
            opacity: 0.3,
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(16, 185, 129, 0.8)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0.1)' }
            ])
          },
          emphasis: {
            focus: 'series'
          },
          lineStyle: {
            width: 2
          },
          showSymbol: false,
          smooth: true,
          itemStyle: {
            color: '#10b981'
          },
          data: ratingCounts
        }
      ]
    };
  }
  // 创建互动统计图表选项
_createInteractionStatsChartOption(data) {
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      data: data.map(item => item.name)
    },
    series: [
      {
        name: '互动类型',
        type: 'pie',
        radius: ['40%', '70%'],
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
        data: data.map(item => ({
          value: item.value,
          name: item.name,
          itemStyle: {
            color: item.color || this.colors.gradients[0][0]
          }
        }))
      }
    ]
  };
}

  // 创建用户关系网络图选项
_createUserNetworkChartOption(data) {
  // 设置网络节点符号和大小
  data.nodes.forEach(node => {
    node.symbolSize = node.value * 5 + 20; // 节点大小根据值进行缩放
    node.itemStyle = {
      color: node.category === 0 ? this.colors.gradients[0][0] : this.colors.gradients[2][0]
    };
    node.label = {
      show: node.symbolSize > 30 // 只有较大的节点显示标签
    };
  });

  // 设置边的属性
  data.links.forEach(link => {
    link.lineStyle = {
      width: link.value,
      color: link.type === 'reply' ? this.colors.gradients[1][0] : this.colors.gradients[3][0],
      curveness: 0.3 // 添加一些曲度，使边不重叠
    };
  });

  return {
    tooltip: {
      formatter: function(params) {
        if (params.dataType === 'node') {
          return `${params.name}: ${params.value}`;
        }
        return `${params.data.source} → ${params.data.target}: ${params.data.value}`;
      }
    },
    legend: [
      {
        data: ['用户', '互动目标'],
        orient: 'vertical',
        right: 10,
        top: 'center'
      }
    ],
    series: [
      {
        name: '用户互动网络',
        type: 'graph',
        layout: 'force',
        data: data.nodes,
        links: data.links,
        categories: [
          { name: '用户' },
          { name: '互动目标' }
        ],
        roam: true,
        draggable: true,
        label: {
          position: 'right',
          formatter: '{b}'
        },
        force: {
          repulsion: 100,
          edgeLength: [50, 200],
          gravity: 0.1
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 5
          }
        },
        animation: true,
        animationDuration: 1500,
        animationEasingUpdate: 'quinticInOut'
      }
    ]
  };
}
  // 创建互动时间线图表选项
_createInteractionTimelineChartOption(data) {
  // 解析日期
  const dates = data.map(item => item.date);

  // 提取各类型互动数量
  const likes = data.map(item => item.likes || 0);
  const replies = data.map(item => item.replies || 0);
  const mentions = data.map(item => item.mentions || 0);

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      data: ['点赞', '回复', '提及']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45,
        interval: 'auto'
      }
    },
    yAxis: {
      type: 'value',
      name: '互动次数',
      minInterval: 1
    },
    series: [
      {
        name: '点赞',
        type: 'bar',
        stack: 'total',
        emphasis: {
          focus: 'series'
        },
        data: likes,
        itemStyle: {
          color: this.colors.gradients[3][0]
        }
      },
      {
        name: '回复',
        type: 'bar',
        stack: 'total',
        emphasis: {
          focus: 'series'
        },
        data: replies,
        itemStyle: {
          color: this.colors.gradients[1][0]
        }
      },
      {
        name: '提及',
        type: 'bar',
        stack: 'total',
        emphasis: {
          focus: 'series'
        },
        data: mentions,
        itemStyle: {
          color: this.colors.gradients[2][0]
        }
      }
    ]
  };
}
  // 创建互动热力图选项
_createInteractionHeatmapChartOption(data) {
  // 获取用户名称和日期
  const users = data.users;
  const dates = data.dates;

  // 构建热力图数据
  const heatmapData = [];
  data.values.forEach((value, index) => {
    const rowIndex = Math.floor(index / dates.length);
    const colIndex = index % dates.length;
    if (value > 0) {
      heatmapData.push([colIndex, rowIndex, value]);
    }
  });

  return {
    tooltip: {
      position: 'top',
      formatter: function(params) {
        return `${users[params.value[1]]} 在 ${dates[params.value[0]]} 有 ${params.value[2]} 次互动`;
      }
    },
    grid: {
      height: '70%',
      y: '10%'
    },
    xAxis: {
      type: 'category',
      data: dates,
      splitArea: {
        show: true
      },
      axisLabel: {
        rotate: 45,
        interval: 0
      }
    },
    yAxis: {
      type: 'category',
      data: users,
      splitArea: {
        show: true
      }
    },
    visualMap: {
      min: 0,
      max: Math.max(...heatmapData.map(item => item[2])),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127']
      }
    },
    series: [{
      name: '互动热力图',
      type: 'heatmap',
      data: heatmapData,
      label: {
        show: false
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  };
}
  // 创建雷达图选项
  _createRadarChartOption(data) {
    // 最多取前6个类型，避免雷达图过于拥挤
    const topGenres = data.slice(0, 6);

    // 计算最大值，用于数据归一化
    const maxValue = Math.max(...topGenres.map(g => g.value));

    // 生成指标和数据
    const indicators = topGenres.map(g => ({
      name: g.name,
      max: 100
    }));

    const seriesData = topGenres.map(g => ({
      value: Math.round((g.value / maxValue) * 100),
      name: g.name
    }));

    return {
      tooltip: {
        trigger: 'item'
      },
      radar: {
        indicator: indicators,
        splitNumber: 4,
        axisName: {
          color: '#666',
          fontSize: 12,
          fontWeight: 'bold',
          padding: [3, 5]
        },
        splitArea: {
          areaStyle: {
            color: ['rgba(255, 255, 255, 0.5)', 'rgba(240, 240, 240, 0.5)'],
            shadowColor: 'rgba(0, 0, 0, 0.1)',
            shadowBlur: 10
          }
        },
        axisLine: {
          lineStyle: {
            color: 'rgba(0, 0, 0, 0.2)'
          }
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(0, 0, 0, 0.2)'
          }
        }
      },
      series: [
        {
          name: '类型偏好',
          type: 'radar',
          areaStyle: {
            opacity: 0.6,
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(139, 92, 246, 0.8)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0.8)' }
            ])
          },
          lineStyle: {
            width: 2,
            color: '#6d28d9'
          },
          data: [
            {
              value: seriesData.map(item => item.value),
              name: '偏好程度',
              symbol: 'circle',
              symbolSize: 8,
              itemStyle: {
                color: '#6d28d9'
              }
            }
          ]
        }
      ]
    };
  }

  // 创建热力图选项
  _createHeatmapChartOption(data) {
    const genres = data.genres;
    const dimensions = ['浏览量', '评分', '收藏'];

    // 准备热力图数据
    const heatmapData = [];

    // 处理浏览量数据
    data.views.forEach((item, index) => {
      heatmapData.push([0, index, item.value]);
    });

    // 处理评分数据
    data.ratings.forEach((item, index) => {
      heatmapData.push([1, index, item.value]);
    });

    // 处理收藏数据
    data.favorites.forEach((item, index) => {
      heatmapData.push([2, index, item.value]);
    });

    // 计算数据最大值，用于颜色映射
    const maxValue = Math.max(...heatmapData.map(item => item[2]));

    return {
      tooltip: {
        position: 'top',
        formatter: function(params) {
          return `${dimensions[params.value[0]]} - ${genres[params.value[1]]}: ${params.value[2]}`;
        }
      },
      grid: {
        left: '3%',
        right: '7%',
        bottom: '13%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: dimensions,
        splitArea: {
          show: true
        }
      },
      yAxis: {
        type: 'category',
        data: genres,
        splitArea: {
          show: true
        }
      },
      visualMap: {
        min: 0,
        max: maxValue,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '5%',
        inRange: {
          color: [
            '#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127'
          ]
        }
      },
      series: [
        {
          name: '类型热度',
          type: 'heatmap',
          data: heatmapData,
          label: {
            show: true
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    };
  }
}

// 创建全局可视化引擎实例，确保在全局范围内可访问
window.vizEngine = new QuantumVisualizationEngine();

// 页面加载完成后初始化图表
document.addEventListener('DOMContentLoaded', function() {
  // 初始化可视化引擎和图表
  if (document.getElementById('visualizationPanel')) {
    console.log('[QUANTUM-VIZ] 初始化可视化引擎...');

    // 确保引擎实例存在
    if (!window.vizEngine) {
      console.warn('[QUANTUM-VIZ] 引擎实例不存在，重新创建');
      window.vizEngine = new QuantumVisualizationEngine();
    }

    // 延迟初始化以确保DOM已完全加载
    setTimeout(() => {
      window.vizEngine.initializeCharts();
    }, 300);

    // 窗口调整大小时重新渲染图表
    window.addEventListener('resize', function() {
      if (window.vizEngine && window.vizEngine.charts) {
        window.vizEngine.charts.forEach(chart => {
          if (chart) {
            try {
              chart.resize();
            } catch (e) {
              console.warn('[QUANTUM-VIZ] 图表大小调整失败：', e);
            }
          }
        });
      }
    });
  }
});