// static/anime/js/anime_list.js

document.addEventListener('DOMContentLoaded', function() {
    // 动态调整卡片高度以确保一致性
    function adjustCardHeights() {
        const cards = document.querySelectorAll('.anime-card');
        let maxHeight = 0;

        // 先重置高度
        cards.forEach(card => {
            card.style.height = 'auto';
            const height = card.offsetHeight;
            maxHeight = Math.max(maxHeight, height);
        });

        // 设置所有卡片为相同高度
        cards.forEach(card => {
            card.style.height = `${maxHeight}px`;
        });
    }

    // 初始调整和窗口大小改变时调整
    adjustCardHeights();
    window.addEventListener('resize', adjustCardHeights);

    // 过滤表单提交前的数据处理
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            // 移除空值字段，保持URL干净
            const selects = this.querySelectorAll('select');

            selects.forEach(select => {
                if (select.value === '') {
                    select.disabled = true;
                }
            });

            // 表单提交继续
            return true;
        });
    }

    // 筛选条件改变时自动提交表单
    const filterSelects = document.querySelectorAll('#filterForm select');
    filterSelects.forEach(select => {
        select.addEventListener('change', function() {
            document.getElementById('filterForm').submit();
        });
    });
});