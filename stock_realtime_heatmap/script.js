class StockHeatmap {
    constructor() {
        this.data = null;
        this.autoRefreshInterval = null;
        this.isLoading = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadData();
        this.startAutoRefresh();
    }

    bindEvents() {
        document.getElementById('refreshBtn').addEventListener('click', () => {
            if (!this.isLoading) {
                this.loadData();
            }
        });

        document.getElementById('autoRefresh').addEventListener('change', (e) => {
            if (e.target.checked) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        });
    }

    async loadData() {
        if (this.isLoading) return;
        
        try {
            this.isLoading = true;
            this.showLoading();
            
            // 從後端 API 獲取資料
            const response = await fetch('/api/stock_data');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.data = data;
            this.renderHeatmap();
            this.updateTimestamp();
            
        } catch (error) {
            console.error('載入資料失敗:', error);
            this.showError(`載入資料失敗: ${error.message}`);
        } finally {
            this.isLoading = false;
        }
    }

    renderHeatmap() {
        const container = document.querySelector('.treemap-grid');
        container.innerHTML = '';

        // 檢查資料是否存在
        if (!this.data || Object.keys(this.data).length === 0) {
            this.showError('無股票資料');
            return;
        }

        // 按類別排序
        const sortedCategories = Object.keys(this.data).sort();

        sortedCategories.forEach(category => {
            const stocks = this.data[category];
            if (!stocks || stocks.length === 0) return;

            const categorySection = document.createElement('div');
            categorySection.className = 'category-section';

            const categoryHeader = document.createElement('div');
            categoryHeader.className = 'category-header';
            categoryHeader.textContent = category;
            categorySection.appendChild(categoryHeader);

            const stockGrid = document.createElement('div');
            stockGrid.className = 'stock-grid';

            // 計算網格佈局
            const stockCount = stocks.length;
            const cols = Math.ceil(Math.sqrt(stockCount));
            stockGrid.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

            stocks.forEach(stock => {
                const block = this.createStockBlock(stock);
                stockGrid.appendChild(block);
            });

            categorySection.appendChild(stockGrid);
            container.appendChild(categorySection);
        });
    }

    createStockBlock(stock) {
        const block = document.createElement('div');
        block.className = 'stock-block';

        // 處理數據，確保數值有效
        const change = typeof stock.realtime_change === 'number' ? stock.realtime_change : 0;
        const price = typeof stock.realtime_price === 'number' ? stock.realtime_price : 0;

        // 根據漲跌幅設定顏色 - 更精細的分級
        if (change > 5) {
            block.classList.add('strong-positive');
        } else if (change > 2) {
            block.classList.add('positive');
        } else if (change > 0.5) {
            block.classList.add('weak-positive');
        } else if (change > -0.5) {
            block.classList.add('neutral');
        } else if (change > -2) {
            block.classList.add('weak-negative');
        } else if (change > -5) {
            block.classList.add('negative');
        } else {
            block.classList.add('strong-negative');
        }

        // 如果沒有數據
        if (change === 0 && price === 0) {
            block.classList.add('no-data');
        }

        // 格式化顯示
        const changeText = change > 0 ? `+${change.toFixed(1)}%` : `${change.toFixed(1)}%`;

        block.innerHTML = `
            <div class="stock-code">${stock.stock_id}</div>
            <div class="stock-name">${stock.stock_name}</div>
            <div class="stock-change">${changeText}</div>
        `;

        // 添加懸停效果
        block.addEventListener('mouseenter', (e) => {
            this.showTooltip(e, stock);
        });

        block.addEventListener('mouseleave', () => {
            this.hideTooltip();
        });

        block.addEventListener('mousemove', (e) => {
            this.updateTooltipPosition(e);
        });

        return block;
    }

    showTooltip(event, stock) {
        const tooltip = document.getElementById('tooltip');
        const change = typeof stock.realtime_change === 'number' ? stock.realtime_change : 0;
        const price = typeof stock.realtime_price === 'number' ? stock.realtime_price : 0;
        const lastPrice = typeof stock.last_day_price === 'number' ? stock.last_day_price : 0;
        
        const changeText = change > 0 ? `+${change.toFixed(2)}%` : `${change.toFixed(2)}%`;
        const priceText = price > 0 ? `$${price.toFixed(2)}` : '--';
        const lastPriceText = lastPrice > 0 ? `$${lastPrice.toFixed(2)}` : '--';
        
        tooltip.innerHTML = `
            <div style="font-size: 1.1em; font-weight: bold; margin-bottom: 8px;">
                ${stock.stock_name} (${stock.stock_id})
            </div>
            <div>現價: ${priceText}</div>
            <div>昨收: ${lastPriceText}</div>
            <div>漲跌: ${changeText}</div>
            <div>市場: ${stock.stock_type || '--'}</div>
        `;

        tooltip.classList.add('show');
        this.updateTooltipPosition(event);
    }

    hideTooltip() {
        const tooltip = document.getElementById('tooltip');
        tooltip.classList.remove('show');
    }

    updateTooltipPosition(event) {
        const tooltip = document.getElementById('tooltip');
        const rect = tooltip.getBoundingClientRect();
        
        let x = event.clientX + 10;
        let y = event.clientY + 10;

        // 防止 tooltip 超出螢幕邊界
        if (x + rect.width > window.innerWidth) {
            x = event.clientX - rect.width - 10;
        }
        if (y + rect.height > window.innerHeight) {
            y = event.clientY - rect.height - 10;
        }

        tooltip.style.left = x + 'px';
        tooltip.style.top = y + 'px';
    }

    showLoading() {
        const container = document.querySelector('.treemap-grid');
        container.innerHTML = '<div class="loading">載入股票資料中...</div>';
    }

    showError(message) {
        const container = document.querySelector('.treemap-grid');
        container.innerHTML = `<div class="error">${message}</div>`;
    }

    updateTimestamp() {
        const now = new Date();
        const timestamp = now.toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        document.getElementById('lastUpdate').textContent = timestamp;
    }

    startAutoRefresh() {
        this.stopAutoRefresh();
        this.autoRefreshInterval = setInterval(() => {
            this.loadData();
        }, 5000); // 每5秒更新一次
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    }
}

// 當頁面載入完成時初始化
document.addEventListener('DOMContentLoaded', () => {
    new StockHeatmap();
});

// 頁面卸載時清理
window.addEventListener('beforeunload', () => {
    if (window.stockHeatmap) {
        window.stockHeatmap.stopAutoRefresh();
    }
});
