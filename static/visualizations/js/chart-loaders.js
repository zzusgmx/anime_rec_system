/**
 * 社区分析页面图表加载器
 * 统一管理图表数据加载和渲染
 */
(function() {
  // 确保脚本只在社区分析页面执行
  if (!document.getElementById('community-analysis-page')) {
    return;
  }

  console.log('[图表加载器] 初始化');

  /**
   * 图表加载器类
   */
  class ChartLoader {
    constructor() {
      // API端点映射
      this.apiEndpoints = {
        'community-activity-chart': '/visualizations/api/data/community-activity/',
        'user-activity-distribution-chart': '/visualizations/api/data/user-distribution/',
        'user-influence-distribution-chart': '/visualizations/api/data/user-distribution/',
        'discussion-by-genre-chart': '/visualizations/api/data/discussion-stats/',
        'discussion-trend-chart': '/visualizations/api/data/discussion-stats/',
        'interaction-type-chart': '/visualizations/api/data/interaction-stats/',
        'interaction-trend-chart': '/visualizations/api/data/interaction-stats/',
        'network-visualization': '/visualizations/api/data/network-data/'
      };

      // 加载状态跟踪
      this.loadingStatus = {};

      // 初始化加载状态
      Object.keys(this.apiEndpoints).forEach(chartId => {
        this.loadingStatus[chartId] = 'idle'; // idle, loading, success, error
      });

      // 渲染器映射
      this.renderers = {
        'community-activity-chart': this.renderTrendChart.bind(this),
        'user-activity-distribution-chart': this.renderBarChart.bind(this),
        'user-influence-distribution-chart': this.renderBarChart.bind(this),
        'discussion-by-genre-chart': this.renderBarChart.bind(this),
        'discussion-trend-chart': this.renderTrendChart.bind(this),
        'interaction-type-chart': this.renderPieChart.bind(this),
        'interaction-trend-chart': this.renderTrendChart.bind(this),
        'network-visualization': this.renderNetworkChart.bind(this)
      };

      // 数据处理器映射
      this.dataProcessors = {
        'user-activity-distribution-chart': (data) => data.activityDistribution,
        'user-influence-distribution-chart': (data) => data.influenceDistribution,
        'discussion-by-genre-chart': (data) => data.discussionByGenre,
        'discussion-trend-chart': (data) => data.discussionTrend,
        'interaction-type-chart': (data) => data.interactionByType,
        'interaction-trend-chart': (data) => data.interactionTrend
      };
    }

    /**
     * 加载图表数据
     * @param {string} chartId 图表ID
     * @returns {Promise} 数据加载Promise
     */
    loadChartData(chartId) {
      // 如果没有对应的API端点，返回错误
      if (!this.apiEndpoints[chartId]) {
        return Promise.reject(new Error(`未知图表类型: ${chartId}`));
      }

      // 如果已经在加载中，返回已有Promise
      if (this.loadingStatus[chartId] === 'loading' && this.loadingPromises?.[chartId]) {
        return this.loadingPromises[chartId];
      }

      // 更新加载状态
      this.loadingStatus[chartId] = 'loading';
      this.showLoading(chartId);

      // 创建API URL
      let apiUrl = this.apiEndpoints[chartId];

      // 为网络可视化添加参数
      if (chartId === 'network-visualization') {
        const userFocused = document.getElementById('userFocusedToggle')?.checked || true;
        const interactionType = document.getElementById('interactionTypeSelect')?.value || 'all';
        apiUrl += `?user_focused=${userFocused}&interaction_type=${interactionType}`;
      }

      // 发送请求
      const loadingPromise = fetch(apiUrl)
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP错误! 状态: ${response.status}`);
          }
          return response.json();
        })
        .then(response => {
          if (!response.success) {
            throw new Error(response.error || '获取数据失败');
          }

          // 保存成功状态
          this.loadingStatus[chartId] = 'success';

          // 处理数据
          let data = response.data;

          // 使用特定数据处理器（如果有）
          if (this.dataProcessors[chartId]) {
            data = this.dataProcessors[chartId](data);
          }

          return data;
        })
        .catch(error => {
          // 记录错误
          console.error(`[图表加载器] 加载 ${chartId} 数据失败:`, error);

          // 更新加载状态
          this.loadingStatus[chartId] = 'error';

          // 显示错误
          this.showError(chartId, error.message);

          // 重新抛出错误
          throw error;
        });

      // 保存加载Promise
      if (!this.loadingPromises) this.loadingPromises = {};
      this.loadingPromises[chartId] = loadingPromise;

      return loadingPromise;
    }

    /**
     * 初始化图表
     * @param {string} chartId 图表ID
     */
    initChart(chartId) {
      // 检查图表容器是否存在
      const container = document.getElementById(chartId);
      if (!container) {
        console.error(`[图表加载器] 图表容器不存在: ${chartId}`);
        return Promise.reject(new Error(`图表容器不存在: ${chartId}`));
      }

      console.log(`[图表加载器] 初始化图表: ${chartId}`);

      // 加载数据
      return this.loadChartData(chartId)
        .then(data => {
          // 使用对应的渲染器
          if (this.renderers[chartId]) {
            return this.renderers[chartId](chartId, data);
          } else {
            throw new Error(`未找到渲染器: ${chartId}`);
          }
        })
        .catch(error => {
          console.error(`[图表加载器] 初始化图表 ${chartId} 失败:`, error);
          this.showError(chartId, `初始化失败: ${error.message}`);
          return Promise.reject(error);
        });
    }

    /**
     * 重新加载图表
     * @param {string} chartId 图表ID
     */
    reloadChart(chartId) {
      // 重置加载状态
      this.loadingStatus[chartId] = 'idle';

      // 如果有保存的Promise，删除它
      if (this.loadingPromises?.[chartId]) {
        delete this.loadingPromises[chartId];
      }

      // 重新初始化
      return this.initChart(chartId);
    }

    /**
     * 显示加载状态
     * @param {string} chartId 图表ID
     */
    showLoading(chartId) {
      const container = document.getElementById(chartId);
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

    /**
     * 显示错误状态
     * @param {string} chartId 图表ID
     * @param {string} message 错误信息
     */
    showError(chartId, message) {
      const container = document.getElementById(chartId);
      if (!container) return;

      container.innerHTML = `
        <div class="d-flex justify-content-center align-items-center" style="height: 100%; min-height: 200px;">
          <div class="text-center">
            <div class="text-danger mb-3">
              <i class="fas fa-exclamation-triangle fa-3x"></i>
            </div>
            <h5>加载失败</h5>
            <p class="text-muted">${message}</p>
            <button class="btn btn-primary retry-chart-btn" data-chart-id="${chartId}">
              <i class="fas fa-sync-alt me-1"></i>重试
            </button>
          </div>
        </div>
      `;

      // 添加重试按钮事件
      const retryBtn = container.querySelector('.retry-chart-btn');
      if (retryBtn) {
        retryBtn.addEventListener('click', () => {
          this.reloadChart(chartId);
        });
      }
    }

    /**
     * 渲染趋势图表
     * @param {string} chartId 图表ID
     * @param {Array} data 图表数据
     */
    renderTrendChart(chartId, data) {
      const container = document.getElementById(chartId);
      if (!container) return;

      try {
        // 清空容器
        container.innerHTML = '';

        // 确保Chart.js已加载
        if (typeof Chart === 'undefined') {
          throw new Error('Chart.js未加载');
        }

        // 验证数据
        if (!data || !Array.isArray(data) || data.length === 0) {
          throw new Error('无效的趋势数据');
        }

        // 创建Canvas元素
        const canvas = document.createElement('canvas');
        container.appendChild(canvas);

        // 获取2D上下文
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          throw new Error('无法获取Canvas上下文');
        }

        // 格式化日期（如果需要）
        const formatDate = (dateStr) => {
          try {
            const date = new Date(dateStr);
            if (isNaN(date.getTime())) return dateStr;
            return `${date.getMonth() + 1}/${date.getDate()}`;
          } catch (e) {
            return dateStr;
          }
        };

        // 处理数据格式
        let chartData;

        // 检测数据格式类型
        if (Array.isArray(data[0])) {
          // 多系列数据
          chartData = {
            labels: [],
            datasets: []
          };

          // 收集所有标签
          const allLabels = new Set();
          data.forEach(series => {
            series.forEach(point => {
              allLabels.add(formatDate(point.date || point.x));
            });
          });

          // 排序标签
          chartData.labels = Array.from(allLabels).sort();

          // 创建数据集
          const colors = ['#6d28d9', '#10b981', '#3b82f6', '#f97316', '#ef4444'];

          data.forEach((series, i) => {
            const seriesName = series.name || `系列 ${i+1}`;
            const color = colors[i % colors.length];

            // 处理数据点
            const dataMap = {};
            series.forEach(point => {
              const key = formatDate(point.date || point.x);
              dataMap[key] = point.value || point.y || 0;
            });

            // 填充完整数据集
            const dataPoints = chartData.labels.map(label => dataMap[label] || 0);

            chartData.datasets.push({
              label: seriesName,
              data: dataPoints,
              borderColor: color,
              backgroundColor: `${color}33`,
              tension: 0.4,
              fill: true
            });
          });
        } else if (data[0]?.series) {
          // series格式数据
          chartData = {
            labels: [],
            datasets: []
          };

          // 收集所有标签
          const allLabels = new Set();
          data.forEach(seriesObj => {
            seriesObj.series.data.forEach(point => {
              allLabels.add(formatDate(point.date || point.x));
            });
          });

          // 排序标签
          chartData.labels = Array.from(allLabels).sort();

          // 创建数据集
          const colors = ['#6d28d9', '#10b981', '#3b82f6', '#f97316', '#ef4444'];

          data.forEach((seriesObj, i) => {
            const series = seriesObj.series;
            const seriesName = seriesObj.name || series.name || `系列 ${i+1}`;
            const color = seriesObj.color || colors[i % colors.length];

            // 处理数据点
            const dataMap = {};
            series.data.forEach(point => {
              const key = formatDate(point.date || point.x);
              dataMap[key] = point.value || point.y || 0;
            });

            // 填充完整数据集
            const dataPoints = chartData.labels.map(label => dataMap[label] || 0);

            chartData.datasets.push({
              label: seriesName,
              data: dataPoints,
              borderColor: color,
              backgroundColor: `${color}33`,
              tension: 0.4,
              fill: true
            });
          });
        } else {
          // 单系列数据
          const dataKeys = Object.keys(data[0]);

          if (dataKeys.includes('date') && dataKeys.some(k => k !== 'date')) {
            // 具有多个度量的单个时间序列，如{date, value1, value2}
            chartData = {
              labels: data.map(d => formatDate(d.date)),
              datasets: []
            };

            // 确定值字段
            const valueKeys = dataKeys.filter(k => k !== 'date');
            const colors = ['#6d28d9', '#10b981', '#3b82f6', '#f97316', '#ef4444'];

            valueKeys.forEach((key, i) => {
              const color = colors[i % colors.length];
              chartData.datasets.push({
                label: this.formatKey(key),
                data: data.map(d => d[key] || 0),
                borderColor: color,
                backgroundColor: `${color}33`,
                tension: 0.4,
                fill: true
              });
            });
          } else {
            // 简单时间序列，如{x/date, y/value}
            chartData = {
              labels: data.map(d => formatDate(d.date || d.x)),
              datasets: [{
                label: '值',
                data: data.map(d => d.value || d.y || 0),
                borderColor: '#6d28d9',
                backgroundColor: 'rgba(109, 40, 217, 0.2)',
                tension: 0.4,
                fill: true
              }]
            };
          }
        }

        // 创建图表
        const chart = new Chart(ctx, {
          type: 'line',
          data: chartData,
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
        });

        // 返回图表实例
        return chart;
      } catch (error) {
        console.error(`[图表加载器] 渲染趋势图表错误:`, error);
        this.renderFallbackTable(chartId, data);
        return null;
      }
    }

    /**
     * 渲染柱状图
     * @param {string} chartId 图表ID
     * @param {Array} data 图表数据
     */
    renderBarChart(chartId, data) {
      const container = document.getElementById(chartId);
      if (!container) return;

      try {
        // 清空容器
        container.innerHTML = '';

        // 确保Chart.js已加载
        if (typeof Chart === 'undefined') {
          throw new Error('Chart.js未加载');
        }

        // 验证数据
        if (!data || !Array.isArray(data) || data.length === 0) {
          throw new Error('无效的柱状图数据');
        }

        // 创建Canvas元素
        const canvas = document.createElement('canvas');
        container.appendChild(canvas);

        // 获取2D上下文
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          throw new Error('无法获取Canvas上下文');
        }

        // 确定数据结构
        const useHorizontal = chartId.includes('genre') || chartId.includes('distribution');

        // 处理数据
        const labels = data.map(d => d.name || d.category || d.label || '');
        const values = data.map(d => d.value || d.count || 0);

        // 创建图表
        const chart = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [{
              label: '数量',
              data: values,
              backgroundColor: [
                '#6d28d9', '#8b5cf6', '#10b981', '#3b82f6', '#f97316',
                '#ef4444', '#ec4899', '#84cc16', '#fbbf24', '#06b6d4'
              ],
              borderWidth: 1
            }]
          },
          options: {
            indexAxis: useHorizontal ? 'y' : 'x',
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
        });

        // 返回图表实例
        return chart;
      } catch (error) {
        console.error(`[图表加载器] 渲染柱状图错误:`, error);
        this.renderFallbackTable(chartId, data);
        return null;
      }
    }

    /**
     * 渲染饼图
     * @param {string} chartId 图表ID
     * @param {Array} data 图表数据
     */
    renderPieChart(chartId, data) {
      const container = document.getElementById(chartId);
      if (!container) return;

      try {
        // 清空容器
        container.innerHTML = '';

        // 确保Chart.js已加载
        if (typeof Chart === 'undefined') {
          throw new Error('Chart.js未加载');
        }

        // 验证数据
        if (!data || !Array.isArray(data) || data.length === 0) {
          throw new Error('无效的饼图数据');
        }

        // 创建Canvas元素
        const canvas = document.createElement('canvas');
        container.appendChild(canvas);

        // 获取2D上下文
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          throw new Error('无法获取Canvas上下文');
        }

        // 处理数据
        const labels = data.map(d => d.name || d.category || d.label || '');
        const values = data.map(d => d.value || d.count || 0);

        // 创建图表
        const chart = new Chart(ctx, {
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
        });

        // 返回图表实例
        return chart;
      } catch (error) {
        console.error(`[图表加载器] 渲染饼图错误:`, error);
        this.renderFallbackTable(chartId, data);
        return null;
      }
    }

    /**
     * 渲染网络图
     * @param {string} chartId 图表ID
     * @param {Object} data 网络数据
     */
    renderNetworkChart(chartId, data) {
      const container = document.getElementById(chartId);
      if (!container) return;

      try {
        // 清空容器
        container.innerHTML = '';

        // 确保D3.js已加载
        if (typeof d3 === 'undefined') {
          throw new Error('D3.js未加载');
        }

        // 验证数据
        if (!data || !data.nodes || !data.links || !Array.isArray(data.nodes) || !Array.isArray(data.links)) {
          throw new Error('无效的网络数据');
        }

        // 如果NetworkVisualization类可用，使用它
        if (typeof NetworkVisualization === 'function') {
          const networkViz = new NetworkVisualization(chartId);
          networkViz.loadData(data);
          return networkViz;
        }

        // 否则使用D3.js直接渲染
        const width = container.clientWidth || 800;
        const height = 600;

        // 创建SVG
        const svg = d3.select(`#${chartId}`)
          .append('svg')
          .attr('width', width)
          .attr('height', height);

        // 创建力导向仿真
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
          .attr('stroke', d => this.getLinkColor(d.type));

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
            .on('end', dragended));

        // 创建文本标签
        const text = svg.append('g')
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

        // 添加鼠标事件
        node.on('mouseover', (event, d) => {
            d3.select('.network-tooltip')
              .transition()
              .duration(200)
              .style('opacity', .9);

            d3.select('.network-tooltip')
              .html(`
                <div class="font-weight-bold">${d.username || `用户 ${d.id}`}</div>
                <div>影响力: ${d.influence || 0}</div>
                <div>活跃度: ${d.activity || 0}</div>
              `)
              .style('left', (event.pageX + 10) + 'px')
              .style('top', (event.pageY - 28) + 'px');
          })
          .on('mouseout', () => {
            d3.select('.network-tooltip')
              .transition()
              .duration(500)
              .style('opacity', 0);
          });

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

          text
            .attr('x', d => d.x)
            .attr('y', d => d.y);
        });

        // 拖拽函数
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

        // 绑定网络控件事件
        this.bindNetworkControls(chartId, () => {
          this.reloadChart(chartId);
        });

        // 返回仿真对象作为图表实例
        return simulation;
      } catch (error) {
        console.error(`[图表加载器] 渲染网络图错误:`, error);
        this.showError(chartId, `渲染网络图失败: ${error.message}`);
        return null;
      }
    }

    /**
     * 绑定网络控件事件
     * @param {string} chartId 图表ID
     * @param {Function} callback 回调函数
     */
    bindNetworkControls(chartId, callback) {
      const userFocusedToggle = document.getElementById('userFocusedToggle');
      const interactionTypeSelect = document.getElementById('interactionTypeSelect');

      if (userFocusedToggle) {
        userFocusedToggle.addEventListener('change', callback);
      }

      if (interactionTypeSelect) {
        interactionTypeSelect.addEventListener('change', callback);
      }
    }

    /**
     * 获取节点颜色
     * @param {Object} node 节点数据
     * @returns {string} 颜色值
     */
    getNodeColor(node) {
      const influence = node.influence || 0;
      const activity = node.activity || 0;
      const total = influence + activity;

      if (total > 150) return '#6d28d9'; // 高影响力+活跃度
      if (influence > 80) return '#8b5cf6'; // 高影响力
      if (activity > 80) return '#4f46e5'; // 高活跃度

      return '#a78bfa'; // 普通用户
    }

    /**
     * 获取连接颜色
     * @param {string} type 连接类型
     * @returns {string} 颜色值
     */
    getLinkColor(type) {
      const colors = {
        like: '#ef4444',
        reply: '#3b82f6',
        mention: '#10b981',
        follow: '#f97316'
      };

      return colors[type] || '#999';
    }

    /**
     * 渲染备用表格
     * @param {string} chartId 图表ID
     * @param {Array|Object} data 数据
     */
    renderFallbackTable(chartId, data) {
      const container = document.getElementById(chartId);
      if (!container) return;

      try {
        // 清空容器
        container.innerHTML = '';

        // 创建警告提示
        const alert = document.createElement('div');
        alert.className = 'alert alert-warning';
        alert.innerHTML = `
          <i class="fas fa-exclamation-triangle me-2"></i>
          图表渲染失败，显示表格备用视图
        `;
        container.appendChild(alert);

        // 如果没有数据
        if (!data || (Array.isArray(data) && data.length === 0)) {
          const noData = document.createElement('div');
          noData.className = 'alert alert-info mt-3';
          noData.textContent = '暂无数据';
          container.appendChild(noData);
          return;
        }

        // 创建表格
        const table = document.createElement('table');
        table.className = 'table table-striped table-hover';

        // 创建表头
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');

        // 确定表头列
        let columns = [];
        if (Array.isArray(data)) {
          if (typeof data[0] === 'object') {
            // 从第一个对象获取列
            columns = Object.keys(data[0]);
          } else {
            columns = ['值'];
          }
        } else if (typeof data === 'object') {
          if (data.nodes && data.links) {
            // 网络数据
            const tableWrapper = document.createElement('div');
            tableWrapper.textContent = '网络图数据无法以表格形式展示';
            container.appendChild(tableWrapper);
            return;
          } else {
            columns = Object.keys(data);
          }
        }

        // 创建表头行
        columns.forEach(column => {
          const th = document.createElement('th');
          th.textContent = this.formatKey(column);
          headerRow.appendChild(th);
        });

        thead.appendChild(headerRow);
        table.appendChild(thead);

        // 创建表体
        const tbody = document.createElement('tbody');

        if (Array.isArray(data)) {
          data.forEach(item => {
            const row = document.createElement('tr');

            if (typeof item === 'object') {
              columns.forEach(column => {
                const cell = document.createElement('td');
                cell.textContent = this.formatValue(item[column]);
                row.appendChild(cell);
              });
            } else {
              const cell = document.createElement('td');
              cell.textContent = this.formatValue(item);
              row.appendChild(cell);
            }

            tbody.appendChild(row);
          });
        } else if (typeof data === 'object') {
          const row = document.createElement('tr');

          columns.forEach(column => {
            const cell = document.createElement('td');
            cell.textContent = this.formatValue(data[column]);
            row.appendChild(cell);
          });

          tbody.appendChild(row);
        }

        table.appendChild(tbody);
        container.appendChild(table);
      } catch (error) {
        console.error(`[图表加载器] 渲染备用表格错误:`, error);

        // 如果备用表格也失败，显示简单错误消息
        container.innerHTML = `
          <div class="alert alert-danger">
            <i class="fas fa-exclamation-circle me-2"></i>
            无法显示数据
          </div>
        `;
      }
    }

    /**
     * 格式化键名
     * @param {string} key 原始键名
     * @returns {string} 格式化后的键名
     */
    formatKey(key) {
      if (!key) return '';

      // 处理特殊键名
      const specialKeys = {
        'x': '日期',
        'y': '值',
        'date': '日期',
        'value': '值',
        'count': '数量',
        'name': '名称',
        'category': '类别',
        'label': '标签',
        'comments': '评论数',
        'ratings': '评分数',
        'favorites': '收藏数',
        'total': '总计'
      };

      if (specialKeys[key]) {
        return specialKeys[key];
      }

      // 处理驼峰命名
      return key
        .replace(/([A-Z])/g, ' $1')
        .replace(/_/g, ' ')
        .replace(/^./, str => str.toUpperCase());
    }

    /**
     * 格式化值
     * @param {any} value 原始值
     * @returns {string} 格式化后的值
     */
    formatValue(value) {
      if (value === undefined || value === null) {
        return '';
      }

      if (typeof value === 'object') {
        try {
          return JSON.stringify(value);
        } catch (e) {
          return '[对象]';
        }
      }

      if (typeof value === 'number') {
        // 如果是整数，直接返回
        if (Number.isInteger(value)) {
          return value.toString();
        }
        // 否则保留两位小数
        return value.toFixed(2);
      }

      // 尝试解析日期
      if (typeof value === 'string' && (value.includes('-') || value.includes('/'))) {
        try {
          const date = new Date(value);
          if (!isNaN(date.getTime())) {
            return date.toLocaleDateString();
          }
        } catch (e) {
          // 不是有效日期，忽略
        }
      }

      return value.toString();
    }
  }

  // 创建并保存到全局
  window.chartLoader = new ChartLoader();

  // 自动初始化当前页面上的图表
  document.addEventListener('DOMContentLoaded', function() {
    // 查找当前页面上的所有图表容器
    const chartContainers = document.querySelectorAll('.chart-container, [id$="-chart"], #network-visualization');

    // 初始化当前活动标签页中的图表
    const activeTab = document.querySelector('.tab-pane.active');
    if (activeTab) {
      const chartsInActiveTab = activeTab.querySelectorAll('.chart-container, [id$="-chart"], #network-visualization');

      chartsInActiveTab.forEach(container => {
        if (container.id) {
          console.log(`[图表加载器] 自动初始化活动标签页图表: ${container.id}`);
          window.chartLoader.initChart(container.id);
        }
      });
    }

    // 设置标签页激活事件
    document.querySelectorAll('#communityTabs .nav-link').forEach(tab => {
      tab.addEventListener('shown.bs.tab', function() {
        const tabId = this.getAttribute('id');
        const tabName = tabId.replace('-tab', '');

        // 查找目标标签页中的图表
        const targetPane = document.getElementById(tabName);
        if (targetPane) {
          const chartsInTab = targetPane.querySelectorAll('.chart-container, [id$="-chart"], #network-visualization');

          chartsInTab.forEach(container => {
            if (container.id) {
              console.log(`[图表加载器] 标签页切换初始化图表: ${container.id}`);
              window.chartLoader.initChart(container.id);
            }
          });
        }
      });
    });
  });
})();