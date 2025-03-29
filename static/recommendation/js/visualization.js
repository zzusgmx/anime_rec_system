// 量子态数据可视化引擎 - ECharts集成
// 用于生成用户行为和动漫偏好的可视化图表

class QuantumVisualizationEngine {
  constructor() {
    this.apiEndpoints = {
      userActivity: '/recommendations/api/visualization/user-activity/',
      genrePreference: '/recommendations/api/visualization/genre-preference/',
      ratingDistribution: '/recommendations/api/visualization/rating-distribution/',
      viewingTrends: '/recommendations/api/visualization/viewing-trends/'
    };

    this.charts = new Map();
    this.colors = {
      primary: '#6d28d9',
      secondary: '#10b981',
      accent: '#f97316',
      background: 'rgba(255, 255, 255, 0.8)',
      gradients: [
        ['#6d28d9', '#8b5cf6'],  // 紫色渐变
        ['#10b981', '#34d399'],  // 绿色渐变
        ['#f97316', '#fb923c'],  // 橙色渐变
        ['#2563eb', '#60a5fa']   // 蓝色渐变
      ]
    };

    console.log('[QUANTUM-VIZ] 量子态可视化引擎初始化完成');
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

  // 获取CSRF令牌
  getCsrfToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
           document.cookie.split('; ')
               .find(row => row.startsWith('csrftoken='))
               ?.split('=')[1];
  }

  // 安全的fetch请求
  async fetchData(url) {
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

      return await response.json();
    } catch (error) {
      console.error('[QUANTUM-VIZ] 数据获取失败:', error);
      throw error;
    }
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

  // 显示错误状态
  showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="text-center py-4">
        <div class="empty-icon">
          <i class="fas fa-exclamation-triangle text-warning"></i>
        </div>
        <h5 class="mt-3">数据加载失败</h5>
        <p class="text-muted">${message || '请稍后再试'}</p>
        <button class="btn btn-sm btn-primary mt-2" onclick="vizEngine.refreshChart('${containerId}')">
          <i class="fas fa-sync-alt me-1"></i>重试
        </button>
      </div>
    `;
  }

  // 刷新指定图表
  refreshChart(containerId) {
    const chartType = containerId.replace('Chart', '');
    switch (chartType) {
      case 'activity':
        this.renderActivityChart();
        break;
      case 'genre':
        this.renderGenrePreferenceChart();
        break;
      case 'rating':
        this.renderRatingDistributionChart();
        break;
      case 'trend':
        this.renderViewingTrendsChart();
        break;
    }
  }

  // 初始化所有图表
  initializeCharts() {
    this.renderActivityChart();
    this.renderGenrePreferenceChart();
    this.renderRatingDistributionChart();
    this.renderViewingTrendsChart();
  }

  // ======== 用户活动图表 ========
  async renderActivityChart() {
    const containerId = 'activityChart';
    this.showLoading(containerId);

    try {
      const data = await this.fetchData(this.apiEndpoints.userActivity);

      if (!data.success || !data.data) {
        throw new Error(data.error || '无法获取用户活动数据');
      }

      const container = document.getElementById(containerId);
      if (!container) return;

      // 清除加载状态
      container.innerHTML = '';

      // 创建图表实例
      const chart = echarts.init(container);
      this.charts.set(containerId, chart);

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
          data: data.data.map(item => item.name)
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
            data: data.data.map(item => ({
              value: item.value,
              name: item.name,
              itemStyle: {
                color: item.color
              }
            }))
          }
        ]
      };

      // 设置图表配置并渲染
      chart.setOption(option);

      // 监听窗口大小变化，调整图表大小
      window.addEventListener('resize', () => {
        chart.resize();
      });

    } catch (error) {
      this.showError(containerId, error.message);
    }
  }

  // ======== 类型偏好图表 ========
  async renderGenrePreferenceChart() {
    const containerId = 'genreChart';
    this.showLoading(containerId);

    try {
      const data = await this.fetchData(this.apiEndpoints.genrePreference);

      if (!data.success || !data.data) {
        throw new Error(data.error || '无法获取类型偏好数据');
      }

      const container = document.getElementById(containerId);
      if (!container) return;

      // 清除加载状态
      container.innerHTML = '';

      // 创建图表实例
      const chart = echarts.init(container);
      this.charts.set(containerId, chart);

      // 准备数据
      const genres = data.data.map(item => item.name);
      const values = data.data.map(item => item.value);

      // 图表配置
      const option = {
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

      // 设置图表配置并渲染
      chart.setOption(option);

      // 监听窗口大小变化，调整图表大小
      window.addEventListener('resize', () => {
        chart.resize();
      });

    } catch (error) {
      this.showError(containerId, error.message);
    }
  }

  // ======== 评分分布图表 ========
  async renderRatingDistributionChart() {
    const containerId = 'ratingChart';
    this.showLoading(containerId);

    try {
      const data = await this.fetchData(this.apiEndpoints.ratingDistribution);

      if (!data.success || !data.data) {
        throw new Error(data.error || '无法获取评分分布数据');
      }

      const container = document.getElementById(containerId);
      if (!container) return;

      // 清除加载状态
      container.innerHTML = '';

      // 创建图表实例
      const chart = echarts.init(container);
      this.charts.set(containerId, chart);

      // 准备数据
      const ratings = data.data.map(item => item.rating.toString());
      const counts = data.data.map(item => item.count);

      // 图表配置
      const option = {
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

      // 设置图表配置并渲染
      chart.setOption(option);

      // 监听窗口大小变化，调整图表大小
      window.addEventListener('resize', () => {
        chart.resize();
      });

    } catch (error) {
      this.showError(containerId, error.message);
    }
  }

  // ======== 观看趋势图表 ========
  async renderViewingTrendsChart() {
    const containerId = 'trendChart';
    this.showLoading(containerId);

    try {
      const data = await this.fetchData(this.apiEndpoints.viewingTrends);

      if (!data.success || !data.data) {
        throw new Error(data.error || '无法获取观看趋势数据');
      }

      const container = document.getElementById(containerId);
      if (!container) return;

      // 清除加载状态
      container.innerHTML = '';

      // 创建图表实例
      const chart = echarts.init(container);
      this.charts.set(containerId, chart);

      // 准备数据
      const dates = data.data.map(item => item.date);
      const viewCounts = data.data.map(item => item.views);
      const ratingCounts = data.data.map(item => item.ratings);

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

      // 设置图表配置并渲染
      chart.setOption(option);

      // 监听窗口大小变化，调整图表大小
      window.addEventListener('resize', () => {
        chart.resize();
      });

    } catch (error) {
      this.showError(containerId, error.message);
    }
  }
}

// 创建全局可视化引擎实例
const vizEngine = new QuantumVisualizationEngine();

// 页面加载完成后初始化图表
document.addEventListener('DOMContentLoaded', function() {
  // 检查是否存在可视化面板
  if (document.getElementById('visualizationPanel')) {
    console.log('[QUANTUM-VIZ] 初始化数据可视化面板');
    vizEngine.initializeCharts();
  }
});