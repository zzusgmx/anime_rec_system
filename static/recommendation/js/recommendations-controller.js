// 量子态推荐控制器 - 完全重构版
// 增强事件处理、错误恢复和初始化逻辑

document.addEventListener('DOMContentLoaded', function() {
  // 检查DOM环境
  console.log("DOM加载完成，初始化量子态推荐控制器");
  
  // 先删除可能已存在的重复监听器
  const clearExistingHandlers = () => {
    document.querySelectorAll('.strategy-selector').forEach(selector => {
      const clone = selector.cloneNode(true);
      selector.parentNode.replaceChild(clone, selector);
    });
  };
  
  // 清除旧的事件处理器
  clearExistingHandlers();
  
  // 重新注册策略选择器事件
  document.querySelectorAll('.strategy-selector').forEach(selector => {
    selector.addEventListener('click', function(event) {
      event.preventDefault();
      event.stopPropagation(); // 防止事件冒泡
      
      const strategy = this.dataset.strategy;
      console.log(`选择策略: ${strategy || 'hybrid'}`);
      
      if (typeof window.recommendationUI !== 'undefined') {
        window.recommendationUI.loadRecommendations(strategy || 'hybrid');
      } else {
        console.error('推荐UI组件未初始化');
        
        // 尝试创建UI组件
        try {
          window.recommendationUI = new RecommendationUI('recommendationContainer');
          window.recommendationUI.loadRecommendations(strategy || 'hybrid');
        } catch (e) {
          console.error('创建UI组件失败:', e);
          alert('推荐组件未正确加载，请刷新页面');
        }
      }
    });
  });

  // 获取URL中的策略
  function getStrategyFromUrl() {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      let strategy = urlParams.get('strategy');
      
      // 验证策略有效性
      if (!strategy || strategy === 'undefined' || 
          !['hybrid', 'cf', 'content', 'ml', 'popular'].includes(strategy)) {
        strategy = 'hybrid';
      }
      
      return strategy;
    } catch (e) {
      console.warn('解析URL参数失败:', e);
      return 'hybrid';
    }
  }

  // 初始化推荐系统
  function initRecommendationSystem() {
    if (typeof window.recommendationUI !== 'undefined') {
      const initialStrategy = getStrategyFromUrl();
      console.log('初始化推荐系统，策略:', initialStrategy);
      window.recommendationUI.loadRecommendations(initialStrategy);
    } else {
      console.warn('UI组件未加载，尝试创建...');
      
      // 尝试创建UI组件
      try {
        if (typeof RecommendationUI === 'function') {
          window.recommendationUI = new RecommendationUI('recommendationContainer');
          const initialStrategy = getStrategyFromUrl();
          console.log('手动创建UI组件，使用策略:', initialStrategy);
          window.recommendationUI.loadRecommendations(initialStrategy);
        } else {
          throw new Error('RecommendationUI类未定义');
        }
      } catch (e) {
        console.error('创建UI组件失败:', e);
        
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
      initRecommendationSystem();
    });
  }

  // 添加直接API测试功能（开发人员工具）
  const testApiBtn = document.getElementById('testApiBtn');
  if (testApiBtn) {
    testApiBtn.addEventListener('click', function() {
      const strategy = getStrategyFromUrl();
      const apiUrl = `/recommendations/api/recommendations/?strategy=${strategy}`;
      
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