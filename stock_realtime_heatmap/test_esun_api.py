from configparser import ConfigParser
from esun_trade.sdk import SDK
from esun_trade.order import OrderObject
from esun_trade.constant import (APCode, Trade, PriceFlag, BSFlag, Action)
from esun_marketdata import EsunMarketdata
from pprint import pprint
import sys
from io import StringIO



def esun_login_with_auth(auth_code, password):

    pre_inputs = [
        auth_code,
        password
    ]
    
    sys.stdin = StringIO('\n'.join(pre_inputs))
    
    try:
        # 讀取設定檔
        config = ConfigParser()
        config.read('./esun_key_file/config.ini')
        
        # 登入
        sdk = SDK(config)
        sdk.reset_password()
        login_result = sdk.login()
        # print(login_result)
        # 檢查登入結果
        if login_result is None:
            
            # order = OrderObject(
            # buy_sell = Action.Buy,
            # price_flag = PriceFlag.LimitDown,
            # price = None,
            # stock_no = "2884",
            # quantity = 1,
            # )
            # sdk.place_order(order)
            # print("Your order has been placed successfully.")

            return True, "登入成功", sdk
        else:
            return False, f"登入失敗: {login_result}", None
            
    except Exception as e:
        return False, f"登入過程發生錯誤: {str(e)}", None
    





# # ## 讀取設定檔
# config = ConfigParser()
# config.read('./esun_key_file/config.ini')

# # 登入
# try:

#     sdk = SDK(config)
#     sdk.reset_password()
#     sdk = SDK(config)

#     login_result = sdk.login()

# except Exception as e:
#     print(f"💥 登入過程發生錯誤: {str(e)}")

# ## 建立委託物件
# order = OrderObject(
#     buy_sell = Action.Buy,
#     price_flag = PriceFlag.LimitDown,
#     price = None,
#     stock_no = "2884",
#     quantity = 1,
# )
# sdk.place_order(order)
# print("Your order has been placed successfully.")


# config = ConfigParser()
# config.read('./esun_key_file/config.ini')
# sdk = EsunMarketdata(config)
# sdk.login()

# rest_stock = sdk.rest_client.stock
# rest_stock.intraday.quote(symbol='2330')

# pprint(rest_stock.intraday.quote(symbol='2330'))