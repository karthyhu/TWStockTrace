from configparser import ConfigParser
from esun_trade.sdk import SDK
from esun_trade.order import OrderObject
from esun_trade.constant import (APCode, Trade, PriceFlag, BSFlag, Action)
from esun_marketdata import EsunMarketdata
from pprint import pprint
import sys
from io import StringIO
from datetime import datetime


global config , market_sdk , trade_sdk
def esun_login_with_auth(auth_code, password):

    pre_inputs = [ auth_code , password ]
    sys.stdin = StringIO('\n'.join(pre_inputs))
    
    try:
        # 讀取設定檔
        global config , market_sdk , trade_sdk

        config = ConfigParser()
        config.read('./esun_key_file/config.ini')
        
        trade_sdk = SDK(config)
        trade_sdk.reset_password()
        login_result = trade_sdk.login()
        # print(login_result)
        
        # 檢查登入結果
        if login_result is None:
            market_sdk = EsunMarketdata(config)
            market_sdk.login()
            return True, "登入成功", trade_sdk , market_sdk
        else:
            return False, f"登入失敗: {login_result}", None , None
            
    except Exception as e:
        return False, f"登入過程發生錯誤: {str(e)}", None , None
    

def esun_get_stock_price(type , stock_id):
    
    rest_stock = market_sdk.rest_client.stock
    if type == "ODDLOT":
        try:
            result = rest_stock.intraday.quote(symbol = stock_id , type="oddlot")
        except Exception as e:
            print(f"Failed to get {stock_id} odd price: {e}")
            return None

    elif type == "LOT":
        try:
            result = rest_stock.intraday.quote(symbol = stock_id)
        except Exception as e:
            print(f"Failed to get {stock_id} price: {e}")
            return None
    else:
        print('Not support stock price type')
        return None
    
    return result

def esun_send_onder(stock_id, order_dir, price_type, price, volume, is_oddlot, is_DayTradingSell = "NO"):

    if stock_id == '':
        print('stock id cant be empty')
        return None
    
    if volume == 0:
        print('order volume cant be 0')
        return None

    if order_dir == "BUY":
        send_order_dir = Action.Buy
    elif order_dir == "SELL":
        send_order_dir = Action.Sell
    else:
        print('Incorrect order direction (BUY or SELL?)')
        return None
    
    if is_oddlot == "LOT":
        send_is_oddlot = APCode.Common
    elif is_oddlot == "ODDLOT":
        send_is_oddlot = APCode.IntradayOdd
    else:
        print('Incorrect volume type (LOT or ODDLOT?)')
        return None

    if price_type == "MARKET":
        send_price_type = PriceFlag.Market
        send_price = None
    elif price_type == "LIMIT":
        send_price_type = PriceFlag.Limit
        send_price = price
    elif price_type == "SPEED":
        send_price_type = PriceFlag.Limit
        result = esun_get_stock_price(is_oddlot , stock_id)
        if result == None:
            return None

        if order_dir == "BUY": # 使用賣價二檔買之，有機會成交在一檔
            send_price = result['asks'][1]['price']
        elif order_dir == "SELL": # 使用賣價二檔賣之
            send_price = result['bids'][1]['price']

    else:
        print('Incorrect price type (MARKET or LIMIT or SPEED?)')
        return None

    # 取得當前時間的分與秒
    current_time = datetime.now()
    time_str = current_time.strftime("%H%M%S")  # 格式：MMSS，例如：1530 (15分30秒)
    
    if is_DayTradingSell == "YES":
        send_trade = Trade.DayTradingSell
    elif is_DayTradingSell == "NO":
        send_trade = Trade.Cash
    else:
        print('Incorrect trade type')

    order = OrderObject(
        stock_no = str(stock_id),
        ap_code = send_is_oddlot,
        buy_sell = send_order_dir,
        price_flag = send_price_type,
        price = send_price,
        quantity = volume,
        bs_flag = BSFlag.ROD,
        trade = send_trade,
        user_def = time_str
    )

    trade_sdk.place_order(order)
    return trade_sdk.get_order_results()


def esun_cancel_specific_order(ord_no):
    """取消特定委託書編號的訂單
    Args:
        ord_no (str): 委託書編號
    Returns:
        tuple: (bool, str) - (是否成功取消, 回應訊息)
    """
    try:
        order_list = trade_sdk.get_order_results()
        if order_list == {}:
            return False, "委託列表為空"
        
        # 尋找指定的委託書編號
        target_order = None
        for order in order_list:
            if order['pre_ord_no'] == ord_no:
                target_order = order
                break
        
        if target_order is None:
            return False, f"找不到委託書編號 {ord_no} 的訂單"
        
        # 檢查是否有需要取消的數量
        cancel_shares = target_order['org_qty_share'] - target_order['mat_qty_share']
        done_cancel_shares = target_order['org_qty_share'] - target_order['cel_qty_share']
        
        if cancel_shares == 0 or done_cancel_shares == 0:
            return False, "此筆委託已完全成交或已取消"
            
        # 執行取消委託
        cancel_ret = trade_sdk.cancel_order(target_order)
        if cancel_ret['ret_code'] == '000000':
            return True, f"成功取消委託書號 {ord_no} 的訂單"
        else:
            return False, f"取消失敗: {cancel_ret['ret_msg']}"
            
    except Exception as e:
        return False, f"取消過程發生錯誤: {str(e)}"

def esun_cancel_all_order():
    """取消所有可取消的委託單
    Returns:
        tuple: (bool, list, dict) - (是否全部成功取消, 成功取消的訂單編號列表, {訂單編號: 取消股數})
    """
    success_orders = []  # 成功取消的訂單編號
    cancel_shares_dict = {}  # 記錄每筆訂單取消的股數
    order_list = trade_sdk.get_order_results()

    if order_list == {}:
        print('Your order list is empty')
        return False, [], {}
    
    all_success = True  # 用來追蹤是否全部取消成功
    
    for order in order_list:
        cancel_shares = order['org_qty_share'] - order['mat_qty_share']
        done_cancel_shares = order['org_qty_share'] - order['cel_qty_share']
        
        if cancel_shares == 0 or done_cancel_shares == 0:
            continue

        order_id = order['pre_ord_no']
        print(f"order_id <{order_id}> , stock {order['stock_no']}: cancel number -> {cancel_shares} shares")
        
        cancel_ret = trade_sdk.cancel_order(order)
        if cancel_ret['ret_code'] == '000000':
            success_orders.append(order_id)
            cancel_shares_dict[order_id] = cancel_shares
        else:
            all_success = False
            
    return all_success, success_orders, cancel_shares_dict

def format_inventory_data(inventory_data):
    """
    格式化庫存資料為指定格式
    Args:
        inventory_data (list): 從 get_inventories() 獲得的原始庫存資料
    Returns:
        list: 格式化後的庫存資料列表
    """
    formatted_data = []
    
    for item in inventory_data:
        # 計算未實現損益
        unrealized_pl = sum(float(detail.get('make_a', '0')) for detail in item.get('stk_dats', []))
            
        formatted_item = {
            'trade_type': {
                '0': 'Cash',
                '3': 'Margin',
                '4': 'Short',
                '9': 'DayTrading',
                'A': 'DayTradingSell'
            }.get(item['trade'], 'Unknown'),
            'symbol': f"{item['stk_no']} {item['stk_na']}",
            'remaining_shares': item['qty_l'],
            'current_price': item['price_mkt'],
            'average_price': item['price_avg'],
            'balance_price': item['price_evn'],
            'unrealized_pl': unrealized_pl,
            'profit_rate': item['make_a_per']
        }
        formatted_data.append(formatted_item)
    
    return formatted_data


if __name__ == '__main__':
    
    # test.0 可以先輸入資訊來測試登入
    esun_login_with_auth('' , '')
    
    # test.1 撈取股價測試
    # ret = esun_get_stock_price("LOT" , '2010')
    # pprint(ret['asks'])
    # pprint(ret['bids'])
    
    # test.2 交易測試
    # ret_1 = esun_send_onder('2010' , "BUY" , "MARKET" , 0 , 2, "LOT")
    # pprint(ret_1)
    # ret_2 = esun_send_onder('2010' , "SELL" , "SPEED" , 20 , 1, "ODDLOT" , "YES")
    # pprint(ret_2)

    # result_flag = esun_cancel_all_order()
    # pprint(result_flag)

    # transactions = trade_sdk.get_transactions("0d")
    # pprint(transactions)

    # 庫存明細
    # 回傳參考 -> https://www.esunsec.com.tw/trading-platforms/api-trading/docs/trading/reference/python
    inventories = trade_sdk.get_inventories()
    # pprint(inventories)

    # 測試格式化函數
    formatted_inventories = format_inventory_data(inventories)
    print("\n格式化後的庫存資料:")
    pprint(formatted_inventories)