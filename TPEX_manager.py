import json
import requests
import os
import time
import random
import re


data_list = {
  '02' : '食品工業',
  '03' : '塑膠工業',
  '04' : '紡織纖維',
  '05' : '電機機械',
  '06' : '電器電纜',
  '21' : '化學工業',
  '08' : '玻璃陶瓷',
  '10' : '鋼鐵工業',
  '11' : '橡膠工業',
  '14' : '建材營造',
  '15' : '航運業',
  '16' : '觀光餐旅',
  '17' : '金融業',
  '20' : '其他',
  '22' : '生技醫療類',
  '23' : '油電燃氣類',
  '24' : '半導體類',
  '25' : '電腦及週邊類',
  '26' : '光電業類',
  '27' : '通信網路類',
  '28' : '電子零組件類',
  '29' : '電子通路類',
  '30' : '資訊服務類',
  '31' : '其他電子類',
  '32' : '文化創意業',
  '33' : '農業科技業',
  '35' : '綠能環保類',
  '36' : '數位雲端類',
  '37' : '運動休閒類',
  '38' : '居家生活類',
  '80' : '管理股票',
  'AA' : '受益證券',
  'EE' : '上櫃ETF',
  'EN' : '指數投資證券',
  'TD' : '台灣存託憑證'
}

headers = {
  'Accept': 'application/json, text/javascript, */*; q=0.01',
  'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
  'Connection': 'keep-alive',
  'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
  'Origin': 'https://www.tpex.org.tw',
  'Referer': 'https://www.tpex.org.tw/zh-tw/mainboard/trading/info/mi-pricing.html',
  'Sec-Fetch-Dest': 'empty',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Site': 'same-origin',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
  'X-Requested-With': 'XMLHttpRequest',
  'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"'
}


class TPEX_manager:
    def __init__(self, daily_data_dir='./raw_stock_data/daily/TOC'):
        self.daily_data_dir = daily_data_dir
        
    def save_today_data(self, data):
        if not os.path.exists(self.daily_data_dir):
            os.makedirs(self.daily_data_dir)
        
        with open(f'{self.daily_data_dir}/today.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return True

    def download_get(self, date:str):
        session = requests.Session()
        session.headers.update(headers)
        try:
            session.get('https://www.tpex.org.tw/zh-tw/mainboard/trading/info/pricing.html', timeout=10)
            print("✅ 會話已建立，Cookie 已自動儲存。")
            time.sleep(random.uniform(0.2, 0.5)) # 模擬短暫停留
        except requests.exceptions.RequestException as e:
            print(f"❌ 步驟一失敗，無法建立會話: {e}")
        sdate = date.split('/')
        
        totaldata = {}
        totaldata['date'] = []
        totaldata['fields'] = ['代號', '名稱', '收盤 ', '漲跌', '開盤 ', '最高', '最低', '成交股數', '成交金額(元)', '成交筆數', '最後買價', '最後買量(張數)', '最後賣價', '最後賣量(張數)', '發行股數', '次日漲停價', '次日跌停價']
        totaldata['data'] = {}
        totalCount = 0

        for key, value in data_list.items():
            url = f'https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={sdate[0]}%2F{sdate[1]}%2F{sdate[2]}&type={key}&id=&response=json&order=0&sort=asc'
            try:
                res = session.get(url)
                data = json.loads(res.text)
                totaldata['date'] = str(data['tables'][0]['date'].replace('/', ''))

                for item in data['tables'][0]['data']:
                    item = [re.sub(r'[+,]', '', item) for item in item]

                    totaldata['data'][item[0]] = item

                totalCount += int(data['tables'][0]['totalCount'])
                print('.', end=' ')
            except Exception as e:
                print(f'Error: {e}')

        print(f"total cnt = {totalCount}")
        with open(f"{self.daily_data_dir}/{totaldata['date']}.json", 'w', encoding='utf-8') as f:
            json.dump(totaldata, f, ensure_ascii=False, indent=1)
            print("save done")
        return totaldata

    def download_toc_post(self, date:str):
        session = requests.Session()
        session.headers.update(headers)
        entry_url = "https://www.tpex.org.tw/zh-tw/mainboard/trading/info/mi-pricing.html"
        url = 'https://www.tpex.org.tw/www/zh-tw/afterTrading/otc'
        try:
            print("步驟一：正在訪問入口頁面以建立會話...")
            session.get(entry_url, timeout=10)
            print("✅ 會話已建立，Cookie 已自動儲存。")
            time.sleep(random.uniform(1, 3)) # 模擬短暫停留
        except requests.exceptions.RequestException as e:
            print(f"❌ 步驟一失敗，無法建立會話: {e}")
        
        payload = {
            'date': date,  # 改你要的日期
            'type': '',
            'id': '',
            'response': 'json'
        }
        
        totaldata = {}
        totaldata['date'] = payload['date'].replace('/', '')
        totaldata['fields'] = ['代號', '名稱', '收盤 ', '漲跌', '開盤 ', '最高 ', '最低', '成交股數  ', ' 成交金額(元)', ' 成交筆數 ', '最後買價', '最後買量<br>(張數)', '最後賣價', '最後賣量<br>(張數)', '發行股數 ', '次日漲停價 ', '次日跌停價']
        totaldata['data'] = []
        totalCount = 0
        for key, value in data_list.items():
            payload['type'] = key
            try:
                response = requests.post(url, headers=headers, data=payload)
                data = response.json()
                # print(f"{data['tables'][0]}")
                totaldata['data'].extend(data['tables'][0]['data'])
                totalCount += int(data['tables'][0]['totalCount'])
                print('.', end=' ')
            except Exception as e:
                print(f"key = {key}, {value}")
                print(f'Error: {e}')
            # time.sleep(random.uniform(0.2, 1.0))
            # time.sleep(0.1)
        print(f"total cnt = {totalCount}")

        with open(f"{payload['date'].replace('/', '')}.json", 'w', encoding='utf-8') as f:
            json.dump(totaldata, f, ensure_ascii=False, indent=4)
            print("save done")
    
    
def daily_trace(date: str = None):
    # 取得今天日期
    if date is None:
        from datetime import datetime
        today = datetime.now().strftime('%Y/%m/%d')
        # today轉換成民國年
        today = str(int(today[:4]) - 1911) + today[4:]
        
    else:
        today = f'{date[:3]}/{date[3:5]}/{date[5:]}'

    
    # 儲存今天的資料
    trace_manager = TPEX_manager()
    data = trace_manager.download_get(today)
    if data:
        trace_manager.save_today_data(data)
        print(f"{today} 的資料已成功儲存。")
        

if __name__ == "__main__":
    # 測試用
    # daily_trace()
    t = TPEX_manager()
    t.download_get('114/07/16')