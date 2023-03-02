# import the package
import time

# from mt5linux import MetaTrader5
#
# # connecto to the server
# mt5 = MetaTrader5(
#     # host = 'localhost' (default)
#     # port = 18812       (default)
# )
import MetaTrader5 as mt5
import requests


symbol = 'EURUSD_'
lot = 0.01
stop_loss = 100
take_profit = 200
magic_number = 123456

mt5.initialize()

print(mt5.terminal_info())

mt5.orders_get()


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
    print(result)
    return result


def main():
    while True:
        tick = mt5.symbol_info_tick(symbol)
        if tick.ask > tick.last:
            result = open_trade(symbol, lot, stop_loss, take_profit, magic_number)
            if not result:
                print(mt5.last_error())
            print(f'Trade opened: with {tick.ask}', result)
            break
        time.sleep(1)


if __name__ == '__main__':
    main()
    mt5.shutdown()

# use as you learned from: https://www.mql5.com/en/docs/integration/python_metatrader5/

mt5.terminal_info()
mt5.copy_rates_from_pos('VALE3', mt5.TIMEFRAME_M1, 0, 1000)
print('aaa')
# ...
# don't forget to shutdown
