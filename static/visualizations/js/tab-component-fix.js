/**
 * 修复Bootstrap Tab组件初始化问题
 * 文件路径: static/visualizations/js/tab-component-fix.js
 */
document.addEventListener('DOMContentLoaded', function() {
    // 检查并修复可能的Tab问题
    function fixTabs() {
        // 获取所有标签页触发器
        const tabTriggers = document.querySelectorAll('[data-bs-toggle="pill"], [data-bs-toggle="tab"]');

        // 检查每个标签页触发器
        tabTriggers.forEach(trigger => {
            // 获取目标内容面板的选择器
            const targetSelector = trigger.getAttribute('href') || trigger.getAttribute('data-bs-target');

            if (!targetSelector) {
                console.warn('Tab触发器缺少目标选择器:', trigger);
                return;
            }

            // 检查目标内容面板是否存在
            const targetPanel = document.querySelector(targetSelector);
            if (!targetPanel) {
                console.warn(`Tab目标面板不存在: ${targetSelector}`);

                // 自动创建不存在的面板
                if (targetSelector.startsWith('#')) {
                    const id = targetSelector.substring(1);
                    const tabContent = trigger.closest('.nav').nextElementSibling;

                    if (tabContent && tabContent.classList.contains('tab-content')) {
                        const newPanel = document.createElement('div');
                        newPanel.className = 'tab-pane fade';
                        newPanel.id = id;
                        newPanel.innerHTML = '<div class="alert alert-warning">Tab内容尚未加载</div>';
                        tabContent.appendChild(newPanel);
                        console.log(`为 ${id} 创建了临时标签页面板`);
                    }
                }
            }

            // 防止标签页点击事件引起页面跳转
            trigger.addEventListener('click', function(e) {
                e.preventDefault();

                // 手动激活选项卡，避免Bootstrap自动处理可能引起的错误
                try {
                    // 如果Bootstrap可用，使用Bootstrap API激活标签页
                    if (typeof bootstrap !== 'undefined' && bootstrap.Tab) {
                        const tab = new bootstrap.Tab(this);
                        tab.show();
                    }
                    // 否则手动实现基本的标签页切换功能
                    else {
                        // 获取目标内容面板
                        const targetSelector = this.getAttribute('href') || this.getAttribute('data-bs-target');
                        if (!targetSelector) return;

                        const targetPanel = document.querySelector(targetSelector);
                        if (!targetPanel) return;

                        // 取消激活所有标签页触发器
                        document.querySelectorAll('[data-bs-toggle="pill"], [data-bs-toggle="tab"]').forEach(t => {
                            t.classList.remove('active');
                        });

                        // 隐藏所有内容面板
                        document.querySelectorAll('.tab-pane').forEach(p => {
                            p.classList.remove('show', 'active');
                        });

                        // 激活当前标签页
                        this.classList.add('active');
                        targetPanel.classList.add('show', 'active');
                    }
                } catch (error) {
                    console.error('激活标签页失败:', error);
                }
            });
        });
    }

    // 执行修复
    try {
        fixTabs();
    } catch (e) {
        console.error('修复标签页时出错:', e);
    }

    // 尝试修复图片404错误
    function fixMissingImages() {
        // 获取所有图片元素
        const images = document.querySelectorAll('img');

        // 为每个图片添加错误处理
        images.forEach(img => {
            img.addEventListener('error', function() {
                // 设置默认的替代图片
                this.src = '/static/default-placeholder.png';

                // 如果默认图片也不存在，则替换为内联SVG
                this.onerror = function() {
                    const width = this.width || 100;
                    const height = this.height || 100;

                    // 创建替代的内联SVG
                    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    svg.setAttribute('width', width);
                    svg.setAttribute('height', height);
                    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
                    svg.style.backgroundColor = '#f0f0f0';

                    // 添加图片图标
                    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    path.setAttribute('d', 'M10 1H4c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V5l-4-4zm1 3v-.9L14.1 7H11V4zm-1 7H4V3h6v4h4v4z');
                    path.setAttribute('fill', '#999');
                    path.setAttribute('transform', `translate(${width/2-10}, ${height/2-10}) scale(2)`);

                    svg.appendChild(path);

                    // 替换图片元素
                    this.parentNode.replaceChild(svg, this);
                };
            });
        });
    }

    // 执行修复图片
    try {
        fixMissingImages();
    } catch (e) {
        console.error('修复图片时出错:', e);
    }

    // 延迟执行再次检查，以防有动态加载的内容
    setTimeout(fixTabs, 500);
});