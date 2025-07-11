import plotly.express as px
import plotly.graph_objects as go
import json
import pandas as pd
import twstock
import datetime
import pprint
import time
import requests  
import os

#1. 如何自動獲取上個交易日的 .json (或任意某天的)

def get_stock_info(past_json_data_twse, past_json_data_tpex, target_code):
    """根據 Code 找到 ClosingPrice 和 Name"""
    # 先搜尋證交所資料
    for record in past_json_data_twse:
        if record['Code'] == target_code:
            return {
                'last_close_price': record['ClosingPrice'],
                'stock_name': record['Name'], #證交所股票顯示名稱
                'stock_type': 'TWSE'
            }
    # 如果在證交所找不到，再搜尋上櫃資料
    for record in past_json_data_tpex:
        if record['SecuritiesCompanyCode'] == target_code:
            return {
                'last_close_price': record['Close'],
                'stock_name': record['CompanyName'], #上櫃股票顯示名稱
                'stock_type': 'TPEx'
            }
    return None  # 如果找不到，回傳 None

def DownlodStockData():
    twse_file_path = 'STOCK_DAY_ALL.json'
    tpex_file_path = 'tpex_mainboard_daily_close_quotes.json'

    # 判斷 TWSE 檔案是否已存在
    if not os.path.exists(twse_file_path):
        url = 'https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'
        res = requests.get(url)

        if res.status_code == 200:  # 確保請求成功
            jsondata = res.json()  # 將回應轉換為 JSON 格式
            with open(twse_file_path, 'w', encoding='utf-8') as f:
                json.dump(jsondata, f, ensure_ascii=False, indent=4)  # 儲存 JSON 檔案
            print(f"JSON 檔案已成功儲存為 '{twse_file_path}'")
        else:
            print(f"TWSE 無法下載資料，HTTP 狀態碼: {res.status_code}")
    else:
        print(f"檔案 '{twse_file_path}' 已存在，跳過下載。")

    # 判斷 TPEX 檔案是否已存在
    if not os.path.exists(tpex_file_path):
        url = 'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes'
        res = requests.get(url)

        if res.status_code == 200:  # 確保請求成功
            jsondata = res.json()  # 將回應轉換為 JSON 格式
            with open(tpex_file_path, 'w', encoding='utf-8') as f:
                json.dump(jsondata, f, ensure_ascii=False, indent=4)  # 儲存 JSON 檔案
            print(f"JSON 檔案已成功儲存為 '{tpex_file_path}'")
        else:
            print(f"TPEX 無法下載資料，HTTP 狀態碼: {res.status_code}")
    else:
        print(f"檔案 '{tpex_file_path}' 已存在，跳過下載。")
        

if __name__ == "__main__":
    
    DownlodStockData()
        
    analysis_json_path = './stock_data.json'
    past_day_json_path_twse = './STOCK_DAY_ALL.json'
    past_day_json_path_tpex = './tpex_mainboard_daily_close_quotes.json'

    with open(analysis_json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    with open(past_day_json_path_twse, 'r', encoding='utf-8') as f:
        past_json_data_twse = json.load(f)
    with open(past_day_json_path_tpex, 'r', encoding='utf-8') as f:
        past_json_data_tpex = json.load(f)

    stocks_info_list = {}
    for category, stocks_info in json_data['台股'].items():
        for stock_id, stock_info in stocks_info.items():
            
            last_stock_info = get_stock_info(past_json_data_twse, past_json_data_tpex, stock_id)
            # print(last_stock_info)

            if last_stock_info != None:
                if last_stock_info['last_close_price'] == "":
                    last_stock_price = float('nan')
                else:
                    last_stock_price = float(last_stock_info['last_close_price'])
                
                # 如果股票已存在，則將新的 category 加入到現有的 category 中
                if stock_id in stocks_info_list:
                    # 如果 category 是字串，先轉換成列表
                    if isinstance(stocks_info_list[stock_id]['category'], str):
                        stocks_info_list[stock_id]['category'] = [stocks_info_list[stock_id]['category']]
                    # 將新的 category 加入到列表中（如果不重複）
                    if category not in stocks_info_list[stock_id]['category']:
                        stocks_info_list[stock_id]['category'].append(category)
                else:
                    # 新股票，直接建立資料
                    stocks_info_list[stock_id] = {
                        'category' : [category],  # 使用列表來儲存多個類別
                        'stock_type' : last_stock_info['stock_type'],
                        'stock_name' : last_stock_info['stock_name'],
                        'last_day_price' : last_stock_price,
                        'realtime_price' : float('nan'),
                        'realtime_change' : float('nan')
                    }
                print(f"Stock {stock_id}: {stocks_info_list[stock_id]}")
            else:
                print(f"找不到 Code {stock_id} 的過去資訊")
    
    stocks_df = pd.DataFrame(stocks_info_list)
    # print(stocks_df)
    
    while True:
        track_stock_realtime_data = twstock.realtime.get(list(stocks_df.columns))
        # pprint.pprint(track_stock_realtime_data)

        for stock_id in stocks_df.columns:
            if stock_id in track_stock_realtime_data and 'realtime' in track_stock_realtime_data[stock_id]:
                if track_stock_realtime_data[stock_id]['success']:
                    
                    realtime_data = track_stock_realtime_data[stock_id]['realtime']
                    
                    #如果沒有最新成交價 就用買價(bid)一檔代替
                    if realtime_data['latest_trade_price'] == '-':
                        # print(f"獲取 {stock_id} 的最新成交價失敗")
                        current_price = float(realtime_data['best_bid_price'][0]) # 最佳買價一檔
                    else:
                        current_price = float(realtime_data['latest_trade_price'])
                    
                    last_day_price = stocks_df.loc['last_day_price' , stock_id]
                    current_change_percent = round((current_price - last_day_price) / last_day_price * 100 , 2)
                    
                    
                    stocks_df.loc['realtime_price' , stock_id] = current_price
                    stocks_df.loc['realtime_change' , stock_id] = current_change_percent
                else:
                    print(f"獲取 {stock_id} 的即時價格失敗: {track_stock_realtime_data[stock_id]['rtmessage']}")
            else:
                print(f"無法獲取 {stock_id} 的即時價格資訊")


        # print 類別 *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        # 設定 pandas 顯示選項以完整顯示所有資料
        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_rows', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)

        # 按照 category 分組顯示
        df_transposed = stocks_df.T

        # 收集所有獨特的 category
        all_categories = set()
        for categories_list in df_transposed['category']:
            all_categories.update(categories_list)

        # 為每個 category 顯示相關股票
        for category in sorted(all_categories):
            print(f"\n=== {category} ===")
            # 篩選包含該 category 的股票
            category_stocks = df_transposed[df_transposed['category'].apply(lambda x: category in x)]
            print(category_stocks)
        # print 類別 *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-

        # 每 5 秒執行一次
        time.sleep(5)

        

