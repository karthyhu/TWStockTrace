import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
import json
import twstock
from datetime import datetime
import requests
import os
import time
import plotly.io as pio
import dash_daq as daq
from test_esun_api import *  # 導入所有 API 函數
from pprint import pprint
from utility_function import *  # 導入 utility 函數
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import math

# Global variables
g_const_debug_print = True

g_notified_status = {}
g_last_notification_time = {}
g_stock_category = []
g_category_json = {}
g_past_json_data_twse = {}
g_past_json_data_tpex = {}
g_company_json_data_twse = {}
g_company_json_data_tpex = {}
g_track_stock_realtime_data = {}
g_login_success = False # 登入狀態 flag
g_first_open_momentum_chart = True

# 從即時資料中取得當前價格
def get_current_price_from_realtime(realtime_data):
    """
    從即時資料中取得當前價格
    Args:
        realtime_data: 包含即時交易資訊的字典物件
    Returns:
        float: 當前價格，如果無法取得有效價格則返回 0
    """
    current_price = 0
    
    try:
        #如果沒有最新成交價 就用買價(bid)一檔代替
        if realtime_data['latest_trade_price'] in ['-', '0.0000']:
            if 'best_bid_price' in realtime_data:
                # 確保買價一檔有效
                if (realtime_data['best_bid_price'] and 
                    len(realtime_data['best_bid_price']) > 0 and 
                    realtime_data['best_bid_price'][0] not in ['-', '0.0000']):
                    current_price = float(realtime_data['best_bid_price'][0])
                    
            # 如果買價無效，嘗試賣價一檔
            if current_price == 0 and 'best_ask_price' in realtime_data:
                if (realtime_data['best_ask_price'] and 
                    len(realtime_data['best_ask_price']) > 0 and 
                    realtime_data['best_ask_price'][0] not in ['-', '0.0000']):
                    current_price = float(realtime_data['best_ask_price'][0])
                    
            # 如果買賣價都無效，使用次優報價
            if current_price == 0 and 'best_bid_price' in realtime_data:
                if (realtime_data['best_bid_price'] and 
                    len(realtime_data['best_bid_price']) > 1 and 
                    realtime_data['best_bid_price'][1] not in ['-', '0.0000']):
                    current_price = float(realtime_data['best_bid_price'][1])
            
            if current_price == 0 and 'best_ask_price' in realtime_data:
                if (realtime_data['best_ask_price'] and 
                    len(realtime_data['best_ask_price']) > 1 and 
                    realtime_data['best_ask_price'][1] not in ['-', '0.0000']):
                    current_price = float(realtime_data['best_ask_price'][1])

        else:
            if realtime_data['latest_trade_price'] not in ['-', '0.0000']:
                current_price = float(realtime_data['latest_trade_price'])
                
    except (ValueError, IndexError, TypeError) as e:
        print(f"價格轉換錯誤: {e}")
        current_price = 0
        
    return current_price

# 函數來獲取股票名稱
def get_stock_name(stock_no):
    # 先找 TWSE
    global g_past_json_data_twse, g_past_json_data_tpex

    if g_past_json_data_twse.get('data', {}).get(stock_no):
        return g_past_json_data_twse['data'][stock_no][1]
    # 再找 TPEX
    elif g_past_json_data_tpex.get('data', {}).get(stock_no):
        return g_past_json_data_tpex['data'][stock_no][1]
    else:
        return stock_no  # 如果找不到名稱，就顯示股票代號
            
# def get_section_category_momentum_data(range = 14):

def get_sorted_categories(category_momentum):
    """
    獲取排序後的類別列表，確保在所有地方使用相同的排序邏輯
    
    Args:
        category_momentum (dict): 類別動量數據
    
    Returns:
        list: 排序後的 (類別名稱, 平均漲幅) 列表
    """
    category_avg_momentum = []
    for category in sorted(category_momentum.keys()):
        data = category_momentum[category]
        avg_momentum = sum(data['avg_momentum']) / len(data['avg_momentum'])
        category_avg_momentum.append((category, avg_momentum))
    
    # 依照平均漲幅從高到低排序
    category_avg_momentum.sort(key=lambda x: x[1], reverse=True)
    return category_avg_momentum

def create_summary_chart(category_momentum):
    """
    創建總平均比較圖（左側圖表）
    
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
                cornerradius=3
            ),
            hovertemplate=
            "類別: %{x}<br>" +
            "平均漲幅: %{y:.2f}%<extra></extra>"
        )
    ])
    
    fig.update_layout(
        title='各類別總平均比較',
        yaxis_title='平均漲幅 (%)',
        template='plotly_white',
        margin=dict(t=20, l=10, r=10, b=10),
        height=900
    )
    
    fig.update_xaxes(tickangle=90, tickfont=dict(size=12))
    fig.update_yaxes(tickfont=dict(size=12))
    
    return fig

def create_category_subplots(category_momentum, dates, momentum_data, page=1, grid_size="3x3"):
    """
    創建類別子圖表（右側圖表）
    
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
    for category in sorted(category_momentum.keys()):
        data = category_momentum[category]
        avg_momentum = sum(data['avg_momentum']) / len(data['avg_momentum'])
        # 建立副本並反轉漲幅列表，使最新的資料在右側
        data_copy = data.copy()
        data_copy['avg_momentum'] = data['avg_momentum'][::-1]
        category_avg_momentum.append((category, avg_momentum, data_copy))
    
    # 依照平均漲幅從高到低排序
    category_avg_momentum.sort(key=lambda x: x[1], reverse=True)
    
    # 處理日期格式並反轉順序
    formatted_dates = []
    for date in dates[::-1]:
        date = date.replace('.json', '')
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
    
    n_rows, n_cols, items_per_page = grid_configs.get(grid_size, (3, 3, 9))
    
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
        vertical_spacing=0.15,
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
        
        daily_values = data['avg_momentum']
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
            fig.update_xaxes(showticklabels=True, tickangle=90, tickfont=dict(size=10), row=row, col=col)
    
    fig.update_layout(
        title=f'各類股每日漲幅分布 ({grid_size} 網格，第 {page} 頁)',
        showlegend=False,
        template='plotly_white',
        margin=dict(t=20, l=10, r=10, b=10),
        height=900,
        barmode='overlay'  # 設定柱狀圖為疊加模式
    )
    
    return fig

def create_momentum_dashboard(days=15, grid_size="2x2", page=1):
    """
    創建 Category Momentum 儀表板，左側顯示總圖表，右側顯示子圖表
    
    Args:
        days (int): 要分析的天數
        grid_size (str): 網格大小 ("1x1", "2x2", "3x3", "4x4")
        page (int): 頁數
    """
    try:
        # 獲取數據
        date_files = get_section_category_momentum_data("../raw_stock_data/daily/tpex", days)
        stocks_info = get_unique_stocks(g_category_json)
        
        twse_path = "../raw_stock_data/daily/twse"
        tpex_path = "../raw_stock_data/daily/tpex"
        momentum_data = collect_stock_momentum(twse_path, tpex_path, date_files, stocks_info)
        category_momentum = calculate_category_momentum(g_category_json, momentum_data)
        
        # 根據網格大小決定右側佈局
        grid_configs = {
            "1x1": (1, 1),
            "2x2": (2, 2),
            "3x3": (3, 3),
            "4x4": (4, 4)
        }
        right_rows, right_cols = grid_configs.get(grid_size, (2, 2))
        
        # 創建左右佈局 - 左側1列，右側為網格
        total_cols = 1 + right_cols  # 左側1列 + 右側網格列數
        
        # 創建列寬度 - 左側40%，右側60%平分給網格列
        column_widths = [0.4] + [0.6/right_cols] * right_cols
        
        # 創建子圖標題
        subplot_titles = ["Category Momentum Dashboard"]

        # 計算右側要顯示的類別
        items_per_page = right_rows * right_cols
        
        # 使用共用的排序函數獲取排序後的類別
        category_avg_momentum = get_sorted_categories(category_momentum)
        
        # 根據網格模式計算顯示範圍
        if grid_size == "1x1":
            # 1x1 模式：page 直接對應群組索引
            start_idx = page - 1  # page 從1開始，索引從0開始
            end_idx = start_idx + 1
        else:
            # 其他模式：page 對應頁數
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
        
        # 為右側每個位置添加標題
        display_categories = category_avg_momentum[start_idx:end_idx]
        for i in range(items_per_page):
            if i < len(display_categories):
                cat_name, cat_avg = display_categories[i]
                subplot_titles.append(f"{cat_name} ({cat_avg:.2f}%)")
            else:
                subplot_titles.append("")
        
        # 創建 specs - 左側佔據所有行，右側為網格
        specs = []
        for row in range(right_rows):
            row_specs = []
            if row == 0:
                # 第一行：左側有 rowspan，右側正常
                row_specs.append({"rowspan": right_rows})
            else:
                # 其他行：左側位置為 None（被 rowspan 佔據）
                row_specs.append(None)
            
            # 右側網格位置
            for col in range(right_cols):
                row_specs.append({"secondary_y": False})
            specs.append(row_specs)
        
        combined_fig = make_subplots(
            rows=right_rows,
            cols=total_cols,
            column_widths=column_widths,
            subplot_titles=subplot_titles,
            horizontal_spacing=0.02,
            vertical_spacing=0.1,
            specs=specs
        )
        
        # 添加左側總圖表
        summary_fig = create_summary_chart(category_momentum)
        for trace in summary_fig.data:
            combined_fig.add_trace(trace, row=1, col=1)
        
        # 設定左側圖表的軸
        combined_fig.update_xaxes(
            tickangle=90, 
            tickfont=dict(size=8),
            row=1, col=1
        )
        combined_fig.update_yaxes(
            title="平均漲幅 (%)",
            tickfont=dict(size=8),
            row=1, col=1
        )
        
        # 添加右側子圖表
        # 處理日期格式
        formatted_dates = []
        for date in date_files[::-1]:
            date = date.replace('.json', '')
            mm = date[3:5]
            dd = date[5:]
            formatted_dates.append(f"{mm}/{dd}")
        
        # 獲取大盤數據用於疊圖
        market_data = None
        for cat_name, cat_avg in category_avg_momentum:
            if cat_name == "上市大盤":
                data = category_momentum[cat_name]
                market_data = data['avg_momentum'][::-1]  # 反轉以配合日期順序
                break
        
        # 為右側每個位置添加圖表
        for i in range(len(display_categories)):
            cat_name, cat_avg = display_categories[i]
            cat_data = category_momentum[cat_name]
            daily_values = cat_data['avg_momentum'][::-1]  # 反轉以配合日期順序
            
            row = i // right_cols + 1
            col = i % right_cols + 2  # +2 因為第1列是左側圖表
            
            # 準備每支股票的漲幅資料
            stocks_in_category = cat_data['stocks']
            date_idx = len(date_files) - 1  # 從最後一天開始
            stock_data = []
            for date in date_files[::-1]:  # 反轉日期列表
                stocks_info = []
                for stock in stocks_in_category:
                    if stock in momentum_data:
                        momentum = momentum_data[stock]['momentum_list'][date_idx]
                        stocks_info.append(f"{stock} {momentum_data[stock]['name']}: {momentum:.2f}%")
                stock_data.append("<br>".join(stocks_info))
                date_idx -= 1
            
            # 添加大盤背景（如果不是大盤本身）
            if cat_name != "上市大盤" and market_data is not None:
                combined_fig.add_trace(
                    go.Bar(
                        x=formatted_dates,
                        y=market_data,
                        name="上市大盤 (參考)",
                        marker_color=['rgba(255, 165, 0, 0.4)' for _ in market_data],
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
                        width=0.8
                    ),
                    row=row,
                    col=col
                )
            
            # 添加主要類別的柱狀圖
            colors = ['crimson' if val >= 0 else 'green' for val in daily_values]
            combined_fig.add_trace(
                go.Bar(
                    x=formatted_dates,
                    y=daily_values,
                    name=cat_name,
                    marker_color=colors,
                    marker=dict(
                        line=dict(width=1, color='black'),
                        cornerradius=2
                    ),
                    showlegend=False,
                    customdata=stock_data,
                    hovertemplate=
                    f"<b>{cat_name}</b><br>" +
                    "日期: %{x}<br>" +
                    "類股平均漲幅: %{y:.2f}%<br>" +
                    "個股漲幅:<br>%{customdata}<extra></extra>",
                    width=0.5
                ),
                row=row,
                col=col
            )
            
            # 更新右側子圖的軸
            combined_fig.update_xaxes(
                showticklabels=True, 
                tickangle=90, 
                tickfont=dict(size=10),
                row=row, 
                col=col
            )
            combined_fig.update_yaxes(
                tickfont=dict(size=10),
                row=row, 
                col=col
            )
        
        # 更新整體佈局
        combined_fig.update_layout(
            height=900,  # 增加總高度以容納標題
            template='plotly_white',
            margin=dict(t=20, l=10, r=10, b=10),  # 增加頂部邊距
            barmode='overlay'
        )
        
        # 在兩個圖的中間上方添加標題
        # combined_fig.add_annotation(
        #     text=f'Category Momentum Dashboard | 天數: {days} (實際: {len(date_files)}) | {grid_size} 網格，第 {page} 頁',
        #     xref="paper", yref="paper",
        #     x=0.5, y=1.05,  # 將標題位置移到更高，超出圖表範圍
        #     showarrow=False,
        #     font=dict(size=14, color="black"),  # 稍微縮小字體
        #     xanchor="center",
        #     yanchor="middle"
        # )
        
        return combined_fig, f"資料已更新 (要求: {days} 天, 實際: {len(date_files)} 天)"
        
    except Exception as e:
        # 如果出錯，返回一個空的圖表
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error loading momentum data: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="red")
        )
        fig.update_layout(
            title="Category Momentum Dashboard - Error",
            height=800,
            template='plotly_white'
        )
        return fig, f"更新失敗: {str(e)}"

def send_discord_category_notification(display_df, fig):
    """發送股票群組漲跌幅資訊到 Discord"""
    global g_notified_status, g_last_notification_time, g_const_debug_print
    
    COOLDOWN_SECONDS = 60  # 1分鐘冷卻
    BUFFER_THRESHOLD = 0.8  # 緩衝區 0.8%
    print(f"[DEBUG] Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        # webhook_url = os.getenv('DISCORD_WEBHOOK_URL_TEST')
        if not webhook_url:
            print("Discord webhook URL not found. Skipping notification.")
            return
    
        # 計算各類別平均漲跌幅與數量
        category_stats = display_df.groupby('category')['realtime_change'].agg(['mean', 'count']).round(2)
        category_stats = category_stats.sort_values('mean', ascending=False)
        # print("Category stats calculated:", category_stats)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_timestamp = time.time()
        
        embed = {
            "title": f"📊 台股產業類股漲跌幅 - {current_time}",
            "color": 0x00ff00,
            "description": "",  # 使用 description 而不是 fields
            "type": "rich"
        }
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
                cooling_time = current_timestamp - g_last_notification_time[cat]
                if cooling_time < COOLDOWN_SECONDS:
                    previous_data = g_notified_status.get(cat, {"status": "neutral", "last_mean": 0})
                    previous_mean = previous_data["last_mean"]
                    print(f"{color_code}[DEBUG] Cooldown {round(cooling_time , 0)} sec {cat}: mean={mean} , last_mean={previous_mean}\033[0m")
                    continue
            
            # 獲取前次數據
            previous_data = g_notified_status.get(cat, {"status": "neutral", "last_mean": 0})
            previous_status = previous_data["status"]
            previous_mean = previous_data["last_mean"]
            
            # 緩衝區檢查
            if abs(mean - previous_mean) < BUFFER_THRESHOLD:
                if g_const_debug_print:
                    print(f"{color_code}[DEBUG] Not significant change {cat}: mean={mean} , last_mean={previous_mean}\033[0m")
                continue

            # 判斷是否需要通知
            if -3.5 < mean < 3.5:
                if g_const_debug_print:
                    print(f"{color_code}[DEBUG] Neutral category {cat}: mean={mean} , last_mean={previous_mean}\033[0m")
                # g_notified_status[cat] = {"status": "neutral", "last_mean": mean} -> 不要加，會導致緩衝區無法在界線即時通報
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

            if g_const_debug_print:
                print(f"{color_code}[DEBUG] Notification check {cat}: mean={mean} , {previous_mean} , status={current_status}\033[0m")

            # 僅在狀態變化時通知
            if current_status != previous_status:
                # 收集族群內的股票及漲幅資訊
                stock_details = display_df[display_df['category'] == cat][['stock_name', 'stock_type', 'stock_id', 'realtime_change']]
                stock_info = []
                
                for _, row in stock_details.iterrows():
                    # 根據股票類型產生相對應的 TradingView 連結
                    market_prefix = 'TWSE' if row['stock_type'] == 'TWSE' else 'TPEX'
                    tv_link = f"https://tw.tradingview.com/chart/?symbol={market_prefix}%3A{row['stock_id']}"
                    # 使用 Discord 的 Markdown 格式創建超連結，將股票名稱直接作為連結
                    stock_line = f"[{row['stock_name']} ({row['stock_id']})]({tv_link}) ({row['realtime_change']:+.2f}%)"
                    stock_info.append(stock_line)

                stock_info_text = "\n".join(stock_info)
                text += f"{emoji} **{cat}** ({cnt}檔): {mean:+.2f}%\n{stock_info_text}\n"

                # 更新記錄
                g_notified_status[cat] = {"status": current_status, "last_mean": mean}
                g_last_notification_time[cat] = current_timestamp
            # else:
                # 更新漲幅記錄但不通知
                # g_notified_status[cat]["last_mean"] = mean -> 不要加，會導致緩衝區無法在界線即時通報

        if text:
            embed['description'] = text  # 直接將內容放入 description
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
                
    except Exception as e:
        print(f"Error sending Discord notification: {e}")

def get_stock_info(past_json_data_twse, past_json_data_tpex, company_json_data_twse, company_json_data_tpex, target_code):
    
    if True:
        if past_json_data_twse['data'].get(target_code) != None:
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

            last_close_price = float(past_json_data_twse['data'][target_code][2])
            if  last_close_price == 0:
                try:
                    t2_day_path = '../raw_stock_data/daily/twse/T2_Day.json' #注意變更
                    with open(t2_day_path, 'r', encoding='utf-8') as f:
                        t2_day_json = json.load(f)
                    if t2_day_json['data'].get(target_code) is not None:
                        last_close_price = float(t2_day_json['data'][target_code][2])
                        print(f"已從 T2_Day.json 重新取得 {target_code} 收盤價：{t2_day_json['data'][target_code][2]}")
                except Exception as e:
                    print(f"讀取 T2_Day.json 失敗：{e}")
            
            return {
                'last_close_price': last_close_price, #上市股票收盤價
                'stock_name': past_json_data_twse['data'][target_code][1], #上市股票顯示名稱
                'stock_type': 'TWSE',
                'issue_shares': float(issue_shares)
            }
        
        elif past_json_data_tpex['data'].get(target_code) != None:
            issue_shares = 0
            for company_record in company_json_data_tpex:
                if target_code == '006201':
                    issue_shares = 18946000000 # 18946000 -> 18946000000 不然顯示不出來
                    break
                if company_record['SecuritiesCompanyCode'] == target_code:
                    issue_shares = company_record['IssueShares']
                    break
                
            last_close_price = float(past_json_data_tpex['data'][target_code][2])
            if  last_close_price == 0:
                try:
                    t2_day_path = '../raw_stock_data/daily/tpex/T2_Day.json' #注意變更
                    with open(t2_day_path, 'r', encoding='utf-8') as f:
                        t2_day_json = json.load(f)
                    if t2_day_json['data'].get(target_code) is not None:
                        last_close_price = float(t2_day_json['data'][target_code][2])
                        print(f"已從 T2_Day.json 重新取得 {target_code} 收盤價：{t2_day_json['data'][target_code][2]}")
                except Exception as e:
                    print(f"讀取 T2_Day.json 失敗：{e}")
            return {
                'last_close_price': last_close_price,  #上櫃股票收盤價
                'stock_name': past_json_data_tpex['data'][target_code][1], #上櫃股票顯示名稱
                'stock_type': 'TPEx',
                'issue_shares': float(issue_shares)
                }
        
        print(f"找不到股票代號：{target_code}")
        return None  # 如果找不到，回傳 None

    else:
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

def remove_suspended_stocks(g_category_json):
    """
    讀取所有股票即時資料，若無 best_bid_price 與 best_ask_price 則判定暫停交易並移除
    """
    # 收集所有 stock_id
    all_stock_ids = []
    for category, stocks_info in g_category_json['台股'].items():
        for stock_id in stocks_info.keys():
            all_stock_ids.append(stock_id)

    # 分成兩批取得即時資料
    realtime_data = {}
    mid = len(all_stock_ids) // 2
    batch_ids_1 = all_stock_ids[:mid]
    batch_ids_2 = all_stock_ids[mid:]
    try:
        batch_data_1 = twstock.realtime.get(batch_ids_1)
        batch_data_2 = twstock.realtime.get(batch_ids_2)
        realtime_data.update(batch_data_1)
        realtime_data.update(batch_data_2)
    except Exception as e:
        print(f"取得即時資料失敗: {e}")

    # 檢查並移除暫停交易的股票
    removed_stocks = []
    for category in list(g_category_json['台股'].keys()):
        for stock_id in list(g_category_json['台股'][category].keys()):
            data = realtime_data.get(stock_id, {})
            rt = data.get('realtime', {})
            best_bid = rt.get('best_bid_price')
            best_ask = rt.get('best_ask_price')

            if (not best_bid or best_bid == ['-']) and (not best_ask or best_ask == ['-']):
                stock_name = g_category_json['台股'][category][stock_id].get('股票', '')
                removed_stocks.append(f"{category}  {stock_id}({stock_name})")
                del g_category_json['台股'][category][stock_id]
    if removed_stocks:
        print(f"⚠️ 以下股票今日暫停交易，已移除: {removed_stocks}")

# 載入初始資料
def load_initial_data():
    
    # downlod_stock_data()
    # time.sleep(1)
    # downlod_stock_company_data()
    
    analysis_json_path = './my_stock_category.json'
    # past_day_json_path_twse = './STOCK_DAY_ALL.json'
    # past_day_json_path_tpex = './tpex_mainboard_daily_close_quotes.json'
    past_day_json_path_twse = '../raw_stock_data/daily/twse/T1_Day.json'
    past_day_json_path_tpex = '../raw_stock_data/daily/tpex/T1_Day.json'
    company_data_json_path_twse = './comp_data/t187ap03_L.json'
    company_data_json_path_tpex = './comp_data/mopsfin_t187ap03_O.json'
    
    global g_category_json, g_past_json_data_twse, g_past_json_data_tpex, g_company_json_data_twse, g_company_json_data_tpex

    with open(analysis_json_path, 'r', encoding='utf-8') as f:
        g_category_json = json.load(f)
    with open(past_day_json_path_twse, 'r', encoding='utf-8') as f:
        g_past_json_data_twse = json.load(f)
    with open(past_day_json_path_tpex, 'r', encoding='utf-8') as f:
        g_past_json_data_tpex = json.load(f)
    with open(company_data_json_path_twse, 'r', encoding='utf-8') as f:
        g_company_json_data_twse = json.load(f)
    with open(company_data_json_path_tpex, 'r', encoding='utf-8') as f:
        g_company_json_data_tpex = json.load(f)

    global g_stock_category
    g_stock_category = list(g_category_json['台股'].keys())  # 提取所有類別名稱

    remove_suspended_stocks(g_category_json)

    stocks_info_list = {}
    for category, stocks_info in g_category_json['台股'].items():
        for stock_id, stock_info in stocks_info.items():
            
            last_stock_info = get_stock_info(g_past_json_data_twse, g_past_json_data_tpex, g_company_json_data_twse, g_company_json_data_tpex, stock_id)

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
                current_price = get_current_price_from_realtime(realtime_data)
                
                # 只在有有效價格時更新
                if current_price > 0:
                    last_day_price = stocks_df.loc['last_day_price', stock_id]
                    current_change_percent = round((current_price - last_day_price) / last_day_price * 100, 2)

                    stocks_df.loc['realtime_price', stock_id] = current_price
                    stocks_df.loc['realtime_change', stock_id] = current_change_percent
                else:
                    print(f"⚠️ stock_id={stock_id} 資料轉換錯誤或無有效價格") 
            else:
                print(f"⚠️ stock_id={stock_id} 的 success 為 False")
        else:
            print(f"⚠️ stock_id={stock_id} realtime 資料不存在")
    
    return stocks_df

# 載入初始股票資料
global g_initial_stocks_df  # 明確宣告為全域變數
g_initial_stocks_df = load_initial_data()

app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.layout = html.Div([
    # 1. Taiwan Stock Realtime Heatmap 大標題 ----------------------------
    html.H1("Taiwan Stock Realtime Heatmap", 
            style={'textAlign': 'center', 'marginBottom': 30}),

    # 2. Display Mode ----------------------------
    html.Div([
        html.Label('Display Mode：', style={'marginRight': '5px', 'display': 'inline-block'}),
        dcc.RadioItems(
            options=[
                {'label': 'Normal Display', 'value': 'equal'},
                {'label': 'Market Cap Display', 'value': 'market'},
                {'label': 'Bubble Chart', 'value': 'bubble'},
                {'label': 'Category Momentum', 'value': 'momentum'}
            ],
            id='display-mode',
            value='equal',
            labelStyle={'display': 'inline-block', 'marginRight': '10px'},
            style={'display': 'inline-block'}
        )
    ], style={'textAlign': 'center', 'marginBottom': 20}),
    
    # 3. Enable Notifications ----------------------------
    html.Div([
        html.Label('Enable Notifications：', style={'marginRight': '5px', 'display': 'inline-block'}),
        daq.ToggleSwitch(
            id='enable-notifications', 
            value=False, 
            label=['Disable', 'Enable'], 
            style={'display': 'inline-block'}
        )
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),
    
    # 4. Last Update Time ----------------------------
    html.Div([
        html.Span("Last Update Time: ", style={'fontWeight': 'bold'}),
        html.Span(id='last-update-time', style={'color': 'blue'})
    ], style={'textAlign': 'center', 'marginBottom': 5}),

    # Category Momentum 控制面板 ----------------------------
    html.Div(id='momentum-controls', children=[
        html.Div([
            html.Label('天數選擇:', style={
                'display': 'inline-block', 
                'marginRight': 10,
                'verticalAlign': 'middle'
            }),
            dcc.Input(
                id='momentum-days-input',
                type='number',
                value=5,
                min=1,
                max=30,
                step=1,
                style={
                    'width': 50,
                    'display': 'inline-block',
                    'verticalAlign': 'middle',
                    'marginRight': 20
                }
            ),
            html.Label('網格大小:', style={
                'display': 'inline-block', 
                'marginRight': 10,
                'verticalAlign': 'middle'
            }),
            dcc.Dropdown(
                id='momentum-grid-size',
                options=[
                    {'label': '1x1', 'value': '1x1'},
                    {'label': '2x2', 'value': '2x2'},
                    {'label': '3x3', 'value': '3x3'},
                    {'label': '4x4', 'value': '4x4'}
                ],
                value='3x3',
                style={
                    'width': 100,
                    'display': 'inline-block',
                    'verticalAlign': 'middle',
                    'marginRight': 20
                }
            ),
            html.Label('頁數:', style={
                    'display': 'inline-block', 
                    'marginRight': 10,
                    'verticalAlign': 'middle'
            }),
            dcc.Dropdown(
                id='momentum-page-dropdown',
                options=[{'label': '第 1 頁', 'value': 1}],
                value=1,
                style={
                    'width': 200,
                    'display': 'inline-block',
                    'verticalAlign': 'middle',
                    'marginRight': 20
                }
            ),
            html.Button(
                '更新資料',
                id='momentum-update-button',
                n_clicks=0,
                style={
                    'display': 'inline-block',
                    'verticalAlign': 'middle',
                    'backgroundColor': '#007bff',
                    'color': 'white',
                    'border': 'none',
                    'padding': '5px 15px',
                    'borderRadius': '3px',
                    'cursor': 'pointer',
                    'marginRight': 10
                }
            ),
            html.Div(id='momentum-status-message', style={
                'textAlign': 'center',
                'color': 'green',
                'display': 'inline-block',
            })
        ], style={'textAlign': 'center', 'marginTop': 20}),

    ], style={'display': 'none', 'marginBottom': 20}),

    # 5. Heatmap or Bubble Chart ----------------------------
    dcc.Graph(id='live-chart'),
    dcc.Interval(id='interval-update', interval=5000, n_intervals=0),
    
    # 6. Stock Link Container ----------------------------
    html.Div(id='stock-link-container', style={'textAlign': 'center', 'marginTop': 20}),

    # 7. Stock Trading Interface ----------------------------
    html.Div([
        html.H1("Stock Trading Interface", style={'textAlign': 'center', 'marginTop': 30}),
        
        # 7-0. Authentication Section ----------------------------
        html.Div([
            html.Div([
                html.Div([
                    html.Label("Cert. Password", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                    dcc.Input(
                        id='auth-code-input',
                        type='text',
                        placeholder='請輸入您的憑證密碼',
                        style={'width': '200px', 'padding': '5px'}
                    )
                ], style={'display': 'inline-block', 'marginRight': '30px'}),
                
                html.Div([
                    html.Label("Account Password：", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                    dcc.Input(
                        id='password-input',
                        type='password',
                        placeholder='請輸入您玉山證券的登入密碼',
                        style={'width': '200px', 'padding': '5px'}
                    )
                ], style={'display': 'inline-block', 'marginRight': '30px'}),
                
                html.Button(
                    "Login",
                    id='login-button',
                    n_clicks=0,
                    style={
                        'backgroundColor': '#007bff',
                        'color': 'white',
                        'border': 'none',
                        'padding': '8px 20px',
                        'borderRadius': '5px',
                        'cursor': 'pointer',
                        'fontSize': '14px'
                    }
                )
            ], style={'textAlign': 'center', 'marginBottom': '15px'}),
            
            # 登入狀態顯示
            html.Div(id='login-status', style={
                'textAlign': 'center', 
                'marginBottom': '20px',
                'fontWeight': 'bold'
            })
        ], style={
            'backgroundColor': '#f8f9fa',
            'border': '1px solid #dee2e6',
            'borderRadius': '8px',
            'padding': '20px',
            'marginBottom': '30px'
        }),
        
        # 7-1. Order Type toggle ----------------------------
        html.Div([
            html.Label("Order Type：", style={'marginRight': '5px', 'display': 'inline-block', 'verticalAlign': 'middle'}),
            daq.ToggleSwitch(id='buy-sell-toggle', value=True, label=['Sell', 'Buy'], 
                           style={'display': 'inline-block', 'marginRight': '20px', 'verticalAlign': 'middle'}),
            html.Label("Trade Type：", style={'marginRight': '5px', 'display': 'inline-block', 'verticalAlign': 'middle'}),
            dcc.Dropdown(
                id='trade_type',
                options=[
                    {'label': '現股', 'value': '現股'},
                    {'label': '融資', 'value': '融資'},
                    {'label': '融券', 'value': '融券'},
                    {'label': '現股當沖賣', 'value': '現股當沖賣'}
                ],
                value='現股',
                style={'display': 'inline-block', 'width': '120px', 'marginRight': '20px', 'verticalAlign': 'middle'}
            ),
            html.Label("Order Type：", style={'marginRight': '5px', 'display': 'inline-block', 'verticalAlign': 'middle'}),
            dcc.Dropdown(
                id='order_type',
                options=[
                    {'label': 'Speed Order', 'value': 'SPEED'},
                    {'label': 'Market Order', 'value': 'MARKET'},
                    {'label': 'Limit Order', 'value': 'LIMIT'}
                ],
                value='SPEED',
                style={'display': 'inline-block', 'width': '120px', 'marginRight': '20px', 'verticalAlign': 'middle'}
            ),
            daq.ToggleSwitch(id='Funding_strategy', value=True, label=['Manual', 'Average'], 
                           style={'display': 'inline-block', 'marginRight': '10px', 'verticalAlign': 'middle'}),
            html.Div(id='average-amount-input', style={'display': 'inline-block', 'verticalAlign': 'middle'})
        ], style={'textAlign': 'center', 'marginBottom': '20px'}),
        
        # 7-2. Category Dropdown ----------------------------
        html.Div([
            html.Label("Select Category："),
            dcc.Dropdown(
                id='group-dropdown',
                options=[{'label': cat, 'value': cat} for cat in g_stock_category],
                placeholder="選擇族群",
                style={'width': '50%', 'margin': '0 auto'}
            )
        ], style={'textAlign': 'center', 'marginBottom': '20px'}),
        
        # 股票輸入區和按鈕
        html.Div(id='stock-input-container', style={'textAlign': 'center', 'marginBottom': '20px'}),
        html.Div([
            html.Button("Refresh", id='refersh-button', n_clicks=0, 
                       style={ 'backgroundColor': "#2863a7", 'color': 'white', 'border': 'none', 'padding': '10px 20px', 'borderRadius': '5px', 'cursor': 'pointer', 'marginRight': '10px' }),
            html.Button("Send Order", id='confirm-order-button', n_clicks=0, 
                       style={ 'backgroundColor': '#dc3545', 'color': 'white', 'border': 'none', 'padding': '10px 20px', 'borderRadius': '5px', 'cursor': 'pointer' })
        ], style={'textAlign': 'center', 'marginBottom': '20px'}),
        html.Div(id='order-status', style={
            'textAlign': 'center', 
            'marginTop': '20px', 
            'padding': '10px',
            'whiteSpace': 'pre-line',  # 允許換行
            'wordBreak': 'break-word',  # 確保長文字會換行
            'maxWidth': '800px',        # 限制最大寬度
            'margin': '20px auto',       # 水平置中
        }),
        
        # 確認對話框
        html.Div(id='order-confirmation-modal',
            children=[html.Div([
                html.Div([
                    html.H3("確認下單資訊", style={'textAlign': 'center', 'marginBottom': '20px'}),
                    html.Div(id='confirmation-details', 
                            style={'marginBottom': '20px', 'padding': '15px', 
                                  'backgroundColor': '#f9f9f9', 'border': '1px solid #ddd'}),
                    html.Div([
                        html.Button("確認下單", id='confirm-final-order', n_clicks=0,
                                  style={'marginRight': '10px', 'backgroundColor': '#28a745',
                                        'color': 'white', 'border': 'none', 
                                        'padding': '10px 20px', 'borderRadius': '5px'}),
                        html.Button("取消", id='cancel-order', n_clicks=0,
                                  style={'backgroundColor': '#dc3545', 'color': 'white',
                                        'border': 'none', 'padding': '10px 20px', 'borderRadius': '5px'})
                    ], style={'textAlign': 'center'})
                ], style={'backgroundColor': 'white', 'margin': '50px auto', 'padding': '30px',
                         'width': '60%', 'borderRadius': '10px', 
                         'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'})
            ], style={'position': 'fixed', 'top': '0', 'left': '0', 'width': '100%',
                     'height': '100%', 'backgroundColor': 'rgba(0, 0, 0, 0.5)', 'zIndex': '1000'})],
            style={'display': 'none'}
        )
    ]),

    # 8. Stock Transaction List ----------------------------
    html.Div([
        html.H1("Stock Transaction List", style={'textAlign': 'center', 'marginTop': 30}),
        html.Div([
            html.Div("Order Time", style={'width': '9.09%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Stock", style={'width': '9.09%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Action", style={'width': '9.09%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Trade Type", style={'width': '9.09%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Order Price", style={'width': '9.09%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Order Quantity(股)", style={'width': '9.09%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Cancelled Quantity", style={'width': '9.09%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Filled Quantity", style={'width': '9.09%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Average Fill Price", style={'width': '9.09%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Order No.", style={'width': '9.09%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Cancel", style={'width': '9.09%', 'display': 'inline-block', 'fontWeight': 'bold'})
        ], style={'backgroundColor': '#f0f0f0', 'padding': '10px', 'marginBottom': '5px'}),
        html.Div(id='transaction-list-container', style={'maxHeight': '300px', 'overflowY': 'auto', 'border': '1px solid #ddd'}),
        # Transaction List Buttons
        html.Div([
            html.Button("Refresh", id='transaction-refresh-button', n_clicks=0,
                       style={ 'backgroundColor': '#2863a7', 'color': 'white', 'border': 'none', 'padding': '10px 20px', 'borderRadius': '5px', 'cursor': 'pointer', 'marginRight': '10px' }),
            html.Button("Cancel All", id='transaction-cancel-all-button', n_clicks=0,
                       style={ 'backgroundColor': '#dc3545', 'color': 'white', 'border': 'none', 'padding': '10px 20px', 'borderRadius': '5px', 'cursor': 'pointer' })
        ], style={'marginTop': '10px', 'textAlign': 'center'})
    ], style={'marginTop': '20px', 'marginBottom': '30px', 'textAlign': 'center'}),

    # 9. Stock Inventory List ----------------------------
    html.Div([
        html.H1("Stock Inventory List", style={'textAlign': 'center', 'marginTop': 30}),
        html.Div([
            html.Div("Trade Type", style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Symbol", style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Remaining Shares", style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Current Price", style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Average Price", style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Balance Price", style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Market Value", style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Value Ratio", style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Unrealized P&L", style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("Profit Rate", style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'})

        ], style={'backgroundColor': '#f0f0f0', 'padding': '10px', 'marginBottom': '5px'}),
        html.Div(id='inventory-list-container', style={'maxHeight': '300px', 'overflowY': 'auto', 'border': '1px solid #ddd'}),
        # Inventory List Button
        html.Div([
            html.Button("Refresh", id='inventory-refresh-button', n_clicks=0,
                       style={'backgroundColor': '#2863a7', 'color': 'white', 'border': 'none', 'padding': '10px 20px', 'borderRadius': '5px', 'cursor': 'pointer', 'marginRight': '10px'}),
            html.Button("Add Category", id='add-category-button', n_clicks=0,
                       style={'backgroundColor': '#28a745', 'color': 'white', 'border': 'none', 'padding': '10px 20px', 'borderRadius': '5px', 'cursor': 'pointer', 'marginRight': '10px'}),
            html.Button("Key In", id='key-in-button', n_clicks=0,
                       style={'backgroundColor': '#ffc107', 'color': 'white', 'border': 'none', 'padding': '10px 20px', 'borderRadius': '5px', 'cursor': 'pointer'})
        ], style={'marginTop': '10px', 'textAlign': 'center'}),
        html.Div(id='add-category-status', style={
            'textAlign': 'center',
            'marginTop': '20px',
            'padding': '10px',
            'whiteSpace': 'pre-line',  # 允許換行
            'wordBreak': 'break-word',  # 確保長文字會換行
            'maxWidth': '800px',        # 限制最大寬度
            'margin': '20px auto',       # 水平置中
        })
    ], style={'marginTop': '20px', 'marginBottom': '30px', 'textAlign': 'center'})

])

# 控制 momentum 控制面板的顯示/隱藏
@app.callback(
    Output('momentum-controls', 'style'),
    Input('display-mode', 'value')
)
def toggle_momentum_controls(display_mode):
    """根據顯示模式來控制 momentum 控制面板的顯示"""
    if display_mode == 'momentum':
        return {'display': 'block', 'marginBottom': 20}
    else:
        return {'display': 'none', 'marginBottom': 20}

# 動態更新 momentum 頁數選項
@app.callback(
    [Output('momentum-page-dropdown', 'options'),
     Output('momentum-page-dropdown', 'value')],
    [Input('momentum-grid-size', 'value'),
     Input('momentum-update-button', 'n_clicks')],
    State('momentum-days-input', 'value'),  # 添加天數作為 State
    prevent_initial_call=True
)
def update_momentum_page_options(grid_size, n_clicks, days):
    """根據網格大小更新頁數選項"""
    try:
        # 載入分類資料來計算總頁數
        with open('./my_stock_category.json', 'r', encoding='utf-8') as f:
            category_data = json.load(f)
        
        total_categories = len(category_data.get('台股', {}))
        
        # 根據網格大小計算每頁項目數
        grid_configs = {
            "1x1": 1,
            "2x2": 4,
            "3x3": 9,
            "4x4": 16
        }
        items_per_page = grid_configs.get(grid_size, 4)
        
        if grid_size == "1x1":
            # 1x1 模式：顯示群組名稱，需要取得類別資料並排序
            try:
                # 使用與圖表顯示相同的天數
                actual_days = days if days and days > 0 else 15
                date_files = get_section_category_momentum_data("../raw_stock_data/daily/tpex", actual_days)
                stocks_info = get_unique_stocks(category_data)
                
                twse_path = "../raw_stock_data/daily/twse"
                tpex_path = "../raw_stock_data/daily/tpex"
                momentum_data = collect_stock_momentum(twse_path, tpex_path, date_files, stocks_info)
                category_momentum = calculate_category_momentum(category_data, momentum_data)
                
                # 使用共用的排序函數
                category_avg_momentum = get_sorted_categories(category_momentum)
                
                page_options = [{'label': f"{cat[0]} ({cat[1]:.2f}%)", 'value': i+1} 
                              for i, cat in enumerate(category_avg_momentum)]
                
            except Exception as e:
                # 如果出錯，使用類別名稱作為備選
                categories = list(category_data.get('台股', {}).keys())
                page_options = [{'label': f"{cat}", 'value': i+1} 
                              for i, cat in enumerate(categories)]
        else:
            # 其他模式：顯示頁數
            total_pages = math.ceil(total_categories / items_per_page)
            page_options = [{'label': f'第 {i} 頁', 'value': i} for i in range(1, total_pages + 1)]
        
        return page_options, 1  # 重置到第1頁或第1個群組
        
    except Exception as e:
        return [{'label': '第 1 頁', 'value': 1}], 1

# 動態更新 momentum 頁數下拉選單的樣式
@app.callback(
    Output('momentum-page-dropdown', 'style'),
    Input('momentum-grid-size', 'value'),
    prevent_initial_call=True
)
def update_momentum_page_dropdown_style(grid_size):
    """根據網格大小調整下拉選單的樣式"""
    base_style = {
        'width': 200,
        'display': 'inline-block',
        'verticalAlign': 'middle',
        'marginRight': 20
    }
    
    if grid_size == "1x1":
        # 1x1 模式使用較小的字體
        base_style['fontSize'] = '12px'
    else:
        # 其他模式使用正常字體
        base_style['fontSize'] = '14px'
    
    return base_style

# 專門處理 momentum 模式的更新
@app.callback(
    [Output('live-chart', 'figure', allow_duplicate=True),
     Output('momentum-status-message', 'children')],
    [Input('momentum-update-button', 'n_clicks'),
     Input('momentum-grid-size', 'value'),
     Input('momentum-page-dropdown', 'value')],
    State('momentum-days-input', 'value'),
    prevent_initial_call=True
)
def update_momentum_chart(n_clicks, grid_size, page, days):
    """更新 momentum 圖表"""
    if not days or days < 1:
        return create_momentum_dashboard()[0], "請輸入有效的天數 (1 ≤ x ≤ 30)"
    
    try:
        fig, status_msg = create_momentum_dashboard(days=days, grid_size=grid_size, page=page)
        return fig, status_msg
    except Exception as e:
        return create_momentum_dashboard()[0], f"更新失敗: {str(e)}"

# 處理登入功能
@app.callback(
    Output('login-status', 'children'),
    Input('login-button', 'n_clicks'),
    [State('auth-code-input', 'value'),
     State('password-input', 'value')],
    prevent_initial_call=True
)
def handle_login(n_clicks, auth_code, password):
    """處理登入驗證"""
    if n_clicks == 0:
        return ''
    
    if not auth_code or not password:
        return html.Div("❌ 請輸入憑證密碼和證券登入密碼", style={'color': 'red'})
    
    result , result_str , trade_sdk , market_sdk = esun_login_with_auth(auth_code , password)

    global g_login_success
    # 模擬登入驗證過程
    if result:
        g_login_success = True
        # 取得交易額度資訊
        limits = esun_get_trade_limits()
        # 組合顯示訊息
        return html.Div([
            html.Div("✅ 登入成功！", style={'color': 'green', 'marginBottom': '10px'}),
            html.Div([
                html.Span("💰 交易額度: ", style={'fontWeight': 'bold'}),
                html.Span(f"${limits['trade_limit']:,.0f}", style={'color': 'blue'}),
                html.Span(" | 💳 融資額度: ", style={'fontWeight': 'bold', 'marginLeft': '15px'}),
                html.Span(f"${limits['margin_limit']:,.0f}", style={'color': 'blue'}),
                html.Span(" | 📊 融券額度: ", style={'fontWeight': 'bold', 'marginLeft': '15px'}),
                html.Span(f"${limits['short_limit']:,.0f}", style={'color': 'blue'})
            ])
        ])
    else:
        g_login_success = False
        return html.Div("❌ 登入失敗：" + f"{result_str}" , style={'color': 'red'})


@app.callback(
    [Output('live-chart', 'figure'),
     Output('last-update-time', 'children')],
    [Input('interval-update', 'n_intervals'),
     Input('display-mode', 'value'),
     Input('enable-notifications', 'value')],  # 新增通知開關的輸入
    [State('momentum-days-input', 'value'),
     State('momentum-grid-size', 'value'),
     State('momentum-page-dropdown', 'value')]  # 新增 momentum 控制面板狀態
)
def update_treemap(n, display_mode, enable_notifications, momentum_days, momentum_grid_size, momentum_page):
    
    updated_stocks_df = update_realtime_data(g_initial_stocks_df.copy()) # 更新即時股價
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 取得當前時間

    # 準備 treemap 資料
    display_data = []
    df_transposed = updated_stocks_df.T

    # # 設定 pandas 顯示選項，確保完整顯示
    # with pd.option_context('display.max_rows', None, 
    #                       'display.max_columns', None,
    #                       'display.width', None,
    #                       'display.max_colwidth', None):
    #     print(df_transposed.to_string())
    
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
            display_data.append({
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
    display_df = pd.DataFrame(display_data)

    # 根據顯示模式決定區塊大小
    if display_mode == 'equal' or display_mode == 'market':

        if display_mode == 'equal': # 平均大小模式，所有區塊大小相同
            values = [1] * len(display_df)
        elif display_mode == 'market': # 市值大小模式，分 5 區間
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
            values = display_df['market_value'].apply(map_size).tolist()
            
        # 建立 treemap
        fig = px.treemap(
            display_df,
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

        fig.update_traces(
            marker=dict(cornerradius=5),
            textposition='middle center',
            texttemplate="%{label} %{customdata[1]}<br>%{customdata[2]}<br>%{customdata[3]:.2f}%"
        )
        
        fig.update_layout(
            margin=dict(t=20, l=10, r=10, b=10),
            paper_bgcolor='white',  # 白色背景
            height=900,
            coloraxis_colorbar_tickformat='.2f'
        )

    elif display_mode == 'bubble':
        # Bubble Chart 模式，氣泡大小根據市值加總
        bubble_data = display_df.groupby('category').agg(
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
            range_color=[-10, 10],
            color_continuous_midpoint=0,
            color_continuous_scale='RdYlGn_r',
            title='',
            labels={'mean_change': 'Mean Change (%)', 'total_market_value': 'Total Market Value'},
            hover_name='category',
            size_max=60,
            text='mean_change'  # 改為顯示漲跌幅
        )
        
        # 設定文字顯示格式
        fig.update_traces(
            textposition='top center',
            texttemplate='%{text:.2f}',  # 只顯示漲跌幅，加上百分比符號
            textfont=dict(size=10, color='black')
        )
        
        # 更新布局，設定 Y 軸範圍
        max_abs_change = max(abs(bubble_data['mean_change'].min()), abs(bubble_data['mean_change'].max()))
        y_range = [-max_abs_change * 1.2, max_abs_change * 1.2]

        fig.update_layout(
            xaxis=dict(categoryorder='array', categoryarray=bubble_data['category']),  # X 軸按排序顯示
            yaxis=dict(title='Mean Change (%)', range=y_range),
            margin=dict(t=20, l=10, r=10, b=10),
            paper_bgcolor='white',
            height=900,
            coloraxis_colorbar_tickformat='.2f'
        )
        fig.update_xaxes(tickangle=90, tickfont=dict(size=12))

    elif display_mode == 'momentum':
        global g_first_open_momentum_chart
        if g_first_open_momentum_chart:
            g_first_open_momentum_chart = False
        
        # 使用當前控制面板的狀態，如果沒有值則使用預設值
        days = momentum_days if momentum_days and momentum_days > 0 else 5
        grid_size = momentum_grid_size if momentum_grid_size else "2x2"
        page = momentum_page if momentum_page and momentum_page > 0 else 1
        
        # 創建 Category Momentum 儀表板（使用當前狀態）
        fig, _ = create_momentum_dashboard(days=days, grid_size=grid_size, page=page)

    #發送 Discord 群組漲跌幅通知
    if enable_notifications:  # 只有在通知開關打開時才發送通知
        send_discord_category_notification(display_df, fig)

    return fig, current_time

# 點擊 treemap 顯示外部連結並更新下拉選單
@app.callback(
    [Output('stock-link-container', 'children'),
     Output('group-dropdown', 'value')],
    [Input('live-chart', 'clickData'),
     Input('display-mode', 'value')]
)
def display_stock_link(clickData, display_mode):
    """整合處理 treemap 和 bubble chart 的點擊事件"""
    if not clickData or not clickData['points']:
        return '', None
    
    point = clickData['points'][0]
    selected_category = None
    
    # 取得類別名稱 (bubble chart 用 x，treemap 用 label)
    category = point.get('x') if display_mode == 'bubble' else point.get('label')
    
    # 處理最上層的 "Taiwan Stock" 點擊
    if category == "Taiwan Stock":
        links_div = html.Div([
            html.A("Goodinfo", href="https://goodinfo.tw/tw/index.asp", target="_blank", 
                   style={'fontSize': '18px', 'color': 'blue', 'marginRight': '20px'}),
            html.A("Wantgoo", href="https://www.wantgoo.com/stock", target="_blank", 
                   style={'fontSize': '18px', 'color': 'green', 'marginRight': '20px'}),
            html.A("TradingView - TWSE", href="https://tw.tradingview.com/chart/?symbol=TWSE%3AIX0001",  target="_blank", 
                   style={'fontSize': '18px', 'color': 'black', 'marginRight': '20px'}),
            html.A("TradingView - TPEx", href="https://tw.tradingview.com/chart/?symbol=TPEX%3AIX0118", target="_blank", 
                   style={'fontSize': '18px', 'color': 'black'})
        ], style={'textAlign': 'center', 'marginTop': '10px'})
        return links_div, '上市大盤'
    
    # 處理類股群組點擊
    if category in g_stock_category:
        selected_category = category
        stocks = g_category_json['台股'][category]
        links = []
        
        for stock_id in stocks:
            stock_type = g_initial_stocks_df.loc['stock_type', stock_id]
            prefix = 'TWSE' if stock_type == 'TWSE' else 'TPEX'
            
            # 生成各網站連結
            url_goodinfo = f"https://goodinfo.tw/tw/ShowK_Chart.asp?STOCK_ID={stock_id}"
            url_wantgoo = f"https://www.wantgoo.com/stock/{stock_id}/technical-chart"
            url_tradingView = f"https://tw.tradingview.com/chart/?symbol={prefix}%3A{stock_id}"
            
            # 獲取股票名稱
            stock_name = get_stock_name(stock_id)
            
            links.extend([
                html.A(f"GoodInfo - {stock_id} {stock_name}", href=url_goodinfo, target="_blank", 
                       style={'fontSize': '16px', 'color': 'blue', 'margin': '5px 10px'}),
                html.A(f"Wantgoo - {stock_id} {stock_name}", href=url_wantgoo, target="_blank", 
                       style={'fontSize': '16px', 'color': 'green', 'margin': '5px 10px'}),
                html.A(f"TradingView - {stock_id} {stock_name}", href=url_tradingView, target="_blank", 
                       style={'fontSize': '16px', 'color': 'black', 'margin': '5px 10px'}),
                html.Br()
            ])
        
        links_div = html.Div(links, style={'textAlign': 'center', 'marginTop': '10px', 
                                         'maxHeight': '200px', 'overflowY': 'auto'})
        return links_div, selected_category
    
    # 處理個股點擊 (只在 treemap 模式有效)
    if display_mode != 'bubble':
        try:
            stock_id = point['customdata'][1]
            stock_type = point['customdata'][4]
            prefix = 'TWSE' if stock_type == 'TWSE' else 'TPEX'
            
            url_goodinfo = f"https://goodinfo.tw/tw/ShowK_Chart.asp?STOCK_ID={stock_id}"
            url_wantgoo = f"https://www.wantgoo.com/stock/{stock_id}/technical-chart"
            url_tradingView = f"https://tw.tradingview.com/chart/?symbol={prefix}%3A{stock_id}"
            
            stock_name = get_stock_name(stock_id)

            links_div = html.Div([
                html.A(f"Goodinfo - {stock_id} {stock_name}", href=url_goodinfo, target="_blank", 
                       style={'fontSize': '18px', 'color': 'blue', 'marginRight': '20px'}),
                html.A(f"Wantgoo - {stock_id} {stock_name}", href=url_wantgoo, target="_blank", 
                       style={'fontSize': '18px', 'color': 'green', 'marginRight': '20px'}),
                html.A(f"TradingView - {stock_id} {stock_name}", href=url_tradingView, target="_blank", 
                       style={'fontSize': '18px', 'color': 'black'})
            ], style={'textAlign': 'center', 'marginTop': '10px'})
            return links_div, selected_category
        except:
            pass
    
    return '', None


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
                html.Div("Trade Toggle", style={'width': '8.5%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Stock ID", style={'width': '8.5%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Stock Name", style={'width': '8.5%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Price", style={'width': '8.5%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Volume(張)", style={'width': '8.5%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Odd Price", style={'width': '8.5%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Odd Lots(股)", style={'width': '8.5%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Est. Cost", style={'width': '8.5%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Percentage", style={'width': '8.5%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div("Order Status", style={'width': '20%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            ], style={'marginBottom': '10px', 'backgroundColor': '#f0f0f0', 'padding': '10px'}),
            
            # 股票資訊列
            *[
                html.Div([
                    daq.ToggleSwitch( 
                        id={'type': 'trade-toggle', 'index': stock_id}, 
                        value=True, 
                        label=['Off', 'On'], 
                        style={'width': '8.5%', 'display': 'inline-block'} 
                    ),       
                    html.Div(stock_id, style={'width': '8.5%', 'display': 'inline-block'}), # 股票代號
                    html.Div(stock_info['股票'], style={'width': '8.5%', 'display': 'inline-block'}), # 股票名稱
                    # 價格輸入
                    html.Div(
                        dcc.Input(
                            id={'type': 'price-input', 'index': stock_id},
                            type='number',
                            placeholder='輸入價格',
                            style={'width': '80%'}
                        ),
                        style={'width': '8.5%', 'display': 'inline-block'}
                    ),
                    # 張數輸入
                    html.Div(
                        dcc.Input(
                            id={'type': 'quantity-input', 'index': stock_id},
                            type='number',
                            placeholder='輸入張數',
                            style={'width': '80%'}
                        ),
                        style={'width': '8.5%', 'display': 'inline-block'}
                    ),
                    html.Div(
                        dcc.Input(
                            id={'type': 'odd_price-input', 'index': stock_id},
                            type='number',
                            placeholder='輸入價格',
                            style={'width': '80%'}
                        ),
                        style={'width': '8.5%', 'display': 'inline-block'}
                    ),
                    # 零股顯示
                    html.Div(
                        dcc.Input(
                            id={'type': 'odd-lots-input', 'index': stock_id},
                            type='number',
                            placeholder='輸入股數',
                            style={'width': '80%'}
                        ),
                        style={'width': '8.5%', 'display': 'inline-block'}
                    ),
                    html.Div(id={'type': 'cost-display', 'index': stock_id}, children='0', style={'width': '8.5%', 'display': 'inline-block'}),
                    html.Div(id={'type': 'percentage-display', 'index': stock_id}, children='0%', style={'width': '8.5%', 'display': 'inline-block'}),
                    html.Div(id={'type': 'status-display', 'index': stock_id}, children='Not ordered', style={'width': '20%', 'display': 'inline-block'}),

                ], style={'marginBottom': '5px', 'padding': '5px', 'borderBottom': '1px solid #ddd'})
                for stock_id, stock_info in stocks.items()
            ],
            # 總計行
            html.Div([
                html.Div("", style={'width': '8.5%', 'display': 'inline-block'}),
                html.Div("", style={'width': '8.5%', 'display': 'inline-block'}), 
                html.Div("", style={'width': '8.5%', 'display': 'inline-block'}), 
                html.Div("", style={'width': '8.5%', 'display': 'inline-block'}), 
                html.Div("", style={'width': '8.5%', 'display': 'inline-block'}), 
                html.Div("總計：", style={'width': '8.5%', 'display': 'inline-block', 'fontWeight': 'bold', 'textAlign': 'right'}),
                html.Div("", style={'width': '8.5%', 'display': 'inline-block'}),
                html.Div(id='total-cost-display', children='$0', style={'width': '8.5%', 'display': 'inline-block', 'fontWeight': 'bold', 'color': 'red'}),
                html.Div("100%", style={'width': '8.5%', 'display': 'inline-block', 'fontWeight': 'bold', 'color': 'red'}),
                html.Div("", style={'width': '20%', 'display': 'inline-block'}),
            ], style={'marginTop': '10px', 'padding': '10px', 'backgroundColor': '#f8f8f8', 'borderTop': '2px solid #ddd'})
        ], style={'maxHeight': '400px', 'overflowY': 'auto', 'border': '1px solid #ddd', 'padding': '10px'})

# 整合 refresh 按鈕回調邏輯，依據 Funding_strategy 與 average_amount 狀態分配價格、張數、零股
@app.callback(
    [Output({'type': 'price-input', 'index': ALL}, 'value'),
     Output({'type': 'quantity-input', 'index': ALL}, 'value'),
     Output({'type': 'odd-lots-input', 'index': ALL}, 'value'),
     Output({'type': 'odd_price-input', 'index': ALL}, 'value')],  # 新增 odd_price 輸出
    Input('refersh-button', 'n_clicks'),
    [State('buy-sell-toggle', 'value'),
     State('Funding_strategy', 'value'),
     State('average-amount', 'value'),
     State('group-dropdown', 'value'),
     State({'type': 'trade-toggle', 'index': ALL}, 'value'),
     State({'type': 'trade-toggle', 'index': ALL}, 'id'),
     State({'type': 'price-input', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def refresh_stock_data_all(n_clicks, buy_sell, funding_strategy, average_amount, selected_group, trade_toggles, trade_ids, price_ids):
    """
    重新設計 refresh 的邏輯，整合 refresh_with_average_amount 與 refresh_stock_data
    1. 如果 average-amount 沒有生成 或 Funding_strategy 為 Manual 則只更新價格
    2. 如果 average-amount 有生成但數值為 0，也只更新價格並把 quantity-input 及零股都設為0
    3. 如果 average-amount 有數值則平均分配到有開啟 trade-toggle 的股票
    4. 分配規則：先除以有效股數，得到每個個股可購買金額，換算成可購買零股數，再除以1000將1000零股轉換成1張，剩下餘數為零股
    """
    if n_clicks == 0 or not selected_group:
        raise PreventUpdate

    stock_ids = [trade_id['index'] for trade_id in trade_ids]
    prices = []
    quantities = []
    odd_lots = []
    oddlot_prices = []
    global g_login_success
    
    if g_login_success:
        for i, stock_id in enumerate(stock_ids):
            if trade_toggles[i]:
                # 取得整股價格
                lot_price_data = esun_get_stock_price("LOT", stock_id)
                if buy_sell:  
                    if lot_price_data and 'asks' in lot_price_data and len(lot_price_data['asks']) > 0:
                        lot_price = lot_price_data['asks'][0]['price'] # Buy mode - 使用賣價一檔 (ask_price)
                    else:
                        lot_price = 0
                else:        
                    if lot_price_data and 'bids' in lot_price_data and len(lot_price_data['bids']) > 0:
                        lot_price = lot_price_data['bids'][0]['price'] # Sell mode - 使用買價一檔 (bid_price)
                    else:
                        lot_price = 0

                # 取得零股價格
                oddlot_price_data = esun_get_stock_price("ODDLOT", stock_id)
                if buy_sell:
                    if oddlot_price_data and 'asks' in oddlot_price_data and len(oddlot_price_data['asks']) > 0:
                        oddlot_price = oddlot_price_data['asks'][0]['price']
                    else:
                        oddlot_price = 0

                else:
                    if lot_price_data and 'bids' in oddlot_price_data and len(oddlot_price_data['bids']) > 0:
                        oddlot_price = oddlot_price_data['bids'][0]['price']
                    else:
                        oddlot_price = 0

                prices.append(lot_price)
                oddlot_prices.append(oddlot_price)
            else:
                prices.append(None)
                oddlot_prices.append(None)
    else:
        # 取得即時價格
        for i, stock_id in enumerate(stock_ids):
            if trade_toggles[i]:
                if stock_id in g_track_stock_realtime_data and 'realtime' in g_track_stock_realtime_data[stock_id]:
                    if g_track_stock_realtime_data[stock_id]['success']:
                        realtime_data = g_track_stock_realtime_data[stock_id]['realtime']
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
                        oddlot_prices.append(None)
                    else:
                        prices.append(0)
                        oddlot_prices.append(None)
                else:
                    prices.append(0)
                    oddlot_prices.append(None)
            else:
                prices.append(None)
                oddlot_prices.append(None)

    # Manual 模式或 average-amount 未生成或為 0
    if not funding_strategy or average_amount is None:
        quantities = [0 if trade_toggles[i] else None for i in range(len(stock_ids))]
        odd_lots = [0 if trade_toggles[i] else None for i in range(len(stock_ids))]
        return prices, quantities, odd_lots, oddlot_prices

    if average_amount == 0:
        quantities = [0 if trade_toggles[i] else None for i in range(len(stock_ids))]
        odd_lots = [0 if trade_toggles[i] else None for i in range(len(stock_ids))]
        return prices, quantities, odd_lots, oddlot_prices

    # 平均分配投資金額
    valid_indices = [i for i, price in enumerate(prices) if trade_toggles[i] and price is not None and price > 0]
    valid_count = len(valid_indices)
    if valid_count == 0:
        quantities = [0 if trade_toggles[i] else None for i in range(len(stock_ids))]
        odd_lots = [0 if trade_toggles[i] else None for i in range(len(stock_ids))]
        return prices, quantities, odd_lots, oddlot_prices

    amount_per_stock = average_amount / valid_count
 
    for i, (price, odd_price) in enumerate(zip(prices, oddlot_prices)):
        if i in valid_indices:
            if g_login_success:
                total_shares = int(amount_per_stock / price)
                full_lots = total_shares // 1000
                Remaining_amount = amount_per_stock - (full_lots * 1000 * price)
                odd_share = int(Remaining_amount / odd_price)
            else:
                total_shares = int(amount_per_stock / price)
                full_lots = total_shares // 1000
                odd_share = total_shares % 1000
            quantities.append(full_lots)
            odd_lots.append(odd_share)
        else:
            quantities.append(0 if trade_toggles[i] else None)
            odd_lots.append(0 if trade_toggles[i] else None)

    return prices, quantities, odd_lots, oddlot_prices

# 添加實時更新成本顯示的回調
@app.callback(
    [Output({'type': 'cost-display', 'index': ALL}, 'children'),
     Output({'type': 'percentage-display', 'index': ALL}, 'children'),
     Output('total-cost-display', 'children')],
    [Input({'type': 'price-input', 'index': ALL}, 'value'),
     Input({'type': 'quantity-input', 'index': ALL}, 'value'),
     Input({'type': 'odd_price-input', 'index': ALL}, 'value'),  # 新增 odd_price-input
     Input({'type': 'odd-lots-input', 'index': ALL}, 'value'),
     Input('Funding_strategy', 'value'),
     Input('average-amount', 'value'),
     Input({'type': 'trade-toggle', 'index': ALL}, 'value')],
    prevent_initial_call=True
)
def update_cost_display(prices, quantities, odd_prices, odd_lots, funding_strategy, average_amount, trade_toggles):
    """實時更新估算成本、百分比和總計，odd-lots-input 為 input"""
    costs = []
    percentages = []
    total_cost = 0
    individual_costs = []

    # 計算個別成本與總成本（張數與零股都要算）
    for price, quantity, odd, odd_price in zip(prices, quantities, odd_lots, odd_prices):
        if price is not None and price > 0:
            q = quantity if quantity is not None and quantity > 0 else 0
            o = odd if odd is not None and odd > 0 else 0
            o_prices = odd_price if odd_price is not None and odd_price > 0 else price
            cost = (price * q * 1000) + (o * o_prices)
            individual_costs.append(cost)
            total_cost += cost
        else:
            individual_costs.append(0)

    # 計算百分比
    for i, cost in enumerate(individual_costs):
        if not trade_toggles[i]:
            costs.append("0")
            percentages.append("0%")
            continue
        costs.append(f"${cost:,.0f}")
        if total_cost > 0:
            percentage = (cost / total_cost) * 100
            percentages.append(f"{percentage:.2f}%")
        else:
            percentages.append("0%")

    return costs, percentages, f"${total_cost:,.0f}"

# 顯示確認對話框
@app.callback(
    [Output('order-confirmation-modal', 'style'),
     Output('confirmation-details', 'children')],
    Input('confirm-order-button', 'n_clicks'),
    [State('buy-sell-toggle', 'value'),
     State('trade_type', 'value'),
     State('Funding_strategy', 'value'),
     State('average-amount', 'value'),
     State('group-dropdown', 'value'),
     State('order_type', 'value'),
     State({'type': 'trade-toggle', 'index': ALL}, 'value'),
     State({'type': 'price-input', 'index': ALL}, 'value'),
     State({'type': 'quantity-input', 'index': ALL}, 'value'),
     State({'type': 'odd-lots-input', 'index': ALL}, 'value'),
     State({'type': 'price-input', 'index': ALL}, 'id'),
     State({'type': 'cost-display', 'index': ALL}, 'children'),
     State({'type': 'odd_price-input', 'index': ALL}, 'value'),
     State('total-cost-display', 'children')],
    prevent_initial_call=True
)
def show_confirmation_modal(n_clicks, buy_sell, trade_type, funding_strategy, average_amount, selected_group, order_type_value, trade_toggles, prices, quantities, odd_lots, ids, cost_displays, odd_price_list, total_cost_display):
    """顯示確認對話框（直接用 cost-display 與 total-cost-display）"""
    if n_clicks == 0 or not selected_group or not prices or not quantities or not odd_lots:
        return {'display': 'none'}, ''

    action = "BUY" if buy_sell else "SELL"
    order_type = order_type_value  # 直接使用下拉選單的值

    order_details = []
    # 檢查是否使用平均投資策略
    if funding_strategy:
        if average_amount:
            order_details.append(html.P(f"💰 投資策略：平均投資，總投資金額：${average_amount:,.0f}", style={'margin': '5px 0', 'fontWeight': 'bold'}))
        else:
            order_details.append(html.P(f"💰 投資策略：平均投資", style={'margin': '5px 0', 'fontWeight': 'bold'}))

    order_details.append(html.P(f"📊 交易方向：{action}", style={'margin': '5px 0', 'fontWeight': 'bold'}))
    order_details.append(html.P(f"🔄 交易模式：{trade_type}", style={'margin': '5px 0', 'fontWeight': 'bold'}))
    order_details.append(html.P(f"📋 訂單類型：{order_type}", style={'margin': '5px 0', 'fontWeight': 'bold'}))
    order_details.append(html.Hr())

    # 添加股票訂單詳情
    stock_orders = []
    global g_category_json
    for i, (price, quantity, odd, stock_id, cost_str, odd_price) in enumerate(zip(prices, quantities, odd_lots, ids, cost_displays, odd_price_list)):
        if (i < len(trade_toggles) and trade_toggles[i] and
            price is not None and quantity is not None and odd is not None and
            price > 0 and (quantity > 0 or odd > 0)):
            # 依照 selected_group 與 stock_id['index'] 取得股票名稱
            stock_name = g_category_json['台股'].get(selected_group, {}).get(stock_id['index'], {}).get('股票', '')
            order_text = [
                html.Span(f"🏦 {stock_id['index']}", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                html.Span(f"{stock_name}", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                html.Span(f"價格：${price:,.2f}", style={'marginRight': '10px', 'color': 'green'}),
                html.Span(f"張數：{quantity}", style={'marginRight': '10px'}),
            ]
            if odd > 0:
                if odd_price is not None and odd_price > 0:
                    order_text.append(html.Span(f"零股價格：${odd_price:,.2f}", style={'marginRight': '10px', 'color': 'blue'}))
                order_text.append(html.Span(f"股數：{odd}股", style={'marginRight': '10px'}))

            order_text.append(html.Span(f"成本：{cost_str}", style={'color': 'red', 'fontWeight': 'bold'}))
            stock_orders.append(
                html.Div(order_text, style={'margin': '5px 0', 'padding': '5px', 'backgroundColor': '#f8f9fa', 'borderRadius': '3px'})
            )

    if not stock_orders:
        return {'display': 'none'}, ''

    order_details.extend(stock_orders)
    order_details.append(html.Hr())
    order_details.append(
        html.P(f"💵 總預估成本：{total_cost_display}", 
               style={'margin': '10px 0', 'fontWeight': 'bold', 'fontSize': '18px', 'color': 'red', 'textAlign': 'center'})
    )

    return {'display': 'block'}, order_details

# 處理確認/取消按鈕
@app.callback(
    [Output('order-confirmation-modal', 'style', allow_duplicate=True),
     Output('order-status', 'children'),
     Output({'type': 'status-display', 'index': ALL}, 'children'),
     Output({'type': 'status-display', 'index': ALL}, 'style')],
    [Input('confirm-final-order', 'n_clicks'),
     Input('cancel-order', 'n_clicks')],
    [State('buy-sell-toggle', 'value'),
     State('trade_type', 'value'),
     State('Funding_strategy', 'value'),
     State('average-amount', 'value'),
     State('group-dropdown', 'value'),
     State({'type': 'trade-toggle', 'index': ALL}, 'value'),
     State({'type': 'price-input', 'index': ALL}, 'value'),
     State({'type': 'quantity-input', 'index': ALL}, 'value'),
     State({'type': 'odd_price-input', 'index': ALL}, 'value'),
     State({'type': 'odd-lots-input', 'index': ALL}, 'value'),
     State({'type': 'price-input', 'index': ALL}, 'id'),
     State('order_type', 'value')],  # 新增 order_type 狀態
    prevent_initial_call=True
)
def handle_confirmation(confirm_clicks, cancel_clicks, buy_sell, trade_type, funding_strategy, average_amount, selected_group, trade_toggles, prices, quantities, odd_price, odd_lots, ids, order_type):
    """處理確認或取消訂單（含零股）"""
    from dash import callback_context

    if not callback_context.triggered:
        return {'display': 'none'}, ''

    button_id = callback_context.triggered[0]['prop_id'].split('.')[0]

    # 初始化狀態消息和樣式（用於取消和確認）
    status_messages = ["Not ordered"] * len(ids)
    status_styles = [{'width': '20%', 'display': 'inline-block'}] * len(ids)

    if button_id == 'cancel-order':
        return {'display': 'none'}, '訂單已取消', status_messages, status_styles

    elif button_id == 'confirm-final-order':
        # 執行實際下單邏輯
        if not selected_group or not prices or not quantities or not odd_lots:
            return {'display': 'none'}, "請填寫完整的下單資訊！", status_messages, status_styles

        global g_login_success
        if not g_login_success:
            return {'display': 'none'}, "請先登入系統！", status_messages, status_styles

        action = "買進" if buy_sell else "賣出"
        orders = []

        # 檢查是否使用平均投資策略
        if funding_strategy:
            if average_amount:
                orders.append(f"使用平均投資策略，總投資金額：${average_amount:,.0f}")
            else:
                orders.append(f"使用平均投資策略")

        # 追蹤每支股票的狀態
        stock_status_map = {}

        # 只處理 Trade Toggle 為 True 的股票
        for i, (price, quantity, odd_lot_price, odd_lot, stock_id) in enumerate(zip(prices, quantities, odd_price, odd_lots, ids)):
            if (i < len(trade_toggles) and trade_toggles[i]):
                stock_no = stock_id['index']
                order_direction = "BUY" if buy_sell else "SELL"
                stock_messages = []
                has_errors = False

                # 處理整股下單
                if quantity is not None and quantity > 0:
                    try:
                        # 根據 order_type 切換下單方式
                        success, message = esun_send_order(
                            stock_id=stock_no,
                            order_dir=order_direction,
                            price_type=order_type,
                            price=price,
                            volume=quantity,
                            is_oddlot="LOT",
                            trade_type_str=trade_type
                        )
                        order_str = f"{action}整股 {stock_no}，價格：${price:,.2f}，張數：{quantity}"
                        if success:
                            stock_messages.append(f"✅ 整股下單成功")
                            orders.append(f"✅ {order_str}")
                        else:
                            stock_messages.append(f"❌ 整股下單失敗: {message}")
                            orders.append(f"❌ {order_str} - {message}")
                            has_errors = True
                        time.sleep(0.5)  # 避免頻繁下單
                    except Exception as e:
                        stock_messages.append(f"❌ 整股下單異常: {str(e)}")
                        orders.append(f"❌ {order_str} - {str(e)}")
                        has_errors = True

                # 處理零股下單
                if odd_lot is not None and odd_lot > 0:
                    try:
                        # 如果沒有零股價格，使用整股價格
                        odd_price_to_use = odd_lot_price if odd_lot_price and odd_lot_price > 0 else price
                        success, message = esun_send_order(
                            stock_id=stock_no,
                            order_dir=order_direction,
                            price_type=order_type,
                            price=odd_price_to_use,
                            volume=odd_lot,
                            is_oddlot="ODDLOT",
                            trade_type_str=trade_type
                        )
                        order_str = f"{action}零股 {stock_no}，價格：${odd_price_to_use:,.2f}，股數：{odd_lot}"
                        if success:
                            stock_messages.append(f"✅ 零股下單成功")
                            orders.append(f"✅ {order_str}")
                        else:
                            stock_messages.append(f"❌ 零股下單失敗: {message}")
                            orders.append(f"❌ {order_str} - {message}")
                            has_errors = True
                        time.sleep(0.5)  # 避免頻繁下單
                    except Exception as e:
                        stock_messages.append(f"❌ 零股下單異常: {str(e)}")
                        orders.append(f"❌ {order_str} - {str(e)}")
                        has_errors = True

                # 更新這支股票的狀態
                if len(stock_messages) > 0:
                    combined_message = "\n".join(stock_messages)
                    style = {'color': 'red' if has_errors else 'green', 'width': '20%', 'display': 'inline-block'}
                    stock_status_map[stock_no] = (combined_message, style)

        if not orders:
            return {'display': 'none'}, "請填寫完整的下單資訊！", status_messages, status_styles
        
        # 設置每支股票的狀態顯示
        for i, stock_id in enumerate(ids):
            current_stock = stock_id['index']
            if current_stock in stock_status_map:
                status_messages[i] = stock_status_map[current_stock][0]
                status_styles[i] = stock_status_map[current_stock][1]

        # 檢查是否所有訂單都成功
        has_any_error = any("❌" in order for order in orders)
        status = "⚠️ 部分下單失敗" if has_any_error else "✅ 所有訂單下單成功！"
        
        # 組合最終訊息
        final_message = f"{status}" + "\n".join(orders)
        return {'display': 'none'}, final_message, status_messages, status_styles

    return {'display': 'none'}, '', status_messages, status_styles


# 處理交易明細列表重新整理按鈕
@app.callback(
    Output('transaction-list-container', 'children'),
    Input('transaction-refresh-button', 'n_clicks'),
    prevent_initial_call=True
)
def refresh_transaction_list(n_clicks):
    if n_clicks == 0:
        raise PreventUpdate

    if not g_login_success:
        return html.Div("請先登入", style={'color': 'red', 'textAlign': 'center'})

    try:
        from test_esun_api import trade_sdk
        transactions = trade_sdk.get_order_results()
        # pprint(transactions)
        if not transactions:
            return html.Div("無交易記錄", style={'textAlign': 'center'})

        transaction_rows = []
        for trans in transactions:
            # 計算可取消股數
            cancel_shares = trans['org_qty_share'] - trans['mat_qty_share'] #都成交完成了 case
            done_cancel_shares = trans['org_qty_share'] - trans['cel_qty_share'] #完整取消所有股數 case
            can_not_cancel = (cancel_shares == 0 or done_cancel_shares == 0 or trans['celable'] == "2")

            # 設定按鈕樣式
            button_style = {
                'backgroundColor': '#dc3545' if not can_not_cancel else '#6c757d',  # 紅色或灰色
                'color': 'white',
                'border': 'none',
                'borderRadius': '3px',
                'cursor': 'pointer' if not can_not_cancel else 'not-allowed',
                'fontSize': '12px',
                'opacity': '1' if not can_not_cancel else '0.65'
            }
            order_id = trans['pre_ord_no'] if trans['pre_ord_no'] != "" else trans['ord_no']

            transaction_rows.append(
                html.Div([
                    html.Div(f"{trans['ord_time'][:2]}:{trans['ord_time'][2:4]}:{trans['ord_time'][4:6]}", style={'width': '9.09%', 'display': 'inline-block'}),
                    html.Div(f"{trans['stock_no']} {get_stock_name(trans['stock_no'])}", style={'width': '9.09%', 'display': 'inline-block'}),
                    html.Div(f"{trans['buy_sell']}", style={'width': '9.09%', 'display': 'inline-block'}),
                    html.Div(f"{esun_get_trade_type_string(trans['trade'])}", style={'width': '9.09%', 'display': 'inline-block'}),
                    html.Div(f"{trans.get('od_price', '-')}", style={'width': '9.09%', 'display': 'inline-block'}),
                    html.Div(f"{trans['org_qty_share']}", style={'width': '9.09%', 'display': 'inline-block'}),
                    html.Div(f"{trans['cel_qty_share']}", style={'width': '9.09%', 'display': 'inline-block'}),
                    html.Div(f"{trans['mat_qty_share']}", style={'width': '9.09%', 'display': 'inline-block'}),
                    html.Div(f"{trans.get('avg_price', '-')}", style={'width': '9.09%', 'display': 'inline-block'}),
                    html.Div(f"{order_id}", style={'width': '9.09%', 'display': 'inline-block'}),
                    html.Div(
                        html.Button("取消", 
                                  id={'type': 'cancel-order-button', 'index': order_id},
                                  n_clicks=0,
                                  disabled=can_not_cancel,  # 如果不能取消則禁用按鈕
                                  style=button_style),
                        style={'width': '9.09%', 'display': 'inline-block'}
                    ),
                ], style={'marginBottom': '5px', 'borderBottom': '1px solid #ddd'})
            )
        
        return transaction_rows

    except Exception as e:
        return html.Div(f"更新失敗: {str(e)}", style={'color': 'red', 'textAlign': 'center'})

# 處理取消所有訂單按鈕
@app.callback(
    Output('transaction-list-container', 'children', allow_duplicate=True),
    Input('transaction-cancel-all-button', 'n_clicks'),
    prevent_initial_call=True
)
def cancel_all_transactions(n_clicks):
    if n_clicks == 0:
        raise PreventUpdate

    if not g_login_success:
        return html.Div("請先登入", style={'color': 'red', 'textAlign': 'center'})

    try:
        from test_esun_api import trade_sdk
        
        # 執行取消所有訂單
        all_success, success_orders, cancel_shares = esun_cancel_all_order()
        
        # 重新取得最新交易列表
        transactions = trade_sdk.get_order_results()
        
        if not transactions:
            return html.Div("目前無交易記錄", style={'textAlign': 'center'})

        # 準備顯示內容
        content = []
        
        # 顯示取消結果訊息
        if success_orders:
            message = html.Div([
                html.Div("訂單取消結果：", 
                        style={'fontWeight': 'bold', 'marginBottom': '5px', 'color': 'black'}),
                *[html.Div(f"✅ 已取消委託單 {order_id}，取消股數：{cancel_shares[order_id]}", 
                          style={'color': 'green', 'marginBottom': '2px'})
                  for order_id in success_orders]
            ], style={'backgroundColor': '#e8f5e9', 'padding': '10px', 'marginBottom': '10px', 'borderRadius': '5px'})
        else:
            message = html.Div("無需要取消的委託單", 
                             style={'color': 'blue', 'padding': '10px', 'marginBottom': '10px', 
                                   'textAlign': 'center', 'backgroundColor': '#e3f2fd', 'borderRadius': '5px'})
        content.append(message)
        
        # 更新交易列表
        transaction_rows = []
        for trans in transactions:
            # 檢查這筆訂單是否可以被取消
            can_cancel = (trans['org_qty_share'] - trans['mat_qty_share'] > 0 and 
                        trans['org_qty_share'] - trans['cel_qty_share'] > 0 and
                        trans['celable'] == "1") # 'celable' -> 1:可取消 2:不可取消 (string)
            order_id = trans['pre_ord_no'] if trans['pre_ord_no'] != "" else trans['ord_no']

            transaction_rows.append(
                html.Div([
                    html.Div(f"{trans['ord_time'][:2]}:{trans['ord_time'][2:4]}:{trans['ord_time'][4:6]}",  style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans['stock_no']}",  style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans['buy_sell']}",  style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans.get('od_price', '-')}",  style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans['org_qty_share']}",  style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans['cel_qty_share']}",  style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans['mat_qty_share']}",  style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans.get('avg_price', '-')}",  style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{order_id}",  style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(
                        html.Button(
                            "取消",
                            id={'type': 'cancel-order-button', 'index': order_id},
                            n_clicks=0,
                            disabled=not can_cancel,
                            style={
                                'backgroundColor': '#dc3545' if can_cancel else '#6c757d',
                                'color': 'white',
                                'border': 'none',
                                'borderRadius': '3px',
                                'cursor': 'pointer' if can_cancel else 'not-allowed',
                                'fontSize': '12px',
                                'opacity': '1' if can_cancel else '0.65'
                            }
                        ),
                        style={'width': '10.0%', 'display': 'inline-block'}
                    ),
                ], style={'marginBottom': '5px', 'borderBottom': '1px solid #ddd'})
            )
        
        content.extend(transaction_rows)
        return content

    except Exception as e:
        return html.Div(f"取消失敗: {str(e)}", style={'color': 'red', 'textAlign': 'center'})

# 處理個別訂單取消按鈕
@app.callback(
    Output('transaction-list-container', 'children', allow_duplicate=True),
    Input({'type': 'cancel-order-button', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def cancel_specific_order(n_clicks_list):
    if not any(n for n in n_clicks_list if n):  # 檢查是否有按鈕被點擊
        raise PreventUpdate

    if not g_login_success:
        return html.Div("請先登入", style={'color': 'red', 'textAlign': 'center'})

    # 找出被點擊的按鈕
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    ord_no = eval(button_id)['index']  # 取得訂單編號

    try:
        from test_esun_api import trade_sdk
        
        # 重新取得最新交易列表
        transactions = trade_sdk.get_order_results()
        if not transactions:
            return html.Div("目前無交易記錄", style={'textAlign': 'center'})
            
        # 取消特定訂單
        success, message = esun_cancel_specific_order(ord_no)
        
        # 準備渲染交易列表和訊息
        content = []
        
        # 加入操作結果訊息
        message_style = {'textAlign': 'center', 'marginBottom': '10px', 'padding': '10px'}
        if not success:
            message_style['color'] = 'red'
            message_style['backgroundColor'] = '#ffebee'
        else:
            message_style['color'] = 'green'
            message_style['backgroundColor'] = '#e8f5e9'
        content.append(html.Div(message, style=message_style))

        # 更新交易列表顯示
        transaction_rows = []
        for trans in transactions:
            # 檢查這筆訂單是否可以被取消
            can_cancel = (trans['org_qty_share'] - trans['mat_qty_share'] > 0 and 
                        trans['org_qty_share'] - trans['cel_qty_share'] > 0 and
                        trans['celable'] == "1") # 'celable' -> 1:可取消 2:不可取消 (string)
            order_id = trans['pre_ord_no'] if trans['pre_ord_no'] != "" else trans['ord_no']

            transaction_rows.append(
                html.Div([
                    html.Div(f"{trans['ord_time'][:2]}:{trans['ord_time'][2:4]}:{trans['ord_time'][4:6]}", style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans['stock_no']}", style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans['buy_sell']}", style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans.get('od_price', '-')}", style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans['org_qty_share']}", style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans['cel_qty_share']}", style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans['mat_qty_share']}", style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{trans.get('avg_price', '-')}", style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(f"{order_id}", style={'width': '10.0%', 'display': 'inline-block'}),
                    html.Div(
                        html.Button(
                            "取消", 
                            id={'type': 'cancel-order-button', 'index': order_id},
                            n_clicks=0,
                            disabled=not can_cancel,  # 如果不能取消就禁用按鈕
                            style={
                                'backgroundColor': '#dc3545' if can_cancel else '#6c757d',
                                'color': 'white',
                                'border': 'none',
                                'borderRadius': '3px',
                                'cursor': 'pointer' if can_cancel else 'not-allowed',
                                'fontSize': '12px',
                                'opacity': '1' if can_cancel else '0.65'
                            }
                        ),
                        style={'width': '10.0%', 'display': 'inline-block'}
                    ),
                ], style={'marginBottom': '5px', 'borderBottom': '1px solid #ddd'})
            )
        
        # 將交易列表加入到內容中
        content.extend(transaction_rows)
        return content

    except Exception as e:
        return html.Div(f"取消失敗: {str(e)}", style={'color': 'red', 'textAlign': 'center'})

@app.callback(
    [Output('add-category-status', 'children'),
     Output('group-dropdown', 'options')],
    Input('add-category-button', 'n_clicks'),
    prevent_initial_call=True
)
def add_inventory_category(n_clicks):
    """新增庫存股票到分類"""
    """1. 要新增到下拉式選單 """
    """2. 要新增我的"庫存類別"到熱力圖中 """

    global g_category_json, g_stock_category, g_initial_stocks_df
    global g_past_json_data_twse, g_past_json_data_tpex, g_company_json_data_twse, g_company_json_data_tpex

    dropdown_options = [{'label': category, 'value': category} for category in g_stock_category]

    if not g_login_success:
        return "請先登入" , dropdown_options

    try:

        inventory_data = esun_format_inventory_data()
        
        if not inventory_data:
            return "無庫存資料可加入" , dropdown_options
        
        if "我的庫存" not in g_stock_category:
            g_stock_category.append("我的庫存")

        if "我的庫存" not in g_category_json['台股']:
            g_category_json['台股']["我的庫存"] = {}
            
            # 收集所有庫存股票
            for item in inventory_data:
                stock_id = item['stock_id']
                stock_name = item['stock_name']
                
                g_category_json['台股']["我的庫存"][stock_id] = {
                    '股票': stock_name
                }

        # 檢查暫停交易股票
        remove_suspended_stocks(g_category_json)
        
        # 更新 g_initial_stocks_df
        for stock_id in g_category_json['台股']["我的庫存"].keys():
            
            # 如果此股票已經在 g_initial_stocks_df 中，則跳過
            if stock_id in g_initial_stocks_df.columns:
                # 如果此股票尚未加入"我的庫存"類別，則加入
                if "我的庫存" not in g_initial_stocks_df[stock_id]['category']:
                    g_initial_stocks_df[stock_id]['category'].append("我的庫存")
                continue
            
            # 獲取股票資訊
            stock_info = get_stock_info(g_past_json_data_twse, g_past_json_data_tpex, 
                                        g_company_json_data_twse, g_company_json_data_tpex, stock_id)

            if stock_info != None:
                if stock_info['last_close_price'] == "":
                    last_stock_price = float('nan')
                else:
                    last_stock_price = float(stock_info['last_close_price'])

            g_initial_stocks_df[stock_id] = {
                'category': ["我的庫存"],
                'stock_type': stock_info['stock_type'],
                'stock_name': stock_info['stock_name'],
                'issue_shares': stock_info['issue_shares'],
                'last_day_price': last_stock_price,
                'realtime_price': float('nan'),
                'realtime_change': float('nan')
            }
        # 構建下拉選單選項
        dropdown_options = [{'label': category, 'value': category} for category in g_stock_category]
        
        return "已將庫存股票加入分類", dropdown_options
        
    except Exception as e:
        return f"新增分類時發生錯誤: {str(e)}", dropdown_options

@app.callback(
    Output('inventory-list-container', 'children'),
    Input('inventory-refresh-button', 'n_clicks'),
    prevent_initial_call=True
)
def update_inventory_list(n_clicks):
    """更新庫存列表"""
    if not g_login_success:
        return html.Div("請先登入", style={'color': 'red', 'textAlign': 'center'})

    try:
            
        formatted_data = esun_format_inventory_data()

        if formatted_data == []:
            return html.Div("無庫存資料", style={'textAlign': 'center'})
        
        # 創建列表項目
        inventory_items = []
        total_unrealized_pl = 0
        total_cost = 0
        total_market_value = 0
        
        # 先計算總市值以便計算比例
        for item in formatted_data:
            total_market_value += float(item['market_value'])
        
        for item in formatted_data:
            # 計算顏色 (紅色表示獲利，綠色表示虧損)
            profit_rate_value = float(item['profit_rate'])
            color = 'red' if profit_rate_value > 0 else 'green'
            
            # 加總成本 與 未實現盈虧
            total_cost += float(item['total_cost'])
            total_unrealized_pl += float(item['unrealized_pl'])
            
            # 計算每支股票占總市值的比例
            stock_market_value = float(item['market_value'])
            market_value_ratio = (stock_market_value / total_market_value * 100) if total_market_value > 0 else 0

            inventory_items.append(html.Div([
                html.Div(item['trade_type'], style={'width': '10.0%', 'display': 'inline-block'}),
                html.Div(item['symbol'], style={'width': '10.0%', 'display': 'inline-block'}),
                html.Div(item['remaining_shares'], style={'width': '10.0%', 'display': 'inline-block'}),
                html.Div(f"{item['current_price']}", style={'width': '10.0%', 'display': 'inline-block'}),
                html.Div(f"{item['average_price']}", style={'width': '10.0%', 'display': 'inline-block'}),
                html.Div(f"{item['balance_price']}", style={'width': '10.0%', 'display': 'inline-block'}),
                html.Div(f"${stock_market_value:,.0f}", style={'width': '10.0%', 'display': 'inline-block'}),
                html.Div(f"{market_value_ratio:.2f}%", style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
                html.Div(f"{item['unrealized_pl']}", style={'width': '10.0%', 'display': 'inline-block', 'color': color}),
                html.Div(f"{item['profit_rate']}%", style={'width': '10.0%', 'display': 'inline-block', 'color': color}),
            ], style={'borderBottom': '1px solid #ddd'}))
        
        # 計算總盈虧率
        total_cost = abs(total_cost)

        if total_cost > 0:
            total_profit_rate = (total_unrealized_pl / total_cost) * 100
        else:
            total_profit_rate = 0
        # print(f"Total Investment: {total_investment}, Total Unrealized PL: {total_unrealized_pl}, Total Cost: {total_cost}")    

        # 設定總計列的顏色
        total_color = 'red' if total_unrealized_pl > 0 else 'green'
        
        # 添加總計列
        total_row = html.Div([
            html.Div("總計", style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("", style={'width': '10.0%', 'display': 'inline-block'}),
            html.Div("", style={'width': '10.0%', 'display': 'inline-block'}),
            html.Div("", style={'width': '10.0%', 'display': 'inline-block'}),
            html.Div("", style={'width': '10.0%', 'display': 'inline-block'}),
            html.Div(f"總成本: ${total_cost:,.0f}",  style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div(f"${total_market_value:,.0f}",  style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold'}),
            html.Div("100.00%",  style={'width': '10.0%', 'display': 'inline-block', 'fontWeight': 'bold', 'color': 'blue'}),
            html.Div(f"${total_unrealized_pl:,.0f}",  style={'width': '10.0%', 'display': 'inline-block', 'color': total_color, 'fontWeight': 'bold'}),
            html.Div(f"{total_profit_rate:.2f}%",  style={'width': '10.0%', 'display': 'inline-block', 'color': total_color, 'fontWeight': 'bold'}),
        ], style={'backgroundColor': '#f8f9fa', 'padding': '10px 0'})
        
        inventory_items.append(total_row)
        return html.Div(inventory_items)
        
    except Exception as e:
        return html.Div(f"更新庫存資料時發生錯誤: {str(e)}", 
                       style={'color': 'red', 'textAlign': 'center'})

if __name__ == '__main__':
    app.run(debug=True)
