import requests
import timenormalyize as tn
import json

dir = 'raw_stock_data'
url = "https://tw.stock.yahoo.com/_td-stock/api/resource/StockServices.symbolCalendars;date={date}T00%3A00%3A00%2B08%3A00-{date}T00%3A00%3A00%2B08%3A00;daysAfter=1;eventType=suspendTransaction;includedFields=pagination;limit=200;offset=0;selectedDate={date}"

out = {}

def get_suspend_trading(date: str):
    tn.normalize_date(date, "CE", "-")
    print(f"Fetching suspend trading data for date: {date}")
    response = requests.get(url.format(date=date))
    # out['date'] = tn.normalize_date(date, "ROC")
    # out['code'] = []
    # datas = response.json()
    # for data in datas['calendars']:
    #     out['code'].append(data['symbol'])

        
    
    with open(f"{dir}/suspend_trading.json", "w", encoding="utf-8") as f:
        json.dump(response.json(), f, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    # date = tn.get_current_date("CE", "-")
    date = '2025-08-05'
    get_suspend_trading(date)
    # Example usage
    # get_suspend_trading("2025-08-06")  # Replace with the desired date

    