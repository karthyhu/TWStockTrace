import json
import os
import requests
import time
import re
from datetime import datetime, timedelta
import timenormalyize as tn


class TWSE_manager:
    def __init__(self, daily_data_dir="./raw_stock_data/daily/twse"):
        if not os.path.exists(daily_data_dir):
            os.makedirs(daily_data_dir)
        self.daily_data_dir = daily_data_dir
        self.fill_list = [
            "Code",
            "Name",
            "ClosingPrice",
            "Change",
            "OpeningPrice",
            "HighestPrice",
            "LowestPrice",
            "TradeVolume",
            "TradeValue",
            "Range",
        ]

    def safe_float(self, value):
        """安全轉換為浮點數"""
        try:
            return float(value.replace(",", "") if isinstance(value, str) else value)
        except (ValueError, AttributeError):
            return 0.0

    def safe_int(self, value):
        """安全轉換為整數"""
        try:
            return int(value.replace(",", "") if isinstance(value, str) else value)
        except (ValueError, AttributeError):
            return 0

    def download_internalurl(self, date=None):

        if date:
            date = tn.normalize_date(date, "CE", "")
        else:
            date = tn.get_current_date("CE", "-")

        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={date}&type=ALLBUT0999&response=json"

        try:
            r = requests.get(url)

        except Exception as e:
            print(f"❌ 下載失敗: {e}")
            return None

        jdata = r.json()
        realdate = str(jdata["params"]["date"])
        realdate = f"{int(realdate[:4])-1911}{realdate[4:]}"  # 修正日期格式
        jdata = jdata["tables"][8]
        total_data = {"date": realdate, "fields": self.fill_list.copy(), "data": {}}

        # 0"證券代號",
        # 1"證券名稱",
        # 2"成交股數",
        # 3"成交筆數",
        # 4"成交金額",
        # 5"開盤價",
        # 6"最高價",
        # 7"最低價",
        # 8"收盤價",
        # 9"漲跌(+/-)","<p style= color:red>+</p>"
        # 10"漲跌價差",
        # 11"最後揭示買價",
        # 12"最後揭示買量",
        # 13"最後揭示賣價",
        # 14"最後揭示賣量",
        # 15"本益比"
        for item in jdata["data"]:
            ClosingPrice = self.safe_float(item[8].replace(",", ""))
            Change = self.safe_float(item[10])
            if "+" in item[9]:
                Change = abs(Change)
            else:
                Change = -abs(Change)

            range_percent = (Change / ClosingPrice * 100) if ClosingPrice != 0 else 0.0
            total_data["data"][item[0]] = [
                str(item[0]),  # Code
                str(item[1]),  # Name
                str(self.safe_float(item[8].replace(",", ""))),  # ClosingPrice
                str(self.safe_float(item[10].replace(",", ""))),  # Change
                str(self.safe_float(item[5].replace(",", ""))),  # OpeningPrice
                str(self.safe_float(item[6].replace(",", ""))),  # HighestPrice
                str(self.safe_float(item[7].replace(",", ""))),  # LowestPrice
                str(self.safe_int(item[2].replace(",", ""))),  # TradeVolume
                str(self.safe_int(item[4].replace(",", ""))),  # TradeValue
                str(round(range_percent, 5)),  # Range
            ]
        self.save_file(total_data, filename=f"{realdate}.json")
        
        if  tn.normalize_date(total_data['date']) != tn.normalize_date(date):
            print(f"⚠️ 日期不一致: API 返回 {tn.normalize_date(total_data['date'])}, 請檢查日期格式")
            return None

        return total_data

    def download_openapi(self, date=None):

        # 使用證交所 API
        try:
            url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
            response = requests.get(url, timeout=10)
        except Exception as item_error:
            print(f"⚠️ 處理股票 {item.get('Code', 'Unknown')} 時發生錯誤: {item_error}")
            return None

        datas = response.json()
        if not datas:
            print("❌ API 回傳空資料")
            return None

        total_data = {
            "date": datas[0]["Date"],
            "fields": self.fill_list.copy(),
            "data": {},
        }

        for item in datas:
            # 使用安全轉換和正確的漲跌幅計算
            closing_price = self.safe_float(item.get("ClosingPrice", "0"))
            change = self.safe_float(item.get("Change", "0"))

            range_percent = (
                (change / closing_price * 100) if closing_price != 0 else 0.0
            )

            # print(f"處理股票 {item.get('Code', 'N/A')} - 漲跌幅: {range_percent:.2f}%")

            total_data["data"][item.get("Code", "")] = [
                str(item.get("Code", "")),
                str(item.get("Name", "")),
                str(closing_price),
                str(change),
                str(self.safe_float(item.get("OpeningPrice", ""))),
                str(self.safe_float(item.get("HighestPrice", ""))),
                str(self.safe_float(item.get("LowestPrice", ""))),
                str(self.safe_int(item.get("TradeVolume", ""))),
                str(self.safe_int(item.get("TradeValue", ""))),
                str(round(range_percent, 5))
            ]

        self.save_file(total_data, filename=f"{total_data['date']}.json")

        print(f'📊 共處理 {len(total_data["data"])} 檔股票資料')

        return total_data

    def save_file(self, data, filename="NoName"):
        """儲存資料到 JSON 檔案"""
        try:
            with open(f"{self.daily_data_dir}/{filename}", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            print(f"📁 檔案已儲存: {filename}")
        except Exception as e:
            print(f"❌ 儲存檔案時發生錯誤: {e}")
            
    def genpassdayfile(self, start_date: str, during_days: int = 2):
        all_files = os.listdir(self.daily_data_dir)
        all_files = [f for f in all_files if f.endswith('.json')]
        #逆序
        all_files.sort(reverse=True)
        start_date = tn.normalize_date(start_date, "ROC", "")
        start_index = all_files.index(f'{start_date}.json')
        for i in range(during_days):
            with open(f'{self.daily_data_dir}/{all_files[start_index + i]}', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with open(f'{self.daily_data_dir}/T{i+1}_Day.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=1)

def update_trace_json(date):
    """更新 trace.json 的便利函數（僅 TWSE）"""
    from trace_manager import update_trace_json

    return update_trace_json(twse_date=date)


def daily_trace(date: str = None):
    manager = TWSE_manager()
    if date is None:
        date = tn.get_current_date("ROC", "-")
    data = manager.download_internalurl(date)
    if data:
        manager.save_file(data, f"today.json")
    manager.genpassdayfile(date, 2)
    return date


if __name__ == "__main__":
    # 測試下載功能
    print("測試台股資料下載...")
    t = TWSE_manager()
    # date = t.download_openapi()
    # date = t.download_internalurl("1140724")
    # t.genpassdayfile('114/08/05', 2)

