import json
import os
import requests
import time
import re
from datetime import datetime, timedelta
# from trace_manager import TraceManager

class TWSE_manager:
    def __init__(self, daily_data_dir='./raw_stock_data/daily/twse'):
        if not os.path.exists(daily_data_dir):
            os.makedirs(daily_data_dir)
        self.daily_data_dir = daily_data_dir
        self.fill_list = ['Code', 'Name', 'ClosingPrice', 'Change', 'OpeningPrice', 'HighestPrice', 'LowestPrice', 'TradeVolume', 'TradeValue', 'Range']
    def safe_float(self, value):
        """安全轉換為浮點數"""
        try:
            return float(value.replace(',', '') if isinstance(value, str) else value)
        except (ValueError, AttributeError):
            return 0.0

    def safe_int(self, value):
        """安全轉換為整數"""
        try:
            return int(value.replace(',', '') if isinstance(value, str) else value)
        except (ValueError, AttributeError):
            return 0

    def download_openapi(self, date=None):
        try:
            # 如果沒有指定日期，使用今日
            
            # 使用證交所 API
            url = 'https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"❌ API 請求失敗: {response.status_code}")
                return None

            datas = response.json()
            if not datas:
                print("❌ API 回傳空資料")
                return None
                
            total_data = {
                'date': datas[0]['Date'],
                'fields': self.fill_list.copy(),
                'data': {}
            }
            
            for item in datas:
                try:
                    # 使用安全轉換和正確的漲跌幅計算                    
                    closing_price = self.safe_float(item.get('ClosingPrice', '0'))
                    change = self.safe_float(item.get('Change', '0'))
                    
                    range_percent = (change / closing_price * 100) if closing_price != 0 else 0.0

                    # print(f"處理股票 {item.get('Code', 'N/A')} - 漲跌幅: {range_percent:.2f}%")
                    
                    total_data['data'][item.get('Code', '')] = [
                        item.get('Code', ''),
                        item.get('Name', ''),
                        closing_price,
                        change,
                        self.safe_float(item.get('OpeningPrice', '0')),
                        self.safe_float(item.get('HighestPrice', '0')),
                        self.safe_float(item.get('LowestPrice', '0')),
                        self.safe_int(item.get('TradeVolume', '0')),
                        self.safe_int(item.get('TradeValue', '0')),
                        round(range_percent, 2)
                    ]
                except Exception as item_error:
                    print(f"⚠️ 處理股票 {item.get('Code', 'Unknown')} 時發生錯誤: {item_error}")
                    continue
            
            # 使用指定的目錄儲存檔案
            
            self.save_file(total_data, filename=f"{total_data['date']}.json")

            print(f'📊 共處理 {len(total_data["data"])} 檔股票資料')
            
            return total_data
                        
        except Exception as e:
            print(f"❌ 下載台股資料時發生錯誤: {e}")
            return None

    def save_file(self, data, filename='NoName'):
        """儲存資料到 JSON 檔案"""
        try:
            with open(f'{self.daily_data_dir}/{filename}', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            print(f"📁 檔案已儲存: {filename}")
        except Exception as e:
            print(f"❌ 儲存檔案時發生錯誤: {e}")


def update_trace_json(date):
    """更新 trace.json 的便利函數（僅 TWSE）"""
    from trace_manager import update_trace_json
    return update_trace_json(twse_date=date)


def daily_trace(date:str = None):
    manager = TWSE_manager()
    data = manager.download_openapi()
    if data:
        manager.save_file(data, f"today.json")
        
    return data['date'] if 'date' in data else None


if __name__ == "__main__":
    # 測試下載功能
    print("測試台股資料下載...")
    manager = TWSE_manager()
    date = manager.download_openapi()
