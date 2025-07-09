import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import json
import twstock
import datetime

app = dash.Dash(__name__)

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

# 載入初始資料
def load_initial_data():
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
    
    return pd.DataFrame(stocks_info_list)

# 更新即時股價資料
def update_realtime_data(stocks_df):
    track_stock_realtime_data = twstock.realtime.get(list(stocks_df.columns))

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
                current_change_percent = round((current_price - last_day_price) / last_day_price * 100 , 2)
                
                stocks_df.loc['realtime_price' , stock_id] = current_price
                stocks_df.loc['realtime_change' , stock_id] = current_change_percent
    
    return stocks_df

# 載入初始股票資料
initial_stocks_df = load_initial_data()

app.layout = html.Div([
    html.H1("台股即時熱力圖", style={'textAlign': 'center', 'marginBottom': 30}),
    html.Div([
        html.Span("最後更新時間: ", style={'fontWeight': 'bold'}),
        html.Span(id='last-update-time', style={'color': 'blue'})
    ], style={'textAlign': 'center', 'marginBottom': 20}),
    dcc.Graph(id='live-treemap'),
    dcc.Interval(id='interval-update', interval=3000, n_intervals=0)  # 每 x 秒更新一次
])

@app.callback(
    [Output('live-treemap', 'figure'),
     Output('last-update-time', 'children')],
    Input('interval-update', 'n_intervals')
)
def update_treemap(n):
    # 更新即時股價
    updated_stocks_df = update_realtime_data(initial_stocks_df.copy())
    
    # 準備 treemap 資料
    treemap_data = []
    df_transposed = updated_stocks_df.T
    
    for stock_id, row in df_transposed.iterrows():
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
                'stock_type': row['stock_type']
            })
    
    # 轉換成 DataFrame
    treemap_df = pd.DataFrame(treemap_data)
    
    # 建立 treemap
    fig = px.treemap(
        treemap_df,
        path=['stock_meta', 'category', 'stock_name'],
        values=[1] * len(treemap_df),  # 設定所有值為 1，確保大小相等
        color='realtime_change',
        color_continuous_scale='RdYlGn_r',
        title='Taiwan Stock Category Heat Map',
        range_color=[-10, 10],
        color_continuous_midpoint=0,
        hover_data=['stock_id', 'realtime_price', 'last_day_price', 'stock_type']
    )
    
    fig.update_traces(marker=dict(cornerradius=5))
    fig.update_layout(
        margin=dict(t=50, l=10, r=10, b=10),
        height=800
    )
    
    # 取得當前時間
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return fig, current_time

if __name__ == '__main__':
    app.run(debug=True)
