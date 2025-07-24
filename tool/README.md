# 台股歷史資料下載工具

這個工具可以讓您輕鬆下載台灣證券交易所 (TWSE) 和櫃買中心 (TPEX) 的歷史股票資料。

## 功能特色

- 🎯 **支援兩大市場**: TWSE (上市) 和 TPEX (上櫃)
- 📅 **靈活日期範圍**: 單日、多日、當月、最近幾天
- 🌍 **台灣時區**: 使用台灣時間進行日期計算
- 📊 **詳細統計**: 下載進度和完成摘要
- 🛡️ **安全機制**: 自動延遲避免被封鎖
- 📝 **多種格式**: 支援民國年/西元年日期格式

## 安裝需求

```bash
pip install requests pytz
```

## 使用方式

### 1. 命令列介面 (推薦)

```bash
# 下載最近7天的資料 (兩個市場)
python tool/download_cli.py recent 7 both

# 下載當月TWSE資料
python tool/download_cli.py month twse

# 下載指定日期範圍
python tool/download_cli.py range 1140701 1140731 both

# 下載單一日期
python tool/download_cli.py single 1140724 tpex

# 顯示說明
python tool/download_cli.py help
```

### 2. 互動式介面

```bash
python tool/gethistory.py
```

會顯示選單讓您選擇功能。

### 3. 程式碼整合

```python
from tool.gethistory import HistoryDataDownloader

# 建立下載器
downloader = HistoryDataDownloader()

# 下載日期範圍
downloader.download_date_range(
    start_date="1140701",     # 開始日期
    end_date="1140731",       # 結束日期
    source="both",            # 資料來源: twse/tpex/both
    exclude_weekends=True,    # 排除週末
    max_workers=1,            # 併發數 (建議設為1)
    delay_range=(1.0, 3.0)    # 請求延遲範圍
)

# 下載最近幾天
downloader.download_recent_days(7, "both")

# 下載當月資料
downloader.download_current_month("both")

# 下載單一日期
result = downloader.download_single_date("1140724", "both")
```

## 參數說明

### 日期格式
支援多種日期格式，會自動轉換：
- `1140724` (民國年)
- `114/07/24` (民國年含分隔符)  
- `2025-07-24` (西元年)
- `20250724` (西元年)

### 資料來源
- `twse`: 只下載台灣證券交易所資料
- `tpex`: 只下載櫃買中心資料  
- `both`: 同時下載兩個市場資料 (預設)

### 其他參數
- `exclude_weekends`: 是否排除週末 (預設: True)
- `max_workers`: 併發下載數 (建議: 1, 避免被封鎖)
- `delay_range`: 請求間延遲時間範圍 (秒)

## 輸出格式

下載的資料會儲存為 JSON 格式：

```json
{
  "date": "1140724",
  "fields": ["Code", "Name", "ClosingPrice", "Change", "OpeningPrice", "HighestPrice", "LowestPrice", "TradeVolume", "TradeValue", "Range"],
  "data": {
    "2330": ["2330", "台積電", "1000.0", "10.0", "990.0", "1005.0", "985.0", "50000", "50000000", "1.0"],
    "2317": ["2317", "鴻海", "180.0", "-5.0", "185.0", "186.0", "178.0", "30000", "5400000", "-2.7"]
  }
}
```

## 儲存位置

- TWSE 資料: `./raw_stock_data/daily/twse/`
- TPEX 資料: `./raw_stock_data/daily/tpex/`

## 使用建議

1. **避免頻繁請求**: 建議使用預設的延遲設定
2. **單線程下載**: `max_workers=1` 避免被伺服器封鎖
3. **合理時間範圍**: 一次不要下載太多天的資料
4. **檢查交易日**: 週末和國定假日沒有資料
5. **網路穩定**: 確保網路連線穩定

## 常見問題

### Q: 為什麼某些日期沒有資料？
A: 可能是週末、國定假日或非交易日。

### Q: 下載速度很慢？
A: 這是正常的，為了避免被封鎖會自動延遲請求。

### Q: 下載失敗怎麼辦？
A: 檢查網路連線，或稍後再試。工具會顯示詳細錯誤訊息。

### Q: 可以同時下載嗎？
A: 不建議，請使用 `max_workers=1` 避免被封鎖。

## 範例場景

### 場景1: 建立歷史資料庫
```bash
# 下載過去一個月的完整資料
python tool/download_cli.py range 1140601 1140630 both
```

### 場景2: 每日更新
```bash
# 下載最近3天，確保不漏資料
python tool/download_cli.py recent 3 both
```

### 場景3: 特定市場分析
```bash
# 只下載TWSE上市公司資料
python tool/download_cli.py month twse
```

### 場景4: 資料補齊
```bash
# 補齊特定日期的TPEX資料
python tool/download_cli.py single 1140715 tpex
```

## 注意事項

- 請遵守網站的使用條款
- 不要過度頻繁請求
- 下載的資料僅供個人研究使用
- 建議在非交易時間下載歷史資料

## 更新日誌

- v1.0: 初版發布，支援TWSE和TPEX資料下載
- 支援台灣時區日期處理
- 提供命令列和互動式介面
- 完整的錯誤處理和統計功能
