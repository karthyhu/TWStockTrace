import sys
import os
import json
import find
import twstock
import time

update_trigger_l = {}


def update_trigger(code: str, yesvol, nowvol, _5maprice, nowprice):

    if code not in update_trigger_l:
        update_trigger_l[code] = {
            "yesvol": yesvol,
            "nowvol": nowvol,
            "5maprice": _5maprice,
            "nowprice": nowprice,
        }
    print(
        f"code = {code}, yes = {yesvol}, today = {nowvol}, 5ma = {_5maprice}, now = {nowprice}"
    )


def trigger_code(rdatas: dict):
    for data in rdatas:
        if data == "success":
            continue
        # print(f'data = {data}')
        yesday_acc_trade_vol = yesterday[data]["TradeVolume"] / 1000
        # print(yesday_acc_trade_vol)
        today_acc_trade_vol = float(rdatas[data]["realtime"]["accumulate_trade_volume"])
        # print(today_acc_trade_vol)
        if today_acc_trade_vol >= yesday_acc_trade_vol * 2:
            update_trigger(
                data,
                yesday_acc_trade_vol,
                today_acc_trade_vol,
                yesterday[data]["5ma_TradeVolume"],
                float(rdatas[data]["realtime"]["accumulate_trade_volume"]),
            )
            # print(f'code = {data}, yes = {yesday_acc_trade_vol}, today = {today_acc_trade_vol}')


if __name__ == "__main__":
    find.find_Target("1140729")
    data_dir = "./raw_stock_data/daily/twse"
    with open("./test.json", "r", encoding="utf-8") as f:
        yesterday = json.load(f)

    code_list = [item for item in yesterday]
    # code_list = [stock_id for stock_id in code_list if stock_id in twstock.codes]

    idx = 0
    count = 0
    while count < 1:
        time.sleep(2)
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
            print("Successfully retrieved data.")
            trigger_code(ret)
        else:
            print(f"Failed to retrieve data for list: {this_list}")
            break

        with open("./error.json", "a", encoding="utf-8") as f:
            json.dump(ret, f, ensure_ascii=False, indent=1)
        count += 1
