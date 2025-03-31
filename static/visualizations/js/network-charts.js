/**
 * 关系网络可视化
 * 使用D3.js Force-Directed图来可视化用户交互网络
 */
class NetworkVisualization {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('[QUANTUM-NETWORK] 容器不存在:', containerId);
            return;
        }

        // 默认选项
        this.options = {
            width: this.container.clientWidth || 800,
            height: 600,
            nodeRadius: 10,
            linkDistance: 150,
            charge: -300,
            ...options
        };

        // 数据
        this.data = {
            nodes: [],
            links: []
        };

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
                .attr('class', 'network-svg');

            // 创建箭头定义
            this.svg.append('defs').append('marker')
                .attr('id', 'arrowhead')
                .attr('viewBox', '-0 -5 10 10')
                .attr('refX', 20)
                .attr('refY', 0)
                .attr('orient', 'auto')
                .attr('markerWidth', 6)
                .attr('markerHeight', 6)
                .attr('xoverflow', 'visible')
                .append('svg:path')
                .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
                .attr('fill', '#999')
                .style('stroke', 'none');

            // 创建容器组
            this.container = this.svg.append('g')
                .attr('class', 'network-container');

            // 创建图例
            this.createLegend();

            // 创建工具提示
            this.tooltip = d3.select('body').append('div')
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

            // 响应窗口大小变化
            window.addEventListener('resize', this.resize.bind(this));
        } catch (error) {
            console.error('[QUANTUM-NETWORK] 初始化错误:', error);
        }
    }

    /**
     * 加载数据
     * @param {Object} data 网络数据 {nodes, links}
     */
    loadData(data) {
        try {
            // 验证数据
            if (!data || !Array.isArray(data.nodes) || !Array.isArray(data.links)) {
                console.warn('[QUANTUM-NETWORK] 无效的网络数据');
                this.data = { nodes: [], links: [] };
            } else {
                // 复制数据以避免修改原始数据
                this.data = {
                    nodes: [...data.nodes],
                    links: [...data.links]
                };
            }

            this.render();
        } catch (error) {
            console.error('[QUANTUM-NETWORK] 加载数据错误:', error);
            this.data = { nodes: [], links: [] };
            this.showErrorState('加载数据错误');
        }
    }

    /**
     * 渲染网络图
     */
    render() {
        try {
            // 清空容器
            this.container.selectAll('*').remove();

            // 如果没有数据，显示提示
            if (!this.data.nodes || this.data.nodes.length === 0) {
                this.showEmptyState();
                return;
            }

            // 数据验证
            const validNodes = this.data.nodes.filter(d => d && (d.id !== undefined || d.id !== null));
            const validLinks = this.data.links.filter(d =>
                d &&
                d.source !== undefined && d.source !== null &&
                d.target !== undefined && d.target !== null
            );

            if (validNodes.length === 0) {
                this.showEmptyState();
                return;
            }

            // 确保每个节点都有初始位置
            validNodes.forEach(node => {
                node.x = node.x || this.options.width / 2;
                node.y = node.y || this.options.height / 2;
            });

            // 创建力导向模拟
            this.simulation = d3.forceSimulation(validNodes)
                .force('link', d3.forceLink(validLinks)
                    .id(d => d.id)
                    .distance(this.options.linkDistance))
                .force('charge', d3.forceManyBody().strength(this.options.charge))
                .force('center', d3.forceCenter(this.options.width / 2, this.options.height / 2))
                .force('collision', d3.forceCollide().radius(d => (d.size || 15)))
                .on('tick', this.ticked.bind(this));

            // 创建连接
            this.link = this.container.append('g')
                .attr('class', 'links')
                .selectAll('line')
                .data(validLinks)
                .enter().append('line')
                .attr('stroke-width', d => Math.max(1, d.width || 1))
                .attr('stroke', this.getLinkColor.bind(this))
                .attr('marker-end', d => d.type === 'reply' ? 'url(#arrowhead)' : '');

            // 创建节点
            this.node = this.container.append('g')
                .attr('class', 'nodes')
                .selectAll('circle')
                .data(validNodes)
                .enter().append('circle')
                .attr('r', d => Math.max(this.options.nodeRadius, d.size || this.options.nodeRadius))
                .attr('fill', this.getNodeColor.bind(this))
                .attr('stroke', '#fff')
                .attr('stroke-width', 1.5)
                .call(this.drag())
                .on('mouseover', this.showNodeTooltip.bind(this))
                .on('mouseout', this.hideTooltip.bind(this));

            // 创建节点标签
            this.label = this.container.append('g')
                .attr('class', 'labels')
                .selectAll('text')
                .data(validNodes)
                .enter().append('text')
                .text(d => d.username || `Node ${d.id}`)
                .attr('font-size', 10)
                .attr('dx', 12)
                .attr('dy', 4)
                .style('pointer-events', 'none');
        } catch (error) {
            console.error('[QUANTUM-NETWORK] 渲染错误:', error);
            this.showErrorState('渲染网络图错误');
        }
    }

    /**
     * 创建图例
     */
    createLegend() {
        try {
            const legend = this.svg.append('g')
                .attr('class', 'legend')
                .attr('transform', 'translate(20, 20)');

            const types = [
                { type: 'user', label: '用户', color: '#6d28d9' },
                { type: 'like', label: '点赞', color: '#ef4444' },
                { type: 'reply', label: '回复', color: '#3b82f6' },
                { type: 'mention', label: '提及', color: '#10b981' }
            ];

            const legendItem = legend.selectAll('.legend-item')
                .data(types)
                .enter().append('g')
                .attr('class', 'legend-item')
                .attr('transform', (d, i) => `translate(0, ${i * 20})`);

            legendItem.append('circle')
                .attr('r', 6)
                .attr('fill', d => d.type === 'user' ? d.color : 'none')
                .attr('stroke', d => d.type === 'user' ? 'none' : d.color)
                .attr('stroke-width', d => d.type === 'user' ? 0 : 2);

            legendItem.append('text')
                .attr('x', 15)
                .attr('y', 5)
                .attr('font-size', 12)
                .text(d => d.label);
        } catch (error) {
            console.error('[QUANTUM-NETWORK] 创建图例错误:', error);
        }
    }

    /**
     * 模拟每帧更新
     */
    ticked() {
        try {
            if (!this.link || !this.node || !this.label) return;

            this.link
                .attr('x1', d => d.source.x !== undefined ? d.source.x : 0)
                .attr('y1', d => d.source.y !== undefined ? d.source.y : 0)
                .attr('x2', d => d.target.x !== undefined ? d.target.x : 0)
                .attr('y2', d => d.target.y !== undefined ? d.target.y : 0);

            this.node
                .attr('cx', d => {
                    // 确保节点在可视区域内
                    const radius = Math.max(this.options.nodeRadius, d.size || this.options.nodeRadius);
                    return d.x = Math.max(radius, Math.min(this.options.width - radius, d.x || 0));
                })
                .attr('cy', d => {
                    // 确保节点在可视区域内
                    const radius = Math.max(this.options.nodeRadius, d.size || this.options.nodeRadius);
                    return d.y = Math.max(radius, Math.min(this.options.height - radius, d.y || 0));
                });

            this.label
                .attr('x', d => d.x !== undefined ? d.x : 0)
                .attr('y', d => d.y !== undefined ? d.y : 0);
        } catch (error) {
            console.error('[QUANTUM-NETWORK] 更新位置错误:', error);
        }
    }

    /**
     * 显示节点工具提示
     * @param {Event} event 事件对象
     * @param {Object} d 节点数据
     */
    showNodeTooltip(event, d) {
        try {
            this.tooltip.transition()
                .duration(200)
                .style('opacity', .9);

            const username = d.username || `节点 ${d.id}`;
            const influence = d.influence !== undefined ? d.influence : 0;
            const activity = d.activity !== undefined ? d.activity : 0;

            this.tooltip.html(`
                <div class="font-bold">${username}</div>
                <div class="flex justify-between mt-1">
                    <span>影响力:</span>
                    <span>${influence}</span>
                </div>
                <div class="flex justify-between">
                    <span>活跃度:</span>
                    <span>${activity}</span>
                </div>
            `)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
        } catch (error) {
            console.error('[QUANTUM-NETWORK] 显示工具提示错误:', error);
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
            console.error('[QUANTUM-NETWORK] 隐藏工具提示错误:', error);
        }
    }

    /**
     * 获取连接颜色
     * @param {Object} d 连接数据
     * @returns {string} 颜色值
     */
    getLinkColor(d) {
        try {
            const colors = {
                like: '#ef4444',
                reply: '#3b82f6',
                mention: '#10b981'
            };

            return colors[d.type] || '#999';
        } catch (error) {
            console.error('[QUANTUM-NETWORK] 获取连接颜色错误:', error);
            return '#999';
        }
    }

    /**
     * 获取节点颜色
     * @param {Object} d 节点数据
     * @returns {string} 颜色值
     */
    getNodeColor(d) {
        try {
            const influence = d.influence || 0;
            const activity = d.activity || 0;
            const total = influence + activity;

            if (total > 150) return '#6d28d9';  // 高影响力 + 活跃度
            if (influence > 80) return '#8b5cf6';  // 高影响力
            if (activity > 80) return '#4f46e5';  // 高活跃度

            return '#a78bfa';  // 普通用户
        } catch (error) {
            console.error('[QUANTUM-NETWORK] 获取节点颜色错误:', error);
            return '#a78bfa';
        }
    }

    /**
     * 创建拖拽行为
     * @returns {d3.drag} 拖拽行为
     */
    drag() {
        try {
            return d3.drag()
                .on('start', (event, d) => {
                    if (!event.active && this.simulation) this.simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                })
                .on('drag', (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on('end', (event, d) => {
                    if (!event.active && this.simulation) this.simulation.alphaTarget(0);
                    d.fx = null;
                    d.fy = null;
                });
        } catch (error) {
            console.error('[QUANTUM-NETWORK] 创建拖拽行为错误:', error);
            return d3.drag(); // 返回一个空的拖拽行为
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

            if (this.simulation) {
                this.simulation
                    .force('center', d3.forceCenter(width / 2, this.options.height / 2))
                    .restart();
            }
        } catch (error) {
            console.error('[QUANTUM-NETWORK] 调整大小错误:', error);
        }
    }

    /**
     * 显示空状态
     */
    showEmptyState() {
        try {
            const width = this.options.width;
            const height = this.options.height;

            this.container.append('text')
                .attr('x', width / 2)
                .attr('y', height / 2)
                .attr('text-anchor', 'middle')
                .attr('font-size', 16)
                .text('暂无网络数据');
        } catch (error) {
            console.error('[QUANTUM-NETWORK] 显示空状态错误:', error);
        }
    }

    /**
     * 显示错误状态
     * @param {string} message 错误消息
     */
    showErrorState(message) {
        try {
            const width = this.options.width;
            const height = this.options.height;

            this.container.append('text')
                .attr('x', width / 2)
                .attr('y', height / 2)
                .attr('text-anchor', 'middle')
                .attr('font-size', 16)
                .attr('fill', 'red')
                .text('网络图渲染错误');

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
            console.error('[QUANTUM-NETWORK] 显示错误状态错误:', error);
        }
    }
}