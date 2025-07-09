from flask import Flask, jsonify, send_from_directory
import json
import pandas as pd
import twstock
import datetime
import os

app = Flask(__name__)

# 簡單的跨域處理
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

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

@app.route('/')
def index():
    return send_from_directory('.', 'stock_heatmap.html')

@app.route('/style.css')
def serve_css():
    return send_from_directory('.', 'style.css')

@app.route('/script.js')
def serve_js():
    return send_from_directory('.', 'script.js')

@app.route('/api/stock_data')
def get_stock_data():
    try:
        # 載入資料
        analysis_json_path = './stock_data.json'
        past_day_json_path_twse = './json_file/STOCK_DAY_0704.json'
        past_day_json_path_tpex = './json_file/tpex_mainboard_daily_close_quotes_0704.json'

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
                
                if last_stock_info != None:
                    if last_stock_info['last_close_price'] == "":
                        last_stock_price = float('nan')
                    else:
                        last_stock_price = float(last_stock_info['last_close_price'])
                    
                    # 如果股票已存在，則將新的 category 加入到現有的 category 中
                    if stock_id in stocks_info_list:
                        if isinstance(stocks_info_list[stock_id]['category'], str):
                            stocks_info_list[stock_id]['category'] = [stocks_info_list[stock_id]['category']]
                        if category not in stocks_info_list[stock_id]['category']:
                            stocks_info_list[stock_id]['category'].append(category)
                    else:
                        stocks_info_list[stock_id] = {
                            'category': [category],
                            'stock_type': last_stock_info['stock_type'],
                            'stock_name': last_stock_info['stock_name'],
                            'last_day_price': last_stock_price,
                            'realtime_price': float('nan'),
                            'realtime_change': float('nan')
                        }

        # 獲取即時資料
        stocks_df = pd.DataFrame(stocks_info_list)
        track_stock_realtime_data = twstock.realtime.get(list(stocks_df.columns))

        for stock_id in stocks_df.columns:
            if stock_id in track_stock_realtime_data and 'realtime' in track_stock_realtime_data[stock_id]:
                if track_stock_realtime_data[stock_id]['success']:
                    realtime_data = track_stock_realtime_data[stock_id]['realtime']
                    
                    if realtime_data['latest_trade_price'] == '-':
                        current_price = float(realtime_data['best_bid_price'][0])
                    else:
                        current_price = float(realtime_data['latest_trade_price'])
                    
                    last_day_price = stocks_df.loc['last_day_price', stock_id]
                    current_change_percent = round((current_price - last_day_price) / last_day_price * 100, 2)
                    
                    stocks_df.loc['realtime_price', stock_id] = current_price
                    stocks_df.loc['realtime_change', stock_id] = current_change_percent

        # 整理資料格式
        df_transposed = stocks_df.T
        result = {}
        
        # 收集所有獨特的 category
        all_categories = set()
        for categories_list in df_transposed['category']:
            all_categories.update(categories_list)
        
        # 為每個 category 建立股票列表
        for category in all_categories:
            result[category] = []
            category_stocks = df_transposed[df_transposed['category'].apply(lambda x: category in x)]
            
            for stock_id, row in category_stocks.iterrows():
                result[category].append({
                    'stock_id': stock_id,
                    'stock_name': row['stock_name'],
                    'realtime_change': row['realtime_change'] if not pd.isna(row['realtime_change']) else 0,
                    'realtime_price': row['realtime_price'] if not pd.isna(row['realtime_price']) else 0,
                    'last_day_price': row['last_day_price'] if not pd.isna(row['last_day_price']) else 0,
                    'stock_type': row['stock_type']
                })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
