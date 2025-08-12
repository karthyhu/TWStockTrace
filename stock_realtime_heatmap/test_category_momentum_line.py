import plotly.express as px
import plotly.graph_objects as go
import json
import pandas as pd
import twstock
import datetime
from pprint import pprint
import time
import requests  
import os
from utility_function import *

def plot_momentum_trends(category_momentum, dates, momentum_data):
    """
    使用 Plotly 繪製各類別漲幅走勢圖，只顯示滑鼠停留的線條資訊
    依照平均漲幅排序
    
    Args:
        category_momentum (dict): calculate_category_momentum 函式的輸出結果
        dates (list): 日期列表
        momentum_data (dict): collect_stock_momentum 函式的輸出結果
    """
    # 準備資料
    fig = go.Figure()
    
    # 處理日期格式 (從 YYYMMDD.json 轉換為 YY/MM/DD)，並反轉順序
    formatted_dates = []
    for date in dates[::-1]:  # 反轉日期列表
        # 去除 .json 副檔名
        date = date.replace('.json', '')
        # 格式化日期
        yy = date[:3]
        mm = date[3:5]
        dd = date[5:]
        formatted_dates.append(f"{yy}/{mm}/{dd}")
    
    # 計算每個類別的平均漲幅並排序
    category_avg_momentum = []
    for category, data in category_momentum.items():
        avg_momentum = sum(data['avg_momentum']) / len(data['avg_momentum'])
        # 反轉漲幅列表，使最新的資料在右側
        data['avg_momentum'] = data['avg_momentum'][::-1]
        category_avg_momentum.append((category, avg_momentum, data))
    
    # 依照平均漲幅從高到低排序
    category_avg_momentum.sort(key=lambda x: x[1], reverse=True)
    
    # 計算三等分的位置
    total_categories = len(category_avg_momentum)
    third_size = total_categories // 3
    
    # 分類每個類別的表現區間
    for i, (category, avg_momentum, data) in enumerate(category_avg_momentum):
        if i < third_size:
            performance = "高漲幅群"
        elif i < 2 * third_size:
            performance = "中漲幅群"
        else:
            performance = "低漲幅群"
        category_avg_momentum[i] = (category, avg_momentum, data, performance)
    
    # 為每個類別添加一條線 (依照排序後的順序)
    total_lines = len(category_avg_momentum)
    for idx, (category, avg_momentum, data, performance) in enumerate(category_avg_momentum):
        # 準備每個時間點的詳細資訊
        hover_texts = []
        category_label = f"{category} ({data['stock_count']}) [{performance}] [avg: {avg_momentum:.2f}%]"
        
        # 其他類別使用漸層顏色（從深紅到深綠）
        gradient_position = idx / (total_lines - 1)  # 0 到 1 之間的值
        red = int(255 * (1 - gradient_position))    # 紅色從255漸變到0
        green = int(255 * gradient_position)        # 綠色從0漸變到255
        color = f'rgb({red}, {green}, 0)'          # 使用RGB格式
        
        # 設定是否預設顯示（中漲幅群預設隱藏）
        visible = True if performance != "中漲幅群" else "legendonly"
        for i in range(len(formatted_dates)):
            stocks_info = []
            for stock_id in data['stocks']:
                if stock_id in momentum_data:
                    stock_momentum = momentum_data[stock_id]['momentum_list'][i]
                    stock_name = momentum_data[stock_id]['name']
                    momentum_str = f"{stock_momentum:.2f}%" if stock_momentum is not None else "N/A"
                    stocks_info.append(f"- {stock_id} {stock_name}: {momentum_str}")
            hover_texts.append("<br>".join(stocks_info))

        # 添加trace
        fig.add_trace(go.Scatter(
            x=formatted_dates,
            y=data['avg_momentum'],
            mode='lines+markers',  # 線條模式
            name=category_label,  # 顯示類別名稱、股票數量和平均漲幅
            text=hover_texts,  # 使用準備好的hover文字
            customdata=hover_texts,  # 用於hover顯示
            visible=visible,  # 設定是否預設顯示
            line=dict(
                shape='spline',  # 使用平滑曲線
                smoothing=0.5,   # 設定平滑度（可以調整 0.8-1.3 之間）
                color=color      # 使用計算出的漸層顏色
            ),
            hovertemplate=
            f"<b>{category}</b><br>" +
            "<b>日期:</b> %{x}<br>" +
            "<b>平均漲幅:</b> %{y:.2f}%<br>" +
            f"<b>股票數:</b> {data['stock_count']}<br>" +
            f"<b>表現分群:</b> {performance}<br>" +
            "<b>成分股漲幅:</b><br>%{customdata}<extra></extra>",  # 使用customdata顯示股票資訊
            hoverlabel=dict(namelength=-1),  # 顯示完整的名稱
        ))
    
    # 設定版面
    fig.update_layout(
        title='各類股漲幅趨勢',
        xaxis_title='日期',
        yaxis_title='漲幅 (%)',
        hovermode='closest',  # 改為只顯示最接近的點
        yaxis=dict(
            range=[min(min(data['avg_momentum']) for data in category_momentum.values()) - 1,
                  max(max(data['avg_momentum']) for data in category_momentum.values()) + 1]
        ),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.05
        ),
        margin=dict(r=150),  # 為圖例留出空間
        hoverdistance=100,      # 增加hover感應距離
        spikedistance=100       # 增加十字線感應距離
    )
    
    # 設定互動配置
    fig.update_traces(
        line=dict(width=2),     # 線條寬度
        marker=dict(size=6),  # 點的大小
    )
    
    # 顯示圖表
    fig.show()

if __name__ == '__main__':
    # 讀取原始分類資料
    with open('my_stock_category.json', 'r', encoding='utf-8') as f:
        category_data = json.load(f)

    # 取得日期檔案列表
    date_files = get_section_category_momentum_data("../raw_stock_data/daily/tpex" , 10)  # 取得最近10天的資料
    
    stocks_info = get_unique_stocks(category_data)

    # 收集漲幅資訊
    twse_path = "../raw_stock_data/daily/twse"
    tpex_path = "../raw_stock_data/daily/tpex"
    momentum_data = collect_stock_momentum(twse_path, tpex_path, date_files, stocks_info)

    # 計算類別平均漲幅
    category_momentum = calculate_category_momentum(category_data, momentum_data)
    # 印出結果
    # for category, data in category_momentum.items():
    #     print(f"\n類別: {category} (共 {data['stock_count']} 支股票)")
    #     print(f"股票: {', '.join(data['stocks'])}")
    #     print(f"平均漲幅: {[round(x, 2) for x in data['avg_momentum']]}")

    # 繪製漲幅趨勢圖
    plot_momentum_trends(category_momentum, momentum_data['dates'], momentum_data)