import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
import json
import twstock
import datetime
import requests
import os
import time
import plotly.io as pio
from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging.models import TextMessage, PushMessageRequest
import dash_daq as daq


# Global variables
g_notified_status = {}
g_last_notification_time = {}
g_stock_category = []
g_category_json = {}
g_track_stock_realtime_data = {}

def send_line_message_v3(message, channel_access_token, user_id):
    """使用 Line Messaging API v3 發送訊息"""
    try:
        messaging_api = MessagingApi(channel_access_token)
        text_message = TextMessage(text=message)
        push_message_request = PushMessageRequest(to=user_id, messages=[text_message])
        messaging_api.push_message(push_message_request)
        print("Line message sent successfully!")
    except Exception as e:
        print(f"Failed to send Line message: {e}")
        
def send_discord_category_notification(treemap_df, fig):
    """發送股票群組漲跌幅資訊到 Discord"""
    global g_notified_status, g_last_notification_time
    
    COOLDOWN_SECONDS = 60  # 1分鐘冷卻
    BUFFER_THRESHOLD = 0.8  # 緩衝區 0.8%
    print(f"[DEBUG] Current time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            print("Discord webhook URL not found. Skipping notification.")
            return
    
        # 計算各類別平均漲跌幅與數量
        category_stats = treemap_df.groupby('category')['realtime_change'].agg(['mean', 'count']).round(2)
        category_stats = category_stats.sort_values('mean', ascending=False)
        # print("Category stats calculated:", category_stats)
        
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_timestamp = time.time()
        
        embed = {"title": f"📊 台股產業類股漲跌幅 - {current_time}", "color": 0x00ff00, "fields": []}
        text = ""

        # 在 send_discord_category_notification 中加入顏色控制
        for cat, row in category_stats.iterrows():
            mean = row['mean']
            cnt = int(row['count'])

            # 設定顏色
            if cat in ['上市大盤', '上櫃大盤']:
                color_code = '\033[37m'  # 白色
            elif mean > 0:
                color_code = '\033[31m'  # 紅色
            else:
                color_code = '\033[32m'  # 綠色

            # 檢查冷卻時間
            if cat in g_last_notification_time:
                if current_timestamp - g_last_notification_time[cat] < COOLDOWN_SECONDS:
                    continue
            
            # 獲取前次數據
            previous_data = g_notified_status.get(cat, {"status": "neutral", "last_mean": 0})
            previous_status = previous_data["status"]
            previous_mean = previous_data["last_mean"]
            
            # 緩衝區檢查
            if abs(mean - previous_mean) < BUFFER_THRESHOLD:
                print(f"{color_code}[DEBUG] Skipping notification for {cat}: mean={mean}, last_mean={previous_mean}\033[0m")
                continue

            # 判斷是否需要通知
            if -3.5 < mean < 3.5:
                print(f"{color_code}[DEBUG] Neutral category {cat}: mean={mean}, last_mean={previous_mean}\033[0m")
                g_notified_status[cat] = {"status": "neutral", "last_mean": mean}
                continue

            # 判斷狀態變化
            if mean >= 6.5:
                current_status = "high_positive"
                emoji = "🚀🚀"
            elif mean >= 3.5:
                current_status = "positive"
                emoji = "🚀"
            elif mean <= -6.5:
                current_status = "high_negative"
                emoji = "💥💥"
            elif mean <= -3.5:
                current_status = "negative"
                emoji = "💥"
            else:
                current_status = "neutral"

            print(f"{color_code}[DEBUG] Notification check for {cat}: mean={mean}, last_mean={previous_mean}, status={current_status}\033[0m")

            # 僅在狀態變化時通知
            if current_status != previous_status:
                # 收集族群內的股票及漲幅資訊
                stock_details = treemap_df[treemap_df['category'] == cat][['stock_name', 'realtime_change']]
                stock_info = "\n".join([f"{row['stock_name']} ({row['realtime_change']:+.2f}%)" for _, row in stock_details.iterrows()])

                text += f"{emoji} **{cat}** ({cnt}檔): {mean:+.2f}%\n{stock_info}\n"

                # 更新記錄
                g_notified_status[cat] = {"status": current_status, "last_mean": mean}
                g_last_notification_time[cat] = current_timestamp
            else:
                # 更新漲幅記錄但不通知
                g_notified_status[cat]["last_mean"] = mean

        if text:
            embed['fields'].append({"name": "", "value": text, "inline": False})
            payload = {"embeds": [embed]}
            resp = requests.post(webhook_url, json=payload)
            
            if resp.status_code == 204:
                print("Discord notification sent successfully!")

                # 發送圖片和文字
                heatmap_image_path = "heatmap.png"
                pio.write_image(fig, heatmap_image_path, format="png", width=1920, height=1080)

                with open(heatmap_image_path, "rb") as f:
                    files = {"file": f}
                    resp = requests.post(webhook_url, files=files)
                if resp.status_code == 200:
                    print("Discord heatmap image sent successfully!")
                else:
                    print(f"Failed to send Discord heatmap image. Status code: {resp.status_code}, Response: {resp.text}")
            else:
                print(f"Failed to send Discord notification. Status code: {resp.status_code}, Response: {resp.text}")
                
            # if text:
            #     send_line_message_v3(f"📊 台股產業類股漲跌幅通知\n{text}", channel_access_token, user_id)
            # else:
            #     print("No text message to send.")
                
    except Exception as e:
        print(f"Error sending Discord notification: {e}")

def get_stock_info(past_json_data_twse, past_json_data_tpex, company_json_data_twse, company_json_data_tpex, target_code):
    
    
    """根據 Code 找到 ClosingPrice 和 Name"""
    # 先搜尋證交所資料
    for record in past_json_data_twse:
        if record['Code'] == target_code:
            issue_shares = 0
            for company_record in company_json_data_twse:
                if target_code == '0050':
                    issue_shares = 13234500000
                    break
                elif target_code == '0051':
                    issue_shares = 26000000
                    break
                if company_record['公司代號'] == target_code:
                    issue_shares = company_record['已發行普通股數或TDR原股發行股數']
                    break  # 找到後立即跳出迴圈
            return {
                'last_close_price': record['ClosingPrice'],
                'stock_name': record['Name'], 
                'stock_type': 'TWSE',
                'issue_shares': float(issue_shares)
            }

    # 如果在證交所找不到，再搜尋上櫃資料
    for record in past_json_data_tpex:
        if record['SecuritiesCompanyCode'] == target_code:
            issue_shares = 0
            for company_record in company_json_data_tpex:
                if target_code == '006201':
                    issue_shares = 18946000000 # 18946000 -> 18946000000 不然顯示不出來
                    break
                if company_record['SecuritiesCompanyCode'] == target_code:
                    issue_shares = company_record['IssueShares']
                    break
            return {
                'last_close_price': record['Close'],
                'stock_name': record['CompanyName'], #上櫃股票顯示名稱
                'stock_type': 'TPEx',
                'issue_shares': float(issue_shares)
            }
        
    print(f"找不到股票代號：{target_code}")
    return None  # 如果找不到，回傳 None

def downlod_stock_company_data():
    
    twse_company_file_path = './comp_data/t187ap03_L.json'  # 上市公司資料
    tpex_company_file_path = './comp_data/mopsfin_t187ap03_O.json'  # 上櫃公司資料

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
    # time.sleep(1)
    # downlod_stock_company_data()
    
    analysis_json_path = './my_stock_category.json'
    past_day_json_path_twse = './STOCK_DAY_ALL.json'
    past_day_json_path_tpex = './tpex_mainboard_daily_close_quotes.json'
    company_data_json_path_twse = './comp_data/t187ap03_L.json'
    company_data_json_path_tpex = './comp_data/mopsfin_t187ap03_O.json'

    with open(analysis_json_path, 'r', encoding='utf-8') as f:
        global g_category_json
        g_category_json = json.load(f)
    with open(past_day_json_path_twse, 'r', encoding='utf-8') as f:
        past_json_data_twse = json.load(f)
    with open(past_day_json_path_tpex, 'r', encoding='utf-8') as f:
        past_json_data_tpex = json.load(f)
    with open(company_data_json_path_twse, 'r', encoding='utf-8') as f:
        company_json_data_twse = json.load(f)
    with open(company_data_json_path_tpex, 'r', encoding='utf-8') as f:
        company_json_data_tpex = json.load(f)

    global g_stock_category
    g_stock_category = list(g_category_json['台股'].keys())  # 提取所有類別名稱

    stocks_info_list = {}
    for category, stocks_info in g_category_json['台股'].items():
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
    
    try:
        # 分次讀取即時資料 好像會有上限
        track_stock_realtime_data_1 = twstock.realtime.get(list(stocks_df.columns[:len(stocks_df.columns)//2]))
        track_stock_realtime_data_2 = twstock.realtime.get(list(stocks_df.columns[len(stocks_df.columns)//2:]))

        # 合併資料
        global g_track_stock_realtime_data
        g_track_stock_realtime_data = {**track_stock_realtime_data_1, **track_stock_realtime_data_2}
    except (KeyError, ValueError):
        print("部分即時資料缺少 timestamp，略過")
        g_track_stock_realtime_data = {}

    for stock_id in stocks_df.columns:
        if stock_id in g_track_stock_realtime_data and 'realtime' in g_track_stock_realtime_data[stock_id]:
            if g_track_stock_realtime_data[stock_id]['success']:
                
                realtime_data = g_track_stock_realtime_data[stock_id]['realtime']
                
                #如果沒有最新成交價 就用買價(bid)一檔代替
                if realtime_data['latest_trade_price'] == '-' or realtime_data['latest_trade_price'] == '0':
                    current_price = float(realtime_data['best_bid_price'][0]) # 最佳買價一檔
                    if current_price == 0:
                        current_price = float(realtime_data['best_bid_price'][1])
                else:
                    current_price = float(realtime_data['latest_trade_price'])
                
                last_day_price = stocks_df.loc['last_day_price' , stock_id]
                current_change_percent = round((current_price - last_day_price) / last_day_price * 100 , 1)
                
                stocks_df.loc['realtime_price' , stock_id] = current_price
                stocks_df.loc['realtime_change' , stock_id] = current_change_percent
    
    return stocks_df

# 載入初始股票資料
initial_stocks_df = load_initial_data()

app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.layout = html.Div([
    # 1. Taiwan Stock Realtime Heatmap 大標題 ----------------------------
    html.H1("Taiwan Stock Realtime Heatmap", style={'textAlign': 'center', 'marginBottom': 30}),

    # 2. Display Mode ----------------------------
    html.Div([
        html.Label('Display Mode：', style={'marginRight': '5px', 'display': 'inline-block'}),
        dcc.RadioItems(
            options=[
                {'label': 'Normal Display', 'value': 'equal'},
                {'label': 'Market Cap Display', 'value': 'market'},
                {'label': 'Bubble Chart', 'value': 'bubble'}  # 新增 Bubble Chart 選項
            ],
            id='size-mode',
            value='equal',
            labelStyle={'display': 'inline-block', 'marginRight': '10px'},
            style={'display': 'inline-block'}
        )
    ], style={'textAlign': 'center', 'marginBottom': 20}),
    
    # 3. Enable Notifications ----------------------------
    html.Div([
        html.Label('Enable Notifications：', style={'marginRight': '5px', 'display': 'inline-block'}),
        daq.ToggleSwitch(id='enable-notifications', value=False, label=['Disable', 'Enable'], style={'display': 'inline-block'})  # 使用 dash_daq.ToggleSwitch
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),
    
    # 4. Last Update Time ----------------------------
    html.Div([
        html.Span("Last Update Time: ", style={'fontWeight': 'bold'}),
        html.Span(id='last-update-time', style={'color': 'blue'})
    ], style={'textAlign': 'center', 'marginBottom': 20}),
    
    # 5. Heatmap or Bubble Chart ----------------------------
    dcc.Graph(id='live-treemap'),
    dcc.Interval(id='interval-update', interval=5000, n_intervals=0),
    
    # 6. Stock Link Container ----------------------------
    html.Div(id='stock-link-container', style={'textAlign': 'center', 'marginTop': 20}),

    # 7. Stock Trading Interface ----------------------------
    html.Div([
        html.H1("Stock Trading Interface", style={'textAlign': 'center', 'marginTop': 30}),
        # 7-1. Order Type toggle ----------------------------
        html.Div([
            html.Label("Order Type：", style={'marginRight': '5px', 'display': 'inline-block'}),
            daq.ToggleSwitch( id='buy-sell-toggle', value=True, label=['Sell', 'Buy'], style={'display': 'inline-block', 'marginRight': '20px'} ),
            daq.ToggleSwitch( id='order_type', value=True, label=['Market Order：', 'Limit Order'], style={'display': 'inline-block', 'marginRight': '20px'} ),
            daq.ToggleSwitch( id='Funding_strategy', value=False, label=['Manual', 'Average'], style={'display': 'inline-block', 'marginRight': '10px'} ),
            html.Div(id='average-amount-input', style={'display': 'inline-block'})
        ], style={'textAlign': 'center', 'marginBottom': '20px'}),
        html.Div([
            html.Label("Select Category："),
            # 7-2. Category Dropdown ----------------------------
            dcc.Dropdown(
                id='group-dropdown',
                options=[{'label': cat, 'value': cat} for cat in g_stock_category],
                placeholder="選擇族群",
                style={'width': '50%', 'margin': '0 auto'}
            ),
        ], style={'textAlign': 'center', 'marginBottom': '20px'}),
        html.Div(id='stock-input-container', style={'textAlign': 'center', 'marginBottom': '20px'}),
        html.Div([
            html.Button("Refresh", id='refersh-button', n_clicks=0, style={'display': 'inline-block', 'marginRight': '20px'}),
            html.Button("Send Order", id='confirm-order-button', n_clicks=0, style={'display': 'inline-block'})
        ]
        , style={'textAlign': 'center', 'marginBottom': '20px'}),
        html.Div(id='order-status', style={'textAlign': 'center', 'marginTop': '20px', 'color': 'green'}),
        
        # 確認對話框
        html.Div(
            id='order-confirmation-modal',
            children=[
                html.Div([
                    html.Div([
                        html.H3("確認下單資訊", style={'textAlign': 'center', 'marginBottom': '20px'}),
                        html.Div(id='confirmation-details', style={'marginBottom': '20px', 'padding': '15px', 'backgroundColor': '#f9f9f9', 'border': '1px solid #ddd'}),
                        html.Div([
                            html.Button("確認下單", id='confirm-final-order', n_clicks=0, style={'marginRight': '10px', 'backgroundColor': '#28a745', 'color': 'white', 'border': 'none', 'padding': '10px 20px', 'borderRadius': '5px'}),
                            html.Button("取消", id='cancel-order', n_clicks=0, style={'backgroundColor': '#dc3545', 'color': 'white', 'border': 'none', 'padding': '10px 20px', 'borderRadius': '5px'})
                        ], style={'textAlign': 'center'})
                    ], style={
                        'backgroundColor': 'white',
                        'margin': '50px auto',
                        'padding': '30px',
                        'width': '60%',
                        'borderRadius': '10px',
                        'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'
                    })
                ], style={
                    'position': 'fixed',
                    'top': '0',
                    'left': '0',
                    'width': '100%',
                    'height': '100%',
                    'backgroundColor': 'rgba(0, 0, 0, 0.5)',
                    'zIndex': '1000'
                })
            ],
            style={'display': 'none'}
        )
    ])
])


@app.callback(
    [Output('live-treemap', 'figure'),
     Output('last-update-time', 'children')],
    [Input('interval-update', 'n_intervals'),
     Input('size-mode', 'value'),
     Input('enable-notifications', 'value')]  # 新增通知開關的輸入
)
def update_treemap(n, size_mode, enable_notifications):
    
    updated_stocks_df = update_realtime_data(initial_stocks_df.copy()) # 更新即時股價
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 取得當前時間
    
    # 準備 treemap 資料
    treemap_data = []
    df_transposed = updated_stocks_df.T

    for stock_id, row in df_transposed.iterrows():
        # 計算市值
        market_value = row['issue_shares'] * row['realtime_price'] if not pd.isna(row['realtime_price']) else 0
        # 格式化市值顯示
        if market_value >= 1e8:
            market_value_display = f"{int(market_value / 1e8)}e"
        else:
            market_value_display = f"{int(market_value / 1e4)}w"
        
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
                'market_cap': market_value_display,  # Display 使用
                'market_value': market_value  # 保留原始數字值
            })

    # 轉換成 DataFrame
    treemap_df = pd.DataFrame(treemap_data)

    # 根據顯示模式決定區塊大小
    if size_mode == 'equal' or size_mode == 'market':
        if size_mode == 'equal':
            # 平均大小模式，所有區塊大小相同
            values = [1] * len(treemap_df)
        elif size_mode == 'market':
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
            hover_data=['stock_id', 'realtime_price', 'last_day_price', 'stock_type', 'market_cap'],
            custom_data=['stock_name', 'stock_id', 'realtime_price', 'realtime_change', 'stock_type']
        )

        fig.update_traces(marker=dict(cornerradius=5), textposition='middle center', texttemplate="%{label} %{customdata[1]}<br>%{customdata[2]}<br>%{customdata[3]:.2f}%")
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',  # 透明背景
            margin=dict(t=50, l=10, r=10, b=10),
            height=900,
            coloraxis_colorbar_tickformat='.2f'
        )
    else:
        # Bubble Chart 模式，氣泡大小根據市值加總
        bubble_data = treemap_df.groupby('category').agg(
            mean_change=('realtime_change', 'mean'),
            total_market_value=('market_value', 'sum')
        ).reset_index()

        # 修改 Bubble Chart 的 X 軸和 Y 軸設置
        bubble_data = bubble_data.sort_values('mean_change')  # 按漲幅排序
        fig = px.scatter(
            bubble_data,
            x='category',  # X 軸顯示群組類別
            y='mean_change',  # Y 軸顯示漲幅
            size='total_market_value',
            color='mean_change',
            color_continuous_scale='RdYlGn_r',
            title='',
            labels={'mean_change': 'Mean Change (%)', 'total_market_value': 'Total Market Value'},
            hover_name='category',
            size_max=60
        )

        fig.update_layout(
            xaxis=dict(title='Category', categoryorder='array', categoryarray=bubble_data['category']),  # X 軸按排序顯示
            yaxis=dict(title='Mean Change (%)'),
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=50, l=10, r=10, b=10),
            height=900,
            coloraxis_colorbar_tickformat='.2f'
        )
    
    #發送 Discord 群組漲跌幅通知
    if enable_notifications:  # 只有在通知開關打開時才發送通知
        send_discord_category_notification(treemap_df, fig)

    return fig, current_time

# 點擊 treemap 顯示外部連結並更新下拉選單
@app.callback(
    [Output('stock-link-container', 'children'),
     Output('group-dropdown', 'value')],
    Input('live-treemap', 'clickData')
)
def display_stock_link(clickData):
    if not clickData or not clickData['points']:
        return '', None
    
    point = clickData['points'][0]
    label = point['label']  # 獲取點擊的標籤
    
    # 檢查是否是類股群組名稱
    selected_category = None
    if label in g_stock_category:
        selected_category = label

    # 如果點擊的是最外圍的 "Taiwan Stock"，顯示三個指定的連結
    if label == "Taiwan Stock":
        links_div = html.Div([
            html.A("Goodinfo", href="https://goodinfo.tw/tw/index.asp", target="_blank", style={'fontSize': '18px', 'color': 'blue', 'marginRight': '20px'}),
            html.A("Wantgoo", href="https://www.wantgoo.com/stock", target="_blank", style={'fontSize': '18px', 'color': 'green', 'marginRight': '20px'}),
            html.A("TradingView - TWSE", href="https://tw.tradingview.com/chart/?symbol=TWSE%3AIX0001", target="_blank", style={'fontSize': '18px', 'color': 'black', 'marginRight': '20px'}),
            html.A("TradingView - TPEx", href="https://tw.tradingview.com/chart/?symbol=TPEX%3AIX0118", target="_blank", style={'fontSize': '18px', 'color': 'black'})
        ], style={'textAlign': 'center', 'marginTop': '10px'})
        return links_div, None

    # 如果點擊的是其他股票，顯示該股票的連結
    stock_id = point['customdata'][1]
    stock_type = point['customdata'][4]
    prefix = 'TWSE' if stock_type == 'TWSE' else 'TPEX'
    url_goodinfo = f"https://goodinfo.tw/tw/ShowK_Chart.asp?STOCK_ID={stock_id}"
    url_wantgoo = f"https://www.wantgoo.com/stock/{stock_id}/technical-chart"
    url_tradingView = f"https://tw.tradingview.com/chart/?symbol={prefix}%3A{stock_id}"
    
    links_div = html.Div([
        html.A(f"Goodinfo - {stock_id}", href=url_goodinfo, target="_blank", style={'fontSize': '18px', 'color': 'blue', 'marginRight': '20px'}),
        html.A(f"Wantgoo - {stock_id}", href=url_wantgoo, target="_blank", style={'fontSize': '18px', 'color': 'green', 'marginRight': '20px'}),
        html.A(f"TradingView - {stock_id}", href=url_tradingView, target="_blank", style={'fontSize': '18px', 'color': 'black'})
    ], style={'textAlign': 'center', 'marginTop': '10px'})
    return links_div, selected_category


@app.callback(
    Output('average-amount-input', 'children'),
    Input('Funding_strategy', 'value')
)
def toggle_average_input(funding_strategy_value):
    """當Funding_strategy切換到Average時顯示金額輸入框"""
    if funding_strategy_value:  # True 表示切換到 "Average"
        return [
            html.Label("投資金額(元)：", style={'marginRight': '5px', 'display': 'inline-block'}),
            dcc.Input(
                id='average-amount',
                type='number',
                placeholder='輸入總投資金額',
                style={'width': '150px', 'display': 'inline-block'}
            )
        ]
    else:  # False 表示切換到 "Manual"
        return ''


@app.callback(
    Output('stock-input-container', 'children'),
    Input('group-dropdown', 'value')
)
def populate_stock_inputs(selected_group):
    """根據選擇的族群自動填充股票資訊"""
    if not selected_group:
        return ''
    
    # 獲取選定類股群組的股票
    if selected_group in g_category_json['台股']:
        stocks = g_category_json['台股'][selected_group]
        
        # 建立股票列表界面
        return html.Div([
            # 標題列
            html.Div([
                html.Div("Trade Toggle", style={'width': '10%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Stock ID", style={'width': '10%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Stock Name", style={'width': '10%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Price", style={'width': '10%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Volume(張)", style={'width': '10%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Odd Lots(股)", style={'width': '10%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Est. Cost", style={'width': '12%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Percentage", style={'width': '12%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Order Status", style={'width': '16%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            ], style={'marginBottom': '10px', 'backgroundColor': '#f0f0f0', 'padding': '10px'}),
            
            # 股票資訊列
            *[
                html.Div([
                    daq.ToggleSwitch( 
                        id={'type': 'trade-toggle', 'index': stock_id}, 
                        value=True, 
                        label=['Off', 'On'], 
                        style={'width': '10%', 'display': 'inline-block'} 
                    ),       
                    html.Div(stock_id, style={'width': '10%', 'display': 'inline-block'}), # 股票代號
                    html.Div(stock_info['股票'], style={'width': '10%', 'display': 'inline-block'}), # 股票名稱
                    # 價格輸入
                    html.Div(
                        dcc.Input(
                            id={'type': 'price-input', 'index': stock_id},
                            type='number',
                            placeholder='輸入價格',
                            style={'width': '80%'}
                        ),
                        style={'width': '10%', 'display': 'inline-block'}
                    ),
                    # 張數輸入
                    html.Div(
                        dcc.Input(
                            id={'type': 'quantity-input', 'index': stock_id},
                            type='number',
                            placeholder='輸入張數',
                            style={'width': '80%'}
                        ),
                        style={'width': '10%', 'display': 'inline-block'}
                    ),
                    # 零股顯示
                    html.Div(id={'type': 'odd-lots-display', 'index': stock_id}, children='0', style={'width': '10%', 'display': 'inline-block'}),
                    html.Div(id={'type': 'cost-display', 'index': stock_id}, children='0', style={'width': '12%', 'display': 'inline-block'}),
                    html.Div(id={'type': 'percentage-display', 'index': stock_id}, children='0%', style={'width': '12%', 'display': 'inline-block'}),
                    html.Div(id={'type': 'status-display', 'index': stock_id}, children='Not ordered', style={'width': '16%', 'display': 'inline-block'}),

                ], style={'marginBottom': '5px', 'padding': '5px', 'borderBottom': '1px solid #ddd'})
                for stock_id, stock_info in stocks.items()
            ],
            # 總計行
            html.Div([
                html.Div("", style={'width': '10%', 'display': 'inline-block'}),
                html.Div("", style={'width': '10%', 'display': 'inline-block'}), 
                html.Div("", style={'width': '10%', 'display': 'inline-block'}), 
                html.Div("", style={'width': '10%', 'display': 'inline-block'}), 
                html.Div("總計：", style={'width': '10%', 'display': 'inline-block', 'fontWeight': 'bold', 'textAlign': 'right'}),
                html.Div("", style={'width': '10%', 'display': 'inline-block'}),
                html.Div(id='total-cost-display', children='$0', style={'width': '12%', 'display': 'inline-block', 'fontWeight': 'bold', 'color': 'red'}),
                html.Div("100%", style={'width': '12%', 'display': 'inline-block', 'fontWeight': 'bold', 'color': 'red'}),
                html.Div("", style={'width': '16%', 'display': 'inline-block'}),
            ], style={'marginTop': '10px', 'padding': '10px', 'backgroundColor': '#f8f8f8', 'borderTop': '2px solid #ddd'})
        ], style={'maxHeight': '400px', 'overflowY': 'auto', 'border': '1px solid #ddd', 'padding': '10px'})

# 合併後的 Refresh 按鈕回調邏輯
@app.callback(
    [Output({'type': 'price-input', 'index': ALL}, 'value'),
     Output({'type': 'quantity-input', 'index': ALL}, 'value')],
    Input('refersh-button', 'n_clicks'),
    [State('buy-sell-toggle', 'value'),
     State('Funding_strategy', 'value'),
     State('group-dropdown', 'value'),
     State({'type': 'trade-toggle', 'index': ALL}, 'value'),
     State({'type': 'trade-toggle', 'index': ALL}, 'id'),
     State({'type': 'price-input', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def refresh_stock_data(n_clicks, buy_sell, funding_strategy, selected_group, trade_toggles, trade_ids, price_ids):
    """合併的 Refresh 按鈕處理邏輯"""
    if n_clicks == 0 or not selected_group:
        raise PreventUpdate
    
    # 獲取股票代號列表
    stock_ids = [trade_id['index'] for trade_id in trade_ids]
    
    # 初始化價格和張數列表
    prices = []
    quantities = []
    
    for i, stock_id in enumerate(stock_ids):
        # 只處理 Trade Toggle 為 True 的股票
        if trade_toggles[i]:
            # 從即時資料中獲取買賣價
            if stock_id in g_track_stock_realtime_data and 'realtime' in g_track_stock_realtime_data[stock_id]:
                if g_track_stock_realtime_data[stock_id]['success']:
                    realtime_data = g_track_stock_realtime_data[stock_id]['realtime']
                    
                    # 根據買賣方向設定價格
                    if buy_sell:  # Buy mode - 使用賣價一檔 (ask_price)
                        if 'best_ask_price' in realtime_data and len(realtime_data['best_ask_price']) > 0:
                            price = float(realtime_data['best_ask_price'][0]) if realtime_data['best_ask_price'][0] != '-' else 0
                        else:
                            price = 0
                    else:  # Sell mode - 使用買價一檔 (bid_price)
                        if 'best_bid_price' in realtime_data and len(realtime_data['best_bid_price']) > 0:
                            price = float(realtime_data['best_bid_price'][0]) if realtime_data['best_bid_price'][0] != '-' else 0
                        else:
                            price = 0
                    
                    prices.append(price)
                else:
                    prices.append(0)
            else:
                prices.append(0)
        else:
            prices.append(None)  # Trade Toggle 為 False 的股票不填入價格
    
    # 處理張數邏輯
    if funding_strategy:  # Average 模式
        # 沒有投資金額，使用預設金額
        try:
            # 計算有效股票數量（Trade Toggle 為 True 且價格大於 0）
            valid_stocks = sum(1 for i, price in enumerate(prices) 
                              if trade_toggles[i] and price is not None and price > 0)
            
            if valid_stocks > 0:
                # 假設每檔股票分配 10000 元
                default_amount_per_stock = 10000
                
                for i, price in enumerate(prices):
                    if trade_toggles[i] and price is not None and price > 0:
                        # 計算張數（每張1000股）
                        quantity = int(default_amount_per_stock / (price * 1000))
                        quantities.append(quantity)
                    else:
                        quantities.append(None)
            else:
                quantities = [None] * len(stock_ids)
        except:
            quantities = [None] * len(stock_ids)
    else:  # Manual 模式
        # Manual 模式只刷新價格，不修改張數
        quantities = [None] * len(stock_ids)
    
    return prices, quantities

# 處理有投資金額的 Average 模式 Refresh
@app.callback(
    Output({'type': 'quantity-input', 'index': ALL}, 'value', allow_duplicate=True),
    Input('refersh-button', 'n_clicks'),
    [State('buy-sell-toggle', 'value'),
     State('Funding_strategy', 'value'),
     State('average-amount', 'value'),
     State('group-dropdown', 'value'),
     State({'type': 'trade-toggle', 'index': ALL}, 'value'),
     State({'type': 'trade-toggle', 'index': ALL}, 'id'),
     State({'type': 'price-input', 'index': ALL}, 'value')],
    prevent_initial_call=True
)
def refresh_with_average_amount(n_clicks, buy_sell, funding_strategy, average_amount, selected_group, trade_toggles, trade_ids, current_prices):
    """處理有投資金額時的 Average 模式 Refresh 邏輯"""
    if (n_clicks == 0 or not selected_group or not funding_strategy or 
        average_amount is None or average_amount <= 0):
        raise PreventUpdate
    
    # 獲取股票代號列表
    stock_ids = [trade_id['index'] for trade_id in trade_ids]
    quantities = []
    
    # 計算有效股票數量（Trade Toggle 為 True 且價格大於 0）
    valid_stocks = sum(1 for i, price in enumerate(current_prices) 
                      if (i < len(trade_toggles) and trade_toggles[i] and 
                          price is not None and price > 0))
    
    if valid_stocks > 0:
        # 平均分配投資金額
        amount_per_stock = average_amount / valid_stocks
        
        for i, price in enumerate(current_prices):
            if (i < len(trade_toggles) and trade_toggles[i] and 
                price is not None and price > 0):
                # 計算張數（每張1000股）
                quantity = int(amount_per_stock / (price * 1000))
                quantities.append(quantity)
            else:
                quantities.append(None)
    else:
        quantities = [None] * len(stock_ids)
    
    return quantities

# 添加實時更新成本顯示的回調
@app.callback(
    [Output({'type': 'cost-display', 'index': ALL}, 'children'),
     Output({'type': 'percentage-display', 'index': ALL}, 'children'),
     Output({'type': 'odd-lots-display', 'index': ALL}, 'children'),
     Output('total-cost-display', 'children')],
    [Input({'type': 'price-input', 'index': ALL}, 'value'),
     Input({'type': 'quantity-input', 'index': ALL}, 'value'),
     Input('Funding_strategy', 'value'),
     Input('average-amount', 'value')],
    prevent_initial_call=True
)
def update_cost_display(prices, quantities, funding_strategy, average_amount):
    """實時更新估算成本、百分比、零股和總計"""
    costs = []
    percentages = []
    odd_lots = []
    total_cost = 0
    
    # 首先計算總成本
    individual_costs = []
    for price, quantity in zip(prices, quantities):
        if price is not None and quantity is not None and price > 0 and quantity > 0:
            cost = price * quantity * 1000  # 每張1000股
            individual_costs.append(cost)
            total_cost += cost
        else:
            individual_costs.append(0)
    
    # 計算有效股票數量（用於平均投資策略的零股計算）
    valid_stock_count = 0
    if funding_strategy and average_amount and average_amount > 0:
        valid_stock_count = sum(1 for price, quantity in zip(prices, quantities) 
                               if price is not None and quantity is not None and price > 0 and quantity > 0)
    
    # 然後計算每個股票的成本、百分比和零股
    for i, (price, quantity) in enumerate(zip(prices, quantities)):
        if price is not None and quantity is not None and price > 0 and quantity > 0:
            cost = individual_costs[i]
            costs.append(f"${cost:,.0f}")
            
            # 計算百分比
            if total_cost > 0:
                percentage = (cost / total_cost) * 100
                percentages.append(f"{percentage:.1f}%")
            else:
                percentages.append("0%")
            
            # 計算零股：根據策略決定計算方式
            if funding_strategy and average_amount and average_amount > 0 and valid_stock_count > 0:
                # 平均投資策略：計算平均分配後每檔可購買的總股數
                amount_per_stock = average_amount / valid_stock_count
                total_shares = int(amount_per_stock / price)
                odd_lots.append(f"{total_shares}")
            else:
                # 一般計算：用當前投資金額可以買多少股（不足一張的部分）
                total_shares = int(cost / price)  # 總共可以買多少股
                odd_lot_shares = total_shares % 1000  # 零股部分（不足一張的股數）
                odd_lots.append(f"{odd_lot_shares}")
        else:
            costs.append("0")
            percentages.append("0%")
            odd_lots.append("0")
    
    return costs, percentages, odd_lots, f"${total_cost:,.0f}"

# 顯示確認對話框
@app.callback(
    [Output('order-confirmation-modal', 'style'),
     Output('confirmation-details', 'children')],
    Input('confirm-order-button', 'n_clicks'),
    [State('buy-sell-toggle', 'value'),
     State('Funding_strategy', 'value'),
     State('average-amount', 'value'),
     State('group-dropdown', 'value'),
     State({'type': 'trade-toggle', 'index': ALL}, 'value'),
     State({'type': 'price-input', 'index': ALL}, 'value'),
     State({'type': 'quantity-input', 'index': ALL}, 'value'),
     State({'type': 'price-input', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def show_confirmation_modal(n_clicks, buy_sell, funding_strategy, average_amount, selected_group, trade_toggles, prices, quantities, ids):
    """顯示確認對話框"""
    if n_clicks == 0 or not selected_group or not prices or not quantities:
        return {'display': 'none'}, ''
    
    action = "買進" if buy_sell else "賣出"
    order_type = "限價單" if True else "市價單"  # 假設都是限價單
    
    # 計算訂單詳情
    order_details = []
    total_cost = 0
    
    # 檢查是否使用平均投資策略
    if funding_strategy:
        if average_amount:
            order_details.append(html.P(f"💰 投資策略：平均投資，總投資金額：${average_amount:,.0f}", style={'margin': '5px 0', 'fontWeight': 'bold'}))
        else:
            order_details.append(html.P(f"💰 投資策略：平均投資", style={'margin': '5px 0', 'fontWeight': 'bold'}))
    
    order_details.append(html.P(f"📊 交易方向：{action}", style={'margin': '5px 0', 'fontWeight': 'bold'}))
    order_details.append(html.P(f"📋 訂單類型：{order_type}", style={'margin': '5px 0', 'fontWeight': 'bold'}))
    order_details.append(html.Hr())
    
    # 添加股票訂單詳情
    stock_orders = []
    for i, (price, quantity, stock_id) in enumerate(zip(prices, quantities, ids)):
        if (i < len(trade_toggles) and trade_toggles[i] and 
            price is not None and quantity is not None and 
            price > 0 and quantity > 0):
            cost = price * quantity * 1000
            total_cost += cost
            stock_orders.append(
                html.Div([
                    html.Span(f"🏦 {stock_id['index']}", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                    html.Span(f"價格：${price:,.2f}", style={'marginRight': '10px'}),
                    html.Span(f"張數：{quantity}", style={'marginRight': '10px'}),
                    html.Span(f"成本：${cost:,.0f}", style={'color': 'red', 'fontWeight': 'bold'})
                ], style={'margin': '5px 0', 'padding': '5px', 'backgroundColor': '#f8f9fa', 'borderRadius': '3px'})
            )
    
    if not stock_orders:
        return {'display': 'none'}, ''
    
    order_details.extend(stock_orders)
    order_details.append(html.Hr())
    order_details.append(
        html.P(f"💵 總預估成本：${total_cost:,.0f}", 
               style={'margin': '10px 0', 'fontWeight': 'bold', 'fontSize': '18px', 'color': 'red', 'textAlign': 'center'})
    )
    
    return {'display': 'block'}, order_details

# 處理確認/取消按鈕
@app.callback(
    [Output('order-confirmation-modal', 'style', allow_duplicate=True),
     Output('order-status', 'children')],
    [Input('confirm-final-order', 'n_clicks'),
     Input('cancel-order', 'n_clicks')],
    [State('buy-sell-toggle', 'value'),
     State('Funding_strategy', 'value'),
     State('average-amount', 'value'),
     State('group-dropdown', 'value'),
     State({'type': 'trade-toggle', 'index': ALL}, 'value'),
     State({'type': 'price-input', 'index': ALL}, 'value'),
     State({'type': 'quantity-input', 'index': ALL}, 'value'),
     State({'type': 'price-input', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def handle_confirmation(confirm_clicks, cancel_clicks, buy_sell, funding_strategy, average_amount, selected_group, trade_toggles, prices, quantities, ids):
    """處理確認或取消訂單"""
    from dash import callback_context
    
    if not callback_context.triggered:
        return {'display': 'none'}, ''
    
    button_id = callback_context.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'cancel-order':
        return {'display': 'none'}, '訂單已取消'
    
    elif button_id == 'confirm-final-order':
        # 執行實際下單邏輯
        if not selected_group or not prices or not quantities:
            return {'display': 'none'}, "請填寫完整的下單資訊！"
        
        action = "買進" if buy_sell else "賣出"
        orders = []
        
        # 檢查是否使用平均投資策略
        if funding_strategy:
            if average_amount:
                orders.append(f"使用平均投資策略，總投資金額：${average_amount:,.0f}")
            else:
                orders.append(f"使用平均投資策略")
        
        # 只處理 Trade Toggle 為 True 的股票
        for i, (price, quantity, stock_id) in enumerate(zip(prices, quantities, ids)):
            if (i < len(trade_toggles) and trade_toggles[i] and 
                price is not None and quantity is not None and 
                price > 0 and quantity > 0):
                orders.append(f"{action} {stock_id['index']}，價格：${price:,.2f}，張數：{quantity}")
        
        if not orders:
            return {'display': 'none'}, "請填寫完整的下單資訊！"
        
        # 模擬下單成功
        return {'display': 'none'}, f"✅ 下單成功！\n" + "\n".join(orders)
    
    return {'display': 'none'}, ''


if __name__ == '__main__':
    app.run(debug=True)
