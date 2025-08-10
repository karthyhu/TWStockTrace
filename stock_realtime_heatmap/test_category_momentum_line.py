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

def get_unique_stocks():
    """
    從 my_stock_category.json 讀取並整理不重複的股票資訊
    
    Returns:
        dict: 股票資訊字典，格式為 {
            'stock_id': {
                'name': '股票名稱',
                'categories': ['分類1', '分類2', ...]
            }
        }
    """
    try:
        # 讀取 my_stock_category.json 檔案
        json_path = os.path.join(os.path.dirname(__file__), 'my_stock_category.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            category_data = json.load(f)
        
        # 使用字典來儲存不重複的股票資訊
        unique_stocks = {}
        
        # 檢查並收集所有股票
        if '台股' in category_data:
            for category_name, stocks in category_data['台股'].items():
                # 將每個分類下的股票資訊加入字典中
                for stock_id, stock_info in stocks.items():
                    # 如果股票不存在，創建新的記錄
                    if stock_id not in unique_stocks:
                        unique_stocks[stock_id] = {
                            'name': stock_info['股票'].strip(),  # 移除可能的空白
                            'categories': [category_name]
                        }
                    # 如果股票已存在，只添加新的分類
                    else:
                        if category_name not in unique_stocks[stock_id]['categories']:
                            unique_stocks[stock_id]['categories'].append(category_name)
        
        return unique_stocks
        
    except FileNotFoundError:
        print(f"錯誤: 找不到 my_stock_category.json 檔案")
        return {}
    except json.JSONDecodeError:
        print(f"錯誤: my_stock_category.json 格式錯誤")
        return {}
    except Exception as e:
        print(f"發生未預期的錯誤: {str(e)}")
        return {}

def collect_stock_momentum(date_files, unique_stocks_dict):
    """
    收集每個股票在特定日期的漲幅資訊
    
    Args:
        date_files (list): 日期檔案名稱列表 (例如: ['1140807.json', '1140806.json'])
        unique_stocks_dict (dict): 不重複股票的字典
        
    Returns:
        dict: 包含每個股票漲幅資訊和日期的字典，格式為:
        {
            'stock_id': {
                'name': '股票名稱',
                'categories': ['分類1', '分類2'],
                'momentum_list': [1.2, -0.5, ...]  # 依照日期順序的漲幅列表
            },
            'dates': ['1140807.json', ...]  # 日期檔案列表
        }
    """
    import json
    import os
    
    result_dict = {}
    base_path_tpex = os.path.join(os.path.dirname(__file__), '..', 'raw_stock_data', 'daily', 'tpex')
    base_path_twse = os.path.join(os.path.dirname(__file__), '..', 'raw_stock_data', 'daily', 'twse')
    
    # 初始化結果字典，保留原有資訊並添加漲幅列表
    for stock_id, stock_info in unique_stocks_dict.items():
        result_dict[stock_id] = {
            'name': stock_info['name'],
            'categories': stock_info['categories'],
            'momentum_list': []  # 用來存放歷史漲幅
        }
    
    # 加入日期檔案列表
    result_dict['dates'] = date_files
    
    # 處理每個日期檔案
    for date_file in date_files:
        # 先嘗試從 TWSE 讀取
        twse_path = os.path.join(base_path_twse, date_file)
        tpex_path = os.path.join(base_path_tpex, date_file)
        
        # 讀取 TWSE 資料
        twse_data = {}
        if os.path.exists(twse_path):
            with open(twse_path, 'r', encoding='utf-8') as f:
                twse_data = json.load(f)
        
        # 讀取 TPEX 資料
        tpex_data = {}
        if os.path.exists(tpex_path):
            with open(tpex_path, 'r', encoding='utf-8') as f:
                tpex_data = json.load(f)
        
        # 對每個股票找尋當日漲幅
        for stock_id in unique_stocks_dict.keys():
            momentum = None
            
            # 先找 TWSE
            if 'data' in twse_data and stock_id in twse_data['data']:
                stock_data = twse_data['data'][stock_id]
                if len(stock_data) > 0:
                    momentum = float(stock_data[-1])  # 取最後一個元素作為漲幅
            
            # 如果在 TWSE 找不到，找 TPEX
            if momentum is None and 'data' in tpex_data and stock_id in tpex_data['data']:
                stock_data = tpex_data['data'][stock_id]
                if len(stock_data) > 0:
                    momentum = float(stock_data[-1])  # 取最後一個元素作為漲幅
            
            # 將漲幅加入結果，如果都找不到就用 0.0
            result_dict[stock_id]['momentum_list'].append(momentum if momentum is not None else 0.0)
    
    return result_dict

def calculate_category_momentum(category_json, momentum_data):
    """
    計算每個類別的平均漲幅
    
    Args:
        category_json (dict): my_stock_category.json 的內容
        momentum_data (dict): collect_stock_momentum 函式的輸出結果
        
    Returns:
        dict: 各類別的平均漲幅資料，格式為:
        {
            '類別名稱': {
                'stocks': ['2330', '2317', ...],  # 該類別包含的股票
                'avg_momentum': [1.2, -0.5, ...], # 該類別每天的平均漲幅
                'stock_count': 3                   # 該類別包含的股票數量
            }
        }
    """
    result = {}
    dates = momentum_data.get('dates', [])
    date_count = len(dates)
    
    # 檢查台股分類
    if '台股' not in category_json:
        return result
        
    # 處理每個類別
    for category_name, stocks in category_json['台股'].items():
        # 初始化該類別的資料
        result[category_name] = {
            'stocks': list(stocks.keys()),
            'avg_momentum': [0.0] * date_count,  # 初始化為0
            'stock_count': len(stocks)
        }
        
        # 計算每天的平均漲幅
        for date_idx in range(date_count):
            momentum_sum = 0.0
            valid_stock_count = 0
            
            # 加總該類別所有股票的漲幅
            for stock_id in stocks.keys():
                if stock_id in momentum_data:
                    momentum = momentum_data[stock_id]['momentum_list'][date_idx]
                    if momentum is not None:  # 如果有有效的漲幅數據
                        momentum_sum += momentum
                        valid_stock_count += 1
            
            # 計算平均值
            if valid_stock_count > 0:
                result[category_name]['avg_momentum'][date_idx] = momentum_sum / valid_stock_count
            else:
                result[category_name]['avg_momentum'][date_idx] = 0.0
                
    return result

def get_section_category_momentum_data(num=10):    
 #default is 2 weeks
    """
    收集最近 n 天的 TPEX JSON 檔案路徑
    Args:
        num: 要收集的天數，預設14天
    Returns:
        list: 檔案路徑列表，由新到舊排序
    """
    from datetime import datetime, timedelta
    import os

    base_path = '../raw_stock_data/daily/tpex'
    file_paths = []
    current_date = datetime.now()
    
    # 收集最近 n 天的檔案路徑
    days_checked = 0
    found_files = 0
    
    while found_files < num:
        check_date = current_date - timedelta(days=days_checked)
        # 轉換西元年為民國年 (yyyy -> yyy)
        year = check_date.year - 1911
        # 格式化檔名 (ex: 1140808.json)
        file_name = f"{year}{check_date.strftime('%m%d')}.json"
        file_path = os.path.join(base_path, file_name)
        
        if os.path.exists(file_path):
            file_paths.append(file_name)
            found_files += 1
            
        days_checked += 1
        
        # 避免無限迴圈，設定最大檢查天數
        if days_checked > 28:  # 設定一個合理的上限
            break

    return file_paths



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
    date_files = get_section_category_momentum_data(10)  # 取得最近10天的資料

    # 取得不重複股票資訊
    stocks_info = get_unique_stocks()

    # 收集漲幅資訊
    momentum_data = collect_stock_momentum(date_files, stocks_info)

    # 計算類別平均漲幅
    category_momentum = calculate_category_momentum(category_data, momentum_data)
    # 印出結果
    # for category, data in category_momentum.items():
    #     print(f"\n類別: {category} (共 {data['stock_count']} 支股票)")
    #     print(f"股票: {', '.join(data['stocks'])}")
    #     print(f"平均漲幅: {[round(x, 2) for x in data['avg_momentum']]}")

    # 繪製漲幅趨勢圖
    plot_momentum_trends(category_momentum, momentum_data['dates'], momentum_data)

    


