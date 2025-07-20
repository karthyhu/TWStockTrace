from configparser import ConfigParser
from esun_trade.sdk import SDK
from esun_trade.order import OrderObject
from esun_trade.constant import (APCode, Trade, PriceFlag, BSFlag, Action)
from esun_marketdata import EsunMarketdata
from pprint import pprint


## 讀取設定檔
#config = ConfigParser()
#config.read('./esun_key_file/config.ini')
## 登入
#sdk = SDK(config)
#sdk.login()
## 建立委託物件
#order = OrderObject(
#  buy_sell = Action.Buy,
#  price_flag = PriceFlag.LimitDown,
#  price = None,
#  stock_no = "2884",
#  quantity = 1,
#)
#sdk.place_order(order)
#print("Your order has been placed successfully.")


config = ConfigParser()
config.read('./esun_key_file/config.ini')
sdk = EsunMarketdata(config)
sdk.login()

rest_stock = sdk.rest_client.stock
rest_stock.intraday.quote(symbol='2330')

pprint(rest_stock.intraday.quote(symbol='2330'))