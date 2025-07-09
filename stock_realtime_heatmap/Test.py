import plotly.express as px
import numpy as np
import json
import pandas as pd
import twstock
import datetime
import pprint

"""讀取 JSON 檔案並返回股票資料"""
def read_stock_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

"""一次性獲取指定股票的開、高、低、收價格及成交量"""
def fetch_stock_prices(stock_id):
    try:
        stock = twstock.Stock(stock_id)
        today = pd.Timestamp.today()
        stock.fetch(today.year, today.month)

        if len(stock.price) > 0:
            return {
                '開': stock.open[-1] if len(stock.open) > 0 else None,
                '高': stock.high[-1] if len(stock.high) > 0 else None,
                '低': stock.low[-1] if len(stock.low) > 0 else None,
                '收': stock.close[-1] if len(stock.close) > 0 else None,
                '價差': stock.change[-1] if len(stock.change) > 0 else None,
                '成交股數': stock.capacity[-1] if len(stock.capacity) > 0 else None #成交股數 已驗證 https://www.twse.com.tw/zh/trading/historical/stock-day.html
            }
        return None
    except Exception as e:
        print(f"無法獲取 {stock_id} 的價格資訊: {e}")
        return None

def fetch_stock_prices_realtime(stock_id):
    """獲取即時股票價格，僅回傳漲跌幅與當前價格"""
    try:
        stock = twstock.realtime.get(stock_id)
        if stock and 'realtime' in stock and stock['success']:
            return {
                '收': stock['realtime']['latest_trade_price'],
                '漲跌幅': stock['realtime']['change']
            }
        return None
    except Exception as e:
        print(f"無法獲取 {stock_id} 的即時價格資訊: {e}")
        return None

"""更新股票資料，新增漲跌幅和成交量"""
def calculate_stock_metrics(stocks):
    for stock in stocks:
        stock_id = stock['股票代號']
        try:
            stock_info = twstock.Stock(stock_id)
            today = pd.Timestamp.today()
            stock_info.fetch(today.year, today.month)

            if len(stock_info.price) > 1:
                yesterday_close = stock_info.price[-2]
                today_close = stock_info.price[-1]
                stock['漲跌幅'] = ((today_close - yesterday_close) / yesterday_close) * 100
            else:
                stock['漲跌幅'] = None

            stock['成交量'] = stock_info.capacity[-1] if len(stock_info.capacity) > 0 else None
        except Exception as e:
            print(f"無法獲取 {stock_id} 的漲跌幅或成交量: {e}")
    return stocks

"""將股票資料轉換為 DataFrame"""
def create_dataframe(stocks):
    return pd.DataFrame(stocks)

"""繪製熱力圖"""
def plot_treemap(dataframe):
    fig = px.treemap(
        dataframe,
        path=['群組', '股票名稱'],
        values=[1] * len(dataframe),  # 設定所有值為 1，確保大小相等
        color='漲跌幅',
        color_continuous_scale='balance',
        title='台股今日漲跌幅熱力圖',
        range_color=[-10, 10],
        color_continuous_midpoint=0
    )
    fig.show()

# 更新 JSON 檔案中的數值，包括價格的開、高、低、收，並將漲跌幅保存為小數點後兩位
def update_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        stock_data = json.load(f)

    for category, stocks_info in stock_data['台股'].items():
        for stock_id, stock_info in stocks_info.items():
            try:
                stock = twstock.Stock(stock_id)
                today = pd.Timestamp.today()
                stock.fetch(today.year, today.month)

                if len(stock.price) > 1:
                    yesterday_close = stock.price[-2]
                    today_close = stock.price[-1]
                    stock_info['漲幅'] = round(((today_close - yesterday_close) / yesterday_close) * 100, 2)
                else:
                    stock_info['漲幅'] = None

                stock_info['成交量'] = stock.capacity[-1] if len(stock.capacity) > 0 else None
                stock_info['價格']['開'] = stock.open[-1] if len(stock.open) > 0 else None
                stock_info['價格']['高'] = stock.high[-1] if len(stock.high) > 0 else None
                stock_info['價格']['低'] = stock.low[-1] if len(stock.low) > 0 else None
                stock_info['價格']['收'] = stock.price[-1] if len(stock.price) > 0 else None
            except Exception as e:
                print(f"無法更新 {stock_id} 的數值: {e}")

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(stock_data, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    
    # 讀取股票資料
    json_path = './stock_data.json'
    stock_data = read_stock_data(json_path)

    # 整理股票資料
    # stocks = []
    # for category, stocks_info in stock_data['台股'].items():
    #     for stock_id, stock_info in stocks_info.items():
    #         trade_info = fetch_stock_prices(stock_id)
    #         stocks.append({
    #             '群組': category,
    #             '股票代號': stock_id,
    #             '股票名稱': stock_info['股票'],
    #             '交易資訊': trade_info
    #         })
    stocks = []
    for category, stocks_info in stock_data['台股'].items():
        for stock_id, stock_info in stocks_info.items():
            trade_info = fetch_stock_prices_realtime(stock_id)
            
            
            
            
    # 計算漲跌幅需要知道T-1交易日收盤價
    stocks = calculate_stock_metrics(stocks)

    # 轉換為 DataFrame
    stocks_df = create_dataframe(stocks)
    print(stocks_df)

    # 繪製熱力圖
    plot_treemap(stocks_df)

    # 更新 JSON 檔案
    # update_json(json_path)