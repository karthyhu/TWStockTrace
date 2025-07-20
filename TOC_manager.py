import json
import requests
import os


class TOC_manager:
    def __init__(self, trace_file_path='./raw_stock_data/trace.json', daily_data_dir='./raw_stock_data/daily/TOC'):
        self.url = 'https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes'
        self.daily_data_dir = daily_data_dir
        self.trace_data = {}

    def save_trace_Specify_date(self, date, Issavetoday = False):
        # 清空之前的資料
        self.trace_data = {}
        
        # 檢查是否已經有今天的資料
        if os.path.exists(f'{self.daily_data_dir}/{date}.json'):
            print(f"Data for {date} already exists.")
            return
        
        payload = {
            'type': 'Daily',
            'date': date,
            'id': '',
            'response': 'json'
        }
        response = requests.post(self.url, data=payload)
        response.raise_for_status() # 非200會拋例外
        data_list = response.json()['tables'][0]['data']
        get_date = response.json()['tables'][0]['date'].replace('/', '')
        print(f"response date: {get_date}")
        for item in data_list:
            self.trace_data[item[0]] = {
                "Date": get_date,
                "Code" : item[0],
                "Name" : item[1],
                "TradeVolume" : item[8].replace(',',''),
                "TradeValue" : item[9].replace(',',''),
                "OpeningPrice" : item[4],
                "HighestPrice" : item[5],
                "LowestPrice" : item[6],
                "ClosingPrice" : item[2],
                "Change" : item[3].replace('+','').replace(' ',''),   
                "Transaction" : item[10].replace(',',''),
                "AveragePrice" : item[7].replace(',','')                
            }
        with open(f'{self.daily_data_dir}/{get_date}.json', 'w', encoding='utf-8') as f:
            json.dump(self.trace_data, f, ensure_ascii=False, indent=0)
        if Issavetoday:
            with open(f'{self.daily_data_dir}/today.json', 'w', encoding='utf-8') as f:
                json.dump(self.trace_data, f, ensure_ascii=False, indent=0)
        return True
    
    def daily_trace(self):
        # 取得今天日期
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        # today轉換成民國年
        today = today.replace('/', '')
        today = str(int(today[:4]) - 1911) + today[4:]
    
        
        # 儲存今天的資料
        self.save_trace_Specify_date(today, Issavetoday=True)
        

if __name__ == "__main__":
    # 測試用
    trace_manager = TOC_manager()
    # trace_manager.save_trace_Specify_date('1130717')
    trace_manager.daily_trace()