from configparser import ConfigParser
from esun_trade.sdk import SDK
from esun_trade.order import OrderObject
from esun_trade.constant import (APCode, Trade, PriceFlag, BSFlag, Action)


# 讀取設定檔
config = ConfigParser()
config.read('./config.ini')
# 登入
sdk = SDK(config)
sdk.login()
# 建立委託物件
order = OrderObject(
  buy_sell = Action.Buy,
  price_flag = PriceFlag.LimitDown,
  price = None,
  stock_no = "2884",
  quantity = 1,
)
sdk.place_order(order)
print("Your order has been placed successfully.")