import json
import requests
import os
import time
import random
import re
import itertools
import timenormalyize as tn



data_list = {
    '02':'食品工業',
    '03':'塑膠工業',
    '04':'紡織纖維',
    '05':'電機機械',
    '06':'電器電纜',
    '21':'化學工業',
    '08':'玻璃陶瓷',
    '10':'鋼鐵工業',
    '11':'橡膠工業',
    '14':'建材營造',
    '15':'航運業',
    '16':'觀光餐旅',
    '17':'金融業',
    '20':'其他',
    '22':'生技醫療類',
    '23':'油電燃氣類',
    '24':'半導體類',
    '25':'電腦及週邊類',
    '26':'光電業類',
    '27':'通信網路類',
    '28':'電子零組件類',
    '29':'電子通路類',
    '30':'資訊服務類',
    '31':'其他電子類',
    '32':'文化創意業',
    '33':'農業科技業',
    '35':'綠能環保類',
    '36':'數位雲端類',
    '37':'運動休閒類',
    '38':'居家生活類',
    '80':'管理股票',
    'AA':'受益證券',
    'EE':'上櫃ETF',
    'EN':'指數投資證券(ETN)',
    'TD':'台灣存託憑證(TDR)',
    'WW':'認購售權證',
    'GG':'認股權憑證',
    'BC':'牛熊證(不含展延型牛熊證)',
    'XY':'展延型牛熊證',
    'EW':'所有證券(不含權證、牛熊證)',
    'AL':'所有證券',
    'OR':'委託及成交資訊(16:05提供)'
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
    def __init__(self, daily_data_dir='./raw_stock_data/daily/tpex'):
        if not os.path.exists(daily_data_dir):
            os.makedirs(daily_data_dir)
        self.daily_data_dir = daily_data_dir
        
        # '代號', '名稱', '收盤', '漲跌', '開盤', '最高', '最低', '成交股數', '成交金額(元)', '漲幅%'
        self.fill_list = ['Code', 'Name', 'ClosingPrice', 'Change', 'OpeningPrice', 'HighestPrice', 'LowestPrice', 'TradeVolume', 'TradeValue', 'Range']

        self.session = requests.Session()
        self.session.headers.update(headers)
        try:
            self.session.get('https://www.tpex.org.tw/zh-tw/mainboard/trading/info/pricing.html', timeout=10)
            print("✅ 會話已建立，Cookie 已自動儲存。")
            time.sleep(random.uniform(0.2, 0.5)) # 模擬短暫停留
        except requests.exceptions.RequestException as e:
            print(f"❌ 步驟一失敗，無法建立會話: {e}")

    def save_file(self, data, filename:str = 'Noname'):
        with open(f'{self.daily_data_dir}/{filename}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)

    def safe_float(self, value):
        try:
          return float(value)
        except ValueError:
          return 0.0

    def safe_int(self, value):
        try:
          return int(value)
        except ValueError:
          return 0

    def gan_url(self, date: str, type: str = 'AL') -> str:
        # print(f"正在生成 URL，日期: {date}, 類型: {type}")
        sdate = date.split('/')
        url = f'https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={sdate[0]}%2F{sdate[1]}%2F{sdate[2]}&type={type}&id=&response=json&order=0&sort=asc'
        # print(f"URL: {url}")
        return url


    def _process_stock_item(self, item):
        """處理單個股票項目數據的共用方法"""
        # 只取前9個欄位
        item = item[:9]
        # 清理數據，移除加號和逗號
        item = [re.sub(r'[+,]', '', str(field)) for field in item]
        
        # 計算漲幅
        closeprice = self.safe_float(item[self.fill_list.index('ClosingPrice')])
        change = self.safe_float(item[self.fill_list.index('Change')])
        range_percent = (change / closeprice * 100) if closeprice != 0 else 0.0
        
        # 添加漲幅到項目末尾
        item.append(str(round(range_percent, 3)))

        return item

    def _fetch_and_parse_data(self, date, type_code='AL'):
        """獲取並解析股票數據的共用方法"""
        try:
            res = self.session.get(self.gan_url(date, type_code), timeout=10)
            data = json.loads(res.text)
            return data['tables'][0]
        except Exception as e:
            print(f'Error fetching data for {type_code}: {e}')
            return None

    def download_get_once(self, date: str = '114/07/14'):
        date = tn.normalize_date(date, "ROC", "/")
        """下載單一類型(AL)的股票數據"""
        table_data = self._fetch_and_parse_data(date)
        
        if not table_data:
            print(f'Failed to fetch data for date {date}')
            return None
            
        try:
            totaldata = {
                'date': table_data['date'].replace('/', ''),
                'fields': self.fill_list.copy(),
                'data': {}
            }
            
            for item in table_data['data']:
                processed_item = self._process_stock_item(item)
                totaldata['data'][processed_item[0]] = processed_item
                
            self.save_file(totaldata, totaldata['date'])
            print(f"✅ Successfully downloaded {len(totaldata['data'])} records for {totaldata['date']}")
            return totaldata
            
        except Exception as e:
            print(f'Error processing data: {e}')
            return False

    def download_get_loop(self, date: str, max_types: int = None):
        if max_types is None:
            max_types = list(data_list.keys()).index('TD') + 1
    
        """下載多種類型股票數據的循環方法"""
        totaldata = {
            'date': '',
            'fields': self.fill_list.copy(),
            'data': {}
        }
        total_count = 0
        
        # print(f"Starting download for {max_types} stock types...")
        
        for key, value in itertools.islice(data_list.items(), max_types):
            print(f'.', end=' ')
            # print(f"正在處理類型: {key} - {value}")
            
            table_data = self._fetch_and_parse_data(date, key)
            
            if table_data:
                try:
                    # 設定日期（只需要設定一次）
                    if not totaldata['date']:
                        totaldata['date'] = table_data['date'].replace('/', '')
                    
                    # 處理該類型的所有股票數據
                    for item in table_data['data']:
                        processed_item = self._process_stock_item(item)
                        totaldata['data'][processed_item[0]] = processed_item
                    
                    total_count += len(table_data['data'])                    
                except Exception as e:
                    print(f'❌ Error processing {key}: {e}, at {key}, {value}')
                    return False
            else:
                print('❌ Failed to fetch')
                
            # 短暫延遲避免過於頻繁的請求
            time.sleep(random.uniform(0.1, 0.3))
        print(f'done, datacount = {total_count}')
        # print(f"\n📊 Total records downloaded: {total_count}")
        # print(f"📊 Unique stocks processed: {len(totaldata['data'])}")
        
        if totaldata['data']:
            self.save_file(totaldata, totaldata['date'])
            return totaldata
        else:
            print("No data was successfully downloaded")
            return None

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
        totaldata['fields'] = ['代號', '名稱', '收盤 ', '漲跌', '開盤 ', '最高 ', '最低', '成交股數  ', ' 成交金額(元)', ' 成交筆數 ', '最後買價', '最後買量<br>(張數)', '最後賣價', '最後賣量<br>(張數)', '發行股數 ', '次日漲停價 ', '次日跌停價', '漲幅']
        totaldata['data'] = []
        totalCount = 0
        for key, value in data_list.items():
            payload['type'] = key
            try:
                response = requests.post(url, headers=headers, data=payload)
                data = response.json()

                # closeprice = float(data['tables'][0][2])
                # change = float(data['tables'][0][3])
                # range = (change / closeprice * 100) if closeprice != 0 else 0
                # data['tables'][0]['data'].append(range)
                # totaldata['data'].extend(data['tables'][0]['data'])
                # totalCount += int(data['tables'][0]['totalCount'])
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


def daily_trace(date: str = None):
    # 取得今天日期
    if date is None:
        date = tn.get_current_date("ROC", "")
    
    date = tn.normalize_date(date, "ROC", "")
        
    # 儲存今天的資料
    trace_manager = TPEX_manager()
    data = trace_manager.download_get_once(date)
    if data:
        trace_manager.save_file(data, 'today')
        print(f"{date} 的資料已成功儲存。")
    trace_manager.genpassdayfile(date, 2)


if __name__ == "__main__":
    # 測試用
    # daily_trace('114/07/17')
    t = TPEX_manager()
    # t.download_get_loop('114/07/14')
    # t.download_get_once('114/07/15')
    # t.genpassdayfile('114/08/05', 2)

