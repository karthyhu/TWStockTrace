import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import json
import twstock
import datetime
import requests
import os
import time

app = dash.Dash(__name__)

def send_discord_category_notification(treemap_df):
    """發送股票群組漲跌幅資訊到 Discord"""
    try:
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            print("Discord webhook URL not found. Skipping notification.")
            return
        # 計算各類別平均漲跌幅與數量
        category_stats = treemap_df.groupby('category')['realtime_change'].agg(['mean', 'count']).round(1)
        category_stats = category_stats.sort_values('mean', ascending=False)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        embed = {"title": f"📊 台股產業類股漲跌幅 - {current_time}", "color": 0x00ff00, "fields": []}
        text = ""
        for cat, row in category_stats.iterrows():
            mean = row['mean']; cnt = int(row['count'])
            emoji = "🔴" if mean > 0 else "🟢" if mean < 0 else "🟡"
            text += f"{emoji} **{cat}** ({cnt}檔): {mean:+.2f}%\n"
        embed['fields'].append({"name": "產業類股漲跌幅", "value": text, "inline": False})
        payload = {"embeds": [embed]}
        resp = requests.post(webhook_url, json=payload)
        if resp.status_code == 204:
            print("Discord notification sent successfully!")
        else:
            print(f"Failed to send Discord notification. Status code: {resp.status_code}")
    except Exception as e:
        print(f"Error sending Discord notification: {e}")

def get_stock_info(past_json_data_twse, past_json_data_tpex, company_json_data_twse, company_json_data_tpex, target_code):
    """根據 Code 找到 ClosingPrice 和 Name"""
    # 先搜尋證交所資料
    for record in past_json_data_twse:
        if record['Code'] == target_code:
            for company_record in company_json_data_twse:
                if company_record['公司代號'] == target_code:
                    issue_shares = company_record['已發行普通股數或TDR原股發行股數']
            return {
                'last_close_price': record['ClosingPrice'],
                'stock_name': record['Name'], #證交所股票顯示名稱
                'stock_type': 'TWSE',
                'issue_shares': float(issue_shares)
            }

    # 如果在證交所找不到，再搜尋上櫃資料
    for record in past_json_data_tpex:
        if record['SecuritiesCompanyCode'] == target_code:
            for company_record in company_json_data_tpex:
                if company_record['SecuritiesCompanyCode'] == target_code:
                    issue_shares = company_record['IssueShares']
            return {
                'last_close_price': record['Close'],
                'stock_name': record['CompanyName'], #上櫃股票顯示名稱
                'stock_type': 'TPEx',
                'issue_shares': float(issue_shares)
            }
        
    print(f"找不到股票代號：{target_code}")
    return None  # 如果找不到，回傳 None

def downlod_stock_company_data():
    
    twse_company_file_path = 't187ap03_L.json'  # 上市公司資料
    tpex_company_file_path = 'mopsfin_t187ap03_O.json'  # 上櫃公司資料

    # 判斷上市公司資料檔案是否已存在
    if not os.path.exists(twse_company_file_path):
        url = 'https://openapi.twse.com.tw/v1/opendata/t187ap03_L'
        res = requests.get(url)

        if res.status_code == 200:
            jsondata = res.json()
            with open(twse_company_file_path, 'w', encoding='utf-8') as f:
                json.dump(jsondata, f, ensure_ascii=False, indent=4)
            print(f"JSON 檔案已成功儲存為 '{twse_company_file_path}'")
        else:
            print(f"TWSE 公司資料無法下載，HTTP 狀態碼: {res.status_code}")
    else:
        print(f"檔案 '{twse_company_file_path}' 已存在，跳過下載。")

    # 判斷上櫃公司資料檔案是否已存在
    if not os.path.exists(tpex_company_file_path):
        url = 'https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O'
        res = requests.get(url)

        if res.status_code == 200:
            jsondata = res.json()
            with open(tpex_company_file_path, 'w', encoding='utf-8') as f:
                json.dump(jsondata, f, ensure_ascii=False, indent=4)
            print(f"JSON 檔案已成功儲存為 '{tpex_company_file_path}'")
        else:
            print(f"TPEX 公司資料無法下載，HTTP 狀態碼: {res.status_code}")
    else:
        print(f"檔案 '{tpex_company_file_path}' 已存在，跳過下載。")
        
def downlod_stock_data():
    
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
        
# 載入初始資料
def load_initial_data():
    
    downlod_stock_data()
    downlod_stock_company_data()
    
    analysis_json_path = './stock_data.json'

    past_day_json_path_twse = './STOCK_DAY_ALL.json'
    past_day_json_path_tpex = './tpex_mainboard_daily_close_quotes.json'
    company_data_json_path_twse = './t187ap03_L.json'
    company_data_json_path_tpex = './mopsfin_t187ap03_O.json'

    with open(analysis_json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    with open(past_day_json_path_twse, 'r', encoding='utf-8') as f:
        past_json_data_twse = json.load(f)
    with open(past_day_json_path_tpex, 'r', encoding='utf-8') as f:
        past_json_data_tpex = json.load(f)
    with open(company_data_json_path_twse, 'r', encoding='utf-8') as f:
        company_json_data_twse = json.load(f)
    with open(company_data_json_path_tpex, 'r', encoding='utf-8') as f:
        company_json_data_tpex = json.load(f)
        
    stocks_info_list = {}
    for category, stocks_info in json_data['台股'].items():
        for stock_id, stock_info in stocks_info.items():
            
            last_stock_info = get_stock_info(past_json_data_twse, past_json_data_tpex, company_json_data_twse, company_json_data_tpex, stock_id)

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
                        'issue_shares' : last_stock_info['issue_shares'],
                        'last_day_price' : last_stock_price,
                        'realtime_price' : float('nan'),
                        'realtime_change' : float('nan')
                    }
    
    return pd.DataFrame(stocks_info_list)

# 更新即時股價資料
def update_realtime_data(stocks_df):
    
    # track_stock_realtime_data = twstock.realtime.get(list(stocks_df.columns))
    try:
        track_stock_realtime_data = twstock.realtime.get(list(stocks_df.columns))
        time.sleep(5)
    except (KeyError, ValueError):
        print("部分即時資料缺少 timestamp，略過")
        track_stock_realtime_data = {}

    for stock_id in stocks_df.columns:
        if stock_id in track_stock_realtime_data and 'realtime' in track_stock_realtime_data[stock_id]:
            if track_stock_realtime_data[stock_id]['success']:
                
                realtime_data = track_stock_realtime_data[stock_id]['realtime']
                
                #如果沒有最新成交價 就用買價(bid)一檔代替
                if realtime_data['latest_trade_price'] == '-':
                    current_price = float(realtime_data['best_bid_price'][0]) # 最佳買價一檔
                else:
                    current_price = float(realtime_data['latest_trade_price'])
                
                last_day_price = stocks_df.loc['last_day_price' , stock_id]
                current_change_percent = round((current_price - last_day_price) / last_day_price * 100 , 1)
                
                stocks_df.loc['realtime_price' , stock_id] = current_price
                stocks_df.loc['realtime_change' , stock_id] = current_change_percent
    
    return stocks_df

# 載入初始股票資料
initial_stocks_df = load_initial_data()

app.layout = html.Div([
    html.H1("Taiwan Stock Realtime Heatmap", style={'textAlign': 'center', 'marginBottom': 30}),
    html.Div([
        html.Label('Display Mode：', style={'marginRight': '10px'}),
        dcc.RadioItems(
            options=[
                {'label': 'Normal Display', 'value': 'equal'},
                {'label': 'Market Cap Display', 'value': 'market'}
            ],
            id='size-mode',
            value='equal',
            labelStyle={'display': 'inline-block', 'marginRight': '10px'}
        )
    ], style={'textAlign': 'center', 'marginBottom': 20}),
    html.Div([
        html.Span("Last Update Time: ", style={'fontWeight': 'bold'}),
        html.Span(id='last-update-time', style={'color': 'blue'})
    ], style={'textAlign': 'center', 'marginBottom': 20}),
    dcc.Graph(id='live-treemap'),
    dcc.Interval(id='interval-update', interval=5000, n_intervals=0),
    # 顯示點擊股票後的連結，開啟新分頁
    html.Div(id='stock-link-container', style={'textAlign': 'center', 'marginTop': 20})
])

@app.callback(
    [Output('live-treemap', 'figure'),
     Output('last-update-time', 'children')],
    [Input('interval-update', 'n_intervals'),
     Input('size-mode', 'value')]
)
# def update_treemap(n):
def update_treemap(n, size_mode):
    # 更新即時股價
    updated_stocks_df = update_realtime_data(initial_stocks_df.copy())

    # 準備 treemap 資料
    treemap_data = []
    df_transposed = updated_stocks_df.T

    for stock_id, row in df_transposed.iterrows():
        # 計算市值
        market_value = row['issue_shares'] * row['realtime_price'] if not pd.isna(row['realtime_price']) else 0
        # 為每個股票的每個類別建立一筆資料
        for category in row['category']:
            treemap_data.append({
                'stock_meta': 'Taiwan Stock',
                'stock_id': stock_id,
                'stock_name': row['stock_name'],
                'category': category,
                'realtime_change': row['realtime_change'],
                'realtime_price': row['realtime_price'],
                'last_day_price': row['last_day_price'],
                'stock_type': row['stock_type'],
                'market_value': market_value
            })

    # 轉換成 DataFrame
    treemap_df = pd.DataFrame(treemap_data)

    # 每2次更新（即10秒）發送 Discord 群組漲跌幅通知
    # if n and n % 2 == 0:
        # send_discord_category_notification(treemap_df)

    # 計算族群加總市值
    category_market_values = treemap_df.groupby('category')['market_value'].transform('sum')

    # 根據市值調整比例
    treemap_df['proportion'] = treemap_df['market_value'] / category_market_values

    # 根據顯示模式決定區塊大小
    if size_mode == 'equal':
        values = [1] * len(treemap_df)
    else:
        # 市值大小模式，分 5 區間
        def map_size(mv):
            # 區間對應大小
            if mv > 6e11:      # 6000e 以上
                return 5
            elif mv > 1e11:    # 1000e 以上
                return 4
            elif mv > 5e10:    # 500e 以上
                return 3
            elif mv > 1e10:    # 100e 以上
                return 2
            else:              # 100e 以下
                return 1
        values = treemap_df['market_value'].apply(map_size).tolist()
    
    # 建立 treemap
    fig = px.treemap(
        treemap_df,
        path=['stock_meta', 'category', 'stock_name'],
        values=values,
        color='realtime_change',
        color_continuous_scale='RdYlGn_r',
        title='',
        range_color=[-10, 10],
        color_continuous_midpoint=0,
        hover_data=['stock_id', 'realtime_price', 'last_day_price', 'stock_type', 'market_value'],
        custom_data=['stock_name', 'stock_id', 'realtime_price', 'realtime_change', 'stock_type']
    )

    fig.update_traces(marker=dict(cornerradius=3), textposition='middle center', texttemplate="%{label} %{customdata[1]}<br>%{customdata[2]}<br>%{customdata[3]:.2f}%")
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',  # 透明背景
        margin=dict(t=50, l=10, r=10, b=10),
        height=800,
        coloraxis_colorbar_tickformat='.2f'
    )

    # 取得當前時間
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return fig, current_time

# 點擊 treemap 顯示外部連結
@app.callback(
    Output('stock-link-container', 'children'),
    Input('live-treemap', 'clickData')
)
def display_stock_link(clickData):
    if not clickData or not clickData['points']:
        return ''
    point = clickData['points'][0]
    stock_id = point['customdata'][1]
    # 取得 stock_type，選擇 TradingView 前綴
    stock_type = point['customdata'][4]
    prefix = 'TWSE' if stock_type == 'TWSE' else 'TPEX'
    url_goodinfo = f"https://goodinfo.tw/tw/ShowK_Chart.asp?STOCK_ID={stock_id}"
    url_wantgoo = f"https://www.wantgoo.com/stock/{stock_id}/technical-chart"
    url_tradingView = f"https://tw.tradingview.com/chart/?symbol={prefix}%3A{stock_id}"
    
    return html.Div([
        html.A(f"Goodinfo - {stock_id}", href=url_goodinfo, target="_blank", style={'fontSize': '18px', 'color': 'blue', 'marginRight': '20px'}),
        html.A(f"Wantgoo - {stock_id}", href=url_wantgoo, target="_blank", style={'fontSize': '18px', 'color': 'green' , 'marginRight': '20px'}),
        html.A(f"TradingView - {stock_id}", href=url_tradingView, target="_blank", style={'fontSize': '18px', 'color': 'black'})
    ], style={'textAlign': 'center', 'marginTop': '10px'})

if __name__ == '__main__':
    app.run(debug=True)
