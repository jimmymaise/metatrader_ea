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




filtered_postion = [position for position in mt5.positions_get() if position.magic in magic_numbers]






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

    trader_id = 12234
    external_order_id= 223344
    seprate_number='0000'
    
    open_copied_postions = [position for position in mt5.positions_get() if str(position.magic).startswith(f'{trader_id}{seprate_number}')]
    
    closed_copied_deals = [deal for deal in mt5.history_deals_get(position=0) if deal.magic.startswith(f'{trader_id}{seprate_number}')]

    open_copied_position_to_be_closed = [position for position in open_copied_postions if position.magic not in magic_numbers ]



    signals_from_api =[]
    magic_numbers = []
    for signal in signals_from_api:
        signal['magic_numbers'] = int(f'{signal["trader_id"]}{seprate_number}{signal["external_order_id"]}')

    open_positions=  mt5.positions_get()

    


   


if __name__ == '__main__':
    main()
    mt5.shutdown()

# use as you learned from: https://www.mql5.com/en/docs/integration/python_metatrader5/

mt5.terminal_info()
mt5.copy_rates_from_pos('VALE3', mt5.TIMEFRAME_M1, 0, 1000)
print('aaa')
# ...
# don't forget to shutdown