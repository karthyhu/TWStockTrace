import datetime
import os
import json
import find
import twstock
import time
import requests
import schedule

# 加入上層目錄到 sys.path 以便匯入 timenormalize
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import timenormalyize as tn

base_dir = './Strategy1'
update_trigger_l = {}
date = tn.get_current_date()
date = tn.normalize_date(date, "ROC", "")
find.find_Target(tn.cal_date(date, -1))
data_dir = "./raw_stock_data/daily/twse"
with open("./test.json", "r", encoding="utf-8") as f:
    yesterday = json.load(f)
with open("raw_stock_data/suspend_trading.json", "r", encoding="utf-8") as f:
    suspend_trading = json.load(f)

code_list = [item for item in yesterday]

stop_track = [code.split('.')[0] for code in suspend_trading[tn.normalize_date(date, "CE", "-")].keys()]
code_list = [item for item in yesterday if item not in stop_track]

notify_list = {}

idx = 0
count = 0

def creat_temp_record_data():
    return{
        'last_record_time':'-',
        'last_api_trigger_time':'-',
        'normalized_trade_volume':'-',
        'his_per3_min_time':[],
        'his_per3_min_acc_trade':[],
        'his_per3_min_trade':[]
    }

def save_update_trigger_l():
    print("Saving update_trigger_l to file...")
    global update_trigger_l
    with open(f'{base_dir}/update_trigger.json', "w", encoding="utf-8") as f:
        json.dump(update_trigger_l, f, ensure_ascii=False, indent=1)


def notify_discord():
    """Send a notification to Discord with the stock data."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("⚠️ DISCORD_WEBHOOK_URL is not set.")
        return

    headers = {"Content-Type": "application/json"}

    # 建立 Discord 訊息
    embed = {
        "title": f"Stock Alert Notification",
        # "color": 0x00FF00,  # 綠色
        "fields": [],
    }

    for code, data in notify_list.items():
        embed["fields"].append(
            {
                "name": f"Stock Code: {code}",
                "value": (
                    f"Yesterday Volume: {data['yesvol']}K\n"
                    f"Today Volume: {data['nowvol']}K\n"
                    f"5MA Volume: {data['5maprice']}K\n"
                    f"Current Price: {data['nowprice']}\n"
                    f"Link: [View on Yahoo Finance](https://tw.stock.yahoo.com/quote/{code}/technical-analysis)"
                ),
                "inline": False,
            }
        )

    payload = {"embeds": [embed]}

    try:
        response = requests.post(webhook_url, headers=headers, json=payload)
        response.raise_for_status()
        print("✅ Notification sent successfully.")
    except requests.RequestException as e:
        print(f"❌ Failed to send notification: {e}")
    notify_list.clear()  # 清空通知列表


def update_trigger(code: str, yesvol, nowvol, _5maprice, nowprice):

    if code not in update_trigger_l:
        update_trigger_l[code] = {
            "yesvol": yesvol,
            "nowvol": nowvol,
            "5maprice": _5maprice,
            "nowprice": nowprice,
        }
        print(
            f"code = {code}, yesval = {yesvol}, todayval = {nowvol}, 5maval = {_5maprice}, nowprice = {nowprice}"
        )

        notify_list[code] = update_trigger_l[code]


def trigger_code_NEW(rdatas: dict):
    now = datetime.datetime.now()
    start_t = datetime.datetime.combine(now.date(), datetime.time(9, 0, 0))
    end_t = datetime.datetime.combine(now.date(), datetime.time(13, 30, 0))
    for data in rdatas:
        if data == "success":
            continue
        if data not in update_trigger_l:
            update_trigger_l[data] = creat_temp_record_data()
            print(f"Create new record for {data}")
        _5ma_trade_vol = yesterday[data]["5ma_TradeVolume"] / 1000  # 轉換為千股(張)
        now_acc_trade_vol = float(rdatas[data]["realtime"]["accumulate_trade_volume"])  #本來就是張
        # now_time = rdatas[data]['info']['time'].split(" ")[1]
        # now_time = datetime.datetime.strptime(now_time, "%H:%M:%S")
        # print(f'now_time = {now_time.strftime("%H:%M:%S")}')

        now_time = now
        # now_time = now_time.strftime("%H:%M:%S")
        
        time_percentage = (now_time - start_t) / (end_t - start_t)
        # print(f'time_percentage = {time_percentage}')

        normalized_trade_volume = now_acc_trade_vol * (1 / time_percentage)  # 正規化的成交量

        update_trigger_l[data]['last_record_time'] = now_time.strftime("%H:%M:%S")
        update_trigger_l[data]['last_api_trigger_time'] = rdatas[data]['info']['time'].split(" ")[1]
        update_trigger_l[data]['normalized_trade_volume'] = normalized_trade_volume

        # 每 3 分鐘記錄一次：若分鐘為 3 的倍數，且 (尚無紀錄 或 與上一筆紀錄的 HH:MM 不同) 才新增
        per3_time_list = update_trigger_l[data]['his_per3_min_time']
        current_min_key = now_time.strftime("%H:%M")
        last_min_key = per3_time_list[-1][:5] if per3_time_list else None
        if (now_time.minute % 3 == 0) and (not per3_time_list or current_min_key != last_min_key):
            per3_time_list.append(now_time.strftime("%H:%M:%S"))
            acc_list = update_trigger_l[data]['his_per3_min_acc_trade']
            acc_list.append(str(now_acc_trade_vol))
            trade_list = update_trigger_l[data]['his_per3_min_trade']
            if len(acc_list) == 1:
                trade_list.append('-')  # 第一筆沒有差值
            else:
                try:
                    diff = float(acc_list[-1]) - float(acc_list[-2])
                except ValueError:
                    diff = 0
                trade_list.append(str(diff))
        # if normalized_trade_volume >= _5ma_trade_vol * 2:
        #     print(f'code = {data}, 5matrade = {_5ma_trade_vol}, nowtrade = {now_acc_trade_vol}, time_percentage = {time_percentage}, normalized trade volume = {normalized_trade_volume}')
            # print(f"Code {data} meets the condition.")




def trigger_code(rdatas: dict):
    for data in rdatas:
        if data == "success":
            continue
        # print(f'data = {data}')
        yesday_acc_trade_vol = yesterday[data]["TradeVolume"] / 1000
        yesday_5ma_trade_vol = yesterday[data]["5ma_TradeVolume"] / 1000
        yesday_last_price = float(yesterday[data]["ClosingPrice"])
        # print(yesday_acc_trade_vol)
        today_acc_trade_vol = float(rdatas[data]["realtime"]["accumulate_trade_volume"])

        if rdatas[data]["realtime"]["latest_trade_price"] != "-":
            today_last_price = float(rdatas[data]["realtime"]["latest_trade_price"])
        else:
            today_last_price = 0
        # print(f'{today_last_price}, ')

        # print(today_acc_trade_vol)
        if (
            today_acc_trade_vol >= yesday_5ma_trade_vol * 2
            and today_last_price > yesday_last_price
        ):
            update_trigger(
                data,
                yesday_acc_trade_vol,
                today_acc_trade_vol,
                yesday_5ma_trade_vol,
                today_last_price,
            )
            # print(f'code = {data}, yes = {yesday_acc_trade_vol}, today = {today_acc_trade_vol}')


def get_ontime_data():
    print(".", end='')
    global idx
    if idx + 100 < len(code_list):
        this_list = code_list[idx : idx + 100]
        idx += 100
    else:
        this_list = code_list[idx:]
        idx = 0
        print("")
    # print(this_list)
    try:
        ret = twstock.realtime.get(this_list)
    except Exception as e:
        print(f"An error occurred while fetching data: {e}")
        print(f"Failed to retrieve data for list: {this_list}")
        return
    if ret:  # Check if success is True
        # print("Successfully retrieved data.")
        trigger_code_NEW(ret)
        # trigger_code(ret)
    else:
        print("Failed to ret data.")
        with open("./error.json", "a", encoding="utf-8") as f:
            json.dump(ret, f, ensure_ascii=False, indent=1)
        return
    # with open("./error.json", "a", encoding="utf-8") as f:
    #     json.dump(ret, f, ensure_ascii=False, indent=1)
    if idx == 0:
        save_update_trigger_l()

    # if(len(notify_list) != 0):
    # notify_discord()

schedule.every(2).seconds.do(get_ontime_data)
# schedule.every(1).minutes.do(save_update_trigger_l)

if __name__ == "__main__":
    
    test_count = 0

    # while test_count < 125:
    while True:
        schedule.run_pending()
        time.sleep(1)
        test_count += 1
