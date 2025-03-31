/**
 * 量子动漫可视化组件管理器
 * 解决多个可视化组件冲突和资源竞争问题
 */
(function() {
  // 避免重复初始化
  if (window.QuantumVizManager) {
    console.log('可视化组件管理器已初始化');
    return;
  }

  /**
   * 可视化组件管理器
   */
  class VisualizationManager {
    constructor() {
      // 组件注册表
      this.components = {};

      // 活动组件
      this.activeComponents = {};

      // 正在加载的库
      this.loadingLibraries = {};

      // API请求计数和限制
      this.apiRequests = {
        count: 0,
        limit: 3,  // 同时最多3个API请求
        pending: []
      };

      // 初始化
      this.initialize();
    }

    // 在VisualizationManager类中添加
initialize() {
  console.log('初始化可视化组件管理器');

  // 设置标签页监听器
  this.setupTabListeners();

  // 监控窗口大小变化
  window.addEventListener('resize', this.handleResize.bind(this));

  // 创建调试面板（仅开发模式）
  if (this.isDevelopment()) {
    this.createDebugPanel();
  }

  // 注册所有组件
  this.registerAllComponents();

  // 添加页面加载完成后的延迟初始化
  window.addEventListener('load', () => {
    setTimeout(() => {
      // 检查和自动修复未加载的图表
      this.autoFixFailedCharts();
    }, 1500);
  });
}
    // 添加自动修复未加载图表的函数
autoFixFailedCharts() {
  // 检查当前活动标签页中的图表
  const activeTab = document.querySelector('.tab-pane.active');
  if (!activeTab) return;

  // 特别关注互动类型分布和互动趋势图表
  const chartIds = ['interaction-type-chart', 'interaction-trend-chart'];

  // 查找失败的图表（具有错误消息或为空的图表）
  chartIds.forEach(id => {
    const container = document.getElementById(id);
    if (!container) return;

    // 检查容器内容
    const hasError = container.querySelector('.fallback-message') ||
                    container.querySelector('.alert-warning');
    const isEmpty = container.children.length === 0;

    // 如果图表没有正确加载，尝试重新初始化
    if (hasError || isEmpty) {
      console.log(`自动修复图表: ${id}`);
      this.retryComponent(id);
    }
  });
}
    cancelPendingRequests(tabSelector) {
      const tabPane = document.querySelector(tabSelector);
      if (!tabPane) return;

      const containers = tabPane.querySelectorAll('.chart-container, [id$="-chart"]');
      const containerIds = Array.from(containers).map(container => container.id);

      this.apiRequests.pending = this.apiRequests.pending.filter(request => {
        const componentId = request.component.id;
        return !containerIds.includes(componentId);
      });
    }
    // 修改_handleTabShown函数，确保网络标签页正确初始化
_handleTabShown = (event) => {
  const targetId = event.target.getAttribute('href');
  if (!targetId) return;

  console.log(`切换到标签页: ${targetId}`);

  // 网络标签页特殊处理
  if (targetId === '#network') {
    // 强制初始化网络标签页中的所有图表
    setTimeout(() => {
      const containers = document.querySelectorAll('#network .chart-container, #network [id$="-chart"]');
      containers.forEach(container => {
        if (container.id) {
          this.retryComponent(container.id);
        }
      });
    }, 300);
  } else {
    // 其他标签页使用正常处理流程
    this.preloadKnownComponents(targetId);
  }

  // 延迟以允许DOM完全更新
  setTimeout(() => {
    // 停用不可见的组件
    this.deactivateHiddenComponents();

    // 初始化当前标签页中的组件
    this.initializeVisibleComponents(targetId);
  }, 200);
};
    setupTabListeners() {
      // 找到所有标签页触发器
      const tabTriggers = document.querySelectorAll('[data-bs-toggle="pill"], [data-bs-toggle="tab"]');

      // 绑定事件
      tabTriggers.forEach(trigger => {
        // 移除可能已存在的监听器
        trigger.removeEventListener('shown.bs.tab', this._handleTabShown);
        trigger.removeEventListener('hide.bs.tab', this._handleTabHide);

        // 添加新的监听器
        trigger.addEventListener('shown.bs.tab', this._handleTabShown);
        trigger.addEventListener('hide.bs.tab', this._handleTabHide);
      });

      // 更新_handleTabShown函数
      this._handleTabShown = (event) => {
        const targetId = event.target.getAttribute('href');
        if (!targetId) return;

        console.log(`切换到标签页: ${targetId}`);

        // 首先预加载已知组件
        this.preloadKnownComponents(targetId);

        // 延迟以允许DOM完全更新
        setTimeout(() => {
          // 停用不可见的组件
          this.deactivateHiddenComponents();

          // 初始化当前标签页中的组件
          this.initializeVisibleComponents(targetId);
        }, 200);
      };

      // 处理标签页隐藏事件
      this._handleTabHide = (event) => {
        const targetId = event.target.getAttribute('href');
        if (!targetId) return;

        // 取消此标签页的待处理API请求
        this.cancelPendingRequests(targetId);
      };

      // 初始化当前活动标签页中的组件
      const activeTab = document.querySelector('.tab-pane.active');
      if (activeTab) {
        setTimeout(() => {
          this.initializeVisibleComponents('#' + activeTab.id);
        }, 500);
      }
    }

    initializeVisibleComponents(tabSelector) {
      const tabPane = document.querySelector(tabSelector);
      if (!tabPane) return;

      console.log(`初始化标签页 ${tabSelector} 中的组件`);

      // 查找所有可视化容器 - 使用更全面的选择器
      const containers = tabPane.querySelectorAll(
        '.chart-container, .network-container, [id$="-chart"], [id$="-visualization"]'
      );

      // 初始化每个容器
      containers.forEach(container => {
        const id = container.id;
        if (!id) return;

        // 根据ID确定组件类型
        let type = this.determineChartType(id);

        // 注册并激活组件
        this.registerComponent(id, type);

        // 添加小延迟以防止资源争用
        setTimeout(() => {
          this.activateComponent(id);
        }, 50);
      });
    }

    registerAllComponents() {
  // 查找所有可视化容器
  const containers = document.querySelectorAll(
    '.chart-container, .network-container, [id$="-chart"], [id$="-visualization"]'
  );

  console.log(`找到 ${containers.length} 个可视化容器`);

  // 注册每个容器
  containers.forEach(container => {
    const id = container.id;
    if (!id) return;

    // 使用自动检测类型注册
    this.registerComponent(id, this.determineChartType(id));
  });

  // 延迟激活活动标签页中的组件
  setTimeout(() => {
    const activeTab = document.querySelector('.tab-pane.active');
    if (activeTab) {
      // 先处理可见标签页中的可视化
      this.initializeVisibleComponents('#' + activeTab.id);

      // 如果活动标签页是网络标签页，特殊处理
      if (activeTab.id === 'network') {
        setTimeout(() => {
          // 特别关注这两个图表
          ['interaction-type-chart', 'interaction-trend-chart'].forEach(id => {
            if (document.getElementById(id)) {
              this.activateComponent(id);
            }
          });
        }, 600);
      }
    }
  }, 500);
}
    preloadKnownComponents(tabId) {
      // 标签页ID到已知组件ID的映射
      const tabComponentMap = {
        '#overview': ['community-activity-chart'],
        '#network': ['network-visualization', 'interaction-type-chart', 'interaction-trend-chart'],
        '#users': ['user-activity-distribution-chart', 'user-influence-distribution-chart'],
        '#discussions': ['discussion-by-genre-chart', 'discussion-trend-chart']
      };

      // 获取此标签页的组件
      const componentIds = tabComponentMap[tabId] || [];
      if (componentIds.length === 0) return;

      console.log(`预加载标签页 ${tabId} 的已知组件:`, componentIds);

      // 错开注册和激活每个组件
      componentIds.forEach((id, index) => {
        setTimeout(() => {
          if (!this.components[id]) {
            this.registerComponent(id, this.determineChartType(id));
          }

          // 只有当容器存在时才激活
          if (document.getElementById(id)) {
            this.activateComponent(id);
          }
        }, index * 100); // 每个组件延迟100ms
      });
    }

    deactivateHiddenComponents() {
      for (const id in this.activeComponents) {
        const component = this.activeComponents[id];
        const container = document.getElementById(id);

        // 如果容器不存在或不可见，则停用组件
        if (!container || !this.isElementVisible(container)) {
          console.log(`停用隐藏组件: ${id}`);
          this.deactivateComponent(id);
        }
      }
    }

    isElementVisible(element) {
      if (!element) return false;

      // 检查元素是否在文档中
      if (!document.body.contains(element)) return false;

      // 检查元素或其父级是否隐藏
      let current = element;
      while (current) {
        const style = window.getComputedStyle(current);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
          return false;
        }

        // 检查是否在不活动的标签页内
        if (current.classList &&
            current.classList.contains('tab-pane') &&
            !current.classList.contains('active')) {
          return false;
        }

        current = current.parentElement;
      }

      return true;
    }

    registerComponent(id, type, options = {}) {
      if (this.components[id]) return this.components[id];

      // If type is unknown, try to determine it
      if (type === 'unknown') {
        type = this.determineChartType(id);
      }

      console.log(`Registering component: ${id} (${type})`);

      this.components[id] = {
        id,
        type,
        options,
        status: 'registered',
        dependencies: this.getDependencies(type),
        initialized: false,
        instance: null
      };

      return this.components[id];
    }

    activateComponent(id) {
      // If component doesn't exist, try to register it first
      if (!this.components[id]) {
        console.log(`组件 ${id} 不存在，尝试自动注册`);
        this.registerComponent(id, this.determineChartType(id));

        // If registration failed, show error
        if (!this.components[id]) {
          console.error(`未找到组件: ${id}`);

          // Try to find the container and show error
          const container = document.getElementById(id);
          if (container) {
            this.showComponentError(id, '组件初始化失败');
          }
          return;
        }
      }

      const component = this.components[id];

      // If component is already active, don't process again
      if (this.activeComponents[id]) return;

      console.log(`激活组件: ${id} (${component.type})`);

      // Add component to active list
      this.activeComponents[id] = component;

      // Load dependencies
      this.loadDependencies(component)
        .then(() => {
          // Initialize component
          this.initializeComponent(id);
        })
        .catch(error => {
          console.error(`组件 ${id} 依赖加载失败:`, error);
          this.showComponentError(id, '依赖加载失败');
        });
    }

    deactivateComponent(id) {
      if (!this.activeComponents[id]) return;

      console.log(`停用组件: ${id}`);

      const component = this.activeComponents[id];

      // 清理组件资源
      if (component.instance && typeof component.instance.destroy === 'function') {
        try {
          component.instance.destroy();
        } catch (e) {
          console.warn(`组件 ${id} 销毁时出错:`, e);
        }
      }

      // 从活动列表中移除
      delete this.activeComponents[id];

      // 保留组件配置，但重置状态
      component.status = 'registered';
      component.instance = null;
    }

    initializeComponent(id) {
      if (!this.components[id]) return;

      const component = this.components[id];
      const container = document.getElementById(id);

      if (!container) {
        console.error(`组件容器不存在: ${id}`);
        return;
      }

      // 显示加载状态
      this.showLoading(container);

      // 标记状态
      component.status = 'initializing';

      // 根据组件类型初始化
      try {
        if (component.type === 'network') {
          this.initializeNetworkComponent(component, container);
        } else if (component.type.startsWith('chart-')) {
          this.initializeChartComponent(component, container);
        } else {
          console.warn(`未知组件类型: ${component.type}`);
          this.showComponentError(id, '未知组件类型');
        }
      } catch (error) {
        console.error(`初始化组件 ${id} 失败:`, error);
        this.showComponentError(id, `初始化失败: ${error.message}`);
      }
    }

    initializeNetworkComponent(component, container) {
      const id = component.id;

      // 获取控制选项
      const userFocused = document.getElementById('userFocusedToggle')?.checked || true;
      const interactionType = document.getElementById('interactionTypeSelect')?.value || 'all';

      // 构建API URL
      const apiUrl = `/visualizations/api/data/network-data/?user_focused=${userFocused}&interaction_type=${interactionType}`;

      // 发送API请求
      this.queueApiRequest(apiUrl, component, (data) => {
        if (!this.activeComponents[id]) return; // 组件已不再活动

        try {
          if (!data || !data.nodes || !data.links || data.nodes.length === 0) {
            throw new Error('无效的网络数据');
          }

          // 创建网络可视化
          component.instance = this.createNetworkVisualization(container, data);
          component.status = 'active';
          component.initialized = true;

          // 绑定控制事件
          this.bindNetworkControls(component);

          console.log(`网络组件 ${id} 初始化完成`);
        } catch (error) {
          console.error(`渲染网络组件 ${id} 失败:`, error);

          // 尝试使用模拟数据
          try {
            const mockData = this.generateMockNetworkData();
            component.instance = this.createNetworkVisualization(container, mockData, true);
            component.status = 'active-mock';
            component.initialized = true;

            // 显示模拟数据提示
            this.showMockDataAlert(container);

            // 绑定控制事件
            this.bindNetworkControls(component);

            console.log(`网络组件 ${id} 使用模拟数据初始化`);
          } catch (mockError) {
            console.error(`使用模拟数据渲染失败:`, mockError);
            this.showComponentError(id, '渲染失败');
          }
        }
      });
    }

    // 修复的图表初始化方法
    initializeChartComponent(component, container) {
      const id = component.id;
      let apiUrl = '';

      // 扩展图表类型检测
      if (id.includes('rating-distribution')) {
        apiUrl = '/visualizations/api/data/rating-distribution/';
      } else if (id.includes('genre-preference')) {
        apiUrl = '/visualizations/api/data/genre-preference/';
      } else if (id.includes('viewing-trends') || id.includes('trend')) {
        apiUrl = '/visualizations/api/data/viewing-trends/';
      } else if (id.includes('activity-summary')) {
        apiUrl = '/visualizations/api/data/activity-summary/';
      } else if (id.includes('community-activity')) {
        apiUrl = '/visualizations/api/data/community-activity/';
        component.type = 'chart-trend';
      } else if (id.includes('interaction-type')) {
        apiUrl = '/visualizations/api/data/interaction-stats/';
        component.type = 'chart-pie'; // 将类型更改为饼图, 因为数据是互动类型分布
        component.dataKey = 'interactionByType'; // 指定数据键
      } else if (id.includes('interaction-trend')) {
        apiUrl = '/visualizations/api/data/interaction-stats/';
        component.type = 'chart-trend';
        component.dataKey = 'interactionTrend'; // 指定数据键
      } else if (id.includes('discussion-by-genre')) {
        apiUrl = '/visualizations/api/data/discussion-stats/';
        component.type = 'chart-distribution';
        component.dataKey = 'discussionByGenre'; // 指定数据键
      } else if (id.includes('discussion-trend')) {
        apiUrl = '/visualizations/api/data/discussion-stats/';
        component.type = 'chart-trend';
        component.dataKey = 'discussionTrend'; // 指定数据键
      } else if (id.includes('user-activity-distribution') || id.includes('user-influence-distribution')) {
        apiUrl = '/visualizations/api/data/user-distribution/';
        component.type = 'chart-distribution';

        // 针对不同用户分布图指定不同的数据键
        if (id.includes('activity')) {
          component.dataKey = 'activityDistribution';
        } else {
          component.dataKey = 'influenceDistribution';
        }
      } else if (id.includes('recommendation-factors')) {
        apiUrl = '/visualizations/api/data/recommendation-insights/';
        component.dataKey = 'recommendationFactors';
      } else {
        console.warn(`未知图表类型: ${id}`);
        this.showComponentError(id, '未知图表类型');
        return;
      }

      // 发送API请求
      this.queueApiRequest(apiUrl, component, (data) => {
        if (!this.activeComponents[id]) return; // 组件已不再活动

        try {
          // 从响应中提取正确的数据部分
          const chartData = this.extractChartData(data, component);

          // 根据图表类型渲染
          component.instance = this.createChartVisualization(container, chartData, component.type);
          component.status = 'active';
          component.initialized = true;

          console.log(`图表组件 ${id} 初始化完成`);
        } catch (error) {
          console.error(`渲染图表组件 ${id} 失败:`, error);

          try {
            // 尝试创建模拟数据并显示
            const mockData = this.generateMockChartData(component.type);
            component.instance = this.createChartVisualization(container, mockData, component.type);
            component.status = 'active-mock';
            component.initialized = true;

            // 显示模拟数据提示
            this.showMockDataAlert(container);

            console.log(`图表组件 ${id} 使用模拟数据初始化`);
          } catch (mockError) {
            console.error(`使用模拟数据渲染失败:`, mockError);
            this.showComponentError(id, '渲染失败');
          }
        }
      });
    }

    // 新增方法: 从响应中提取正确的数据部分
    extractChartData(data, component) {
      if (!data) {
        throw new Error('没有数据');
      }

      // 如果数据已经是数组，不需要额外处理
      if (Array.isArray(data)) {
        return data;
      }

      // 如果有指定数据键，并且存在，则返回该部分数据
      if (component.dataKey && data[component.dataKey]) {
        return data[component.dataKey];
      }

      // 针对不同图表类型的特殊处理
      if (component.type === 'chart-pie' && data.interactionByType) {
        return data.interactionByType;
      } else if (component.type === 'chart-trend' && data.interactionTrend) {
        return data.interactionTrend;
      } else if (component.id.includes('discussion-by-genre') && data.discussionByGenre) {
        return data.discussionByGenre;
      } else if (component.id.includes('discussion-trend') && data.discussionTrend) {
        return data.discussionTrend;
      }

      // 尝试智能识别可能的数据结构
      for (const key in data) {
        if (Array.isArray(data[key]) && data[key].length > 0) {
          return data[key];
        }
      }

      // 如果没有找到合适的数据，则抛出错误
      throw new Error('无法提取图表数据');
    }

    // 新增方法: 生成不同类型的模拟图表数据
    generateMockChartData(type) {
      if (type === 'chart-distribution' || type === 'chart-pie') {
        // 生成分布/饼图数据
        return [
          { name: '类别1', value: 45 },
          { name: '类别2', value: 30 },
          { name: '类别3', value: 15 },
          { name: '类别4', value: 10 }
        ];
      } else if (type === 'chart-trend') {
        // 生成趋势数据
        const result = [];
        const today = new Date();

        for (let i = 0; i < 10; i++) {
          const date = new Date();
          date.setDate(today.getDate() - 9 + i);

          result.push({
            date: date.toISOString().split('T')[0],
            value: Math.floor(Math.random() * 50) + 10
          });
        }

        return result;
      } else {
        // 默认数据
        return [
          { name: '示例1', value: 25 },
          { name: '示例2', value: 40 },
          { name: '示例3', value: 35 }
        ];
      }
    }

    queueApiRequest(url, component, callback) {
      const request = {
        url,
        component,
        callback,
        timestamp: Date.now()
      };

      // 添加到队列
      this.apiRequests.pending.push(request);

      // 处理队列
      this.processApiQueue();
    }

    processApiQueue() {
      // 如果没有等待的请求，返回
      if (this.apiRequests.pending.length === 0) return;

      // 如果已达到并发限制，返回
      if (this.apiRequests.count >= this.apiRequests.limit) return;

      // 获取下一个请求
      const request = this.apiRequests.pending.shift();

      // 增加计数
      this.apiRequests.count++;

      // 显示加载状态
      const container = document.getElementById(request.component.id);
      if (container) {
        this.showLoading(container);
      }

      // 设置超时
      const timeoutId = setTimeout(() => {
        console.warn(`API请求超时: ${request.url}`);

        // 减少计数
        this.apiRequests.count--;

        // 调用回调，传入null数据
        request.callback(null);

        // 继续处理队列
        this.processApiQueue();
      }, 15000);

      // 发送请求
      fetch(request.url)
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP错误! 状态: ${response.status}`);
          }
          return response.json();
        })
        .then(responseData => {
          // 清除超时
          clearTimeout(timeoutId);

          // 减少计数
          this.apiRequests.count--;

          // 调用回调
          if (responseData.success) {
            request.callback(responseData.data);
          } else {
            console.error(`API响应错误: ${responseData.error}`);
            request.callback(null);
          }

          // 继续处理队列
          this.processApiQueue();
        })
        .catch(error => {
          // 清除超时
          clearTimeout(timeoutId);

          // 减少计数
          this.apiRequests.count--;

          // 记录错误
          console.error(`API请求失败: ${request.url}`, error);

          // 调用回调，传入null数据
          request.callback(null);

          // 继续处理队列
          this.processApiQueue();
        });
    }

    loadDependencies(component) {
      const dependencies = component.dependencies;

      // 如果没有依赖，直接返回
      if (!dependencies || dependencies.length === 0) {
        return Promise.resolve();
      }

      // 创建Promise数组
      const promises = dependencies.map(dep => this.loadLibrary(dep));

      // 等待所有依赖加载完成
      return Promise.all(promises);
    }

    loadLibrary(url) {
      // 如果库已加载，直接返回
      if (this.isLibraryLoaded(url)) {
        return Promise.resolve();
      }

      // 如果库正在加载，返回现有Promise
      if (this.loadingLibraries[url]) {
        return this.loadingLibraries[url];
      }

      // 创建加载Promise
      const loadPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = url;
        script.async = true;

        script.onload = () => {
          console.log(`库加载成功: ${url}`);
          delete this.loadingLibraries[url];
          resolve();
        };

        script.onerror = () => {
          console.error(`库加载失败: ${url}`);
          delete this.loadingLibraries[url];
          reject(new Error(`无法加载库: ${url}`));
        };

        document.head.appendChild(script);
      });

      // 存储加载Promise
      this.loadingLibraries[url] = loadPromise;

      return loadPromise;
    }

    isLibraryLoaded(url) {
      // D3.js
      if (url.includes('d3') && typeof d3 !== 'undefined') {
        return true;
      }

      // Chart.js
      if (url.includes('chart') && typeof Chart !== 'undefined') {
        return true;
      }

      // 检查是否在文档中
      const scripts = document.querySelectorAll('script');
      for (let i = 0; i < scripts.length; i++) {
        if (scripts[i].src.includes(url)) {
          return true;
        }
      }

      return false;
    }

    getDependencies(type) {
      const dependencies = [];

      if (type === 'network') {
        dependencies.push('https://cdn.jsdelivr.net/npm/d3@7');
      } else if (type.startsWith('chart-')) {
        dependencies.push('https://cdn.jsdelivr.net/npm/chart.js');
      }

      return dependencies;
    }

    showLoading(container) {
      if (!container) return;

      container.innerHTML = `
        <div class="d-flex justify-content-center align-items-center" style="height: 100%; min-height: 200px;">
          <div class="text-center">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">加载中...</span>
            </div>
            <p class="mt-3">加载数据中...</p>
          </div>
        </div>
      `;
    }

    showComponentError(id, message) {
      const container = document.getElementById(id);
      if (!container) return;

      container.innerHTML = `
        <div class="d-flex justify-content-center align-items-center" style="height: 100%; min-height: 200px;">
          <div class="text-center">
            <div class="text-danger mb-3">
              <i class="fas fa-exclamation-triangle fa-3x"></i>
            </div>
            <h5>可视化加载失败</h5>
            <p class="text-muted">${message}</p>
            <button class="btn btn-primary retry-viz-btn" data-viz-id="${id}">
              <i class="fas fa-sync-alt me-1"></i>重试
            </button>
          </div>
        </div>
      `;

      // 绑定重试按钮
      const retryBtn = container.querySelector('.retry-viz-btn');
      if (retryBtn) {
        retryBtn.addEventListener('click', () => {
          this.retryComponent(id);
        });
      }
    }

    showMockDataAlert(container) {
      if (!container) return;

      const alertDiv = document.createElement('div');
      alertDiv.className = 'alert alert-info alert-dismissible fade show position-absolute top-0 start-0 m-3';
      alertDiv.style.zIndex = '100';
      alertDiv.style.maxWidth = 'calc(100% - 2rem)';
      alertDiv.innerHTML = `
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        <i class="fas fa-info-circle me-2"></i>
        当前显示的是模拟数据，可能与实际情况不符。
      `;

      // 添加提示到容器
      container.style.position = 'relative';
      container.appendChild(alertDiv);
    }

    retryComponent(id) {
      console.log(`重试组件: ${id}`);

      // 停用组件
      this.deactivateComponent(id);

      // 重新激活
      this.activateComponent(id);
    }

    handleResize() {
      // 为活动组件触发resize事件
      for (const id in this.activeComponents) {
        const component = this.activeComponents[id];

        if (component.instance && typeof component.instance.resize === 'function') {
          try {
            component.instance.resize();
          } catch (e) {
            console.warn(`组件 ${id} resize时出错:`, e);
          }
        }
      }
    }

    bindNetworkControls(component) {
      const userFocusedToggle = document.getElementById('userFocusedToggle');
      const interactionTypeSelect = document.getElementById('interactionTypeSelect');

      if (userFocusedToggle) {
        userFocusedToggle.addEventListener('change', () => {
          this.retryComponent(component.id);
        });
      }

      if (interactionTypeSelect) {
        interactionTypeSelect.addEventListener('change', () => {
          this.retryComponent(component.id);
        });
      }
    }

    createNetworkVisualization(container, data, isMockData = false) {
      // 清空容器
      container.innerHTML = '';

      // 从原生D3.js创建网络可视化
      const width = container.clientWidth || 800;
      const height = 600;

      // 创建SVG元素
      const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('class', 'network-svg')
        .attr('data-is-mock', isMockData);

      // 创建箭头标记
      svg.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '-0 -5 10 10')
        .attr('refX', 15)
        .attr('refY', 0)
        .attr('orient', 'auto')
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .append('svg:path')
        .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
        .attr('fill', '#999');

      // 创建力导向图
      const simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links).id(d => d.id).distance(150))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => (d.size || 10) + 5));

      // 创建连接
      const link = svg.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(data.links)
        .enter().append('line')
        .attr('stroke-width', d => Math.max(1, d.width || 1))
        .attr('stroke', d => this.getLinkColor(d))
        .attr('marker-end', d => d.type === 'reply' ? 'url(#arrowhead)' : '');

      // 创建节点
      const node = svg.append('g')
        .attr('class', 'nodes')
        .selectAll('circle')
        .data(data.nodes)
        .enter().append('circle')
        .attr('r', d => d.size || 10)
        .attr('fill', d => this.getNodeColor(d))
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
        .call(d3.drag()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended))
        .on('mouseover', function(event, d) {
          // 显示工具提示
          d3.select('.network-tooltip')
            .transition()
            .duration(200)
            .style('opacity', .9);

          d3.select('.network-tooltip')
            .html(`
              <div style="font-weight: bold">${d.username || `用户 ${d.id}`}</div>
              <div>影响力: ${d.influence || 0}</div>
              <div>活跃度: ${d.activity || 0}</div>
            `)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function() {
          // 隐藏工具提示
          d3.select('.network-tooltip')
            .transition()
            .duration(500)
            .style('opacity', 0);
        });

      // 创建标签
      const label = svg.append('g')
        .attr('class', 'labels')
        .selectAll('text')
        .data(data.nodes)
        .enter().append('text')
        .text(d => d.username || `用户 ${d.id}`)
        .attr('font-size', 10)
        .attr('dx', 12)
        .attr('dy', 4);

      // 创建工具提示
      if (!document.querySelector('.network-tooltip')) {
        d3.select('body').append('div')
          .attr('class', 'network-tooltip')
          .style('opacity', 0)
          .style('position', 'absolute')
          .style('background', 'rgba(15, 23, 42, 0.8)')
          .style('color', 'white')
          .style('padding', '8px 12px')
          .style('border-radius', '6px')
          .style('font-size', '0.8rem')
          .style('pointer-events', 'none')
          .style('z-index', 1000);
      }

      // 定义拖拽行为
      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }

      // 更新位置
      simulation.on('tick', () => {
        link
          .attr('x1', d => d.source.x)
          .attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x)
          .attr('y2', d => d.target.y);

        node
          .attr('cx', d => d.x = Math.max(d.size || 10, Math.min(width - (d.size || 10), d.x)))
          .attr('cy', d => d.y = Math.max(d.size || 10, Math.min(height - (d.size || 10), d.y)));

        label
          .attr('x', d => d.x)
          .attr('y', d => d.y);
      });

      // 返回网络可视化对象
      return {
        svg,
        simulation,
        container,
        width,
        height,

        // 销毁方法
        destroy() {
          // 停止模拟
          if (simulation) simulation.stop();

          // 移除事件监听器
          if (node) {
            node.on('mouseover', null)
              .on('mouseout', null)
              .call(d3.drag().on('start', null).on('drag', null).on('end', null));
          }

          // 清空容器
          if (container) container.innerHTML = '';
        },

        // 调整大小
        resize() {
          const newWidth = container.clientWidth || width;

          if (newWidth !== width) {
            svg.attr('width', newWidth);
            simulation.force('center', d3.forceCenter(newWidth / 2, height / 2));
            simulation.alpha(0.3).restart();
          }
        }
      };
    }

    createChartVisualization(container, data, type) {
      // 清空容器
      container.innerHTML = '';

      // 创建Canvas元素
      const canvas = document.createElement('canvas');
      container.appendChild(canvas);

      // 验证Chart.js是否可用
      if (typeof Chart === 'undefined') {
        throw new Error('Chart.js未加载');
      }

      // 图表配置
      let chartConfig;

      // 根据类型创建不同的图表
      switch (type) {
        case 'chart-distribution':
          chartConfig = this.createDistributionChartConfig(data);
          break;
        case 'chart-trend':
          chartConfig = this.createTrendChartConfig(data);
          break;
        case 'chart-pie':
          chartConfig = this.createPieChartConfig(data);
          break;
        default:
          chartConfig = this.createGenericChartConfig(data);
      }

      // 创建图表
      const chart = new Chart(canvas, chartConfig);

      // 返回图表对象
      return {
        chart,
        container,

        // 销毁方法
        destroy() {
          if (chart) chart.destroy();
          if (container) container.innerHTML = '';
        },

        // 调整大小
        resize() {
          if (chart) chart.resize();
        }
      };
    }

    createDistributionChartConfig(data) {
      // 验证数据
      if (!data || !Array.isArray(data) || data.length === 0) {
        throw new Error('无效的分布图数据');
      }

      // 提取标签和数据
      let labels, values;

      if (data[0].hasOwnProperty('rating') && data[0].hasOwnProperty('count')) {
        labels = data.map(item => `${item.rating}星`);
        values = data.map(item => item.count);
      } else if (data[0].hasOwnProperty('name') && data[0].hasOwnProperty('value')) {
        labels = data.map(item => item.name);
        values = data.map(item => item.value);
      } else {
        throw new Error('未知的数据格式');
      }

      // 图表配置
      return {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: '分布',
            data: values,
            backgroundColor: [
              '#6d28d9', '#8b5cf6', '#10b981', '#3b82f6', '#f97316'
            ],
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            }
          },
          scales: {
            y: {
              beginAtZero: true
            }
          }
        }
      };
    }

    // 新增饼图配置创建方法
    createPieChartConfig(data) {
      // 验证数据
      if (!data || !Array.isArray(data) || data.length === 0) {
        throw new Error('无效的饼图数据');
      }

      // 提取标签和数据
      let labels, values;

      if (data[0].hasOwnProperty('name') && data[0].hasOwnProperty('value')) {
        labels = data.map(item => item.name);
        values = data.map(item => item.value);
      } else {
        throw new Error('未知的数据格式');
      }

      // 图表配置
      return {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: values,
            backgroundColor: [
              '#6d28d9', '#8b5cf6', '#10b981', '#3b82f6', '#f97316',
              '#ef4444', '#ec4899', '#84cc16', '#fbbf24', '#06b6d4'
            ],
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'right'
            }
          }
        }
      };
    }

    createTrendChartConfig(data) {
      // 验证数据
      if (!data || !Array.isArray(data) || data.length === 0) {
        throw new Error('无效的趋势图数据');
      }

      // 格式化日期
      const formatDate = (dateStr) => {
        try {
          const date = new Date(dateStr);
          if (isNaN(date.getTime())) return dateStr;
          return `${date.getMonth() + 1}/${date.getDate()}`;
        } catch (e) {
          return dateStr;
        }
      };

      // 提取标签和数据集
      let labels, datasets;

      // 处理不同的数据结构
      if (data[0].hasOwnProperty('date')) {
        // 单系列趋势数据
        labels = data.map(item => formatDate(item.date));
        datasets = [];

        // 动态创建数据集，基于可用属性
        const dataProps = Object.keys(data[0]).filter(key =>
          key !== 'date' && typeof data[0][key] === 'number');

        const colors = ['#6d28d9', '#10b981', '#3b82f6', '#f97316', '#ef4444'];

        dataProps.forEach((prop, index) => {
          datasets.push({
            label: this.formatLabel(prop),
            data: data.map(item => item[prop] || 0),
            borderColor: colors[index % colors.length],
            backgroundColor: `rgba(${this.hexToRgb(colors[index % colors.length])}, 0.2)`,
            tension: 0.4,
            fill: true
          });
        });
      } else if (data[0].hasOwnProperty('x') && data[0].hasOwnProperty('y')) {
        // x/y 格式数据
        labels = data.map(item => formatDate(item.x));
        datasets = [{
          label: '趋势',
          data: data.map(item => item.y),
          borderColor: '#6d28d9',
          backgroundColor: 'rgba(109, 40, 217, 0.2)',
          tension: 0.4,
          fill: true
        }];
      } else {
        // 可能是多系列数据
        throw new Error('未知的趋势数据格式');
      }

      // 图表配置
      return {
        type: 'line',
        data: {
          labels: labels,
          datasets: datasets
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'top'
            }
          },
          scales: {
            y: {
              beginAtZero: true
            }
          }
        }
      };
    }

    formatLabel(key) {
      // 将驼峰命名或下划线命名转换为标题大小写
      return key
        .replace(/([A-Z])/g, ' $1')
        .replace(/_/g, ' ')
        .replace(/^./, str => str.toUpperCase());
    }

    hexToRgb(hex) {
      // 移除#符号
      hex = hex.replace('#', '');

      // 解析16进制值
      const r = parseInt(hex.substring(0, 2), 16);
      const g = parseInt(hex.substring(2, 4), 16);
      const b = parseInt(hex.substring(4, 6), 16);

      return `${r}, ${g}, ${b}`;
    }

    createGenericChartConfig(data) {
      // 尝试智能创建合适的图表
      if (!data) {
        throw new Error('无数据');
      }

      if (Array.isArray(data)) {
        if (data.length === 0) {
          throw new Error('空数据数组');
        }

        if (data[0].hasOwnProperty('name') && data[0].hasOwnProperty('value')) {
          // 键值对格式 - 适合条形图或饼图
          return this.createPieChartConfig(data);
        } else if (data[0].hasOwnProperty('date') || (data[0].hasOwnProperty('x') && data[0].hasOwnProperty('y'))) {
          // 趋势数据
          return this.createTrendChartConfig(data);
        }
      } else if (typeof data === 'object') {
        // 尝试创建普通条形图
        const labels = [];
        const values = [];

        for (const key in data) {
          if (typeof data[key] === 'number') {
            labels.push(key);
            values.push(data[key]);
          }
        }

        if (labels.length > 0) {
          return {
            type: 'bar',
            data: {
              labels: labels,
              datasets: [{
                data: values,
                backgroundColor: '#6d28d9'
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false
            }
          };
        }
      }

      throw new Error('无法确定数据类型');
    }

    determineChartType(id) {
      // 映射规则扩展
      const chartTypeMap = [
        { pattern: 'community-activity', type: 'chart-trend' },
        { pattern: 'interaction-type', type: 'chart-pie' },
        { pattern: 'interaction-trend', type: 'chart-trend' },
        { pattern: 'distribution', type: 'chart-distribution' },
        { pattern: 'trend', type: 'chart-trend' },
        { pattern: 'discussion-by-genre', type: 'chart-distribution' },
        { pattern: 'discussion-trend', type: 'chart-trend' },
        { pattern: 'network', type: 'network' }
      ];

      // 查找匹配规则
      for (const mapping of chartTypeMap) {
        if (id.includes(mapping.pattern)) {
          return mapping.type;
        }
      }

      return 'chart-generic'; // 默认类型
    }

    getNodeColor(node) {
      const influence = node.influence || 0;
      const activity = node.activity || 0;
      const total = influence + activity;

      if (total > 150) return '#6d28d9';  // 高影响力+活跃度
      if (influence > 80) return '#8b5cf6';  // 高影响力
      if (activity > 80) return '#4f46e5';  // 高活跃度

      return '#a78bfa';  // 普通用户
    }

    getLinkColor(link) {
      const colors = {
        like: '#ef4444',
        reply: '#3b82f6',
        mention: '#10b981',
        follow: '#f97316'
      };

      return colors[link.type] || '#999';
    }

    generateMockNetworkData() {
      // 生成节点
      const nodes = [];
      for (let i = 1; i <= 20; i++) {
        nodes.push({
          id: i.toString(),
          username: `用户${i}`,
          influence: Math.floor(Math.random() * 100),
          activity: Math.floor(Math.random() * 100),
          size: Math.floor(Math.random() * 8) + 8
        });
      }

      // 生成连接
      const links = [];
      const types = ['like', 'reply', 'mention', 'follow'];

      for (let i = 0; i < 30; i++) {
        const source = Math.floor(Math.random() * nodes.length) + 1;
        let target = Math.floor(Math.random() * nodes.length) + 1;

        // 确保source和target不同
        while (target === source) {
          target = Math.floor(Math.random() * nodes.length) + 1;
        }

        links.push({
          source: source.toString(),
          target: target.toString(),
          type: types[Math.floor(Math.random() * types.length)],
          strength: Math.floor(Math.random() * 5) + 1,
          width: Math.floor(Math.random() * 3) + 1
        });
      }

      return { nodes, links };
    }
  }

  // 初始化并保存到全局
  window.QuantumVizManager = new VisualizationManager();
})();

/**
 * 应用可视化管理器解决冲突
 * 在页面加载完成后运行
 */
document.addEventListener('DOMContentLoaded', function() {
  // 确保只在社区分析页面执行
  if (!document.querySelector('.quantum-dashboard') ||
      !document.querySelector('.tab-content')) {
    return;
  }

  console.log('应用可视化冲突解决方案');

  // CSS 冲突修复
  const fixStyleConflicts = () => {
    // 创建样式元素
    const style = document.createElement('style');
    style.textContent = `
      /* 确保网络可视化容器有正确的高度 */
      #network-visualization {
        height: 600px;
        width: 100%;
        position: relative;
      }
      
      /* 修复图表位置 */
      .chart-container {
        position: relative;
        height: 300px;
        width: 100%;
      }
      
      /* 修复标签页内容区域 */
      .tab-pane {
        transition: opacity 0.15s linear;
      }
      
      /* 修复工具提示位置 */
      .network-tooltip {
        z-index: 1070 !important;
      }
      
      /* 修复SVG内部文本样式 */
      .network-svg text {
        fill: #1e293b;
        font-family: system-ui, -apple-system, sans-serif;
      }
      
      /* 深色主题兼容 */
      [data-theme="dark"] .network-svg text {
        fill: #f8fafc;
      }
    `;

    document.head.appendChild(style);
  };

  // 执行修复
  fixStyleConflicts();
});