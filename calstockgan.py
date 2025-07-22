import json
import os

def gan_range(date: str = None):
    directory = './raw_stock_data/daily'

    with open(os.path.join(directory, f'{date}.json'), 'r', encoding='utf-8') as f:
        t = json.load(f)
    
    for i in range(0, len(t)):
        if t[i]['ClosingPrice'] == "" or t[i]['Change'] == "":
            r = 0.0
        else:
            closing_price = float(t[i]['ClosingPrice'])
            change = float(t[i]['Change'])
            # 計算漲跌幅百分比：Change / (ClosingPrice - Change) * 100
            previous_price = closing_price - change
            if previous_price != 0:
                r = (change / previous_price) * 100.0
            else:
                r = 0.0
        t[i]['Range'] = r
    
    #依照range sort
    # t_range['Value'] = sorted(t_range['Value'], key=lambda x: x['range'], reverse=True)
    t = json.dumps(t, ensure_ascii=False, indent=0)

    with open(f'{directory}/today.json', 'w', encoding='utf-8') as f:
        f.write(t)
    with open(f'{directory}/{date}.json', 'w', encoding='utf-8') as f:
        f.write(t)
    return t

