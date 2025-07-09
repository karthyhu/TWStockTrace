import json
import os

directory = './raw_stock_data/daily'
files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
print(files)
for file in files:
    with open(os.path.join(directory, file), 'r', encoding='utf-8') as f:
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
    
    with open(os.path.join(directory, file), 'w', encoding='utf-8') as f:
        json.dump(t, f, ensure_ascii=False, indent=2)
    

    
