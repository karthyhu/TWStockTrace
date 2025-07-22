import requests  
import json
import os
import calstockgan
import trace_manager
import heatmap_discord
import TPEX_manager

def check_and_delete_old_files(directory, max_files=30):
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    while len(files) >= max_files:
        oldest_file = min(files, key=lambda x: os.path.getctime(os.path.join(directory, x)))
        os.remove(os.path.join(directory, oldest_file))
        print(f"Deleted old file: {oldest_file}")

def DownlodStockData():
    url = 'https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'  
    res = requests.get(url)
    jsondata = json.loads(res.text)
    
    # 儲存當日資料
    with open(f'./raw_stock_data/daily/{jsondata[0]["Date"]}.json', 'w', encoding='utf-8') as f:
        json.dump(jsondata, f, ensure_ascii=False, indent=0)
    
    # 同時儲存為 today.json 供其他模組使用
    with open('./raw_stock_data/daily/today.json', 'w', encoding='utf-8') as f:
        json.dump(jsondata, f, ensure_ascii=False, indent=0)
    
    date = f'{jsondata[0]["Date"]}'
    return date

def send_discord_notification():
    """發送當日股票漲跌幅前十名到 Discord"""
    try:
        # 讀取 webhook URL（支援環境變數和檔案兩種方式）
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        # if not webhook_url:
        #     # 如果環境變數不存在，讀取本地檔案
        #     try:
        #         with open('./discord/webhook_url', 'r', encoding='utf-8') as f:
        #             webhook_url = f.read().strip()
        #     except FileNotFoundError:
        #         print("Discord webhook URL not found. Skipping notification.")
        #         return
        
        # 讀取今日股票資料
        with open('./raw_stock_data/daily/today.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 轉換日期格式
        date_str = data[0]['Date']  # 取第一筆資料的日期
        year = int(date_str[:3]) + 1911  # 民國轉西元
        month = date_str[3:5]
        day = date_str[5:7]
        formatted_date = f"{year}/{month}/{day}"

        # 按漲跌幅排序
        sorted_data = sorted(data, key=lambda x: x['Range'], reverse=True)

        # 取得漲幅前十名和跌幅前十名
        top_gainers = sorted_data[:10]
        top_losers = sorted_data[-10:]  # 取最後十名（跌幅最大）
        
        # 建立 Discord 訊息
        embed = {
            "title": f"📈 台股漲跌幅排行榜 - {formatted_date}",
            "color": 0x00ff00,  # 綠色
            "fields": []
        }
        
        # 漲幅前十名
        if top_gainers:
            gainers_text = ""
            for i, stock in enumerate(top_gainers, 1):
                gainers_text += f"{i}. **{stock['Code']}** {stock['Name']}: +{stock['Range']:.2f}%\n"
            
            embed["fields"].append({
                "name": "🚀 漲幅前十名",
                "value": gainers_text,
                "inline": True
            })
        
        # 跌幅前十名
        if top_losers:
            losers_text = ""
            for i, stock in enumerate(top_losers, 1):
                losers_text += f"{i}. **{stock['Code']}** {stock['Name']}: {stock['Range']:.2f}%\n"
            
            embed["fields"].append({
                "name": "📉 跌幅前十名",
                "value": losers_text,
                "inline": True
            })
        
        # 發送到 Discord
        payload = {
            "embeds": [embed]
        }
        
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code == 204:
            print("Discord notification sent successfully!")
        else:
            print(f"Failed to send Discord notification. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error sending Discord notification: {e}")

if __name__ == "__main__":
    check_and_delete_old_files('./raw_stock_data/daily')
    date = DownlodStockData()
    print(f'update date data...: {date}')
    calstockgan.gan_range(date)

    # 更新 trace.json
    print("\n" + "="*50)
    print("📊 開始更新股票追蹤資料...")
    trace_manager.update_trace_json(date)
    print("="*50 + "\n")
    
    send_discord_notification()
    
    # 發送產業熱力圖通知
    print("\n" + "="*50)
    print("🔥 開始發送產業熱力圖...")
    
    # # 先發送treemap版本
    # print("📊 發送Treemap熱力圖...")
    # heatmap_discord.send_heatmap_to_discord(send_image=True, use_treemap=True)
    
    # 也可選擇發送傳統圖表版本
    print("📈 發送傳統圖表...")
    heatmap_discord.send_heatmap_to_discord(send_image=True, use_treemap=False)
    
    print("="*50 + "\n")
    
    # 更新 上櫃 資料
    print("開始更新上櫃資料...")
    TPEX_manager.daily_trace(date)
    
    print("Update completed.")