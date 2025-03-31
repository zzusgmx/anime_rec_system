/**
 * 用户旅程时间线可视化
 * 将用户在系统中的互动行为以时间线形式可视化
 */
class UserJourneyTimeline {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('[QUANTUM-TIMELINE] 容器不存在:', containerId);
            return;
        }

        // 默认选项
        this.options = {
            width: this.container.clientWidth || 800,
            height: 600,
            margin: { top: 50, right: 20, bottom: 50, left: 50 },
            eventRadius: 8,
            ...options
        };

        // 数据
        this.data = [];

        // 初始化
        this.init();
    }

    /**
     * 初始化可视化
     */
    init() {
        try {
            // 创建SVG容器
            this.svg = d3.select(`#${this.containerId}`)
                .append('svg')
                .attr('width', this.options.width)
                .attr('height', this.options.height)
                .attr('class', 'timeline-svg');

            // 创建容器组
            this.container = this.svg.append('g')
                .attr('class', 'timeline-container')
                .attr('transform', `translate(${this.options.margin.left}, ${this.options.margin.top})`);

            // 创建工具提示
            this.tooltip = d3.select('body').append('div')
                .attr('class', 'timeline-tooltip')
                .style('opacity', 0)
                .style('position', 'absolute')
                .style('background', 'rgba(15, 23, 42, 0.8)')
                .style('color', 'white')
                .style('padding', '8px 12px')
                .style('border-radius', '6px')
                .style('font-size', '0.8rem')
                .style('pointer-events', 'none')
                .style('z-index', 1000);

            // 创建图例
            this.createLegend();

            // 响应窗口大小变化
            window.addEventListener('resize', this.resize.bind(this));
        } catch (error) {
            console.error('[QUANTUM-TIMELINE] 初始化错误:', error);
        }
    }

    /**
     * 加载数据
     * @param {Array} data 时间线数据
     */
    loadData(data) {
        try {
            if (!data || !Array.isArray(data)) {
                console.warn('[QUANTUM-TIMELINE] 无效的时间线数据');
                this.data = [];
            } else {
                // 验证数据
                this.data = data.filter(item =>
                    item &&
                    typeof item === 'object' &&
                    item.date &&
                    item.type &&
                    typeof item.date === 'string'
                );

                // 按日期排序
                this.data.sort((a, b) => new Date(a.date) - new Date(b.date));
            }

            this.render();
        } catch (error) {
            console.error('[QUANTUM-TIMELINE] 加载数据错误:', error);
            this.data = [];
            this.showErrorState('加载数据错误');
        }
    }

    /**
     * 渲染时间线
     */
    render() {
        try {
            // 清空容器
            this.container.selectAll('*').remove();

            // 如果没有数据，显示提示
            if (!this.data || this.data.length === 0) {
                this.showEmptyState();
                return;
            }

            // 计算可用宽度和高度
            const width = this.options.width - this.options.margin.left - this.options.margin.right;
            const height = this.options.height - this.options.margin.top - this.options.margin.bottom;

            // 设置时间比例尺
            let timeExtent;
            try {
                timeExtent = d3.extent(this.data, d => new Date(d.date));
                // 如果日期解析失败，设置默认范围
                if (timeExtent[0] === undefined || timeExtent[1] === undefined ||
                    isNaN(timeExtent[0].getTime()) || isNaN(timeExtent[1].getTime())) {
                    const now = new Date();
                    timeExtent = [
                        new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000), // 30天前
                        now
                    ];
                }
            } catch (e) {
                console.error('[QUANTUM-TIMELINE] 日期解析错误:', e);
                const now = new Date();
                timeExtent = [
                    new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000), // 30天前
                    now
                ];
            }

            const xScale = d3.scaleTime()
                .domain(timeExtent)
                .range([0, width]);

            // 设置类型比例尺
            const types = ['browse', 'rate', 'comment', 'like', 'favorite'];
            const yScale = d3.scalePoint()
                .domain(types)
                .range([0, height])
                .padding(0.5);

            // 绘制坐标轴
            this.container.append('g')
                .attr('class', 'x-axis')
                .attr('transform', `translate(0, ${height})`)
                .call(d3.axisBottom(xScale));

            this.container.append('g')
                .attr('class', 'y-axis')
                .call(d3.axisLeft(yScale)
                    .tickFormat(d => {
                        const labels = {
                            browse: '浏览',
                            rate: '评分',
                            comment: '评论',
                            like: '点赞',
                            favorite: '收藏'
                        };
                        return labels[d] || d;
                    }));

            // 绘制背景网格线
            this.container.append('g')
                .attr('class', 'grid')
                .selectAll('line')
                .data(yScale.domain())
                .enter().append('line')
                .attr('x1', 0)
                .attr('y1', d => {
                    const y = yScale(d);
                    return isNaN(y) ? 0 : y;
                })
                .attr('x2', width)
                .attr('y2', d => {
                    const y = yScale(d);
                    return isNaN(y) ? 0 : y;
                })
                .attr('stroke', '#e2e8f0')
                .attr('stroke-dasharray', '3,3');

            // 绘制事件点
            const validEvents = this.data.filter(d => {
                try {
                    const date = new Date(d.date);
                    return !isNaN(date.getTime()) && types.includes(d.type);
                } catch (e) {
                    return false;
                }
            });

            this.container.append('g')
                .attr('class', 'events')
                .selectAll('circle')
                .data(validEvents)
                .enter().append('circle')
                .attr('cx', d => {
                    try {
                        const date = new Date(d.date);
                        const x = xScale(date);
                        return isNaN(x) ? 0 : x;
                    } catch (e) {
                        return 0;
                    }
                })
                .attr('cy', d => {
                    const y = yScale(d.type);
                    return isNaN(y) ? 0 : y;
                })
                .attr('r', this.options.eventRadius)
                .attr('fill', d => this.getEventColor(d.type))
                .attr('stroke', '#fff')
                .attr('stroke-width', 1.5)
                .on('mouseover', this.showEventTooltip.bind(this))
                .on('mouseout', this.hideTooltip.bind(this))
                .on('click', this.handleEventClick.bind(this));

            // 绘制连接线
            this.drawConnectionLines(xScale, yScale, validEvents);
        } catch (error) {
            console.error('[QUANTUM-TIMELINE] 渲染错误:', error);
            this.showErrorState('渲染时间线错误');
        }
    }

    /**
     * 绘制事件之间的连接线
     * @param {d3.scale} xScale X轴比例尺
     * @param {d3.scale} yScale Y轴比例尺
     * @param {Array} events 事件数据
     */
    drawConnectionLines(xScale, yScale, events) {
        try {
            if (!events || events.length === 0) return;

            // 按时间排序数据
            const sortedData = [...events].sort((a, b) => new Date(a.date) - new Date(b.date));

            // 验证数据点
            const validPoints = sortedData.filter(d => {
                try {
                    const date = new Date(d.date);
                    const x = xScale(date);
                    const y = yScale(d.type);
                    return !isNaN(x) && !isNaN(y);
                } catch (e) {
                    return false;
                }
            });

            if (validPoints.length < 2) return;

            // 创建线条生成器
            const lineGenerator = d3.line()
                .x(d => {
                    try {
                        const date = new Date(d.date);
                        const x = xScale(date);
                        return isNaN(x) ? 0 : x;
                    } catch (e) {
                        return 0;
                    }
                })
                .y(d => {
                    const y = yScale(d.type);
                    return isNaN(y) ? 0 : y;
                })
                .curve(d3.curveMonotoneX);

            // 绘制连接线
            this.container.append('path')
                .datum(validPoints)
                .attr('class', 'journey-path')
                .attr('fill', 'none')
                .attr('stroke', '#6d28d9')
                .attr('stroke-width', 2)
                .attr('stroke-opacity', 0.6)
                .attr('d', lineGenerator);

            // 创建渐变区域
            const areaGenerator = d3.area()
                .x(d => {
                    try {
                        const date = new Date(d.date);
                        const x = xScale(date);
                        return isNaN(x) ? 0 : x;
                    } catch (e) {
                        return 0;
                    }
                })
                .y0(d => {
                    const y = yScale(d.type);
                    return isNaN(y) ? 0 : (y + 20);
                })
                .y1(d => {
                    const y = yScale(d.type);
                    return isNaN(y) ? 0 : (y - 20);
                })
                .curve(d3.curveMonotoneX);

            this.container.append('path')
                .datum(validPoints)
                .attr('class', 'journey-area')
                .attr('fill', 'url(#journey-gradient)')
                .attr('fill-opacity', 0.2)
                .attr('d', areaGenerator);
        } catch (error) {
            console.error('[QUANTUM-TIMELINE] 绘制连接线错误:', error);
        }
    }

    /**
     * 创建图例
     */
    createLegend() {
        try {
            const legend = this.svg.append('g')
                .attr('class', 'legend')
                .attr('transform', `translate(${this.options.width - 150}, 20)`);

            const types = [
                { type: 'browse', label: '浏览', color: '#3b82f6' },
                { type: 'rate', label: '评分', color: '#10b981' },
                { type: 'comment', label: '评论', color: '#f97316' },
                { type: 'like', label: '点赞', color: '#ef4444' },
                { type: 'favorite', label: '收藏', color: '#8b5cf6' }
            ];

            const legendItem = legend.selectAll('.legend-item')
                .data(types)
                .enter().append('g')
                .attr('class', 'legend-item')
                .attr('transform', (d, i) => `translate(0, ${i * 20})`);

            legendItem.append('circle')
                .attr('r', 6)
                .attr('fill', d => d.color);

            legendItem.append('text')
                .attr('x', 15)
                .attr('y', 5)
                .attr('font-size', 12)
                .text(d => d.label);

            // 创建渐变定义
            const defs = this.svg.append('defs');
            const gradient = defs.append('linearGradient')
                .attr('id', 'journey-gradient')
                .attr('gradientUnits', 'userSpaceOnUse')
                .attr('x1', 0)
                .attr('y1', 0)
                .attr('x2', 0)
                .attr('y2', this.options.height);

            gradient.append('stop')
                .attr('offset', '0%')
                .attr('stop-color', '#6d28d9');

            gradient.append('stop')
                .attr('offset', '100%')
                .attr('stop-color', '#8b5cf6');
        } catch (error) {
            console.error('[QUANTUM-TIMELINE] 创建图例错误:', error);
        }
    }

    /**
     * 显示事件工具提示
     * @param {Event} event 事件对象
     * @param {Object} d 事件数据
     */
    showEventTooltip(event, d) {
        try {
            this.tooltip.transition()
                .duration(200)
                .style('opacity', .9);

            const typeName = {
                browse: '浏览',
                rate: '评分',
                comment: '评论',
                like: '点赞',
                favorite: '收藏'
            }[d.type] || d.type;

            let dateStr;
            try {
                dateStr = new Date(d.date).toLocaleString();
            } catch (e) {
                dateStr = d.date || '未知日期';
            }

            this.tooltip.html(`
                <div class="font-bold">${typeName}</div>
                <div>${d.title || '未知内容'}</div>
                <div class="text-xs mt-1">${dateStr}</div>
            `)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
        } catch (error) {
            console.error('[QUANTUM-TIMELINE] 显示工具提示错误:', error);
        }
    }

    /**
     * 隐藏工具提示
     */
    hideTooltip() {
        try {
            this.tooltip.transition()
                .duration(500)
                .style('opacity', 0);
        } catch (error) {
            console.error('[QUANTUM-TIMELINE] 隐藏工具提示错误:', error);
        }
    }

    /**
     * 处理事件点击
     * @param {Event} event 事件对象
     * @param {Object} d 事件数据
     */
    handleEventClick(event, d) {
        try {
            // 如果设置了点击回调，则调用
            if (this.options.onEventClick && typeof this.options.onEventClick === 'function') {
                this.options.onEventClick(d);
            }
        } catch (error) {
            console.error('[QUANTUM-TIMELINE] 处理事件点击错误:', error);
        }
    }

    /**
     * 获取事件颜色
     * @param {string} type 事件类型
     * @returns {string} 颜色值
     */
    getEventColor(type) {
        try {
            const colors = {
                browse: '#3b82f6',
                rate: '#10b981',
                comment: '#f97316',
                like: '#ef4444',
                favorite: '#8b5cf6'
            };

            return colors[type] || '#6d28d9';
        } catch (error) {
            console.error('[QUANTUM-TIMELINE] 获取事件颜色错误:', error);
            return '#6d28d9';
        }
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
            console.error('[QUANTUM-TIMELINE] 调整大小错误:', error);
        }
    }

    /**
     * 显示空状态
     */
    showEmptyState() {
        try {
            const width = this.options.width - this.options.margin.left - this.options.margin.right;
            const height = this.options.height - this.options.margin.top - this.options.margin.bottom;

            this.container.append('text')
                .attr('x', width / 2)
                .attr('y', height / 2)
                .attr('text-anchor', 'middle')
                .attr('font-size', 16)
                .text('暂无旅程数据');
        } catch (error) {
            console.error('[QUANTUM-TIMELINE] 显示空状态错误:', error);
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

            this.container.append('text')
                .attr('x', width / 2)
                .attr('y', height / 2)
                .attr('text-anchor', 'middle')
                .attr('font-size', 16)
                .attr('fill', 'red')
                .text('时间线渲染错误');

            if (message) {
                this.container.append('text')
                    .attr('x', width / 2)
                    .attr('y', height / 2 + 24)
                    .attr('text-anchor', 'middle')
                    .attr('font-size', 12)
                    .attr('fill', '#666')
                    .text(message);
            }
        } catch (error) {
            console.error('[QUANTUM-TIMELINE] 显示错误状态错误:', error);
        }
    }
}