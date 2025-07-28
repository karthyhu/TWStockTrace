
import pandas as pd
import sys
import os
import json

data_dir = './raw_stock_data/daily/twse'

def find_Target(date:str):
    files = [f for f in os.listdir(data_dir) if f.endswith('.json') and f != 'today.json']
    files = sorted(files, reverse=True)
    files_idx = files.index(f'{date}.json')
    files = files[files_idx:files_idx+5]
    print(files)

    db = pd.DataFrame()

    for file in files:
        with open(os.path.join(data_dir, file), 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'data' in data:
                df = pd.DataFrame(data['data']).T
                df.columns = data['fields']
                df['Date'] = data['date']
                db = pd.concat([db, df], ignore_index=True)
                #刪除OpeningPrice
                db = db.drop(columns=['OpeningPrice', 'HighestPrice', 'LowestPrice', 'TradeValue'])



    #計算所有股票的五日平均成交量
    db['TradeVolume'] = db['TradeVolume'].astype(float)
    # print(db.groupby('Code').get_group('0050'))
    # print(db.groupby('Code')['TradeVolume'].get_group('0050').mean())
    db['5ma_TradeVolume'] = pd.NA
    mean_volumes = db.groupby('Code')['TradeVolume'].mean()

    for code, group in db.groupby('Code'):
        latest_date_index = group['Date'].idxmax()
        db.loc[latest_date_index, '5ma_TradeVolume'] = mean_volumes[code]

    # 新增計算每個股票的樣本標準差
    db['FiveDaySampleStdDev'] = db.groupby('Code')['TradeVolume'].transform('std')
    db['cv'] = db['FiveDaySampleStdDev'] / db['5ma_TradeVolume']

    # 保留最後一天的資訊
    db = db.groupby('Date').get_group(date)

    db = db[db['cv'] < 0.5]
    print(len(db))


    with open('./test.json', 'w', encoding='utf-8') as f:
        json.dump(db.to_dict(orient='records'), f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    find_Target('1140724')
    with open(f'{data_dir}/1140725.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        data = data['data']
    with open('./test.json', 'r', encoding='utf-8') as f:
        target = json.load(f)
    for item in target:
        # print(item['Code'])
        today_val = data[f"{item['Code']}"][7]
        # print(today_val)
        if float(today_val) >= item['5ma_TradeVolume']*2:
        # if True:
            # range = float(data[f"{item['Code']}"][2]) - float(item['ClosingPrice'])/(float(item['ClosingPrice']) if float(item['ClosingPrice']) != 0 else 1)
            # print(f"item['Code']: {item['Code']}")
            today_c = float(data[f"{item['Code']}"][2])
            yesterday_c = float(item['ClosingPrice'])
            # print(f'today_c = {today_c}, yesterday_c = {yesterday_c}')
            range = (today_c - yesterday_c) / (yesterday_c)
            # print(f"range: {range}")
            if range > 0.05:
                print(f"{item['Code']}, {item['Name']}")
                # print(f'today_c = {today_c}, yesterday_c = {yesterday_c}')
                print(f"range: {round(range, 4)}")

                
