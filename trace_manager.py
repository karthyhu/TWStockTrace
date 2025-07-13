import json
import os
import requests
import time
from datetime import datetime, timedelta

class TraceManager:
    def __init__(self, trace_file_path='./raw_stock_data/trace.json', daily_data_dir='./raw_stock_data/daily'):
        self.trace_file_path = trace_file_path
        self.daily_data_dir = daily_data_dir
        self.trace_data = []
        
    def load_trace_data(self):
        """讀取 trace.json 文件"""
        try:
            if os.path.exists(self.trace_file_path) and os.path.getsize(self.trace_file_path) > 0:
                with open(self.trace_file_path, 'r', encoding='utf-8') as f:
                    self.trace_data = json.load(f)
                print(f"✅ 讀取到 {len(self.trace_data)} 筆追蹤記錄")
            else:
                self.trace_data = []
                print("⚠️  trace.json 不存在或為空，初始化為空列表")
        except json.JSONDecodeError as e:
            print(f"❌ trace.json 格式錯誤: {e}")
            self.trace_data = []
    
    def save_trace_data(self):
        """保存 trace.json 文件"""
        try:
            with open(self.trace_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.trace_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存 trace.json 時發生錯誤: {e}")
            return False
    
    def add_today_filtered_stocks(self, today_filename):
        """1. 加入當天過濾後的股票進 trace.json"""
        try:
            today_file_path = os.path.join(self.daily_data_dir, today_filename)
            with open(today_file_path, 'r', encoding='utf-8') as f:
                today_data = json.load(f)
            
            # 過濾漲幅大於等於 6% 的股票
            filtered_stocks = [item for item in today_data if item.get('Range', 0) >= 6]
            
            print(f"📊 今日共有 {len(filtered_stocks)} 檔漲幅大於等於 6% 的股票")
            
            added_count = 0
            updated_count = 0
            
            for stock in filtered_stocks:
                stock_code = stock['Code']
                stock_name = stock['Name']
                trigger_date = stock['Date']
                
                # 檢查是否已存在相同 Code 的股票
                existing_index = None
                for idx, existing_item in enumerate(self.trace_data):
                    if existing_item['Code'] == stock_code:
                        existing_index = idx
                        break
                
                if existing_index is not None:
                    # 更新現有記錄
                    existing_record = self.trace_data[existing_index]
                    
                    # 初始化 Trigger_History
                    if 'Trigger_History' not in existing_record:
                        existing_record['Trigger_History'] = existing_record['Trigger_Date']
                    
                    # 檢查新日期是否已經在歷史記錄中
                    history_dates = existing_record['Trigger_History'].split(',')
                    if trigger_date not in history_dates:
                        existing_record['Trigger_History'] += ',' + trigger_date
                    
                    existing_record['Trigger_Date'] = trigger_date
                    updated_count += 1
                else:
                    # 添加新記錄
                    new_record = {
                        'Name': stock_name,
                        'Code': stock_code,
                        'Trigger_Date': trigger_date
                    }
                    self.trace_data.append(new_record)
                    added_count += 1
            
            print(f"✅ 新增 {added_count} 檔股票，更新 {updated_count} 檔股票")
            return True
            
        except Exception as e:
            print(f"❌ 加入今日股票時發生錯誤: {e}")
            return False
    
    def merge_duplicate_stocks(self):
        """2. 合併有重複部分的股票"""
        try:
            unique_stocks = {}
            
            for stock in self.trace_data:
                code = stock['Code']
                
                if code in unique_stocks:
                    # 合併重複股票
                    existing = unique_stocks[code]
                    
                    # 合併 Trigger_History
                    if 'Trigger_History' in existing and 'Trigger_History' in stock:
                        all_dates = existing['Trigger_History'].split(',') + stock['Trigger_History'].split(',')
                        unique_dates = list(dict.fromkeys(all_dates))  # 保持順序去重
                        existing['Trigger_History'] = ','.join(unique_dates)
                    elif 'Trigger_History' in stock:
                        existing['Trigger_History'] = stock['Trigger_History']
                    
                    # 使用較新的觸發日期
                    if stock['Trigger_Date'] > existing['Trigger_Date']:
                        existing['Trigger_Date'] = stock['Trigger_Date']
                        existing['Name'] = stock['Name']  # 更新名稱以防有變化
                else:
                    unique_stocks[code] = stock
            
            original_count = len(self.trace_data)
            self.trace_data = list(unique_stocks.values())
            merged_count = original_count - len(self.trace_data)
            
            if merged_count > 0:
                print(f"✅ 合併了 {merged_count} 筆重複記錄")
            
            return True
            
        except Exception as e:
            print(f"❌ 合併重複股票時發生錯誤: {e}")
            return False
    
    def remove_old_stocks(self, days=7):
        """3. 刪除觸發時間超過指定天數的股票"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 將民國年日期轉換為西元年進行比較
            def parse_roc_date(date_str):
                try:
                    year = int(date_str[:3]) + 1911
                    month = int(date_str[3:5])
                    day = int(date_str[5:7])
                    return datetime(year, month, day)
                except:
                    return datetime.min
            
            original_count = len(self.trace_data)
            self.trace_data = [
                stock for stock in self.trace_data
                if parse_roc_date(stock['Trigger_Date']) >= cutoff_date
            ]
            
            removed_count = original_count - len(self.trace_data)
            if removed_count > 0:
                print(f"✅ 刪除了 {removed_count} 筆超過 {days} 天的舊記錄")
            
            return True
            
        except Exception as e:
            print(f"❌ 刪除舊股票記錄時發生錯誤: {e}")
            return False
    
    def fill_kline_data_from_daily(self, stock_code):
        """4.1 從 daily 資料夾填充 K 線資料"""
        try:
            kline_data = []
            
            # 獲取所有 daily 檔案
            daily_files = [f for f in os.listdir(self.daily_data_dir) 
                          if f.endswith('.json') and f != 'trace.json']
            
            # 按檔名排序（日期順序）
            daily_files.sort()
            
            for file in daily_files:
                file_path = os.path.join(self.daily_data_dir, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        daily_data = json.load(f)
                    
                    # 尋找對應的股票
                    for stock in daily_data:
                        if stock.get('Code') == stock_code:
                            # 轉換為 K 線格式
                            kline_entry = {
                                'date': stock['Date'].replace('/', '-'),
                                'open': float(stock.get('OpeningPrice', 0)),
                                'high': float(stock.get('HighestPrice', 0)),
                                'low': float(stock.get('LowestPrice', 0)),
                                'close': float(stock.get('ClosingPrice', 0)),
                                'volume': int(stock.get('TradeVolume', 0)),
                                'range': float(stock.get('Range', 0))
                            }
                            kline_data.append(kline_entry)
                            break
                            
                except Exception as e:
                    print(f"⚠️  讀取 {file} 時發生錯誤: {e}")
                    continue
            
            return kline_data
            
        except Exception as e:
            print(f"❌ 從 daily 資料填充 K 線時發生錯誤: {e}")
            return []
    
    def fill_kline_data_from_api(self, stock_code, months=6):
        """4.2 使用台灣證交所 API 填充 K 線資料"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
            stock_data = []
            
            current_date = start_date
            while current_date <= end_date:
                year = current_date.year
                month = current_date.month
                
                params = {
                    'response': 'json',
                    'date': f'{year}{month:02d}01',
                    'stockNo': stock_code,
                }
                
                response = requests.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'data' in data and data['data']:
                        for row in data['data']:
                            try:
                                if len(row) < 9 or row[3] == '--' or row[6] == '--':
                                    continue
                                
                                # 清理數據
                                volume = row[1].replace(',', '') if row[1] != '--' else '0'
                                turnover = row[2].replace(',', '') if row[2] != '--' else '0'
                                transaction = row[8].replace(',', '') if row[8] != '--' else '0'
                                
                                # 處理漲跌價差
                                change_raw = row[7]
                                if change_raw and change_raw != '--':
                                    change = change_raw.replace(',', '').replace('X', '')
                                    change = change if change else '0'
                                else:
                                    change = '0'
                                
                                stock_data.append({
                                    'date': row[0].replace('/', '-'),
                                    'open': float(row[3].replace(',', '')),
                                    'high': float(row[4].replace(',', '')),
                                    'low': float(row[5].replace(',', '')),
                                    'close': float(row[6].replace(',', '')),
                                    'volume': int(volume),
                                    'turnover': int(turnover),
                                    'change': float(change),
                                    'transaction': int(transaction)
                                })
                                
                            except (ValueError, IndexError):
                                continue
                
                # 移動到下個月
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
                
                time.sleep(1)  # 避免請求過於頻繁
            
            return stock_data
            
        except Exception as e:
            print(f"❌ 從 API 獲取 {stock_code} 資料時發生錯誤: {e}")
            return []
    
    def fill_all_kline_data(self):
        """4. 填充所有股票的日 K 資料"""
        try:
            print("📈 開始填充股票 K 線資料...")
            
            for i, stock in enumerate(self.trace_data, 1):
                stock_code = stock['Code']
                stock_name = stock['Name']
                
                print(f"[{i}/{len(self.trace_data)}] 處理 {stock_name} ({stock_code})")
                
                # 檢查是否已有 K 線資料
                if 'kline_data' in stock and stock['kline_data']:
                    print(f"  ⏭️  已有 K 線資料 ({len(stock['kline_data'])} 筆)")
                    continue
                
                # 4.1 先嘗試從 daily 資料填充
                kline_data = self.fill_kline_data_from_daily(stock_code)
                
                if len(kline_data) >= 30:  # 如果有足夠的資料
                    stock['kline_data'] = kline_data
                    stock['kline_last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    stock['kline_source'] = 'daily_files'
                    print(f"  ✅ 從 daily 資料獲取 {len(kline_data)} 筆")
                else:
                    # 4.2 從 API 獲取
                    print(f"  🌐 daily 資料不足，改用 API 獲取...")
                    kline_data = self.fill_kline_data_from_api(stock_code)
                    
                    if kline_data:
                        stock['kline_data'] = kline_data
                        stock['kline_last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        stock['kline_source'] = 'twse_api'
                        print(f"  ✅ 從 API 獲取 {len(kline_data)} 筆")
                    else:
                        stock['kline_data'] = []
                        stock['kline_last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        stock['kline_source'] = 'failed'
                        print(f"  ⚠️  無法獲取資料")
            
            return True
            
        except Exception as e:
            print(f"❌ 填充 K 線資料時發生錯誤: {e}")
            return False
    
    def update_trace_data(self, today_filename):
        """完整的 trace.json 更新流程"""
        print("🔄 開始更新 trace.json...")
        
        # 載入現有資料
        self.load_trace_data()
        
        # 1. 加入當天過濾後的股票
        print("\n1️⃣ 加入當天過濾後的股票...")
        self.add_today_filtered_stocks(today_filename)
        
        # 2. 合併重複股票
        print("\n2️⃣ 合併重複股票...")
        self.merge_duplicate_stocks()
        
        # 3. 刪除超過一週的股票
        print("\n3️⃣ 刪除超過一週的股票...")
        self.remove_old_stocks(days=7)
        
        # 4. 填充 K 線資料
        print("\n4️⃣ 填充 K 線資料...")
        self.fill_all_kline_data()
        
        # 按日期排序
        self.trace_data = sorted(self.trace_data, key=lambda x: x['Trigger_Date'])
        
        # 保存結果
        if self.save_trace_data():
            print(f"\n✅ trace.json 更新完成！共 {len(self.trace_data)} 筆記錄")
            return True
        else:
            print("\n❌ trace.json 保存失敗！")
            return False

def update_trace_json(today_filename):
    """主要入口函數，供 main.py 調用"""
    trace_manager = TraceManager()
    return trace_manager.update_trace_data(today_filename)

if __name__ == "__main__":
    # 測試用
    update_trace_json('today.json')
