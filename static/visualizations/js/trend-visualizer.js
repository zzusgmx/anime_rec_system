/**
 * 趋势可视化
 * 实现各种动态趋势图表
 */
class TrendVisualizer {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('[QUANTUM-TREND] 容器不存在:', containerId);
            return;
        }

        // 默认选项
        this.options = {
            width: this.container.clientWidth,
            height: 400,
            margin: { top: 30, right: 20, bottom: 50, left: 50 },
            animationDuration: 800,
            type: 'line',  // line, bar, area
            theme: 'quantum',
            ...options
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
        this.currentTheme = this.themes[this.options.theme] || this.themes.quantum;

        // 数据
        this.data = [];

        // 初始化
        this.init();
    }

    /**
     * 初始化可视化
     */
    init() {
        // 创建SVG容器
        this.svg = d3.select(`#${this.containerId}`)
            .append('svg')
            .attr('width', this.options.width)
            .attr('height', this.options.height)
            .attr('class', 'trend-svg');

        // 创建容器组
        this.chart = this.svg.append('g')
            .attr('class', 'trend-container')
            .attr('transform', `translate(${this.options.margin.left}, ${this.options.margin.top})`);

        // 创建工具提示
        this.tooltip = d3.select('body').append('div')
            .attr('class', 'trend-tooltip')
            .style('opacity', 0)
            .style('position', 'absolute')
            .style('background', 'rgba(15, 23, 42, 0.8)')
            .style('color', 'white')
            .style('padding', '8px 12px')
            .style('border-radius', '6px')
            .style('font-size', '0.8rem')
            .style('pointer-events', 'none')
            .style('z-index', 1000);

        // 创建图例组
        this.legend = this.svg.append('g')
            .attr('class', 'trend-legend')
            .attr('transform', `translate(${this.options.margin.left}, 10)`);

        // 响应窗口大小变化
        window.addEventListener('resize', this.resize.bind(this));
    }

    /**
     * 加载数据
     * @param {Array} data 趋势数据
     */
    loadData(data) {
    // 检查是否为空数据
    if (!data || (Array.isArray(data) && data.length === 0)) {
        console.warn('[QUANTUM-TREND] 加载的数据为空，将使用模拟数据');

        // 根据图表类型生成模拟数据
        if (this.options.type === 'line' || this.options.type === 'area') {
            // 为线图生成模拟数据
            const mockData = [];
            const months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'];
            const currentYear = new Date().getFullYear();

            for (let i = 0; i < months.length; i++) {
                mockData.push({
                    x: `${currentYear}-${months[i]}-01`,
                    y: Math.floor(Math.random() * 50) + 50
                });
            }

            this.data = mockData;
        } else if (this.options.type === 'bar') {
            // 为柱状图生成模拟数据
            const mockData = [];
            const categories = ['类型A', '类型B', '类型C', '类型D', '类型E'];

            for (let i = 0; i < categories.length; i++) {
                mockData.push({
                    name: categories[i],
                    value: Math.floor(Math.random() * 50) + 50
                });
            }

            this.data = mockData;
        } else if (this.options.type === 'doughnut' || this.options.type === 'pie') {
            // 为饼图/环形图生成模拟数据
            const mockData = [];
            const categories = ['类别A', '类别B', '类别C', '类别D'];

            for (let i = 0; i < categories.length; i++) {
                mockData.push({
                    name: categories[i],
                    value: Math.floor(Math.random() * 30) + 10
                });
            }

            this.data = mockData;
        } else {
            // 默认空数据
            this.data = [];
        }
    } else {
        this.data = data;
    }

    this.render();
}

    /**
     * 渲染趋势图
     */
    render() {
        // 清空容器
        this.chart.selectAll('*').remove();
        this.legend.selectAll('*').remove();

        // 如果没有数据，显示提示
        if (!this.data || this.data.length === 0) {
            this.showEmptyState();
            return;
        }

        // 计算可用宽度和高度
        const width = this.options.width - this.options.margin.left - this.options.margin.right;
        const height = this.options.height - this.options.margin.top - this.options.margin.bottom;

        // 确定数据结构类型
        // 数据可能是单系列或多系列
        const isMultiSeries = Array.isArray(this.data[0]) ||
                             (typeof this.data[0] === 'object' && this.data[0] !== null && this.data[0].hasOwnProperty('series'));

        if (isMultiSeries) {
            this.renderMultiSeries(width, height);
        } else {
            this.renderSingleSeries(width, height);
        }
    }

    /**
     * 渲染单一数据系列
     * @param {number} width 可用宽度
     * @param {number} height 可用高度
     */
    renderSingleSeries(width, height) {
        // 数据验证
        const validData = this.data.filter(d =>
            d && typeof d === 'object' &&
            (d.x !== undefined || d.label !== undefined || d.category !== undefined) &&
            (d.y !== undefined || d.value !== undefined)
        );

        if (validData.length === 0) {
            this.showEmptyState();
            return;
        }

        // 获取X值
        const xValues = validData.map(d => d.x || d.label || d.category);

        // 设置X轴比例尺
        const xScale = d3.scalePoint()
            .domain(xValues)
            .range([0, width])
            .padding(0.5);

        // 获取Y值
        const yValues = validData.map(d => d.y || d.value || 0);
        const yMax = d3.max(yValues) || 1;

        // 设置Y轴比例尺
        const yScale = d3.scaleLinear()
            .domain([0, yMax * 1.1])
            .range([height, 0]);

        try {
            // 绘制X轴
            this.chart.append('g')
                .attr('class', 'x-axis')
                .attr('transform', `translate(0, ${height})`)
                .call(d3.axisBottom(xScale))
                .selectAll('text')
                .style('text-anchor', 'end')
                .attr('dx', '-.8em')
                .attr('dy', '.15em')
                .attr('transform', 'rotate(-45)');

            // 绘制Y轴
            this.chart.append('g')
                .attr('class', 'y-axis')
                .call(d3.axisLeft(yScale));

            // 绘制网格线
            this.chart.append('g')
                .attr('class', 'grid')
                .selectAll('line')
                .data(yScale.ticks())
                .enter().append('line')
                .attr('x1', 0)
                .attr('y1', d => yScale(d))
                .attr('x2', width)
                .attr('y2', d => yScale(d))
                .attr('stroke', this.currentTheme.grid)
                .attr('stroke-dasharray', '3,3');

            // 根据图表类型绘制
            if (this.options.type === 'line' || this.options.type === 'area') {
                this.drawLineChart(xScale, yScale, validData, this.currentTheme.colors[0], width, height);
            } else if (this.options.type === 'bar') {
                this.drawBarChart(xScale, yScale, validData, this.currentTheme.colors[0], width, height);
            }
        } catch (error) {
            console.error('[QUANTUM-TREND] 渲染单系列图表错误:', error);
            this.showErrorState(error.message);
        }
    }

    /**
     * 渲染多系列数据
     * @param {number} width 可用宽度
     * @param {number} height 可用高度
     */
    renderMultiSeries(width, height) {
        try {
            // 标准化数据
            let series = [];
            if (Array.isArray(this.data[0])) {
                // 多个数组形式
                series = this.data.map((data, i) => ({
                    name: `Series ${i + 1}`,
                    data: data
                }));
            } else {
                // 包含series属性的对象
                series = this.data;
            }

            // 数据验证
            series = series.filter(s => s && Array.isArray(s.data) && s.data.length > 0);

            if (series.length === 0) {
                this.showEmptyState();
                return;
            }

            // 获取所有X值
            const allX = new Set();
            series.forEach(s => {
                s.data.forEach(d => {
                    if (d && (d.x !== undefined || d.label !== undefined || d.category !== undefined)) {
                        allX.add(d.x || d.label || d.category);
                    }
                });
            });
            const xValues = Array.from(allX);

            if (xValues.length === 0) {
                this.showEmptyState();
                return;
            }

            // 设置X轴比例尺
            const xScale = d3.scalePoint()
                .domain(xValues)
                .range([0, width])
                .padding(0.5);

            // 找出最大Y值
            let maxY = 0;
            series.forEach(s => {
                s.data.forEach(d => {
                    const value = d.y || d.value || 0;
                    if (!isNaN(value) && value > maxY) {
                        maxY = value;
                    }
                });
            });

            if (maxY === 0) maxY = 1; // 防止数据全为0

            // 设置Y轴比例尺
            const yScale = d3.scaleLinear()
                .domain([0, maxY * 1.1])
                .range([height, 0]);

            // 绘制X轴
            this.chart.append('g')
                .attr('class', 'x-axis')
                .attr('transform', `translate(0, ${height})`)
                .call(d3.axisBottom(xScale))
                .selectAll('text')
                .style('text-anchor', 'end')
                .attr('dx', '-.8em')
                .attr('dy', '.15em')
                .attr('transform', 'rotate(-45)');

            // 绘制Y轴
            this.chart.append('g')
                .attr('class', 'y-axis')
                .call(d3.axisLeft(yScale));

            // 绘制网格线
            this.chart.append('g')
                .attr('class', 'grid')
                .selectAll('line')
                .data(yScale.ticks())
                .enter().append('line')
                .attr('x1', 0)
                .attr('y1', d => yScale(d))
                .attr('x2', width)
                .attr('y2', d => yScale(d))
                .attr('stroke', this.currentTheme.grid)
                .attr('stroke-dasharray', '3,3');

            // 绘制每个系列
            series.forEach((s, i) => {
                const color = this.currentTheme.colors[i % this.currentTheme.colors.length];

                // 过滤有效数据
                const validData = s.data.filter(d =>
                    d && typeof d === 'object' &&
                    (d.x !== undefined || d.label !== undefined || d.category !== undefined)
                );

                if (validData.length === 0) return;

                if (this.options.type === 'line' || this.options.type === 'area') {
                    this.drawLineChart(xScale, yScale, validData, color, width, height, s.name);
                } else if (this.options.type === 'bar') {
                    const barWidth = (width / xValues.length / series.length) * 0.8;
                    const barOffset = i * barWidth;
                    this.drawBarChart(xScale, yScale, validData, color, width, height, barWidth, barOffset, s.name);
                }
            });

            // 绘制图例
            this.drawLegend(series);
        } catch (error) {
            console.error('[QUANTUM-TREND] 渲染多系列图表错误:', error);
            this.showErrorState(error.message);
        }
    }

    /**
     * 绘制折线图
     * @param {d3.scale} xScale X轴比例尺
     * @param {d3.scale} yScale Y轴比例尺
     * @param {Array} data 数据
     * @param {string} color 线条颜色
     * @param {number} width 宽度
     * @param {number} height 高度
     * @param {string} seriesName 系列名称
     */
    drawLineChart(xScale, yScale, data, color, width, height, seriesName = '') {
        try {
            // 确保数据点有效
            const validData = data.filter(d => {
                const x = d.x || d.label || d.category;
                const y = d.y || d.value || 0;
                return x !== undefined && !isNaN(y);
            });

            if (validData.length === 0) return;

            // 创建线条生成器
            const line = d3.line()
                .x(d => {
                    const x = xScale(d.x || d.label || d.category);
                    return isNaN(x) ? 0 : x;
                })
                .y(d => {
                    const y = yScale(d.y || d.value || 0);
                    return isNaN(y) ? height : y;
                })
                .curve(d3.curveMonotoneX);

            // 绘制线条
            const path = this.chart.append('path')
                .datum(validData)
                .attr('class', 'line')
                .attr('fill', 'none')
                .attr('stroke', color)
                .attr('stroke-width', 2)
                .attr('d', line);

            // 添加动画
            const pathLength = path.node()?.getTotalLength() || 0;
            if (pathLength > 0) {
                path.attr('stroke-dasharray', pathLength)
                    .attr('stroke-dashoffset', pathLength)
                    .transition()
                    .duration(this.options.animationDuration)
                    .attr('stroke-dashoffset', 0);
            }

            // 如果是面积图，添加面积
            if (this.options.type === 'area') {
                const area = d3.area()
                    .x(d => {
                        const x = xScale(d.x || d.label || d.category);
                        return isNaN(x) ? 0 : x;
                    })
                    .y0(height)
                    .y1(d => {
                        const y = yScale(d.y || d.value || 0);
                        return isNaN(y) ? height : y;
                    })
                    .curve(d3.curveMonotoneX);

                this.chart.append('path')
                    .datum(validData)
                    .attr('class', 'area')
                    .attr('fill', color)
                    .attr('fill-opacity', 0.1)
                    .attr('d', area)
                    .style('opacity', 0)
                    .transition()
                    .duration(this.options.animationDuration)
                    .style('opacity', 1);
            }

            // 添加数据点
            this.chart.selectAll('.dot')
                .data(validData)
                .enter().append('circle')
                .attr('class', 'dot')
                .attr('cx', d => {
                    const x = xScale(d.x || d.label || d.category);
                    return isNaN(x) ? 0 : x;
                })
                .attr('cy', d => {
                    const y = yScale(d.y || d.value || 0);
                    return isNaN(y) ? height : y;
                })
                .attr('r', 0)
                .attr('fill', color)
                .attr('stroke', '#fff')
                .attr('stroke-width', 1.5)
                .on('mouseover', (event, d) => this.showTooltip(event, d, seriesName))
                .on('mouseout', () => this.hideTooltip())
                .transition()
                .duration(this.options.animationDuration)
                .delay((d, i) => i * (this.options.animationDuration / validData.length))
                .attr('r', 5);
        } catch (error) {
            console.error('[QUANTUM-TREND] 绘制折线图错误:', error);
        }
    }

    /**
     * 绘制柱状图
     * @param {d3.scale} xScale X轴比例尺
     * @param {d3.scale} yScale Y轴比例尺
     * @param {Array} data 数据
     * @param {string} color 柱子颜色
     * @param {number} width 图表宽度
     * @param {number} height 图表高度
     * @param {number} barWidth 柱子宽度
     * @param {number} barOffset 柱子偏移量
     * @param {string} seriesName 系列名称
     */
    drawBarChart(xScale, yScale, data, color, width, height, barWidth = null, barOffset = 0, seriesName = '') {
        try {
            // 确保数据点有效
            const validData = data.filter(d => {
                const x = d.x || d.label || d.category;
                const y = d.y || d.value || 0;
                return x !== undefined && !isNaN(y);
            });

            if (validData.length === 0) return;

            // 默认柱宽度
            if (!barWidth) {
                barWidth = (xScale.range()[1] / validData.length) * 0.8;
            }

            // 绘制柱子
            this.chart.selectAll('.bar')
                .data(validData)
                .enter().append('rect')
                .attr('class', 'bar')
                .attr('x', d => {
                    const x = xScale(d.x || d.label || d.category);
                    return isNaN(x) ? 0 : x - barWidth / 2 + barOffset;
                })
                .attr('y', height)
                .attr('width', barWidth)
                .attr('height', 0)
                .attr('fill', color)
                .attr('fill-opacity', 0.8)
                .on('mouseover', (event, d) => this.showTooltip(event, d, seriesName))
                .on('mouseout', () => this.hideTooltip())
                .transition()
                .duration(this.options.animationDuration)
                .attr('y', d => {
                    const y = yScale(d.y || d.value || 0);
                    return isNaN(y) ? height : y;
                })
                .attr('height', d => {
                    const y = yScale(d.y || d.value || 0);
                    return isNaN(y) ? 0 : height - y;
                });
        } catch (error) {
            console.error('[QUANTUM-TREND] 绘制柱状图错误:', error);
        }
    }

    /**
     * 绘制图例
     * @param {Array} series 数据系列
     */
    drawLegend(series) {
        try {
            // 过滤有效系列
            const validSeries = series.filter(s => s && s.name);

            if (validSeries.length === 0) return;

            const legendItems = this.legend.selectAll('.legend-item')
                .data(validSeries)
                .enter().append('g')
                .attr('class', 'legend-item')
                .attr('transform', (d, i) => {
                    const offset = i * 100;
                    return isNaN(offset) ? `translate(0, 0)` : `translate(${offset}, 0)`;
                });

            legendItems.append('rect')
                .attr('width', 12)
                .attr('height', 12)
                .attr('fill', (d, i) => this.currentTheme.colors[i % this.currentTheme.colors.length]);

            legendItems.append('text')
                .attr('x', 18)
                .attr('y', 9)
                .attr('font-size', 12)
                .text(d => d.name);
        } catch (error) {
            console.error('[QUANTUM-TREND] 绘制图例错误:', error);
        }
    }

    /**
     * 显示工具提示
     * @param {Event} event 事件对象
     * @param {Object} d 数据点
     * @param {string} seriesName 系列名称
     */
    showTooltip(event, d, seriesName) {
        try {
            this.tooltip.transition()
                .duration(200)
                .style('opacity', .9);

            const value = d.y || d.value || 0;
            const label = d.x || d.label || d.category || '';

            let html = `<div>${label}: <b>${this.formatValue(value)}</b></div>`;
            if (seriesName) {
                html = `<div class="font-bold">${seriesName}</div>` + html;
            }

            this.tooltip.html(html)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
        } catch (error) {
            console.error('[QUANTUM-TREND] 显示工具提示错误:', error);
        }
    }

    /**
     * 隐藏工具提示
     */
    hideTooltip() {
        this.tooltip.transition()
            .duration(500)
            .style('opacity', 0);
    }

    /**
     * 格式化数值
     * @param {number} value 数值
     * @returns {string} 格式化后的字符串
     */
    formatValue(value) {
        if (typeof value !== 'number' || isNaN(value)) return '0';

        // 如果是整数，返回原值
        if (Number.isInteger(value)) return value.toString();

        // 如果是小数，保留两位小数
        return value.toFixed(2);
    }

    /**
     * 设置主题
     * @param {string} theme 主题名称
     */
    setTheme(theme) {
        if (!this.themes[theme]) {
            console.warn(`[QUANTUM-TREND] 未知主题: ${theme}, 使用默认主题`);
            theme = 'quantum';
        }

        this.options.theme = theme;
        this.currentTheme = this.themes[theme];

        // 重新渲染
        this.render();
    }

    /**
     * 调整大小
     */
    resize() {
        try {
            const width = this.container.clientWidth || this.options.width;

            this.options.width = width;
            this.svg.attr('width', width);

            this.render();
        } catch (error) {
            console.error('[QUANTUM-TREND] 调整大小错误:', error);
        }
    }

    /**
     * 显示空状态
     */
    showEmptyState() {
        try {
            const width = this.options.width - this.options.margin.left - this.options.margin.right;
            const height = this.options.height - this.options.margin.top - this.options.margin.bottom;

            this.chart.append('text')
                .attr('x', width / 2)
                .attr('y', height / 2)
                .attr('text-anchor', 'middle')
                .attr('font-size', 16)
                .text('暂无数据');
        } catch (error) {
            console.error('[QUANTUM-TREND] 显示空状态错误:', error);
        }
    }

    /**
     * 显示错误状态
     * @param {string} message 错误消息
     */
    showErrorState(message) {
        try {
            const width = this.options.width - this.options.margin.left - this.options.margin.right;
            const height = this.options.height - this.options.margin.top - this.options.margin.bottom;

            this.chart.append('text')
                .attr('x', width / 2)
                .attr('y', height / 2)
                .attr('text-anchor', 'middle')
                .attr('font-size', 16)
                .attr('fill', 'red')
                .text('图表渲染错误');

            this.chart.append('text')
                .attr('x', width / 2)
                .attr('y', height / 2 + 24)
                .attr('text-anchor', 'middle')
                .attr('font-size', 12)
                .attr('fill', '#666')
                .text(message || '请检查数据格式');
        } catch (error) {
            console.error('[QUANTUM-TREND] 显示错误状态错误:', error);
        }
    }
}