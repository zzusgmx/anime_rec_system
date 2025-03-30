// 量子态推荐控制器 - 分页增强版
// 重构事件处理、参数解析和路由控制

document.addEventListener('DOMContentLoaded', function() {
  // 检查DOM环境
  console.log("[QUANTUM-CONTROLLER] DOM加载完成，初始化量子态推荐控制器 v2.0");

  // 先删除可能已存在的重复监听器
  const clearExistingHandlers = () => {
    document.querySelectorAll('.strategy-selector').forEach(selector => {
      const clone = selector.cloneNode(true);
      selector.parentNode.replaceChild(clone, selector);
    });
  };

  // 清除旧的事件处理器
  clearExistingHandlers();

  // 重新注册策略选择器事件 - 修改为保持页码状态
  document.querySelectorAll('.strategy-selector').forEach(selector => {
    selector.addEventListener('click', function(event) {
      event.preventDefault();
      event.stopPropagation(); // 防止事件冒泡

      const strategy = this.dataset.strategy;
      console.log(`[QUANTUM-STRATEGY] 切换推荐策略: ${strategy || 'hybrid'}`);

      // 策略改变时重置为第一页
      if (typeof window.recommendationUI !== 'undefined') {
        window.recommendationUI.loadRecommendations(strategy || 'hybrid', 1);
      } else {
        console.error('[QUANTUM-ERROR] 推荐UI组件未初始化');

        // 尝试创建UI组件
        try {
          window.recommendationUI = new RecommendationUI('recommendationContainer');
          window.recommendationUI.loadRecommendations(strategy || 'hybrid', 1);
        } catch (e) {
          console.error('[QUANTUM-ERROR] 创建UI组件失败:', e);
          alert('推荐组件未正确加载，请刷新页面');
        }
      }
    });
  });

  // 解析URL参数
  function parseUrlParams() {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      let strategy = urlParams.get('strategy');
      let page = parseInt(urlParams.get('page'));

      // 验证策略有效性
      if (!strategy || strategy === 'undefined' ||
          !['hybrid', 'cf', 'content', 'ml', 'popular'].includes(strategy)) {
        strategy = 'hybrid';
      }

      // 验证页码有效性
      if (!page || isNaN(page) || page < 1) {
        page = 1;
      }

      return { strategy, page };
    } catch (e) {
      console.warn('[QUANTUM-WARNING] 解析URL参数失败:', e);
      return { strategy: 'hybrid', page: 1 };
    }
  }

  // 初始化推荐系统
  function initRecommendationSystem() {
    const { strategy, page } = parseUrlParams();

    if (typeof window.recommendationUI !== 'undefined') {
      console.log(`[QUANTUM-INIT] 初始化推荐系统: 策略=${strategy}, 页码=${page}`);
      window.recommendationUI.loadRecommendations(strategy, page);
    } else {
      console.warn('[QUANTUM-WARNING] UI组件未加载，尝试创建...');

      // 尝试创建UI组件
      try {
        if (typeof RecommendationUI === 'function') {
          window.recommendationUI = new RecommendationUI('recommendationContainer');
          console.log(`[QUANTUM-INIT] 手动创建UI组件: 策略=${strategy}, 页码=${page}`);
          window.recommendationUI.loadRecommendations(strategy, page);
        } else {
          throw new Error('RecommendationUI类未定义');
        }
      } catch (e) {
        console.error('[QUANTUM-ERROR] 创建UI组件失败:', e);

        // 显示错误信息
        const container = document.getElementById('recommendationContainer');
        if (container) {
          container.innerHTML = `
            <div class="col-12 text-center my-5">
              <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                推荐组件加载失败: ${e.message}
              </div>
              <button class="btn btn-primary mt-3" onclick="location.reload()">
                <i class="fas fa-sync-alt me-1"></i> 刷新页面
              </button>
            </div>
          `;
        }
      }
    }
  }

  // 添加重置按钮功能
  const resetBtn = document.getElementById('resetRecommendations');
  if (resetBtn) {
    resetBtn.addEventListener('click', function() {
      if (window.recommendationEngine) {
        window.recommendationEngine.clearCache();
      }
      const { strategy } = parseUrlParams();
      // 重置时返回第一页
      if (window.recommendationUI) {
        window.recommendationUI.loadRecommendations(strategy, 1);
      } else {
        initRecommendationSystem();
      }
    });
  }

  // 添加浏览器历史导航支持
  window.addEventListener('popstate', function(event) {
    const { strategy, page } = parseUrlParams();
    if (window.recommendationUI) {
      console.log(`[QUANTUM-HISTORY] 历史导航: 策略=${strategy}, 页码=${page}`);
      window.recommendationUI.loadRecommendations(strategy, page);
    }
  });

  // 添加键盘导航支持
  document.addEventListener('keydown', function(event) {
    // 避免在输入框中触发
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
      return;
    }

    if (window.recommendationUI) {
      const { page } = parseUrlParams();
      const paginationState = window.recommendationEngine.getPaginationState();

      // 左箭头 - 上一页
      if (event.key === 'ArrowLeft' && page > 1) {
        window.recommendationUI.loadRecommendations(paginationState.strategy, page - 1);
      }

      // 右箭头 - 下一页
      if (event.key === 'ArrowRight' && page < paginationState.totalPages) {
        window.recommendationUI.loadRecommendations(paginationState.strategy, page + 1);
      }
    }
  });

  // 添加自动刷新功能
  let autoRefreshInterval;
  const toggleAutoRefresh = document.getElementById('toggleAutoRefresh');
  if (toggleAutoRefresh) {
    toggleAutoRefresh.addEventListener('click', function() {
      if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        this.innerHTML = '<i class="fas fa-sync-alt me-1"></i> 启用自动刷新';
        this.classList.remove('btn-danger');
        this.classList.add('btn-success');
      } else {
        this.innerHTML = '<i class="fas fa-stop-circle me-1"></i> 停止自动刷新';
        this.classList.remove('btn-success');
        this.classList.add('btn-danger');

        // 每30秒刷新一次，模拟"探索"功能
        autoRefreshInterval = setInterval(() => {
          if (window.recommendationEngine) {
            window.recommendationEngine.clearCache();
          }
          if (window.recommendationUI) {
            const { strategy, page } = parseUrlParams();
            window.recommendationUI.loadRecommendations(strategy, page);
          }
        }, 30000);
      }
    });
  }

  // 添加直接API测试功能（开发人员工具）
  const testApiBtn = document.getElementById('testApiBtn');
  if (testApiBtn) {
    testApiBtn.addEventListener('click', function() {
      const { strategy, page } = parseUrlParams();
      const apiUrl = `/recommendations/api/recommendations/?strategy=${strategy}&page=${page}`;
      
      const resultContainer = document.getElementById('apiResult');
      if (resultContainer) {
        resultContainer.innerHTML = '<div class="spinner-border text-primary" role="status"></div> 请求中...';
        
        fetch(apiUrl)
          .then(response => {
            if (!response.ok) {
              throw new Error(`API错误: ${response.status} ${response.statusText}`);
            }
            return response.json();
          })
          .then(data => {
            resultContainer.innerHTML = `<pre class="bg-light p-3 rounded">${JSON.stringify(data, null, 2)}</pre>`;
          })
          .catch(error => {
            resultContainer.innerHTML = `
              <div class="alert alert-danger">
                ${error.message}
              </div>
            `;
          });
      }
    });
  }

  // 延迟启动初始化，确保其他脚本已加载
  setTimeout(initRecommendationSystem, 100);
});