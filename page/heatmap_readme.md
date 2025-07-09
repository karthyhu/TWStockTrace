# 台股靜態熱力圖說明文件

## 專案概述
這是一個基於 `today.json` 資料的靜態台股熱力圖頁面，使用純前端技術（HTML、CSS、JavaScript）和 Plotly.js 實現，與 Test3.py 的 Dash 版本功能相同。

## 檔案結構
```
page/
├── heatmap.html          # 主要 HTML 頁面
├── heatmap.css           # 樣式表
├── heatmap.js            # JavaScript 功能模組
└── heatmap_readme.md     # 說明文件
```

## 資料來源
- 股票資料：`../raw_stock_data/daily/today.json`
- 股票分類：`../stock_realtime_heatmap/stock_data.json`

## 檔案說明

### heatmap.html
- **功能**：主要的 HTML 結構文件
- **特色**：
  - 語義化 HTML 標籤
  - 響應式 viewport 設定
  - 外部資源引用（Plotly.js CDN）
  - 清晰的 DOM 結構

### heatmap.css
- **功能**：樣式表文件
- **特色**：
  - 響應式設計（支援手機、平板、桌面）
  - 現代化 CSS 語法
  - 主題一致的色彩搭配
  - 流暢的使用者體驗

### heatmap.js
- **功能**：JavaScript 功能模組
- **架構**：採用 ES6 類別 (Class) 設計
- **特色**：
  - 模組化設計
  - 完整的錯誤處理
  - 詳細的 JSDoc 註解
  - 支援 CommonJS 匯出

## 功能特色

### 1. 靜態資料顯示
- 讀取 `today.json` 中的當日股票資料
- 使用 `stock_data.json` 的分類資訊
- 顯示股票的收盤價、漲跌幅、成交量等資訊

### 2. 熱力圖視覺化
- 使用 Plotly.js 建立互動式樹狀圖
- 三層階層結構：台股 → 類別 → 個股
- 顏色映射：根據漲跌幅著色（-10% 到 +10%）
- 顏色方案：紅綠漸變（紅色代表下跌，綠色代表上漲）

### 3. 互動功能
- 懸停顯示詳細資訊：股票代碼、類別、漲跌幅、收盤價、成交量
- 可縮放和平移
- 響應式設計，適應不同螢幕大小

### 4. 資訊面板
- 顯示資料日期（轉換民國年為西元年）
- 顯示頁面更新時間
- 色彩圖例說明

## 技術實現

### StockHeatmap 類別
```javascript
class StockHeatmap {
    constructor()                           // 建構子
    async loadStockCategories()             // 載入股票分類資料
    async loadTodayData()                   // 載入今日股票資料
    createStockDataMap(todayData)           // 建立股票代碼映射
    processHeatmapData(categories, stockDataMap)  // 處理熱力圖資料
    createHeatmap(data)                     // 建立熱力圖
    updateTimeInfo(todayData)               // 更新時間資訊
    showLoading()                           // 顯示載入狀態
    hideLoading()                           // 隱藏載入狀態
    showError(message)                      // 顯示錯誤訊息
    async init()                            // 主要初始化函數
}
```

### 資料處理流程
1. **載入資料**：
   ```javascript
   loadStockCategories() // 載入股票分類
   loadTodayData()       // 載入今日股票資料
   ```

2. **資料映射**：
   ```javascript
   createStockDataMap(todayData) // 建立股票代碼到資料的映射
   ```

3. **熱力圖資料處理**：
   ```javascript
   processHeatmapData(categories, stockDataMap) // 處理成 Plotly 樹狀圖格式
   ```

4. **視覺化**：
   ```javascript
   createHeatmap(data) // 使用 Plotly.js 建立熱力圖
   ```

### 顏色設定
- 使用 7 色漸變調色盤
- 顏色範圍：-10% 到 +10%
- 中點設為 0%（平盤）
- 顏色對應：
  - 深紅 (-10%)
  - 紅 (-5%)
  - 淺黃 (-1%)
  - 黃 (0%)
  - 淺綠 (+1%)
  - 綠 (+5%)
  - 深綠 (+10%)

### 懸停資訊
顯示以下資訊：
- 股票代碼和名稱
- 所屬類別
- 漲跌幅百分比
- 收盤價格
- 成交量（格式化顯示）

## 使用方式

### 開啟頁面
1. 確保以下文件存在：
   - `../raw_stock_data/daily/today.json`
   - `../stock_realtime_heatmap/stock_data.json`

2. 確保檔案結構正確：
   ```
   page/
   ├── heatmap.html
   ├── heatmap.css
   └── heatmap.js
   ```

3. 在瀏覽器中開啟 `heatmap.html`

### 互動操作
- **懸停**：將滑鼠移到股票方塊上查看詳細資訊
- **縮放**：使用滑鼠滾輪或觸控板縮放
- **平移**：點擊拖拽移動視圖
- **重置**：點擊工具列的重置按鈕

## 與 Test3.py 的差異

### 相同功能
- 相同的熱力圖視覺效果
- 相同的分類階層結構
- 相同的顏色映射方案
- 相同的懸停資訊顯示

### 主要差異
| 功能 | Test3.py (Dash) | heatmap.html (靜態) |
|------|-----------------|-------------------|
| 資料來源 | 即時 API | 靜態 JSON 文件 |
| 更新方式 | 自動更新 (3秒) | 手動重新整理 |
| 部署方式 | 需要 Python 服務器 | 直接開啟 HTML |
| 依賴套件 | Dash, Plotly, twstock | 僅需瀏覽器 |
| 程式架構 | Python 函數式 | JavaScript 類別式 |

## 技術優勢

### 1. 模組化設計
- **關注點分離**：HTML 結構、CSS 樣式、JavaScript 邏輯分離
- **可維護性**：每個檔案職責明確，便於維護和修改
- **可重用性**：CSS 和 JavaScript 可以被其他頁面重用

### 2. 響應式設計
- **多裝置支援**：手機、平板、桌面完美適配
- **流暢體驗**：觸控和滑鼠操作皆支援
- **性能優化**：CSS 媒體查詢優化不同解析度顯示

### 3. 現代化開發
- **ES6 語法**：使用現代 JavaScript 特性
- **類別設計**：面向物件程式設計
- **JSDoc 註解**：完整的程式碼文件

## 技術需求
- 現代瀏覽器（支援 ES6+）
- 網路連線（載入 Plotly.js CDN）
- 本地檔案系統訪問權限

## 故障排除

### 常見問題
1. **頁面顯示空白**：檢查瀏覽器控制台是否有 JavaScript 錯誤
2. **無法載入資料**：確認 JSON 文件路徑是否正確
3. **熱力圖不顯示**：檢查網路連線是否正常（需要載入 Plotly.js）
4. **樣式異常**：確認 CSS 文件路徑是否正確

### 除錯建議
- 開啟瀏覽器開發者工具查看控制台錯誤
- 確認 JSON 文件格式正確
- 檢查文件路徑是否相對正確
- 確認所有檔案 (HTML、CSS、JS) 都在正確位置

## 擴展建議

### 1. 功能擴展
- **添加刷新按鈕**：實現手動數據刷新
- **添加篩選功能**：按類別或漲跌幅篩選
- **添加排序功能**：按不同條件排序顯示
- **添加歷史數據**：支援查看不同日期的數據
- **添加匯出功能**：匯出圖表或數據

### 2. 技術優化
- **使用 TypeScript**：提供更好的類型安全
- **添加單元測試**：確保程式碼品質
- **使用 Webpack**：模組打包和優化
- **添加 Service Worker**：離線功能支援
- **使用 CSS 預處理器**：Sass 或 Less

### 3. 效能優化
- **資料快取**：減少重複請求
- **圖片優化**：壓縮和格式優化
- **代碼分割**：按需載入功能模組
- **CDN 優化**：使用本地 Plotly.js 文件
