/**
 * 社区分析页面标签页管理脚本
 * 处理标签页切换和图表初始化逻辑
 */
(function() {
  // 确保脚本只在社区分析页面上执行
  if (!document.getElementById('community-analysis-page')) {
    return;
  }

  console.log('[社区分析] 初始化标签页管理器');

  /**
   * 标签页管理类
   */
  class CommunityTabManager {
    constructor() {
      // 状态跟踪
      this.initialized = false;
      this.currentTab = 'overview';
      this.loadedTabs = {
        overview: false,
        users: false,
        discussions: false,
        network: false
      };

      // 初始化
      this.init();
    }

    /**
     * 初始化标签页
     */
    init() {
      // 防止重复初始化
      if (this.initialized) return;

      // 标签切换监听器
      this.setupTabListeners();

      // 初始化当前激活的标签页
      this.initializeActiveTab();

      // 启用查看更多按钮
      this.setupViewMoreButtons();

      // 修复兼容性问题
      this.fixCompatibilityIssues();

      // 注册所有图表
      this.registerCharts();

      // 标记为已初始化
      this.initialized = true;
    }

    /**
     * 设置标签切换监听器
     */
    setupTabListeners() {
      // 找到所有标签切换器
      const tabTriggers = document.querySelectorAll('#communityTabs .nav-link');

      // 为每个切换器添加事件监听器
      tabTriggers.forEach(tab => {
        // 确保事件不会重复绑定
        tab.removeEventListener('shown.bs.tab', this._handleTabShown);
        tab.removeEventListener('click', this._handleTabClick);

        // 添加Bootstrap事件监听（如果可用）
        if (typeof bootstrap !== 'undefined') {
          tab.addEventListener('shown.bs.tab', (event) => this._handleTabShown(event));
        } else {
          // 否则添加点击事件
          tab.addEventListener('click', (event) => this._handleTabClick(event));
        }
      });
    }

    /**
     * 处理Bootstrap标签页显示事件
     * @param {Event} event
     */
    _handleTabShown(event) {
      // 获取目标标签页ID
      const targetId = event.target.getAttribute('id');
      const tabName = targetId.replace('-tab', '');

      console.log(`[社区分析] 激活标签页: ${tabName}`);

      // 更新当前标签页
      window.communityTabManager.currentTab = tabName;

      // 检查并初始化标签页内容
      window.communityTabManager.initializeTabContent(tabName);
    }

    /**
     * 处理标签页点击事件（当Bootstrap不可用时）
     * @param {Event} event
     */
    _handleTabClick(event) {
      event.preventDefault();

      // 获取目标标签页和内容面板
      const tab = event.currentTarget;
      const targetId = tab.getAttribute('data-bs-target') || tab.getAttribute('href');
      const tabName = tab.getAttribute('id').replace('-tab', '');

      // 如果已经激活，不做任何操作
      if (tab.classList.contains('active')) return;

      // 手动激活标签页
      this._activateTab(tab, targetId, tabName);
    }

    /**
     * 手动激活标签页
     * @param {HTMLElement} tab 要激活的标签页元素
     * @param {string} targetId 目标内容面板ID
     * @param {string} tabName 标签页名称
     */
    _activateTab(tab, targetId, tabName) {
      // 更新当前标签页
      this.currentTab = tabName;
      console.log(`[社区分析] 激活标签页: ${tabName}`);

      // 停用所有标签页
      document.querySelectorAll('#communityTabs .nav-link').forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });

      // 停用所有内容面板
      document.querySelectorAll('#communityTabsContent .tab-pane').forEach(p => {
        p.classList.remove('show', 'active');
      });

      // 激活选中的标签页
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');

      // 激活对应的内容面板
      const targetPane = document.querySelector(targetId);
      if (targetPane) {
        targetPane.classList.add('show', 'active');

        // 触发自定义事件
        targetPane.dispatchEvent(new Event('tab-activated'));
      }

      // 检查并初始化标签页内容
      this.initializeTabContent(tabName);
    }

    /**
     * 初始化当前激活的标签页
     */
    initializeActiveTab() {
      // 查找当前激活的标签页
      const activeTab = document.querySelector('#communityTabs .nav-link.active');
      if (activeTab) {
        const tabName = activeTab.getAttribute('id').replace('-tab', '');
        this.currentTab = tabName;

        // 初始化内容
        setTimeout(() => {
          this.initializeTabContent(tabName);
        }, 100);
      }
    }

    /**
     * 初始化标签页内容
     * @param {string} tabName 标签页名称
     */
    initializeTabContent(tabName) {
      // 如果已加载，则不重复加载
      if (this.loadedTabs[tabName]) return;

      // 标记为已加载
      this.loadedTabs[tabName] = true;

      console.log(`[社区分析] 初始化标签页内容: ${tabName}`);

      // 根据标签页类型加载不同图表
      switch (tabName) {
        case 'overview':
          this.initializeOverviewTab();
          break;
        case 'users':
          this.initializeUsersTab();
          break;
        case 'discussions':
          this.initializeDiscussionsTab();
          break;
        case 'network':
          this.initializeNetworkTab();
          break;
      }
    }

    /**
     * 设置"查看更多"按钮功能
     */
    setupViewMoreButtons() {
      // 获取按钮
      const viewMoreActiveUsersBtn = document.getElementById('viewMoreActiveUsers');
      const viewMoreHotDiscussionsBtn = document.getElementById('viewMoreHotDiscussions');

      // 为"查看更多活跃用户"按钮添加事件
      if (viewMoreActiveUsersBtn) {
        viewMoreActiveUsersBtn.addEventListener('click', (e) => {
          e.preventDefault();
          this.switchToTab('users');
        });
      }

      // 为"查看更多热门讨论"按钮添加事件
      if (viewMoreHotDiscussionsBtn) {
        viewMoreHotDiscussionsBtn.addEventListener('click', (e) => {
          e.preventDefault();
          this.switchToTab('discussions');
        });
      }
    }

    /**
     * 切换到指定标签页
     * @param {string} tabName 标签页名称
     */
    switchToTab(tabName) {
      // 获取标签页元素
      const tabEl = document.getElementById(`${tabName}-tab`);
      if (!tabEl) return;

      console.log(`[社区分析] 切换到标签页: ${tabName}`);

      // 检查Bootstrap是否可用
      if (typeof bootstrap !== 'undefined' && bootstrap.Tab) {
        // 使用Bootstrap激活标签页
        const tab = new bootstrap.Tab(tabEl);
        tab.show();
      } else {
        // 手动激活标签页
        const targetId = tabEl.getAttribute('data-bs-target') || tabEl.getAttribute('href');
        this._activateTab(tabEl, targetId, tabName);
      }
    }

    /**
     * 修复兼容性问题
     */
    fixCompatibilityIssues() {
      // 确保所有标签页内容元素都有正确的ARIA属性
      document.querySelectorAll('#communityTabsContent .tab-pane').forEach((pane, index) => {
        const id = pane.getAttribute('id');
        const tabId = `${id}-tab`;

        // 设置ARIA属性
        pane.setAttribute('aria-labelledby', tabId);

        // 确保第一个标签页激活
        if (index === 0 && !pane.classList.contains('active')) {
          pane.classList.add('show', 'active');
        }
      });
    }

    /**
     * 注册所有图表组件
     */
    registerCharts() {
      // 所有图表ID和类型的映射
      const charts = [
        { id: 'community-activity-chart', type: 'chart-trend' },
        { id: 'user-activity-distribution-chart', type: 'chart-bar' },
        { id: 'user-influence-distribution-chart', type: 'chart-bar' },
        { id: 'discussion-by-genre-chart', type: 'chart-bar' },
        { id: 'discussion-trend-chart', type: 'chart-trend' },
        { id: 'interaction-type-chart', type: 'chart-pie' },
        { id: 'interaction-trend-chart', type: 'chart-trend' },
        { id: 'network-visualization', type: 'network' }
      ];

      // 使用可视化管理器注册组件（如果可用）
      if (window.QuantumVizManager) {
        charts.forEach(chart => {
          if (document.getElementById(chart.id)) {
            window.QuantumVizManager.registerComponent(chart.id, chart.type);
          }
        });
      }
    }

    /**
     * 初始化概览标签页
     */
    initializeOverviewTab() {
      // 激活社区活动趋势图表
      this.activateChart('community-activity-chart');
    }

    /**
     * 初始化用户分析标签页
     */
    initializeUsersTab() {
      // 激活用户分布图表
      this.activateChart('user-activity-distribution-chart');
      this.activateChart('user-influence-distribution-chart');
    }

    /**
     * 初始化讨论热度标签页
     */
    initializeDiscussionsTab() {
      // 激活讨论统计图表
      this.activateChart('discussion-by-genre-chart');
      this.activateChart('discussion-trend-chart');
    }

    /**
     * 初始化社交网络标签页
     */
    initializeNetworkTab() {
      // 激活网络可视化
      this.activateChart('network-visualization');

      // 延迟激活互动图表，防止资源竞争
      setTimeout(() => {
        this.activateChart('interaction-type-chart');

        // 再次延迟激活趋势图
        setTimeout(() => {
          this.activateChart('interaction-trend-chart');
        }, 300);
      }, 300);
    }

    /**
     * 激活指定图表
     * @param {string} chartId 图表ID
     */
    activateChart(chartId) {
      const chart = document.getElementById(chartId);
      if (!chart) return;

      console.log(`[社区分析] 激活图表: ${chartId}`);

      // 如果可视化管理器可用，使用它激活图表
      if (window.QuantumVizManager && window.QuantumVizManager.activateComponent) {
        window.QuantumVizManager.activateComponent(chartId);
      } else if (window.vizCore) {
        // 尝试使用vizCore激活
        this.loadChartWithVizCore(chartId);
      } else {
        // 否则添加一个标记，表示需要加载
        chart.setAttribute('data-needs-loading', 'true');
      }
    }

    /**
     * 使用vizCore加载图表
     * @param {string} chartId 图表ID
     */
    loadChartWithVizCore(chartId) {
      // 通过ID确定图表类型
      if (chartId === 'community-activity-chart') {
        // 社区活动趋势
        fetch('/visualizations/api/data/community-activity/')
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              this.renderTrendChartWithVizCore(chartId, data.data);
            }
          })
          .catch(error => console.error('加载图表数据失败', error));
      } else if (chartId.includes('distribution')) {
        // 分布图表
        const apiUrl = chartId.includes('user-activity')
          ? '/visualizations/api/data/user-distribution/'
          : '/visualizations/api/data/user-distribution/';

        fetch(apiUrl)
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              const chartData = chartId.includes('activity')
                ? data.data.activityDistribution
                : data.data.influenceDistribution;
              this.renderBarChartWithVizCore(chartId, chartData);
            }
          })
          .catch(error => console.error('加载图表数据失败', error));
      }
      // 其他图表类型处理...
    }

    /**
     * 使用vizCore渲染趋势图表
     * @param {string} chartId
     * @param {Array} data
     */
    renderTrendChartWithVizCore(chartId, data) {
      // 实现图表渲染逻辑...
    }

    /**
     * 使用vizCore渲染柱状图表
     * @param {string} chartId
     * @param {Array} data
     */
    renderBarChartWithVizCore(chartId, data) {
      // 实现图表渲染逻辑...
    }
  }

  // 创建并保存到全局，以便其他脚本可以访问
  window.communityTabManager = new CommunityTabManager();
})();