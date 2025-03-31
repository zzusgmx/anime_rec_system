/**
 * 量子级可视化核心引擎
 * 处理可视化仪表盘的核心功能
 */
class VisualizationCore {
    constructor() {
        // API端点
        this.apiEndpoints = {
            ratingDistribution: '/visualizations/api/data/rating-distribution/',
            genrePreference: '/visualizations/api/data/genre-preference/',
            viewingTrends: '/visualizations/api/data/viewing-trends/',
            activitySummary: '/visualizations/api/data/activity-summary/',
            saveDashboard: '/visualizations/api/dashboard/save/',
            updatePreferences: '/visualizations/api/preferences/update/',
            exportVisualization: '/visualizations/api/export/'
        };

        // 主题配置
        this.themes = {
            quantum: {
                colors: ['#6d28d9', '#8b5cf6', '#10b981', '#3b82f6', '#f97316', '#ef4444'],
                background: '#f8fafc',
                text: '#1e293b',
                grid: '#e2e8f0'
            },
            dark: {
                colors: ['#8b5cf6', '#10b981', '#3b82f6', '#f97316', '#ef4444', '#ec4899'],
                background: '#1e293b',
                text: '#f8fafc',
                grid: '#334155'
            },
            pastel: {
                colors: ['#c084fc', '#86efac', '#93c5fd', '#fdba74', '#fca5a5', '#f9a8d4'],
                background: '#ffffff',
                text: '#334155',
                grid: '#e2e8f0'
            }
        };

        // 当前主题
        this.currentTheme = 'quantum';

        // 仪表盘状态
        this.dashboard = {
            id: null,
            name: '',
            layout: {
                widgets: [
                    {id: 'rating_distribution', title: '评分分布', type: 'chart', position: {row: 0, col: 0, width: 6, height: 4}},
                    {id: 'viewing_trends', title: '观看趋势', type: 'chart', position: {row: 0, col: 6, width: 6, height: 4}},
                    {id: 'genre_preference', title: '类型偏好', type: 'chart', position: {row: 4, col: 0, width: 6, height: 4}},
                    {id: 'activity_summary', title: '活动摘要', type: 'stats', position: {row: 4, col: 6, width: 6, height: 4}}
                ]
            }
        };

        // 图表引用
        this.charts = {};

        // 确保DOM加载完成后再初始化组件
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    /**
     * 初始化可视化引擎
     */
    init() {
        console.log('[QUANTUM-VIZ] 初始化可视化引擎');

        // 检查当前页面是否需要仪表盘功能
        const isDashboardPage = !!document.getElementById('dashboard') ||
                                window.location.pathname.includes('/dashboard') ||
                                document.querySelector('.quantum-dashboard');

        if (!isDashboardPage) {
            console.log('[QUANTUM-VIZ] 当前页面不需要仪表盘功能，跳过初始化');
            return;
        }

        // 加载用户偏好
        try {
            this.loadUserPreferences();
        } catch (e) {
            console.error('[QUANTUM-VIZ] 加载用户偏好失败:', e);
        }

        // 绑定事件
        try {
            this.bindEvents();
        } catch (e) {
            console.error('[QUANTUM-VIZ] 绑定事件失败:', e);
        }

        // 初始化仪表盘
        try {
            this.initDashboard();
        } catch (e) {
            console.error('[QUANTUM-VIZ] 初始化仪表盘失败:', e);
        }
    }

    /**
     * 加载用户偏好设置
     */
    loadUserPreferences() {
        // 获取用户主题偏好
        const theme = localStorage.getItem('visualization_theme') || 'quantum';
        this.setTheme(theme);
    }

    /**
     * 设置主题
     * @param {string} theme 主题名称
     */
    setTheme(theme) {
        if (!this.themes[theme]) {
            console.warn(`[QUANTUM-VIZ] 未知主题: ${theme}, 使用默认主题`);
            theme = 'quantum';
        }

        this.currentTheme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('visualization_theme', theme);

        // 更新所有图表的主题
        this.updateChartsTheme();
    }

    /**
     * 更新所有图表的主题
     */
    updateChartsTheme() {
        for (const chartId in this.charts) {
            if (this.charts[chartId] && typeof this.charts[chartId].updateTheme === 'function') {
                this.charts[chartId].updateTheme(this.themes[this.currentTheme]);
            }
        }
    }

    /**
     * 绑定事件处理器
     */
    bindEvents() {
        // 主题切换
        document.querySelectorAll('.theme-selector').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const theme = e.currentTarget.dataset.theme;
                this.setTheme(theme);

                // 更新UI状态
                document.querySelectorAll('.theme-selector').forEach(b => {
                    b.classList.remove('active');
                });
                e.currentTarget.classList.add('active');

                // 保存用户偏好
                this.saveUserPreferences({
                    theme: theme
                });
            });
        });

        // 导出图表
        document.querySelectorAll('.export-chart').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const chartType = e.currentTarget.dataset.chartType;
                const format = e.currentTarget.dataset.format || 'png';
                this.exportChart(chartType, format);
            });
        });

        // 保存仪表盘
        const saveBtn = document.getElementById('saveDashboard');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveDashboard();
            });
        }
    }
    initIndividualCharts() {
        // 尝试查找页面上的图表容器
        const chartContainers = [
            'rating-distribution-chart',
            'genre-preference-chart',
            'viewing-trends-chart',
            'activity-summary-content',
            'user-journey-timeline',
            'community-activity-chart',
            'discussion-by-genre-chart',
            'discussion-trend-chart',
            'user-activity-distribution-chart',
            'user-influence-distribution-chart',
            'interaction-type-chart',
            'interaction-trend-chart',
            'network-visualization',
            'recommendation-factors-chart',
            'top-genres-chart'
        ];

        // 尝试初始化找到的图表
        chartContainers.forEach(id => {
            const container = document.getElementById(id);
            if (container) {
                console.log(`[QUANTUM-VIZ] 找到图表容器: ${id}`);

                // 根据容器ID确定图表类型并初始化
                if (id === 'rating-distribution-chart') {
                    this.loadRatingDistribution(container);
                } else if (id === 'genre-preference-chart') {
                    this.loadGenrePreference(container);
                } else if (id === 'viewing-trends-chart') {
                    this.loadViewingTrends(container);
                } else if (id === 'activity-summary-content') {
                    this.loadActivitySummary(container);
                }
                // 为每种图表类型添加相应的初始化逻辑
            }
        });
    }
    initDashboard() {
        // 加载仪表盘布局
        const dashboardEl = document.getElementById('dashboard');
        if (!dashboardEl) {
            console.log('[QUANTUM-VIZ] 仪表盘容器不存在，尝试继续初始化可用的组件');
            // 即使没有仪表盘容器，也尝试初始化可能存在的图表组件
            this.initIndividualCharts();
            return;
        }

        // 获取仪表盘ID
        const dashboardId = dashboardEl.dataset.dashboardId;
        if (dashboardId && !isNaN(parseInt(dashboardId))) {
            this.dashboard.id = parseInt(dashboardId);
        }

        // 获取仪表盘名称
        const dashboardName = dashboardEl.dataset.dashboardName;
        if (dashboardName) {
            this.dashboard.name = dashboardName;
        }

        // 获取仪表盘布局 - 首先尝试从隐藏的JSON元素获取
        let dashboardLayout = null;
        const layoutDataElement = document.getElementById('dashboard-layout-data');

        try {
            if (layoutDataElement && layoutDataElement.textContent) {
                // 从隐藏的JSON元素中获取布局
                const layoutJson = layoutDataElement.textContent.trim();
                console.log('[QUANTUM-VIZ] 从隐藏元素获取布局数据:', layoutJson);
                dashboardLayout = JSON.parse(layoutJson);
            }
            // 如果没有找到隐藏元素，则尝试从data属性获取
            else if (dashboardEl.dataset.layout) {
                console.log('[QUANTUM-VIZ] 从data属性获取布局数据:', dashboardEl.dataset.layout);
                dashboardLayout = JSON.parse(dashboardEl.dataset.layout);
            }
            // 最后尝试从window全局变量获取
            else if (window.dashboardLayoutData) {
                console.log('[QUANTUM-VIZ] 从全局变量获取布局数据');
                dashboardLayout = typeof window.dashboardLayoutData === 'string' ?
                                 JSON.parse(window.dashboardLayoutData) :
                                 window.dashboardLayoutData;
            }

            // 检查解析结果
            if (dashboardLayout && typeof dashboardLayout === 'object') {
                if (Array.isArray(dashboardLayout.widgets)) {
                    this.dashboard.layout = dashboardLayout;
                    console.log('[QUANTUM-VIZ] 成功加载布局配置');
                } else {
                    console.warn('[QUANTUM-VIZ] 布局对象缺少widgets数组，使用默认布局');
                }
            }
        } catch (e) {
            console.error('[QUANTUM-VIZ] 解析仪表盘布局失败:', e);
            console.log('[QUANTUM-VIZ] 使用默认布局');
            // 使用默认布局，构造函数已设置默认值
        }

        // 初始化仪表盘组件
        this.initDashboardWidgets();
    }

    /**
     * 初始化仪表盘组件
     */
    initDashboardWidgets() {
        const widgets = this.dashboard.layout.widgets || [];

        widgets.forEach(widget => {
            try {
                this.initWidget(widget);
            } catch (e) {
                console.error(`[QUANTUM-VIZ] 初始化组件 ${widget.id} 失败:`, e);
            }
        });
    }

    /**
     * 初始化单个组件
     * @param {Object} widget 组件配置
     */
    initWidget(widget) {
        if (!widget || !widget.id) {
            console.warn('[QUANTUM-VIZ] 无效的组件配置');
            return;
        }

        // 查找组件ID对应的容器
        const containerId = `${widget.id}-chart`;
        const statsId = `${widget.id}-content`;
        const chartContainer = document.getElementById(containerId);
        const statsContainer = document.getElementById(statsId);

        if (!chartContainer && !statsContainer) {
            console.warn(`[QUANTUM-VIZ] 未找到组件容器: ${widget.id}`);
            return;
        }

        // 根据组件类型初始化
        try {
            switch (widget.type) {
                case 'chart':
                    if (chartContainer) {
                        this.initChart(widget, chartContainer);
                    }
                    break;
                case 'stats':
                    if (statsContainer) {
                        this.initStats(widget, statsContainer);
                    }
                    break;
                default:
                    console.warn(`[QUANTUM-VIZ] 未知组件类型: ${widget.type}`);
            }
        } catch (e) {
            console.error(`[QUANTUM-VIZ] 初始化组件 ${widget.id} 失败:`, e);
        }
    }

    /**
     * 初始化图表组件
     * @param {Object} widget 组件配置
     * @param {HTMLElement} container 图表容器
     */
    initChart(widget, container) {
        // 根据图表ID加载对应数据
        try {
            switch (widget.id) {
                case 'rating_distribution':
                    this.loadRatingDistribution(container);
                    break;
                case 'genre_preference':
                    this.loadGenrePreference(container);
                    break;
                case 'viewing_trends':
                    this.loadViewingTrends(container);
                    break;
                default:
                    console.warn(`[QUANTUM-VIZ] 未知图表类型: ${widget.id}`);
                    break;
            }
        } catch (e) {
            console.error(`[QUANTUM-VIZ] 初始化图表 ${widget.id} 失败:`, e);
            this.showError(container, `初始化图表失败: ${e.message}`);
        }
    }

    /**
     * 初始化统计组件
     * @param {Object} widget 组件配置
     * @param {HTMLElement} container 统计容器
     */
    initStats(widget, container) {
        // 根据统计ID加载对应数据
        try {
            switch (widget.id) {
                case 'activity_summary':
                    this.loadActivitySummary(container);
                    break;
                default:
                    console.warn(`[QUANTUM-VIZ] 未知统计类型: ${widget.id}`);
                    break;
            }
        } catch (e) {
            console.error(`[QUANTUM-VIZ] 初始化统计 ${widget.id} 失败:`, e);
            this.showError(container, `初始化统计失败: ${e.message}`);
        }
    }

    /**
     * 加载评分分布数据
     * @param {HTMLElement} container 图表容器
     */
    loadRatingDistribution(container) {
        this.showLoading(container);

        fetch(this.apiEndpoints.ratingDistribution)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success && Array.isArray(data.data)) {
                    this.renderRatingDistributionChart(container, data.data);
                } else {
                    this.showError(container, data.error || '获取评分分布数据失败');
                }
            })
            .catch(error => {
                console.error('[QUANTUM-VIZ] 加载评分分布失败:', error);
                this.showError(container, `获取评分分布数据失败: ${error.message}`);
            });
    }

    /**
     * 渲染评分分布图表
     * @param {HTMLElement} container 图表容器
     * @param {Array} data 图表数据
     */
    renderRatingDistributionChart(container, data) {
        // 验证数据
        if (!Array.isArray(data) || data.length === 0) {
            this.showError(container, '没有评分分布数据');
            return;
        }

        try {
            // 清空容器
            container.innerHTML = '';

            // 创建Canvas元素
            const canvas = document.createElement('canvas');
            container.appendChild(canvas);

            // 确保Chart.js已加载
            if (typeof Chart === 'undefined') {
                this.showError(container, '图表库未加载');
                return;
            }

            // 数据验证和格式化
            const validData = data.filter(item =>
                item && typeof item === 'object' &&
                !isNaN(item.rating) && !isNaN(item.count)
            );

            if (validData.length === 0) {
                this.showError(container, '评分分布数据无效');
                return;
            }

            // 尝试获取2D上下文，失败时优雅降级
            let ctx;
            try {
                ctx = canvas.getContext('2d');
            } catch (e) {
                console.error('[QUANTUM-VIZ] 无法获取Canvas上下文:', e);
                // 替换为DOM渲染的简单表格
                this.renderAsTable(container, validData, '评分', '计数');
                return;
            }

            if (!ctx) {
                console.error('[QUANTUM-VIZ] Canvas上下文为空');
                this.renderAsTable(container, validData, '评分', '计数');
                return;
            }

            // 创建图表
            try {
                const chart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: validData.map(item => `${item.rating}星`),
                        datasets: [{
                            label: '评分分布',
                            data: validData.map(item => item.count),
                            backgroundColor: this.themes[this.currentTheme].colors,
                            borderColor: this.themes[this.currentTheme].colors,
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: '评分分布',
                                color: this.themes[this.currentTheme].text
                            },
                            legend: {
                                display: false
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return `${context.parsed.y} 个评分`;
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    color: this.themes[this.currentTheme].text
                                },
                                grid: {
                                    color: this.themes[this.currentTheme].grid
                                }
                            },
                            x: {
                                ticks: {
                                    color: this.themes[this.currentTheme].text
                                },
                                grid: {
                                    color: this.themes[this.currentTheme].grid
                                }
                            }
                        }
                    }
                });

                // 保存图表引用
                this.charts.ratingDistribution = chart;
            } catch (e) {
                console.error('[QUANTUM-VIZ] 创建图表失败:', e);
                this.renderAsTable(container, validData, '评分', '计数');
            }
        } catch (error) {
            console.error('[QUANTUM-VIZ] 渲染评分分布图表失败:', error);
            this.showError(container, `渲染图表失败: ${error.message}`);
        }
    }

    /**
     * 加载类型偏好数据
     * @param {HTMLElement} container 图表容器
     */
    loadGenrePreference(container) {
        this.showLoading(container);

        fetch(this.apiEndpoints.genrePreference)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success && Array.isArray(data.data)) {
                    this.renderGenrePreferenceChart(container, data.data);
                } else {
                    this.showError(container, data.error || '获取类型偏好数据失败');
                }
            })
            .catch(error => {
                console.error('[QUANTUM-VIZ] 加载类型偏好失败:', error);
                this.showError(container, `获取类型偏好数据失败: ${error.message}`);
            });
    }

    /**
     * 渲染类型偏好图表
     * @param {HTMLElement} container 图表容器
     * @param {Array} data 图表数据
     */
    renderGenrePreferenceChart(container, data) {
        // 验证数据
        if (!Array.isArray(data) || data.length === 0) {
            this.showError(container, '没有类型偏好数据');
            return;
        }

        try {
            // 清空容器
            container.innerHTML = '';

            // 创建Canvas元素
            const canvas = document.createElement('canvas');
            container.appendChild(canvas);

            // 确保Chart.js已加载
            if (typeof Chart === 'undefined') {
                this.showError(container, '图表库未加载');
                return;
            }

            // 数据验证和格式化
            const validData = data.filter(item =>
                item && typeof item === 'object' &&
                item.name && !isNaN(item.value)
            );

            if (validData.length === 0) {
                this.showError(container, '类型偏好数据无效');
                return;
            }

            // 排序数据
            validData.sort((a, b) => b.value - a.value);

            // 尝试获取2D上下文，失败时优雅降级
            let ctx;
            try {
                ctx = canvas.getContext('2d');
            } catch (e) {
                console.error('[QUANTUM-VIZ] 无法获取Canvas上下文:', e);
                // 替换为DOM渲染的简单表格
                this.renderAsTable(container, validData, '类型', '偏好值');
                return;
            }

            if (!ctx) {
                console.error('[QUANTUM-VIZ] Canvas上下文为空');
                this.renderAsTable(container, validData, '类型', '偏好值');
                return;
            }

            // 创建图表
            try {
                const chart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: validData.map(item => item.name),
                        datasets: [{
                            axis: 'y',
                            label: '偏好分数',
                            data: validData.map(item => item.value),
                            backgroundColor: this.themes[this.currentTheme].colors,
                            borderColor: this.themes[this.currentTheme].colors,
                            borderWidth: 1
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: '类型偏好',
                                color: this.themes[this.currentTheme].text
                            },
                            legend: {
                                display: false
                            }
                        },
                        scales: {
                            x: {
                                beginAtZero: true,
                                ticks: {
                                    color: this.themes[this.currentTheme].text
                                },
                                grid: {
                                    color: this.themes[this.currentTheme].grid
                                }
                            },
                            y: {
                                ticks: {
                                    color: this.themes[this.currentTheme].text
                                },
                                grid: {
                                    color: this.themes[this.currentTheme].grid
                                }
                            }
                        }
                    }
                });

                // 保存图表引用
                this.charts.genrePreference = chart;
            } catch (e) {
                console.error('[QUANTUM-VIZ] 创建图表失败:', e);
                this.renderAsTable(container, validData, '类型', '偏好值');
            }
        } catch (error) {
            console.error('[QUANTUM-VIZ] 渲染类型偏好图表失败:', error);
            this.showError(container, `渲染图表失败: ${error.message}`);
        }
    }

    /**
     * 加载观看趋势数据
     * @param {HTMLElement} container 图表容器
     */
    loadViewingTrends(container) {
        this.showLoading(container);

        fetch(this.apiEndpoints.viewingTrends)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success && Array.isArray(data.data)) {
                    this.renderViewingTrendsChart(container, data.data);
                } else {
                    this.showError(container, data.error || '获取观看趋势数据失败');
                }
            })
            .catch(error => {
                console.error('[QUANTUM-VIZ] 加载观看趋势失败:', error);
                this.showError(container, `获取观看趋势数据失败: ${error.message}`);
            });
    }

    /**
     * 渲染观看趋势图表
     * @param {HTMLElement} container 图表容器
     * @param {Array} data 图表数据
     */
    renderViewingTrendsChart(container, data) {
        // 验证数据
        if (!Array.isArray(data) || data.length === 0) {
            this.showError(container, '没有观看趋势数据');
            return;
        }

        try {
            // 清空容器
            container.innerHTML = '';

            // 创建Canvas元素
            const canvas = document.createElement('canvas');
            container.appendChild(canvas);

            // 确保Chart.js已加载
            if (typeof Chart === 'undefined') {
                this.showError(container, '图表库未加载');
                return;
            }

            // 数据验证和格式化
            const validData = data.filter(item =>
                item && typeof item === 'object' &&
                item.date && !isNaN(item.views) && !isNaN(item.ratings)
            );

            if (validData.length === 0) {
                this.showError(container, '观看趋势数据无效');
                return;
            }

            // 格式化日期
            const formatDate = (dateStr) => {
                try {
                    const date = new Date(dateStr);
                    if (isNaN(date.getTime())) return "无效日期";
                    return `${date.getMonth() + 1}/${date.getDate()}`;
                } catch (e) {
                    return "无效日期";
                }
            };

            // 尝试获取2D上下文，失败时优雅降级
            let ctx;
            try {
                ctx = canvas.getContext('2d');
            } catch (e) {
                console.error('[QUANTUM-VIZ] 无法获取Canvas上下文:', e);
                // 用表格展示数据
                this.renderAsTrendTable(container, validData);
                return;
            }

            if (!ctx) {
                console.error('[QUANTUM-VIZ] Canvas上下文为空');
                this.renderAsTrendTable(container, validData);
                return;
            }

            // 创建图表
            try {
                const chart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: validData.map(item => formatDate(item.date)),
                        datasets: [
                            {
                                label: '浏览量',
                                data: validData.map(item => item.views),
                                borderColor: this.themes[this.currentTheme].colors[0],
                                backgroundColor: this.themes[this.currentTheme].colors[0] + '33',
                                tension: 0.4,
                                fill: true
                            },
                            {
                                label: '评分数',
                                data: validData.map(item => item.ratings),
                                borderColor: this.themes[this.currentTheme].colors[1],
                                backgroundColor: this.themes[this.currentTheme].colors[1] + '33',
                                tension: 0.4,
                                fill: true
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: '观看趋势',
                                color: this.themes[this.currentTheme].text
                            },
                            legend: {
                                labels: {
                                    color: this.themes[this.currentTheme].text
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    color: this.themes[this.currentTheme].text
                                },
                                grid: {
                                    color: this.themes[this.currentTheme].grid
                                }
                            },
                            x: {
                                ticks: {
                                    color: this.themes[this.currentTheme].text
                                },
                                grid: {
                                    color: this.themes[this.currentTheme].grid
                                }
                            }
                        }
                    }
                });

                // 保存图表引用
                this.charts.viewingTrends = chart;
            } catch (e) {
                console.error('[QUANTUM-VIZ] 创建图表失败:', e);
                this.renderAsTrendTable(container, validData);
            }
        } catch (error) {
            console.error('[QUANTUM-VIZ] 渲染观看趋势图表失败:', error);
            this.showError(container, `渲染图表失败: ${error.message}`);
        }
    }

    /**
     * 加载活动摘要数据
     * @param {HTMLElement} container 统计容器
     */
    loadActivitySummary(container) {
        this.showLoading(container);

        fetch(this.apiEndpoints.activitySummary)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success && Array.isArray(data.data)) {
                    this.renderActivitySummary(container, data.data);
                } else {
                    this.showError(container, data.error || '获取活动摘要数据失败');
                }
            })
            .catch(error => {
                console.error('[QUANTUM-VIZ] 加载活动摘要失败:', error);
                this.showError(container, `获取活动摘要数据失败: ${error.message}`);
            });
    }

    /**
     * 渲染活动摘要统计
     * @param {HTMLElement} container 统计容器
     * @param {Array} data 统计数据
     */
    renderActivitySummary(container, data) {
        // 验证数据
        if (!Array.isArray(data) || data.length === 0) {
            this.showError(container, '没有活动摘要数据');
            return;
        }

        try {
            // 清空容器
            container.innerHTML = '';

            // 创建Canvas元素
            const canvas = document.createElement('canvas');
            container.appendChild(canvas);

            // 确保Chart.js已加载
            if (typeof Chart === 'undefined') {
                this.showError(container, '图表库未加载');
                return;
            }

            // 数据验证和格式化
            const validData = data.filter(item =>
                item && typeof item === 'object' &&
                item.name && !isNaN(item.value) && item.color
            );

            if (validData.length === 0) {
                this.showError(container, '活动摘要数据无效');
                return;
            }

            // 尝试获取2D上下文，失败时优雅降级
            let ctx;
            try {
                ctx = canvas.getContext('2d');
            } catch (e) {
                console.error('[QUANTUM-VIZ] 无法获取Canvas上下文:', e);
                // 使用DOM渲染统计卡片组
                this.renderAsStatCards(container, validData);
                return;
            }

            if (!ctx) {
                console.error('[QUANTUM-VIZ] Canvas上下文为空');
                this.renderAsStatCards(container, validData);
                return;
            }

            // 创建图表
            try {
                const chart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: validData.map(item => item.name),
                        datasets: [{
                            data: validData.map(item => item.value),
                            backgroundColor: validData.map(item => item.color),
                            hoverOffset: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: '活动摘要',
                                color: this.themes[this.currentTheme].text
                            },
                            legend: {
                                position: 'right',
                                labels: {
                                    color: this.themes[this.currentTheme].text
                                }
                            }
                        }
                    }
                });

                // 保存图表引用
                this.charts.activitySummary = chart;
            } catch (e) {
                console.error('[QUANTUM-VIZ] 创建图表失败:', e);
                this.renderAsStatCards(container, validData);
            }
        } catch (error) {
            console.error('[QUANTUM-VIZ] 渲染活动摘要失败:', error);
            this.showError(container, `渲染图表失败: ${error.message}`);
        }
    }

    /**
     * 渲染为表格(当Canvas渲染失败时的备选项)
     * @param {HTMLElement} container 容器元素
     * @param {Array} data 数据
     * @param {string} keyLabel 键标签
     * @param {string} valueLabel 值标签
     */
    renderAsTable(container, data, keyLabel = '名称', valueLabel = '值') {
        container.innerHTML = '';

        const table = document.createElement('table');
        table.className = 'table table-striped table-hover';

        // 创建表头
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        const keyHeader = document.createElement('th');
        keyHeader.textContent = keyLabel;
        const valueHeader = document.createElement('th');
        valueHeader.textContent = valueLabel;
        headerRow.appendChild(keyHeader);
        headerRow.appendChild(valueHeader);
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // 创建表体
        const tbody = document.createElement('tbody');
        data.forEach(item => {
            const row = document.createElement('tr');

            const keyCell = document.createElement('td');
            keyCell.textContent = item.name || item.rating || item.x || '';

            const valueCell = document.createElement('td');
            valueCell.textContent = item.value || item.count || item.y || 0;

            row.appendChild(keyCell);
            row.appendChild(valueCell);
            tbody.appendChild(row);
        });

        table.appendChild(tbody);
        container.appendChild(table);
    }

    /**
     * 渲染趋势数据为表格(当Canvas渲染失败时的备选项)
     * @param {HTMLElement} container 容器元素
     * @param {Array} data 趋势数据
     */
    renderAsTrendTable(container, data) {
        container.innerHTML = '';

        const table = document.createElement('table');
        table.className = 'table table-striped table-hover';

        // 创建表头
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');

        const dateHeader = document.createElement('th');
        dateHeader.textContent = '日期';
        const viewsHeader = document.createElement('th');
        viewsHeader.textContent = '浏览量';
        const ratingsHeader = document.createElement('th');
        ratingsHeader.textContent = '评分数';

        headerRow.appendChild(dateHeader);
        headerRow.appendChild(viewsHeader);
        headerRow.appendChild(ratingsHeader);
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // 创建表体
        const tbody = document.createElement('tbody');
        data.forEach(item => {
            const row = document.createElement('tr');

            const dateCell = document.createElement('td');
            try {
                const date = new Date(item.date);
                dateCell.textContent = date.toLocaleDateString();
            } catch (e) {
                dateCell.textContent = item.date || '';
            }

            const viewsCell = document.createElement('td');
            viewsCell.textContent = item.views || 0;

            const ratingsCell = document.createElement('td');
            ratingsCell.textContent = item.ratings || 0;

            row.appendChild(dateCell);
            row.appendChild(viewsCell);
            row.appendChild(ratingsCell);
            tbody.appendChild(row);
        });

        table.appendChild(tbody);
        container.appendChild(table);
    }

    /**
     * 渲染为统计卡片组(当Canvas渲染失败时的备选项)
     * @param {HTMLElement} container 容器元素
     * @param {Array} data 统计数据
     */
    renderAsStatCards(container, data) {
        container.innerHTML = '';

        const cardsContainer = document.createElement('div');
        cardsContainer.className = 'row g-2';

        data.forEach(item => {
            const cardCol = document.createElement('div');
            cardCol.className = 'col-6 col-md-3';

            const card = document.createElement('div');
            card.className = 'card h-100';
            card.style.borderTop = `3px solid ${item.color}`;

            const cardBody = document.createElement('div');
            cardBody.className = 'card-body text-center';

            const value = document.createElement('h3');
            value.className = 'card-title mb-0';
            value.textContent = item.value;

            const name = document.createElement('p');
            name.className = 'card-text text-muted';
            name.textContent = item.name;

            cardBody.appendChild(value);
            cardBody.appendChild(name);
            card.appendChild(cardBody);
            cardCol.appendChild(card);
            cardsContainer.appendChild(cardCol);
        });

        container.appendChild(cardsContainer);
    }

    /**
     * 显示加载状态
     * @param {HTMLElement} container 容器元素
     */
    showLoading(container) {
        container.innerHTML = `
            <div class="loading-container">
                <div class="quantum-spinner"></div>
                <p class="mt-3">数据加载中...</p>
            </div>
        `;
    }

    /**
     * 显示错误状态
     * @param {HTMLElement} container 容器元素
     * @param {string} message 错误信息
     */
    showError(container, message) {
        container.innerHTML = `
            <div class="error-container">
                <div class="error-icon">
                    <i class="fas fa-exclamation-triangle text-warning"></i>
                </div>
                <p class="mt-3">${message}</p>
                <button class="btn btn-sm btn-primary mt-2 refresh-btn">
                    <i class="fas fa-sync-alt me-1"></i>重试
                </button>
            </div>
        `;

        // 绑定重试按钮
        const refreshBtn = container.querySelector('.refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                // 获取容器ID以确定图表类型
                const containerId = container.id;

                if (containerId.includes('rating_distribution')) {
                    this.loadRatingDistribution(container);
                } else if (containerId.includes('genre_preference')) {
                    this.loadGenrePreference(container);
                } else if (containerId.includes('viewing_trends')) {
                    this.loadViewingTrends(container);
                } else if (containerId.includes('activity_summary')) {
                    this.loadActivitySummary(container);
                }
            });
        }
    }

    /**
     * 保存用户偏好设置
     * @param {Object} preferences 偏好设置
     */
    saveUserPreferences(preferences) {
        const csrfToken = this.getCsrfToken();
        if (!csrfToken) {
            console.error('[QUANTUM-VIZ] 无法获取CSRF Token');
            return;
        }

        fetch(this.apiEndpoints.updatePreferences, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(preferences)
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (!data.success) {
                    console.error('[QUANTUM-VIZ] 保存偏好设置失败:', data.error);
                }
            })
            .catch(error => {
                console.error('[QUANTUM-VIZ] 保存偏好设置失败:', error);
            });
    }

    /**
     * 保存仪表盘布局
     */
    saveDashboard() {
        const nameInput = document.getElementById('dashboardName');
        if (nameInput) {
            this.dashboard.name = nameInput.value || '我的仪表盘';
        }

        const csrfToken = this.getCsrfToken();
        if (!csrfToken) {
            console.error('[QUANTUM-VIZ] 无法获取CSRF Token');
            this.showToast('保存失败，无法获取CSRF Token', 'danger');
            return;
        }

        fetch(this.apiEndpoints.saveDashboard, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                dashboard_id: this.dashboard.id,
                name: this.dashboard.name,
                layout: this.dashboard.layout
            })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // 更新仪表盘ID
                    this.dashboard.id = data.dashboard_id;

                    // 显示成功消息
                    this.showToast('仪表盘已保存', 'success');
                } else {
                    console.error('[QUANTUM-VIZ] 保存仪表盘失败:', data.error);
                    this.showToast(`保存失败: ${data.error}`, 'danger');
                }
            })
            .catch(error => {
                console.error('[QUANTUM-VIZ] 保存仪表盘失败:', error);
                this.showToast('保存失败，请稍后再试', 'danger');
            });
    }

    /**
     * 导出图表
     * @param {string} chartType 图表类型
     * @param {string} format 导出格式
     */
    exportChart(chartType, format) {
        const url = `${this.apiEndpoints.exportVisualization}${chartType}/?format=${format}`;

        // 打开下载窗口
        window.open(url, '_blank');
    }

    /**
     * 显示消息提示
     * @param {string} message 消息内容
     * @param {string} type 消息类型
     */
    showToast(message, type = 'info') {
        // 查找或创建toast容器
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }

        // 创建toast元素
        const toastId = `toast-${Date.now()}`;
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.id = toastId;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;

        toastContainer.appendChild(toast);

        // 显示toast
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            const bsToast = new bootstrap.Toast(toast, {
                autohide: true,
                delay: 3000
            });
            bsToast.show();
        } else {
            // 备用方案: 如果Bootstrap不可用
            toast.style.display = 'block';
            setTimeout(() => {
                toast.remove();
            }, 3000);
        }

        // 自动删除toast元素
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    /**
     * 获取CSRF Token
     * @returns {string} CSRF Token
     */
    getCsrfToken() {
        const tokenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (tokenInput && tokenInput.value) {
            return tokenInput.value;
        }

        const tokenCookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
        if (tokenCookie) {
            return tokenCookie.split('=')[1];
        }

        return null;
    }
}

// 安全地初始化可视化引擎
document.addEventListener('DOMContentLoaded', () => {
    try {
        window.vizCore = new VisualizationCore();
    } catch (e) {
        console.error('[QUANTUM-VIZ] 初始化可视化引擎失败:', e);
    }
});