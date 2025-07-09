/**
 * 台股熱力圖 JavaScript 模組
 * 負責資料載入、處理和視覺化
 */

class StockHeatmap {
    constructor() {
        this.stockCategories = null;
        this.todayData = null;
        this.heatmapData = null;
    }

    /**
     * 載入股票分類資料
     * @returns {Promise<Object|null>} 股票分類資料或 null
     */
    async loadStockCategories() {
        try {
            const response = await fetch('../stock_realtime_heatmap/stock_data.json');
            const data = await response.json();
            this.stockCategories = data['台股'];
            return this.stockCategories;
        } catch (error) {
            console.error('載入股票分類資料失敗:', error);
            return null;
        }
    }

    /**
     * 載入今日股票資料
     * @returns {Promise<Array|null>} 今日股票資料或 null
     */
    async loadTodayData() {
        try {
            const response = await fetch('../raw_stock_data/daily/today.json');
            const data = await response.json();
            this.todayData = data;
            return this.todayData;
        } catch (error) {
            console.error('載入今日股票資料失敗:', error);
            return null;
        }
    }

    /**
     * 建立股票代碼到資料的映射
     * @param {Array} todayData - 今日股票資料
     * @returns {Object} 股票代碼映射物件
     */
    createStockDataMap(todayData) {
        const stockMap = {};
        todayData.forEach(stock => {
            stockMap[stock.Code] = {
                name: stock.Name,
                closingPrice: parseFloat(stock.ClosingPrice),
                change: parseFloat(stock.Change),
                range: stock.Range,
                volume: parseInt(stock.TradeVolume),
                date: stock.Date
            };
        });
        return stockMap;
    }

    /**
     * 處理熱力圖資料
     * @param {Object} categories - 股票分類資料
     * @param {Object} stockDataMap - 股票資料映射
     * @returns {Array} 處理後的熱力圖資料
     */
    processHeatmapData(categories, stockDataMap) {
        const treemapData = [];
        
        // 處理個股資料
        for (const [categoryName, stocks] of Object.entries(categories)) {
            for (const [stockCode, stockInfo] of Object.entries(stocks)) {
                const todayData = stockDataMap[stockCode];
                if (todayData) {
                    treemapData.push({
                        ids: `${categoryName}-${stockCode}`,
                        labels: `${stockCode}<br>${todayData.name}`,
                        parents: categoryName,
                        values: 1, // 相等大小
                        stockCode: stockCode,
                        stockName: todayData.name,
                        category: categoryName,
                        change: todayData.range || 0,
                        closingPrice: todayData.closingPrice,
                        volume: todayData.volume,
                        changeAmount: todayData.change
                    });
                }
            }
        }
        
        // 添加類別節點
        const categories_set = new Set();
        treemapData.forEach(item => categories_set.add(item.category));
        
        categories_set.forEach(category => {
            treemapData.push({
                ids: category,
                labels: category,
                parents: '台股',
                values: 0,
                change: 0
            });
        });
        
        // 添加根節點
        treemapData.push({
            ids: '台股',
            labels: '台股',
            parents: '',
            values: 0,
            change: 0
        });
        
        this.heatmapData = treemapData;
        return treemapData;
    }

    /**
     * 建立熱力圖
     * @param {Array} data - 熱力圖資料
     */
    createHeatmap(data) {
        const trace = {
            type: 'treemap',
            ids: data.map(d => d.ids),
            labels: data.map(d => d.labels),
            parents: data.map(d => d.parents),
            values: data.map(d => d.values),
            
            // 顏色設定
            marker: {
                colorscale: [
                    [0, '#d73027'],     // 深紅 (-10%)
                    [0.2, '#f46d43'],   // 紅 (-5%)
                    [0.4, '#fee08b'],   // 淺黃 (-1%)
                    [0.5, '#ffffbf'],   // 黃 (0%)
                    [0.6, '#d9ef8b'],   // 淺綠 (+1%)
                    [0.8, '#a6d96a'],   // 綠 (+5%)
                    [1, '#1a9641']      // 深綠 (+10%)
                ],
                colorbar: {
                    title: '漲跌幅 (%)',
                    tickmode: 'array',
                    tickvals: [-10, -5, -1, 0, 1, 5, 10],
                    ticktext: ['-10%', '-5%', '-1%', '0%', '+1%', '+5%', '+10%']
                },
                cmin: -10,
                cmax: 10,
                cmid: 0,
                line: {
                    width: 2,
                    color: 'white'
                },
                cornerradius: 5
            },
            
            // 設定顏色值
            z: data.map(d => d.change || 0),
            
            // 懸停資訊
            hovertemplate: 
                '<b>%{label}</b><br>' +
                '類別: %{customdata[0]}<br>' +
                '漲跌幅: %{customdata[1]:.2f}%<br>' +
                '收盤價: %{customdata[2]}<br>' +
                '成交量: %{customdata[3]}<br>' +
                '<extra></extra>',
            
            customdata: data.map(d => [
                d.category || '',
                d.change || 0,
                d.closingPrice || 0,
                d.volume ? d.volume.toLocaleString() : '0'
            ]),
            
            textinfo: 'label',
            textposition: 'middle center',
            textfont: {
                size: 12,
                color: 'black'
            }
        };

        const layout = {
            title: {
                text: '台股類別熱力圖',
                font: {
                    size: 20,
                    color: '#333'
                }
            },
            font: {
                family: 'Microsoft JhengHei, Arial, sans-serif',
                size: 14
            },
            margin: {
                l: 10,
                r: 10,
                t: 60,
                b: 10
            },
            paper_bgcolor: 'white',
            plot_bgcolor: 'white'
        };

        const config = {
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
            displaylogo: false,
            responsive: true
        };

        Plotly.newPlot('heatmap', [trace], layout, config);
    }

    /**
     * 更新日期和時間資訊
     * @param {Array} todayData - 今日股票資料
     */
    updateTimeInfo(todayData) {
        const date = todayData[0]?.Date;
        if (date) {
            // 轉換民國年為西元年
            const year = parseInt(date.substring(0, 3)) + 1911;
            const month = date.substring(3, 5);
            const day = date.substring(5, 7);
            const formattedDate = `${year}年${month}月${day}日`;
            
            document.getElementById('date-info').textContent = `資料日期: ${formattedDate}`;
        }
        
        const now = new Date();
        const timeString = now.toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        document.getElementById('update-time').textContent = `更新時間: ${timeString}`;
    }

    /**
     * 顯示載入狀態
     */
    showLoading() {
        document.getElementById('loading').style.display = 'block';
        document.getElementById('heatmap').style.display = 'none';
    }

    /**
     * 隱藏載入狀態
     */
    hideLoading() {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('heatmap').style.display = 'block';
    }

    /**
     * 顯示錯誤訊息
     * @param {string} message - 錯誤訊息
     */
    showError(message) {
        document.getElementById('loading').innerHTML = 
            `<div class="error">${message}</div>`;
    }

    /**
     * 主要初始化函數
     */
    async init() {
        try {
            this.showLoading();
            
            // 平行載入資料
            const [categories, todayData] = await Promise.all([
                this.loadStockCategories(),
                this.loadTodayData()
            ]);
            
            if (!categories || !todayData) {
                throw new Error('載入資料失敗');
            }
            
            // 處理資料
            const stockDataMap = this.createStockDataMap(todayData);
            const heatmapData = this.processHeatmapData(categories, stockDataMap);
            
            // 更新時間資訊
            this.updateTimeInfo(todayData);
            
            // 建立熱力圖
            this.createHeatmap(heatmapData);
            
            // 隱藏載入提示
            this.hideLoading();
            
        } catch (error) {
            console.error('初始化失敗:', error);
            this.showError('載入失敗，請檢查資料文件是否存在');
        }
    }
}

// 全域實例
const stockHeatmap = new StockHeatmap();

// 頁面載入完成後初始化
document.addEventListener('DOMContentLoaded', () => {
    stockHeatmap.init();
});

// 匯出供其他模組使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StockHeatmap;
}
