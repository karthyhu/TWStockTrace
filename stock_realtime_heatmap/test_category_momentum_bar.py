import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from test_category_momentum_line import get_unique_stocks, collect_stock_momentum, calculate_category_momentum, get_section_category_momentum_data

def plot_momentum_bar_subplots(category_momentum, dates, momentum_data):
    """
    使用子圖表方式呈現各類別漲幅，每個類別一個子圖表，並加入總平均圖表
    
    Args:
        category_momentum (dict): calculate_category_momentum 函式的輸出結果
        dates (list): 日期列表
        momentum_data (dict): collect_stock_momentum 函式的輸出結果
    """
    # 計算每個類別的平均漲幅並排序
    category_avg_momentum = []
    for category, data in category_momentum.items():
        avg_momentum = sum(data['avg_momentum']) / len(data['avg_momentum'])
        # 反轉漲幅列表，使最新的資料在右側
        data['avg_momentum'] = data['avg_momentum'][::-1]
        category_avg_momentum.append((category, avg_momentum, data))
    
    # 依照平均漲幅從高到低排序
    category_avg_momentum.sort(key=lambda x: x[1], reverse=True)
    
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

    # 計算圖表的行列數（每行最多8個圖）
    n_categories = len(category_avg_momentum)
    n_cols = 8
    n_rows = (n_categories + n_cols - 1) // n_cols  # 使用 -1 來確保正確的無條件進位

    # 創建子圖表（包含額外的總平均圖）
    subplot_titles = [f"{cat[0]} (平均: {cat[1]:.2f}%)" for cat in category_avg_momentum]
    subplot_titles.extend([""] * (n_rows * n_cols - len(subplot_titles)))  # 填充空標題
    subplot_titles.append("各類別總平均比較")  # 添加最後一個圖表的標題
    
    fig = make_subplots(
        rows=n_rows + 1,  # 多加一行放總平均圖
        cols=n_cols,
        subplot_titles=subplot_titles,
        vertical_spacing=0.05,
        horizontal_spacing=0.05
    )

    # 為每個類別添加柱狀圖
    for idx, (category, avg_momentum, data) in enumerate(category_avg_momentum):
        row = idx // n_cols + 1
        col = idx % n_cols + 1
        
        # 準備每日漲幅數據
        daily_values = data['avg_momentum']
        
        # 設定顏色（正值為深紅色，負值為灰色）
        colors = ['crimson' if val >= 0 else 'lightslategrey' for val in daily_values]
        
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
        
        # 添加柱狀圖
        fig.add_trace(
            go.Bar(
                x=formatted_dates,
                y=daily_values,
                name=category,
                marker_color=colors,
                marker=dict(
                    line=dict(width=0),
                    cornerradius=3
                ),
                showlegend=False,
                customdata=stock_data,
                hovertemplate=
                f"<b>{category}</b><br>" +
                "日期: %{x}<br>" +
                "類股平均漲幅: %{y:.2f}%<br>" +
                f"類股整體平均: {avg_momentum:.2f}%<br>" +
                "個股漲幅:<br>%{customdata}<extra></extra>"
            ),
            row=row,
            col=col
        )    # 添加總平均比較圖（放在最後一行）
    avg_values = [data[1] for data in category_avg_momentum]
    categories = [data[0] for data in category_avg_momentum]
    colors = ['crimson' if val >= 0 else 'lightslategrey' for val in avg_values]
    
    fig.add_trace(
        go.Bar(
            x=categories,
            y=avg_values,
            name="總平均",
            marker_color=colors,
            marker=dict(
                line=dict(width=0),
                cornerradius=3
            ),
            showlegend=False,
            hovertemplate=
            "類別: %{x}<br>" +
            "平均漲幅: %{y:.2f}%<extra></extra>"
        ),
        row=n_rows + 1,
        col=1,
    )
    
    # 調整最後一個圖表的高度和字體大小
    fig.update_xaxes(
        tickangle=45,
        row=n_rows + 1,
        col=1,
        tickfont=dict(size=10)
    )
    
    # 更新版面設置
    fig.update_layout(
        title='各類股每日漲幅分布與總平均',
        showlegend=False,
        height=250 * n_rows + 400,  # 調整高度，最後一行給予更多空間
        width=2000,                 # 增加寬度以容納更多列
        template='plotly_white',    # 使用白色主題
    )
    
    # 設定最後一個圖表橫跨所有列
    for col in range(2, n_cols + 1):
        fig.update_xaxes(showticklabels=False, row=n_rows + 1, col=col)
        fig.update_yaxes(showticklabels=False, row=n_rows + 1, col=col)
    
    # 更新所有子圖的Y軸範圍，使其一致，並隱藏X軸標籤
    y_min = min(min(data['avg_momentum']) for data in category_momentum.values())
    y_max = max(max(data['avg_momentum']) for data in category_momentum.values())
    for i in range(1, n_categories + 1):
        row = (i - 1) // n_cols + 1
        col = (i - 1) % n_cols + 1
        fig.update_yaxes(range=[y_min - 0.5, y_max + 0.5], row=row, col=col)
        # 隱藏X軸標籤
        fig.update_xaxes(showticklabels=False, row=row, col=col)

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

    # 繪製柱狀圖
    plot_momentum_bar_subplots(category_momentum, momentum_data['dates'], momentum_data)
