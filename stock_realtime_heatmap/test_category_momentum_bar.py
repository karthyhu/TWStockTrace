import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import math
from dash import Dash, html, dcc, Input, Output
import plotly.offline as pyo
from utility_function import *
from pprint import pprint

def create_summary_chart(category_momentum):
    """
    創建總平均比較圖
    
    Args:
        category_momentum (dict): calculate_category_momentum 函式的輸出結果
    
    Returns:
        plotly.graph_objects.Figure: 總平均比較圖
    """
    # 計算每個類別的平均漲幅並排序
    category_avg_momentum = []
    # 使用 sorted() 確保字典迭代順序穩定
    for category in sorted(category_momentum.keys()):
        data = category_momentum[category]
        avg_momentum = sum(data['avg_momentum']) / len(data['avg_momentum'])
        category_avg_momentum.append((category, avg_momentum))
    
    # 依照平均漲幅從低到高排序（左邊跌最多，右邊漲最多）
    category_avg_momentum.sort(key=lambda x: x[1], reverse=False)
    
    categories = [data[0] for data in category_avg_momentum]
    avg_values = [data[1] for data in category_avg_momentum]
    colors = ['crimson' if val >= 0 else 'green' for val in avg_values]
    
    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=avg_values,
            marker_color=colors,
            marker=dict(
                line=dict(width=1 , color='rgba(0, 0, 0, 0.8)'),
                cornerradius=5
            ),
            hovertemplate=
            "類別: %{x}<br>" +
            "平均漲幅: %{y:.2f}%<extra></extra>"
        )
    ])
    
    fig.update_layout(
        title='各類別總平均比較',
        # xaxis_title='類別',
        yaxis_title='平均漲幅 (%)',
        template='plotly_white',
        height=800,  # 調整為與右側圖表相同的高度
        margin=dict(l=50, r=50, t=80, b=100)
    )
    
    fig.update_xaxes(tickangle=90, tickfont=dict(size=12))
    fig.update_yaxes(tickfont=dict(size=12))
    
    return fig

def create_category_subplots(category_momentum, dates, momentum_data, page=1, grid_size="3x3"):
    """
    創建類別子圖表 (可選擇不同的布局)
    
    Args:
        category_momentum (dict): calculate_category_momentum 函式的輸出結果
        dates (list): 日期列表
        momentum_data (dict): collect_stock_momentum 函式的輸出結果
        page (int): 頁數 (從1開始)
        grid_size (str): 網格大小 ("2x2", "3x3", "4x4", "5x5")
    
    Returns:
        plotly.graph_objects.Figure: 子圖表
    """
    # 計算每個類別的平均漲幅並排序
    category_avg_momentum = []
    # 使用 sorted() 確保字典迭代順序穩定
    for category in sorted(category_momentum.keys()):
        data = category_momentum[category]
        avg_momentum = sum(data['avg_momentum']) / len(data['avg_momentum'])
        # 建立副本並反轉漲幅列表，使最新的資料在右側（避免原地修改）
        data_copy = data.copy()
        data_copy['avg_momentum'] = data['avg_momentum'][::-1]
        category_avg_momentum.append((category, avg_momentum, data_copy))
    
    # 依照平均漲幅從高到低排序
    category_avg_momentum.sort(key=lambda x: x[1], reverse=True)
    
    # 處理日期格式 (從 YYYMMDD.json 轉換為 MM/DD)，並反轉順序
    formatted_dates = []
    for date in dates[::-1]:  # 反轉日期列表
        # 去除 .json 副檔名
        date = date.replace('.json', '')
        # 格式化日期 - 只顯示月份/日期
        mm = date[3:5]
        dd = date[5:]
        formatted_dates.append(f"{mm}/{dd}")
    
    # 根據網格大小設定行列數和每頁項目數
    grid_configs = {
        "1x1": (1, 1, 1),
        "2x2": (2, 2, 4),
        "3x3": (3, 3, 9),
        "4x4": (4, 4, 16),
        "5x5": (5, 5, 25)
    }
    
    n_rows, n_cols, items_per_page = grid_configs.get(grid_size, (4, 4, 16))
    
    # 計算分頁
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_categories = category_avg_momentum[start_idx:end_idx]
    
    # 創建子圖表標題
    subplot_titles = []
    for i in range(items_per_page):
        if i < len(page_categories):
            cat = page_categories[i]
            subplot_titles.append(f"{cat[0]} (平均: {cat[1]:.2f}%)")
        else:
            subplot_titles.append("")
    
    fig = make_subplots(
        rows=n_rows,
        cols=n_cols,
        subplot_titles=subplot_titles,
        vertical_spacing=0.15,  # 增加垂直間距以避免標題與X軸重疊
        horizontal_spacing=0.08
    )
    
    # 取得上市大盤的資料用於疊圖
    market_data = None
    for cat_name, cat_avg, cat_data in category_avg_momentum:
        if cat_name == "上市大盤":
            market_data = cat_data['avg_momentum']
            break
    
    # 為每個類別添加柱狀圖
    for idx, (category, avg_momentum, data) in enumerate(page_categories):
        row = idx // n_cols + 1
        col = idx % n_cols + 1
        
        # 準備每日漲幅數據
        daily_values = data['avg_momentum']
        
        # 設定顏色（正值為深紅色，負值為綠色）
        colors = ['crimson' if val >= 0 else 'green' for val in daily_values]
        
        # 取得該類別中的所有股票和其漲幅
        stocks_in_category = data['stocks']
        
        # 準備每支股票的漲幅資料
        date_idx = len(dates) - 1  # 從最後一天開始
        stock_data = []
        for date in dates[::-1]:  # 反轉日期列表
            stocks_info = []
            for stock in stocks_in_category:
                if stock in momentum_data:
                    momentum = momentum_data[stock]['momentum_list'][date_idx]
                    stocks_info.append(f"{stock} {momentum_data[stock]['name']}: {momentum:.2f}%")
            stock_data.append("<br>".join(stocks_info))
            date_idx -= 1
        
        # 如果不是上市大盤本身，且有上市大盤資料，則先添加透明的上市大盤柱狀圖作為背景
        if category != "上市大盤" and market_data is not None:
            market_colors = ['rgba(255, 165, 0, 0.4)' for val in market_data]
            
            fig.add_trace(
                go.Bar(
                    x=formatted_dates,
                    y=market_data,
                    name="上市大盤 (參考)",
                    marker_color=market_colors,
                    marker=dict(
                        line=dict(width=1, color='rgba(255, 165, 0, 0.8)'),
                        cornerradius=2
                    ),
                    showlegend=False,
                    opacity=0.9,
                    hovertemplate=
                    "<b>上市大盤 (參考)</b><br>" +
                    "日期: %{x}<br>" +
                    "大盤平均漲幅: %{y:.2f}%<extra></extra>",
                    width=0.8  # 讓大盤柱狀圖稍微寬一點作為背景
                ),
                row=row,
                col=col
            )
        
        # 添加主要類別的柱狀圖（疊加在大盤之上）
        fig.add_trace(
            go.Bar(
                x=formatted_dates,
                y=daily_values,
                name=category,
                marker_color=colors,
                marker=dict(
                    line=dict(width=1, color='black'),
                    cornerradius=2
                ),
                showlegend=False,
                customdata=stock_data,
                hovertemplate=
                f"<b>{category}</b><br>" +
                "日期: %{x}<br>" +
                "類股平均漲幅: %{y:.2f}%<br>" +
                # f"類股整體平均: {avg_momentum:.2f}%<br>" +
                "個股漲幅:<br>%{customdata}<extra></extra>",
                width=0.5  # 讓主要類別柱狀圖稍微窄一點，這樣可以看到背景的大盤柱狀圖
            ),
            row=row,
            col=col
        )
    
    # 更新Y軸範圍和圖表設定
    if category_momentum:
        y_min = min(min(data['avg_momentum']) for data in category_momentum.values())
        y_max = max(max(data['avg_momentum']) for data in category_momentum.values())
        
        for i in range(1, len(page_categories) + 1):
            row = (i - 1) // n_cols + 1
            col = (i - 1) % n_cols + 1
            fig.update_yaxes(range=[y_min - 0.5, y_max + 0.5], row=row, col=col)
            # 顯示X軸標籤，並設定文字角度和大小
            fig.update_xaxes(showticklabels=True, tickangle=90, tickfont=dict(size=8), row=row, col=col)
    
    fig.update_layout(
        title=f'各類股每日漲幅分布 ({grid_size} 網格，第 {page} 頁)',
        showlegend=False,
        height=800,  # 增加高度以容納更大的垂直間距
        template='plotly_white',
        margin=dict(l=50, r=50, t=80, b=50),
        barmode='overlay'  # 設定柱狀圖為疊加模式
    )
    
    return fig

def create_dashboard_app():
    """
    創建 Dash 應用程式，包含左右分區的儀表板
    """
    app = Dash(__name__)
    
    # 網格大小選項
    grid_options = [
        {'label': '1x1 (1個圖)', 'value': '1x1'},
        {'label': '2x2 (4個圖)', 'value': '2x2'},
        {'label': '3x3 (9個圖)', 'value': '3x3'},
        {'label': '4x4 (16個圖)', 'value': '4x4'},
        {'label': '5x5 (25個圖)', 'value': '5x5'}
    ]
    
    # 初始載入資料
    with open('my_stock_category.json', 'r', encoding='utf-8') as f:
        category_data = json.load(f)
    
    # 初始參數
    initial_days = 15
    date_files = get_section_category_momentum_data("../raw_stock_data/daily/tpex", initial_days)
    stocks_info = get_unique_stocks(category_data)
    
    twse_path = "../raw_stock_data/daily/twse"
    tpex_path = "../raw_stock_data/daily/tpex"
    momentum_data = collect_stock_momentum(twse_path, tpex_path, date_files, stocks_info)
    category_momentum = calculate_category_momentum(category_data, momentum_data)
    
    app.layout = html.Div([
        html.H1('股票類別動量分析儀表板', style={'textAlign': 'center', 'marginBottom': 20}),
        
        # 全域控制面板
        html.Div([
            html.Div([
                html.Label('天數選擇 (幾根柱狀圖):', style={
                    'fontWeight': 'bold', 
                    'display': 'inline-block', 
                    'marginBottom': 5,
                    'marginRight': 10,
                    'verticalAlign': 'middle'
                }),
                dcc.Input(
                    id='days-input',
                    type='number',
                    value=15,
                    min=1,
                    max=50,
                    step=1,
                    style={
                        'width': 80,
                        'display': 'inline-block',
                        'verticalAlign': 'middle',
                        'marginRight': 10
                    }
                ),
                html.Button(
                    '更新資料',
                    id='update-button',
                    n_clicks=0,
                    style={
                        'display': 'inline-block',
                        'verticalAlign': 'middle',
                        'marginRight': 20,
                        'backgroundColor': '#007bff',
                        'color': 'white',
                        'border': 'none',
                        'padding': '5px 15px',
                        'borderRadius': '3px',
                        'cursor': 'pointer'
                    }
                ),
                html.Span(id='status-message', style={
                    'color': 'green',
                    'fontWeight': 'bold',
                    'display': 'inline-block',
                    'verticalAlign': 'middle'
                })
            ], style={'textAlign': 'center', 'marginBottom': 20})
        ]),
        
        html.Div([
            # 左側區域 - 總平均比較圖
            html.Div([
                dcc.Graph(
                    id='summary-chart',
                    figure=create_summary_chart(category_momentum),
                    style={'height': '800px'}  # 調整為與右側圖表相同的高度
                )
            ], style={'width': '49%', 'display': 'inline-block', 'verticalAlign': 'bottom'}),
            
            # 右側區域 - 控制選項和子圖表
            html.Div([
                # 控制面板
                html.Div([
                    # 網格大小選擇器
                    html.Div([
                        html.Label('網格大小:', style={
                            'fontWeight': 'bold', 
                            'display': 'inline-block', 
                            'marginBottom': 5,
                            'marginRight': 10,
                            'verticalAlign': 'middle'
                        }),
                        dcc.Dropdown(
                            id='grid-size-dropdown',
                            options=grid_options,
                            value='3x3',
                            style={
                                'width': 150,
                                'display': 'inline-block',
                                'verticalAlign': 'middle'
                            }
                        )
                    ], style={'display': 'inline-block', 'marginRight': 20, 'verticalAlign': 'middle'}),
                    
                    # 頁數選擇器
                    html.Div([
                        html.Label(id='page-label', style={
                            'fontWeight': 'bold', 
                            'display': 'inline-block', 
                            'marginBottom': 5,
                            'marginRight': 10,
                            'verticalAlign': 'middle'
                        }),
                        dcc.Dropdown(
                            id='page-dropdown',
                            value=1,
                            style={
                                'width': 200,
                                'display': 'inline-block',
                                'verticalAlign': 'middle'
                            }
                        )
                    ], style={'display': 'inline-block', 'verticalAlign': 'middle'})
                ], style={'marginBottom': 20, 'textAlign': 'center'}),
                
                dcc.Graph(
                    id='category-subplots',
                    style={'height': '800px'}  # 配合子圖表的新高度
                )
            ], style={'width': '49%', 'display': 'inline-block', 'verticalAlign': 'bottom', 'marginLeft': '2%'})
        ])
    ], style={'padding': 20})
    
    # 動態更新資料的回調
    @app.callback(
        Output('summary-chart', 'figure'),
        Output('status-message', 'children'),
        Input('update-button', 'n_clicks'),
        Input('days-input', 'value')
    )
    def update_data(n_clicks, days):
        if n_clicks == 0:
            # 初始載入
            return create_summary_chart(category_momentum), ""
        
        if days is None or days < 1:
            return create_summary_chart(category_momentum), "請輸入有效的天數 (≥1)"
        
        try:
            # 重新載入資料
            with open('my_stock_category.json', 'r', encoding='utf-8') as f:
                category_data = json.load(f)
            
            date_files = get_section_category_momentum_data("../raw_stock_data/daily/tpex", days)
            stocks_info = get_unique_stocks(category_data)
            
            twse_path = "../raw_stock_data/daily/twse"
            tpex_path = "../raw_stock_data/daily/tpex"
            new_momentum_data = collect_stock_momentum(twse_path, tpex_path, date_files, stocks_info)
            new_category_momentum = calculate_category_momentum(category_data, new_momentum_data)
            
            # 更新全域變數 (用於其他回調函數)
            app.server.config['current_category_momentum'] = new_category_momentum
            app.server.config['current_momentum_data'] = new_momentum_data
            app.server.config['current_dates'] = new_momentum_data['dates']
            
            # 檢查實際取得的天數
            actual_days = len(new_momentum_data['dates'])
            status_msg = f"資料已更新 (要求: {days} 天, 實際: {actual_days} 天)"
            
            return create_summary_chart(new_category_momentum), status_msg
            
        except Exception as e:
            return create_summary_chart(category_momentum), f"更新失敗: {str(e)}"
    
    # 初始化全域變數
    app.server.config['current_category_momentum'] = category_momentum
    app.server.config['current_momentum_data'] = momentum_data
    app.server.config['current_dates'] = momentum_data['dates']
    # 動態更新頁數選項和標籤的回調
    @app.callback(
        Output('page-dropdown', 'options'),
        Output('page-dropdown', 'value'),
        Output('page-label', 'children'),
        Output('page-dropdown', 'style'),
        Input('grid-size-dropdown', 'value'),
        Input('update-button', 'n_clicks'),
        Input('days-input', 'value')  # 新增天數輸入作為觸發條件
    )
    def update_page_options(grid_size, n_clicks, days):
        # 從全域變數取得當前的類別動量資料
        current_category_momentum = app.server.config.get('current_category_momentum', category_momentum)
        
        # 計算當前網格大小下的每頁項目數
        grid_configs = {
            "1x1": 1,
            "2x2": 4,
            "3x3": 9,
            "4x4": 16,
            "5x5": 25
        }
        items_per_page = grid_configs.get(grid_size, 16)
        total_categories = len(current_category_momentum)
        
        if grid_size == "1x1":
            # 1x1 模式：顯示群組名稱
            # 取得所有類別並依照平均漲幅排序
            category_avg_momentum = []
            # 使用 sorted() 確保字典迭代順序穩定
            for category in sorted(current_category_momentum.keys()):
                data = current_category_momentum[category]
                avg_momentum = sum(data['avg_momentum']) / len(data['avg_momentum'])
                category_avg_momentum.append((category, avg_momentum))
            
            # 依照平均漲幅從低到高排序（與左側總平均圖保持一致）
            category_avg_momentum.sort(key=lambda x: x[1], reverse=True)
            
            page_options = [{'label': f"{cat[0]} ({cat[1]:.2f}%)", 'value': i+1} 
                          for i, cat in enumerate(category_avg_momentum)]
            label_text = "選擇群組:"
            default_value = 1
            # 1x1 模式使用較小的字體
            dropdown_style = {
                'width': 200,
                'display': 'inline-block',
                'verticalAlign': 'middle',
                'fontSize': '12px'
            }
        else:
            # 其他模式：顯示頁數
            total_pages = math.ceil(total_categories / items_per_page)
            page_options = [{'label': f'第 {i} 頁', 'value': i} for i in range(1, total_pages + 1)]
            label_text = "選擇頁數:"
            default_value = 1
            # 其他模式使用正常字體
            dropdown_style = {
                'width': 200,
                'display': 'inline-block',
                'verticalAlign': 'middle'
            }
        
        return page_options, default_value, label_text, dropdown_style
    
    @app.callback(
        Output('category-subplots', 'figure'),
        Input('page-dropdown', 'value'),
        Input('grid-size-dropdown', 'value'),
        Input('update-button', 'n_clicks'),
        Input('days-input', 'value')  # 新增天數輸入作為觸發條件
    )
    def update_subplots(selected_page, grid_size, n_clicks, days):
        # 從全域變數取得當前資料
        current_category_momentum = app.server.config.get('current_category_momentum', category_momentum)
        current_momentum_data = app.server.config.get('current_momentum_data', momentum_data)
        current_dates = app.server.config.get('current_dates', momentum_data['dates'])
        
        return create_category_subplots(current_category_momentum, current_dates, current_momentum_data, page=selected_page, grid_size=grid_size)
    
    return app

def plot_momentum_bar_subplots():
    """
    使用新的儀表板方式呈現各類別漲幅
    """
    # 創建並運行 Dash 應用程式
    app = create_dashboard_app()
    app.run(debug=True)

if __name__ == '__main__':
    # 直接啟動儀表板，資料會在應用程式內部載入
    plot_momentum_bar_subplots()
