import requests
import json
import os
import calstockgan
import trace_manager
import heatmap_discord
import TPEX_manager
import TWSE_manager
import datetime
import timenormalyize as tn
import genSuspendtrading as gst



def check_and_delete_old_files(directory, max_files=30):
    files = [
        f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))
    ]
    while len(files) >= max_files:
        oldest_file = min(
            files, key=lambda x: os.path.getctime(os.path.join(directory, x))
        )
        os.remove(os.path.join(directory, oldest_file))
        print(f"Deleted old file: {oldest_file}")


def DownlodStockData():
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    res = requests.get(url)
    jsondata = json.loads(res.text)

    # 儲存當日資料
    with open(
        f'./raw_stock_data/daily/{jsondata[0]["Date"]}.json', "w", encoding="utf-8"
    ) as f:
        json.dump(jsondata, f, ensure_ascii=False, indent=0)

    # 同時儲存為 today.json 供其他模組使用
    with open("./raw_stock_data/daily/today.json", "w", encoding="utf-8") as f:
        json.dump(jsondata, f, ensure_ascii=False, indent=0)

    date = f'{jsondata[0]["Date"]}'
    return date


def send_discord_notification():
    """發送當日股票漲跌幅前十名到 Discord"""
    try:
        # 讀取 webhook URL (需要設定環境變數或 .env 檔案)
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

        if not webhook_url:
            print("⚠️ 未設定 DISCORD_WEBHOOK_URL 環境變數，跳過 Discord 通知")
            return

        # 讀取今日股票資料 (使用 TWSE_manager 產生的格式)
        data_file = "./raw_stock_data/daily/twse/today.json"

        if not os.path.exists(data_file):
            print(f"❌ 找不到資料檔案: {data_file}")
            return

        with open(data_file, "r", encoding="utf-8") as f:
            stock_data = json.load(f)

        # 檢查資料格式
        if "data" not in stock_data or "date" not in stock_data:
            print("❌ 資料格式錯誤，缺少 'data' 或 'date' 欄位")
            return

        # 轉換日期格式 (民國年轉西元年)
        date_str = stock_data["date"]
        try:
            year = int(date_str[:3]) + 1911  # 民國轉西元
            month = date_str[3:5]
            day = date_str[5:7]
            formatted_date = f"{year}/{month}/{day}"
        except (ValueError, IndexError):
            formatted_date = date_str

        # 轉換資料格式用於排序 (從 TWSE_manager 的格式轉換)
        stock_list = []
        for code, values in stock_data["data"].items():
            try:
                # values 格式: [Code, Name, ClosingPrice, Change, OpeningPrice, HighestPrice, LowestPrice, TradeVolume, TradeValue, Range]
                stock_info = {
                    "Code": values[0],
                    "Name": values[1],
                    "ClosingPrice": values[2],
                    "Change": values[3],
                    "Range": float(values[9]) if len(values) > 9 else 0.0,
                }
                stock_list.append(stock_info)
            except (IndexError, ValueError, TypeError) as e:
                print(f"⚠️ 處理股票 {code} 資料時發生錯誤: {e}")
                continue

        if not stock_list:
            print("❌ 沒有有效的股票資料")
            return

        # 按漲跌幅排序
        sorted_data = sorted(stock_list, key=lambda x: x["Range"], reverse=True)

        # 取得漲幅前十名和跌幅前十名
        top_gainers = sorted_data[:10]
        top_losers = sorted_data[-10:]  # 取最後十名（跌幅最大）

        # 建立 Discord 訊息
        embed = {
            "title": f"📈 台股漲跌幅排行榜 - {formatted_date}",
            "color": 0x00FF00,  # 綠色
            "fields": [],
            "footer": {
                "text": f"共 {len(stock_list)} 檔股票 | 資料來源: 台灣證券交易所"
            },
        }

        # 漲幅前十名
        if top_gainers:
            gainers_text = ""
            for i, stock in enumerate(top_gainers, 1):
                range_val = stock["Range"]
                if range_val > 0:
                    gainers_text += (
                        f"{i}. **{stock['Code']}** {stock['Name']}: +{range_val:.2f}%\n"
                    )
                else:
                    gainers_text += (
                        f"{i}. **{stock['Code']}** {stock['Name']}: {range_val:.2f}%\n"
                    )

            if gainers_text:
                embed["fields"].append(
                    {"name": "🚀 漲幅前十名", "value": gainers_text, "inline": True}
                )

        # 跌幅前十名
        if top_losers:
            losers_text = ""
            for i, stock in enumerate(
                reversed(top_losers), 1
            ):  # 反轉順序，最跌的排第一
                range_val = stock["Range"]
                losers_text += (
                    f"{i}. **{stock['Code']}** {stock['Name']}: {range_val:.2f}%\n"
                )

            if losers_text:
                embed["fields"].append(
                    {"name": "📉 跌幅前十名", "value": losers_text, "inline": True}
                )

        # 如果沒有任何資料，添加說明
        if not embed["fields"]:
            embed["fields"].append(
                {
                    "name": "ℹ️ 資訊",
                    "value": "今日無漲跌幅資料或資料處理中",
                    "inline": False,
                }
            )

        # 發送到 Discord
        payload = {"embeds": [embed]}

        response = requests.post(webhook_url, json=payload, timeout=10)

        if response.status_code == 204:
            print("✅ Discord 通知發送成功!")
        else:
            print(f"❌ Discord 通知發送失敗. 狀態碼: {response.status_code}")
            print(f"回應: {response.text}")

    except FileNotFoundError as e:
        print(f"❌ 找不到檔案: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析錯誤: {e}")
    except requests.RequestException as e:
        print(f"❌ 網路請求錯誤: {e}")
    except Exception as e:
        print(f"❌ Discord 通知發送時發生未知錯誤: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_and_delete_old_files("./raw_stock_data/daily")
    
    date = tn.get_current_date()
    #格式化成datetime
    date = datetime.datetime.strptime(date, "%Y%m%d")
    date = date - datetime.timedelta(days=1)
    date = tn.normalize_date(date.strftime("%Y%m%d"), "ROC", "-")
    
    print(f"update date data...: {date}")
    
    TWSE_manager.daily_trace(date)

    # date = DownlodStockData()
    # calstockgan.gan_range(date)

    # 更新 trace.json
    # print("\n" + "="*50)
    # print("📊 開始更新股票追蹤資料...")
    # trace_manager.update_trace_json(date)
    # print("="*50 + "\n")

    send_discord_notification()

    # 發送產業熱力圖通知
    print("\n" + "=" * 50)
    print("🔥 開始發送產業熱力圖...")

    # # 先發送treemap版本
    # print("📊 發送Treemap熱力圖...")
    # heatmap_discord.send_heatmap_to_discord(send_image=True, use_treemap=True)

    # 也可選擇發送傳統圖表版本
    print("📈 發送傳統圖表...")
    heatmap_discord.send_heatmap_to_discord(send_image=True, use_treemap=False)

    print("=" * 50 + "\n")

    # 更新 上櫃 資料
    print("開始更新上櫃資料...")
    TPEX_manager.daily_trace(date)
    print("=" * 50 + "\n")
    
    print("開始更新當日暫停交易資料...")
    gst.get_event(date)

    print("Update completed.")
