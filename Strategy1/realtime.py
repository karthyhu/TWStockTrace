import os
import json
import find
import twstock
import time
import random
import requests

update_trigger_l = {}
find.find_Target("1140731")
data_dir = "./raw_stock_data/daily/twse"
with open("./test.json", "r", encoding="utf-8") as f:
    yesterday = json.load(f)

code_list = [item for item in yesterday]
# code_list = [stock_id for stock_id in code_list if stock_id in twstock.codes]

notify_list = {}

idx = 0
count = 0


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
    print(".", end=None)
    global idx, count
    if idx + 50 < len(code_list):
        this_list = code_list[idx : idx + 50]
        idx += 50
    else:
        this_list = code_list[idx:]
        idx = 0
    # print(this_list)
    try:
        ret = twstock.realtime.get(this_list)
    except Exception as e:
        print(f"An error occurred while fetching data: {e}")
    if ret and ret.get("success"):  # Check if success is True
        # print("Successfully retrieved data.")
        trigger_code(ret)
    else:
        print(f"Failed to retrieve data for list: {this_list}")
        with open("./error.json", "a", encoding="utf-8") as f:
            json.dump(ret, f, ensure_ascii=False, indent=1)
    count += 1

    # if(len(notify_list) != 0):
    # notify_discord()


if __name__ == "__main__":

    # while count < 1:
    while True:
        time.sleep(2)
        get_ontime_data()
