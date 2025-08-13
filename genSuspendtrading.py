import requests
import timenormalyize as tn
import json
from datetime import datetime, timedelta

dir = 'raw_stock_data'
url = "https://tw.stock.yahoo.com/_td-stock/api/resource/StockServices.symbolCalendars;date={date}T00%3A00%3A00%2B08%3A00-{date}T00%3A00%3A00%2B08%3A00;daysAfter=1;eventType=suspendTransaction;includedFields=pagination;limit=200;offset=0;selectedDate={date}"
detail_url = "https://tw.stock.yahoo.com/_td-stock/api/resource/StockServices.symbolCalendars;symbol={symbol};"

out = {}

def get_last_trading_day(datas:dict):
    for data in datas['code']:
        try:
            response = requests.get(detail_url.format(symbol=data))
        except requests.RequestException as e:
            print(f"❌ Failed to fetch last trading day for {data}: {e}")
            continue
        detail_datas = response.json()
        stoptrading_l = []
        for ddata in detail_datas['calendars']:
            if ddata['eventTypeName'] == '暫停交易':
                stoptrading_l.append(ddata['date'].split('T')[0])
        stoptrading_l.sort(reverse=False)
        last_stop_trading_day = stoptrading_l[0] if stoptrading_l else None
        
        if last_stop_trading_day:
            # 將字串轉換為 datetime 物件
            stop_date = datetime.strptime(last_stop_trading_day, "%Y-%m-%dT%H:%M:%S%z").date() if 'T' in last_stop_trading_day else datetime.strptime(last_stop_trading_day, "%Y-%m-%d").date()
            
            # 找出前一個工作日（周一至周五）
            days_to_subtract = 1
            if stop_date.weekday() == 0:  # 如果是星期一，前一個工作日是星期五
                days_to_subtract = 3
            elif stop_date.weekday() == 6:  # 如果是星期日（雖然不太可能），前一個工作日是星期五
                days_to_subtract = 2
                
            last_trading_day = (stop_date - timedelta(days=days_to_subtract)).strftime("%Y-%m-%d")
        else:
            last_trading_day = None
            
        datas['code'][data]['last_trading_day'] = tn.normalize_date(last_trading_day, "ROC", "") if last_trading_day else None
        print(f"Last trading day for {data}: {last_trading_day}")
    return


def get_suspend_trading(date: str):
    tn.normalize_date(date, "CE", "-")
    print(f"Fetching suspend trading data for date: {date}")
    response = requests.get(url.format(date=date))
    out['date'] = tn.normalize_date(date, "ROC")
    out['code'] = {}
    datas = response.json()
    for data in datas['calendars']:
        out['code'][data['symbol']] = {'Name': data['symbolName']}

    get_last_trading_day(out)

    with open(f"{dir}/suspend_trading.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    # date = tn.get_current_date("CE", "-")
    date = '2025-08-13'
    get_suspend_trading(date)
    # Example usage
    # get_suspend_trading("2025-08-06")  # Replace with the desired date

    