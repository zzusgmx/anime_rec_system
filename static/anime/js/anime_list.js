// static/anime/js/anime_list.js
/**
 * 量子级动漫搜索引擎前端控制器 v2.5
 * 实现多维度搜索、异步数据加载和UI渲染优化
 *
 * 架构设计：事件驱动、防抖动、虚拟DOM预渲染
 */

// 全局命名空间定义 - 避免污染全局作用域
const AnimeSearch = (() => {
    // 私有变量定义 - 闭包封装
    let searchTimeout = null;
    let lastQuery = '';
    let isSearching = false;
    let searchCache = new Map(); // 内存缓存 - 减少重复请求

    // DOM元素引用 - 性能优化
    let elements = {};

    // 配置常量
    const CONFIG = {
        DEBOUNCE_DELAY: 300, // 防抖延迟（毫秒）
        MIN_QUERY_LENGTH: 2, // 最小查询长度触发搜索
        MAX_RESULTS: 10,     // 最大搜索结果数
        CACHE_EXPIRY: 60000, // 缓存过期时间（毫秒）
    };

    // 初始化函数 - 入口点
    function init() {
        console.log('[AnimeSearch] 量子搜索引擎初始化中...');

        // 获取DOM元素引用
        cacheElements();

        // 绑定事件监听器
        bindEvents();

        // 初始化UI状态
        initUIState();

        console.log('[AnimeSearch] 引擎初始化完成 ✓');
    }

    // 缓存DOM元素引用 - 提高后续操作性能
    function cacheElements() {
        elements = {
            searchForm: document.getElementById('searchForm'),
            searchInput: document.querySelector('input[name="query"]'),
            searchResults: document.getElementById('searchResults'),
            filterSelects: document.querySelectorAll('#searchForm select'),
            filterCheckboxes: document.querySelectorAll('#searchForm input[type="checkbox"]'),
            animeCards: document.querySelectorAll('.anime-card'),
            resetButton: document.querySelector('a[href$="anime_list"]')
        };
    }

    // 事件绑定中心
    function bindEvents() {
        // 搜索输入事件 - 实时搜索提示
        if (elements.searchInput) {
            elements.searchInput.addEventListener('input', handleSearchInput);
            elements.searchInput.addEventListener('focus', handleSearchFocus);
        }

        // 点击外部区域隐藏搜索结果
        document.addEventListener('click', (e) => {
            if (elements.searchResults &&
                !elements.searchInput.contains(e.target) &&
                !elements.searchResults.contains(e.target)) {
                elements.searchResults.style.display = 'none';
            }
        });

        // 过滤条件变更自动提交
        elements.filterSelects.forEach(select => {
            select.addEventListener('change', () => elements.searchForm.submit());
        });

        elements.filterCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => elements.searchForm.submit());
        });
    }

    // 初始化UI状态
    function initUIState() {
        // 卡片高度调整
        adjustCardHeights();

        // 响应式调整
        window.addEventListener('resize', debounce(adjustCardHeights, 200));

        // 添加表单提交前的处理
        if (elements.searchForm) {
            elements.searchForm.addEventListener('submit', handleFormSubmit);
        }
    }

    // 搜索输入处理器 - 实现防抖动
    function handleSearchInput(e) {
        const query = e.target.value.trim();

        // 清除之前的定时器
        clearTimeout(searchTimeout);

        // 隐藏结果区域（如果查询为空）
        if (query.length < CONFIG.MIN_QUERY_LENGTH) {
            if (elements.searchResults) {
                elements.searchResults.style.display = 'none';
            }
            return;
        }

        // 设置新的定时器 - 实现搜索防抖
        searchTimeout = setTimeout(() => {
            performAsyncSearch(query);
        }, CONFIG.DEBOUNCE_DELAY);
    }

    // 搜索框获得焦点时处理
    function handleSearchFocus(e) {
        const query = e.target.value.trim();
        if (query.length >= CONFIG.MIN_QUERY_LENGTH) {
            // 检查缓存中是否有结果
            if (searchCache.has(query)) {
                const cachedData = searchCache.get(query);
                renderSearchResults(cachedData);
            } else {
                performAsyncSearch(query);
            }
        }
    }

    // 异步搜索执行器 - 支持请求取消和缓存
    function performAsyncSearch(query) {
        // 防止重复搜索相同内容
        if (query === lastQuery && elements.searchResults.style.display !== 'none') {
            return;
        }

        lastQuery = query;

        // 检查缓存
        if (searchCache.has(query)) {
            const cachedData = searchCache.get(query);
            const now = Date.now();

            // 检查缓存是否过期
            if (now - cachedData.timestamp < CONFIG.CACHE_EXPIRY) {
                renderSearchResults(cachedData.data);
                return;
            } else {
                // 移除过期缓存
                searchCache.delete(query);
            }
        }

        // 防止并发请求
        if (isSearching) {
            return;
        }

        isSearching = true;

        // 显示加载指示器
        showLoadingIndicator();

        // 使用Fetch API执行AJAX请求
        fetch(`/anime/search/?query=${encodeURIComponent(query)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('搜索请求失败');
                }
                return response.json();
            })
            .then(data => {
                // 缓存结果
                searchCache.set(query, {
                    data: data,
                    timestamp: Date.now()
                });

                // 渲染结果
                renderSearchResults(data);
            })
            .catch(error => {
                console.error('[AnimeSearch] 搜索错误:', error);
                showSearchError();
            })
            .finally(() => {
                // 隐藏加载指示器
                hideLoadingIndicator();
                isSearching = false;
            });
    }

    // 渲染搜索结果
    function renderSearchResults(data) {
        if (!elements.searchResults) return;

        // 清空现有结果
        elements.searchResults.innerHTML = '';

        if (data.results && data.results.length > 0) {
            // 创建结果项文档片段 - 减少DOM重排
            const fragment = document.createDocumentFragment();

            data.results.forEach(item => {
                const resultItem = createResultItemElement(item);
                fragment.appendChild(resultItem);
            });

            elements.searchResults.appendChild(fragment);
            elements.searchResults.style.display = 'block';
        } else {
            elements.searchResults.innerHTML = '<div class="search-no-results">没有找到匹配的结果</div>';
            elements.searchResults.style.display = 'block';
        }
    }

    // 创建单个结果项元素
    function createResultItemElement(item) {
        const resultItem = document.createElement('a');
        resultItem.className = 'search-result-item';
        resultItem.href = item.url;

        let itemHtml = '';

        // 添加封面图片
        if (item.cover) {
            itemHtml += `<img src="${item.cover}" alt="${item.title}" loading="lazy">`;
        } else {
            itemHtml += '<div class="search-result-no-image"><i class="fas fa-film"></i></div>';
        }

        // 添加信息区域
        itemHtml += '<div class="search-result-info">';
        itemHtml += `<div class="search-result-title">${escapeHtml(item.title)}</div>`;

        if (item.type) {
            itemHtml += `<div class="search-result-type">${escapeHtml(item.type)}</div>`;
        }

        if (item.rating) {
            itemHtml += `<div class="search-result-rating"><i class="fas fa-star text-warning"></i> ${item.rating}</div>`;
        }

        itemHtml += '</div>';

        resultItem.innerHTML = itemHtml;

        // 添加点击效果
        resultItem.addEventListener('click', () => {
            // 可选：记录搜索点击事件以改进推荐
            console.log(`[AnimeSearch] 用户选择了: ${item.title}`);
        });

        return resultItem;
    }

    // 显示加载指示器
    function showLoadingIndicator() {
        if (elements.searchInput) {
            // 检查是否已经存在加载指示器
            if (!document.querySelector('.search-loading')) {
                const loader = document.createElement('div');
                loader.className = 'search-loading';
                loader.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                elements.searchInput.parentNode.appendChild(loader);
            }
        }
    }

    // 隐藏加载指示器
    function hideLoadingIndicator() {
        const loader = document.querySelector('.search-loading');
        if (loader) {
            loader.remove();
        }
    }

    // 显示搜索错误
    function showSearchError() {
        if (elements.searchResults) {
            elements.searchResults.innerHTML = '<div class="search-no-results">搜索遇到错误，请稍后再试</div>';
            elements.searchResults.style.display = 'block';
        }
    }

    // 表单提交处理
    function handleFormSubmit(e) {
        // 移除空值字段，保持URL干净
        const selects = this.querySelectorAll('select');
        let hasActiveFilters = false;

        selects.forEach(select => {
            if (select.value === '') {
                select.disabled = true;
            } else {
                hasActiveFilters = true;
            }
        });

        // 记录分析数据
        if (hasActiveFilters) {
            console.log('[AnimeSearch] 用户应用了筛选条件');
        }
    }

    // 调整卡片高度保持一致
    function adjustCardHeights() {
        if (!elements.animeCards || elements.animeCards.length === 0) {
            return;
        }

        // 重置高度
        elements.animeCards.forEach(card => {
            card.style.height = 'auto';
        });

        // 获取行分组
        const rows = getCardRows(elements.animeCards);

        // 对每行卡片应用相同高度
        rows.forEach(row => {
            const maxHeight = Math.max(...row.map(card => card.offsetHeight));
            row.forEach(card => {
                card.style.height = `${maxHeight}px`;
            });
        });
    }

    // 根据位置将卡片分组为行
    function getCardRows(cards) {
        const rows = [];
        let currentRow = [];
        let lastTop = -1;

        Array.from(cards).forEach(card => {
            const rect = card.getBoundingClientRect();

            // 如果这是新的一行（与上一个卡片的top值不同）
            if (lastTop !== -1 && Math.abs(rect.top - lastTop) > 10) {
                if (currentRow.length > 0) {
                    rows.push([...currentRow]);
                    currentRow = [];
                }
            }

            currentRow.push(card);
            lastTop = rect.top;
        });

        // 添加最后一行
        if (currentRow.length > 0) {
            rows.push(currentRow);
        }

        return rows;
    }

    // 防抖动函数 - 性能优化
    function debounce(func, delay) {
        let timer;
        return function(...args) {
            clearTimeout(timer);
            timer = setTimeout(() => {
                func.apply(this, args);
            }, delay);
        };
    }

    // 转义HTML - 防止XSS攻击
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 返回公共API
    return {
        init,                  // 初始化引擎
        refresh: init,         // 刷新引擎状态
        forceAdjustHeights: adjustCardHeights, // 强制重新调整高度
    };
})();

// 当DOM内容加载完成后初始化搜索引擎
document.addEventListener('DOMContentLoaded', function() {
    // 初始化量子搜索引擎
    AnimeSearch.init();

    // 在图片加载完成后重新调整卡片高度
    window.addEventListener('load', function() {
        AnimeSearch.forceAdjustHeights();
    });

    // 支持旧代码兼容性 - 保留原始函数
    window.adjustCardHeights = function() {
        AnimeSearch.forceAdjustHeights();
    };
});