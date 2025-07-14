import json
import os
import requests
import datetime
import io
import base64
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv()


def load_stock_categories():
    """載入股票分類資料"""
    try:
        with open('./stock_realtime_heatmap/stock_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("股票分類檔案不存在")
        return None

def load_today_stock_data():
    """載入今日股票資料"""
    try:
        with open('./raw_stock_data/daily/today.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("今日股票資料檔案不存在")
        return None

def create_stock_lookup(today_data):
    """建立股票代碼查詢字典"""
    stock_lookup = {}
    for stock in today_data:
        stock_lookup[stock['Code']] = {
            'Name': stock['Name'],
            'Range': stock['Range'],
            'ClosingPrice': stock['ClosingPrice'],
            'Change': stock['Change'],
            'TradeVolume': stock['TradeVolume']
        }
    return stock_lookup

def calculate_category_performance(stock_categories, stock_lookup):
    """計算各類別的漲跌幅表現"""
    category_stats = defaultdict(list)
    
    # 遍歷所有類別和股票
    for category, stocks in stock_categories['台股'].items():
        for stock_code, stock_info in stocks.items():
            if stock_code in stock_lookup:
                range_value = stock_lookup[stock_code]['Range']
                # 更嚴格的數值檢查
                if (isinstance(range_value, (int, float)) and 
                    not pd.isna(range_value) and 
                    range_value != 0 and 
                    abs(range_value) < 50):  # 過濾異常大的漲跌幅
                    category_stats[category].append({
                        'code': stock_code,
                        'name': stock_lookup[stock_code]['Name'],
                        'range': range_value,
                        'price': stock_lookup[stock_code]['ClosingPrice'],
                        'volume': stock_lookup[stock_code]['TradeVolume']
                    })
    
    # 計算每個類別的統計數據
    category_summary = {}
    for category, stocks in category_stats.items():
        if stocks:  # 確保有股票資料
            ranges = [stock['range'] for stock in stocks]
            avg_range = sum(ranges) / len(ranges)
            max_stock = max(stocks, key=lambda x: x['range'])
            min_stock = min(stocks, key=lambda x: x['range'])
            
            category_summary[category] = {
                'avg_range': avg_range,
                'stock_count': len(stocks),
                'max_stock': max_stock,
                'min_stock': min_stock,
                'all_stocks': stocks
            }
    
    return category_summary

def generate_heatmap_image(category_summary, date_str):
    """生成熱力圖圖片"""
    # 設置中文字體和emoji支持
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['font.size'] = 10
    
    # 準備數據
    categories = []
    avg_ranges = []
    stock_counts = []
    
    for category, data in category_summary.items():
        categories.append(category)
        avg_ranges.append(data['avg_range'])
        stock_counts.append(data['stock_count'])
    
    # 創建 DataFrame
    df = pd.DataFrame({
        'Category': categories,
        'Avg_Range': avg_ranges,
        'Stock_Count': stock_counts
    })
    
    # 按漲跌幅排序
    df = df.sort_values('Avg_Range', ascending=False)
    
    # 創建圖表
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # 左側：平均漲跌幅條形圖
    colors = ['#ff4444' if x > 0 else '#00aa00' if x < 0 else '#888888' for x in df['Avg_Range']]
    bars1 = ax1.barh(df['Category'], df['Avg_Range'], color=colors, alpha=0.7)
    ax1.set_xlabel('平均漲跌幅 (%)')
    ax1.set_title('產業類股平均漲跌幅', fontsize=14, fontweight='bold')
    ax1.axvline(x=0, color='black', linestyle='-', alpha=0.3)
    ax1.grid(axis='x', alpha=0.3)
    
    # 在條形圖上添加數值標籤
    for i, (bar, value) in enumerate(zip(bars1, df['Avg_Range'])):
        ax1.text(value + (0.1 if value >= 0 else -0.1), bar.get_y() + bar.get_height()/2, 
                f'{value:.2f}%', ha='left' if value >= 0 else 'right', va='center', fontsize=9)
    
    # 右側：股票數量圓餅圖
    colors_pie = plt.cm.Set3(range(len(df)))
    wedges, texts, autotexts = ax2.pie(df['Stock_Count'], labels=df['Category'], 
                                      colors=colors_pie, autopct='%1.0f檔',
                                      startangle=90)
    ax2.set_title('各產業股票數量分布', fontsize=14, fontweight='bold')
    
    # 調整字體大小
    for text in texts:
        text.set_fontsize(8)
    for autotext in autotexts:
        autotext.set_fontsize(8)
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    # 轉換日期格式
    year = int(date_str[:3]) + 1911
    month = date_str[3:5]
    day = date_str[5:7]
    formatted_date = f"{year}/{month}/{day}"
    
    # 設置總標題
    fig.suptitle(f'[台股產業熱力圖] - {formatted_date}', fontsize=16, fontweight='bold')
    
    # 調整佈局
    plt.tight_layout()
    
    # 保存為圖片
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    img_buffer.seek(0)
    
    plt.close()  # 關閉圖表以釋放記憶體
    
    return img_buffer

def send_heatmap_image_to_discord(category_summary, date_str, webhook_url):
    """發送熱力圖圖片到 Discord"""
    try:
        # 生成圖片
        img_buffer = generate_heatmap_image(category_summary, date_str)
        
        # 準備文件上傳
        files = {
            'file': ('heatmap.png', img_buffer, 'image/png')
        }
        
        # 轉換日期格式
        year = int(date_str[:3]) + 1911
        month = date_str[3:5]
        day = date_str[5:7]
        formatted_date = f"{year}/{month}/{day}"
        
        # 計算統計數據
        all_avg_ranges = [data['avg_range'] for data in category_summary.values()]
        market_avg = sum(all_avg_ranges) / len(all_avg_ranges) if all_avg_ranges else 0
        positive_categories = len([r for r in all_avg_ranges if r > 0])
        negative_categories = len([r for r in all_avg_ranges if r < 0])
        
        # 準備訊息內容
        content = f"🔥 **台股產業熱力圖 - {formatted_date}**\n\n"
        content += f"📊 市場平均: **{market_avg:+.2f}%**\n"
        content += f"🟢 上漲產業: **{positive_categories}** 個\n"
        content += f"🔴 下跌產業: **{negative_categories}** 個\n"
        content += f"📈 總計產業: **{len(category_summary)}** 個"
        
        # 發送請求
        data = {'content': content}
        response = requests.post(webhook_url, data=data, files=files)
        
        return response.status_code == 200 or response.status_code == 204
        
    except Exception as e:
        print(f"生成或發送熱力圖圖片時發生錯誤: {e}")
        return False

def format_heatmap_message(category_summary, date_str):
    """格式化熱力圖訊息"""
    # 轉換日期格式
    year = int(date_str[:3]) + 1911
    month = date_str[3:5]
    day = date_str[5:7]
    formatted_date = f"{year}/{month}/{day}"
    
    # 按平均漲跌幅排序
    sorted_categories = sorted(category_summary.items(), 
                             key=lambda x: x[1]['avg_range'], 
                             reverse=True)
    
    embed = {
        "title": f"🔥 台股產業熱力圖 - {formatted_date}",
        "color": 0xff6b35,  # 橘色
        "fields": [],
        "footer": {
            "text": f"數據時間: {formatted_date} | 共 {len(sorted_categories)} 個產業類別"
        }
    }
    
    # 漲幅前五名類別
    top_categories = sorted_categories[:5]
    if top_categories:
        top_text = ""
        for i, (category, data) in enumerate(top_categories, 1):
            emoji = "🔥" if data['avg_range'] > 2 else "📈" if data['avg_range'] > 0 else "📊"
            top_stock = data['max_stock']
            top_text += f"{emoji} **{category}** ({data['stock_count']}檔)\n"
            top_text += f"   平均: {data['avg_range']:+.2f}% | 領漲: {top_stock['name']} {top_stock['range']:+.2f}%\n\n"
        
        embed["fields"].append({
            "name": "🚀 強勢產業 TOP 5",
            "value": top_text,
            "inline": False
        })
    
    # 跌幅前五名類別
    bottom_categories = sorted_categories[-5:]
    if bottom_categories:
        bottom_text = ""
        for i, (category, data) in enumerate(reversed(bottom_categories), 1):
            emoji = "💥" if data['avg_range'] < -2 else "📉" if data['avg_range'] < 0 else "📊"
            worst_stock = data['min_stock']
            bottom_text += f"{emoji} **{category}** ({data['stock_count']}檔)\n"
            bottom_text += f"   平均: {data['avg_range']:+.2f}% | 領跌: {worst_stock['name']} {worst_stock['range']:+.2f}%\n\n"
        
        embed["fields"].append({
            "name": "📉 弱勢產業 TOP 5",
            "value": bottom_text,
            "inline": False
        })
    
    # 整體市場概況
    all_avg_ranges = [data['avg_range'] for data in category_summary.values()]
    market_avg = sum(all_avg_ranges) / len(all_avg_ranges) if all_avg_ranges else 0
    positive_categories = len([r for r in all_avg_ranges if r > 0])
    negative_categories = len([r for r in all_avg_ranges if r < 0])
    
    market_text = f"📊 市場平均: {market_avg:+.2f}%\n"
    market_text += f"🟢 上漲產業: {positive_categories} 個\n"
    market_text += f"🔴 下跌產業: {negative_categories} 個"
    
    embed["fields"].append({
        "name": "🌍 整體市場概況",
        "value": market_text,
        "inline": False
    })
    
    return embed

def prepare_treemap_data(category_summary, stock_lookup):
    """準備treemap數據，類似Test3.py的結構"""
    treemap_data = []
    
    for category, data in category_summary.items():
        for stock in data['all_stocks']:
            stock_code = stock['code']
            stock_name = stock['name']
            range_value = stock['range']
            
            # 再次確認數值有效性
            if (isinstance(range_value, (int, float)) and 
                not pd.isna(range_value) and 
                abs(range_value) < 50):
                
                # 計算市值 (使用交易量代替)
                market_value = stock['volume'] if stock['volume'] and not pd.isna(stock['volume']) else 1
                
                # 確保股價也是有效數值
                stock_price = stock['price'] if (stock['price'] and not pd.isna(stock['price'])) else 0
                
                treemap_data.append({
                    'stock_meta': 'Taiwan Stock',
                    'stock_id': stock_code,
                    'stock_name': stock_name,
                    'category': category,
                    'realtime_change': range_value,
                    'realtime_price': stock_price,
                    'market_value': market_value
                })
    
    return pd.DataFrame(treemap_data)

def generate_treemap_heatmap(category_summary, stock_lookup, date_str):
    """生成Plotly treemap熱力圖"""
    try:
        # 準備treemap數據
        treemap_df = prepare_treemap_data(category_summary, stock_lookup)
        
        if treemap_df.empty:
            print("無treemap數據可顯示")
            return None
        
        # 轉換日期格式
        year = int(date_str[:3]) + 1911
        month = date_str[3:5]
        day = date_str[5:7]
        formatted_date = f"{year}/{month}/{day}"
        
        # 建立treemap
        fig = px.treemap(
            treemap_df,
            path=['stock_meta', 'category', 'stock_name'],
            values=[1] * len(treemap_df),  # 使用均等大小
            color='realtime_change',
            color_continuous_scale='RdYlGn',  # 紅-黃-綠配色，紅色表示上漲，綠色表示下跌（台股習慣）
            title=f'台股產業熱力圖 - {formatted_date}',
            range_color=[-10, 10],
            color_continuous_midpoint=0,
            hover_data=['stock_id', 'realtime_price', 'market_value'],
            labels={'realtime_change': '漲跌幅 (%)'},
            custom_data=['stock_id', 'realtime_price', 'market_value']
        )
        
        # 自定義文字顯示
        fig.update_traces(
            marker=dict(cornerradius=3), 
            textposition='middle center',
            texttemplate="%{label}<br>%{customdata[0]}<br>%{color:+.2f}%",
            textfont=dict(size=10, color="white"),
            hovertemplate="<b>%{label}</b><br>" +
                         "股票代碼: %{customdata[0]}<br>" +
                         "股價: %{customdata[1]}<br>" +
                         "漲跌幅: %{color:+.2f}%<br>" +
                         "交易量: %{customdata[2]}<br>" +
                         "<extra></extra>"
        )
        
        # 更新佈局
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=80, l=20, r=20, b=20),
            height=800,
            width=1200,
            font=dict(family="Microsoft JhengHei, Arial", size=12),
            title_font=dict(size=20, family="Microsoft JhengHei, Arial"),
            coloraxis_colorbar=dict(
                title="漲跌幅 (%)",
                tickformat='.1f',
                len=0.7
            )
        )
        
        return fig
        
    except Exception as e:
        print(f"生成treemap熱力圖時發生錯誤: {e}")
        return None

def save_treemap_as_image(fig, filename="treemap_heatmap.png"):
    """將treemap圖表保存為圖片"""
    try:
        img_bytes = fig.to_image(format="png", width=1200, height=800, scale=2)
        img_buffer = io.BytesIO(img_bytes)
        return img_buffer
    except Exception as e:
        print(f"保存treemap圖片時發生錯誤: {e}")
        return None

def send_treemap_to_discord(category_summary, stock_lookup, date_str, webhook_url):
    """發送treemap熱力圖到Discord"""
    try:
        # 生成treemap圖表
        fig = generate_treemap_heatmap(category_summary, stock_lookup, date_str)
        if not fig:
            return False
        
        # 保存為圖片
        img_buffer = save_treemap_as_image(fig)
        if not img_buffer:
            return False
        
        # 準備文件上傳
        files = {
            'file': ('treemap_heatmap.png', img_buffer, 'image/png')
        }
        
        # 轉換日期格式
        year = int(date_str[:3]) + 1911
        month = date_str[3:5]
        day = date_str[5:7]
        formatted_date = f"{year}/{month}/{day}"
        
        # 計算統計數據
        all_avg_ranges = [data['avg_range'] for data in category_summary.values()]
        market_avg = sum(all_avg_ranges) / len(all_avg_ranges) if all_avg_ranges else 0
        positive_categories = len([r for r in all_avg_ranges if r > 0])
        negative_categories = len([r for r in all_avg_ranges if r < 0])
        
        # 準備訊息內容
        content = f"📊 **台股產業熱力圖 (Treemap) - {formatted_date}**\n\n"
        content += f"🎯 市場平均: **{market_avg:+.2f}%**\n"
        content += f"🟢 上漲產業: **{positive_categories}** 個\n"
        content += f"🔴 下跌產業: **{negative_categories}** 個\n"
        content += f"📈 總計產業: **{len(category_summary)}** 個\n\n"
        content += "💡 *顏色越紅表示漲幅越大，越綠表示跌幅越大（台股習慣）*"
        
        # 發送請求
        data = {'content': content}
        response = requests.post(webhook_url, data=data, files=files)
        
        return response.status_code == 200 or response.status_code == 204
        
    except Exception as e:
        print(f"發送treemap熱力圖時發生錯誤: {e}")
        return False

def send_heatmap_to_discord(send_image=True, use_treemap=False):
    """發送熱力圖到 Discord
    
    Args:
        send_image (bool): True 發送圖片，False 發送文字訊息
        use_treemap (bool): True 使用treemap，False 使用條形圖+圓餅圖
    """
    try:
        # 讀取 webhook URL
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            print("Discord webhook URL not found. Skipping heatmap notification.")
            return False
        
        # 載入資料
        stock_categories = load_stock_categories()
        today_data = load_today_stock_data()
        
        if not stock_categories or not today_data:
            print("無法載入必要的資料檔案")
            return False
        
        # 建立股票查詢字典
        stock_lookup = create_stock_lookup(today_data)
        
        # 計算類別表現
        category_summary = calculate_category_performance(stock_categories, stock_lookup)
        
        if not category_summary:
            print("沒有找到相符的股票資料")
            return False
        
        # 格式化訊息
        date_str = today_data[0]['Date']
        
        if send_image:
            # 選擇發送treemap或傳統圖表
            if use_treemap:
                success = send_treemap_to_discord(category_summary, stock_lookup, date_str, webhook_url)
                if success:
                    print("📊 產業熱力圖 (Treemap) Discord 通知發送成功！")
                    return True
                else:
                    print("產業熱力圖 (Treemap) 發送失敗，嘗試發送傳統圖表...")
                    use_treemap = False
            
            if not use_treemap:
                # 發送傳統圖表版本
                success = send_heatmap_image_to_discord(category_summary, date_str, webhook_url)
                if success:
                    print("🔥 產業熱力圖圖片 Discord 通知發送成功！")
                    return True
                else:
                    print("產業熱力圖圖片發送失敗，嘗試發送文字版本...")
                    # 如果圖片發送失敗，則發送文字版本
                    send_image = False
        
        if not send_image:
            # 發送文字版本
            embed = format_heatmap_message(category_summary, date_str)
            payload = {"embeds": [embed]}
            response = requests.post(webhook_url, json=payload)
            
            if response.status_code == 204:
                print("🔥 產業熱力圖文字 Discord 通知發送成功！")
                return True
            else:
                print(f"產業熱力圖 Discord 通知發送失敗。狀態碼: {response.status_code}")
                print(f"回應: {response.text}")
                return False
            
    except Exception as e:
        print(f"發送產業熱力圖時發生錯誤: {e}")
        return False

def save_treemap_locally(category_summary, stock_lookup, date_str, filename="treemap_preview.html"):
    """保存treemap為本地HTML檔案以便預覽"""
    try:
        fig = generate_treemap_heatmap(category_summary, stock_lookup, date_str)
        if fig:
            fig.write_html(filename)
            print(f"Treemap已保存為: {filename}")
            return True
        return False
    except Exception as e:
        print(f"保存treemap本地檔案時發生錯誤: {e}")
        return False

def debug_data_quality(today_data, stock_lookup):
    """調試數據質量，檢查NaN值"""
    print("=== 數據質量檢查 ===")
    
    total_stocks = len(today_data)
    valid_ranges = 0
    zero_ranges = 0
    nan_ranges = 0
    invalid_ranges = 0
    
    range_values = []
    
    for stock in today_data:
        range_val = stock['Range']
        
        if pd.isna(range_val):
            nan_ranges += 1
        elif range_val == 0:
            zero_ranges += 1
        elif isinstance(range_val, (int, float)) and abs(range_val) < 50:
            valid_ranges += 1
            range_values.append(range_val)
        else:
            invalid_ranges += 1
            print(f"異常漲跌幅: {stock['Code']} {stock['Name']} - {range_val}")
    
    print(f"總股票數: {total_stocks}")
    print(f"有效漲跌幅: {valid_ranges}")
    print(f"零漲跌幅: {zero_ranges}")
    print(f"NaN漲跌幅: {nan_ranges}")
    print(f"異常漲跌幅: {invalid_ranges}")
    
    if range_values:
        print(f"漲跌幅範圍: {min(range_values):.2f}% ~ {max(range_values):.2f}%")
        print(f"平均漲跌幅: {sum(range_values)/len(range_values):.2f}%")
    
    print("=" * 30)

if __name__ == "__main__":
    # 測試功能
    print("=== 測試台股產業熱力圖功能 ===\n")
    
    # 載入資料進行測試
    stock_categories = load_stock_categories()
    today_data = load_today_stock_data()
    
    if stock_categories and today_data:
        stock_lookup = create_stock_lookup(today_data)
        
        # 調試數據質量
        debug_data_quality(today_data, stock_lookup)
        
        category_summary = calculate_category_performance(stock_categories, stock_lookup)
        date_str = today_data[0]['Date']
        
        print(f"找到 {len(category_summary)} 個有效產業類別")
        
        # 保存treemap為本地HTML檔案供預覽
        print("\n1. 生成本地Treemap預覽檔案...")
        save_treemap_locally(category_summary, stock_lookup, date_str, "treemap_preview.html")
        
        print("\n2. 測試傳統圖表...")
        send_heatmap_to_discord(send_image=True, use_treemap=False)
        
        print("\n3. 測試Treemap熱力圖...")
        send_heatmap_to_discord(send_image=True, use_treemap=True)
        
        print("\n=== 測試完成 ===")
        print("可以開啟 treemap_preview.html 檔案來預覽Treemap效果")
    else:
        print("無法載入必要的資料檔案，請確認檔案存在")
