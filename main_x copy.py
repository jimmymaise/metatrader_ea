# import the package
import time

# from mt5linux import MetaTrader5

# # connecto to the server
# mt5 = MetaTrader5(
#     # host = 'localhost' (default)
#     # port = 18812       (default)
# )
import MetaTrader5 as mt5


symbol = 'EURUSD_'
lot = 0.001
stop_loss = 100
take_profit = 200
magic_number = 123456

mt5.initialize()

print(mt5.terminal_info())


trader_id = 12234
external_order_id= 223344
seprate_number='0000'
magic_number = f'{trader_id}{seprate_number}{external_order_id}'


# To get the position need to be update, order
def get_open_postions_by_magic_numbers(mt5,magic_numbers):
    filtered_postion = [position for position in mt5.positions_get() if position.magic in magic_numbers]
    return filtered_postion

def get_closed_deals_by_magic_numbers(mt5,magic_numbers):
    closed_deals = mt5.history_deals_get(position=0)
    filtered_deals = [deal for deal in closed_deals if deal.magic in magic_numbers]
    return filtered_deals









def open_trade(symbol, lot, stop_loss, take_profit, magic_number):
    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': symbol,
        'volume': lot,
        'type': mt5.ORDER_TYPE_BUY,
        'price': mt5.symbol_info_tick(symbol).ask,
        'sl': stop_loss,
        'tp': take_profit,
        'magic': magic_number,
        'comment': 'Python EA'
    }
    result = mt5.order_send(request)
    print(mt5.last_error())
    return result


def main():
    # prepare order request
    symbol = "EURUSD_"
    type = mt5.ORDER_TYPE_BUY
    volume = 0.01
    price = mt5.symbol_info_tick(symbol).ask
    stop_loss = 50  # 50 pips
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "type": type,
        "volume": volume,
        "price": price,
        "sl": price - stop_loss * mt5.symbol_info(symbol).point,
        "deviation": 20,
        "magic": 1222323334000123454,
        "comment": "zuluzula",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    # send order request
    result = mt5.order_send(request)

    # check if order was sent successfully
    if result is None:
        print("Order sending failed")
        print("Last error:", mt5.last_error())
    else:
        print("Order sending successful")
        print("Order ticket:", result)

    # shut down connection to MetaTrader 5


if __name__ == '__main__':
    main()
    mt5.shutdown()

# use as you learned from: https://www.mql5.com/en/docs/integration/python_metatrader5/

mt5.terminal_info()
mt5.copy_rates_from_pos('VALE3', mt5.TIMEFRAME_M1, 0, 1000)
print('aaa')
# ...
# don't forget to shutdown