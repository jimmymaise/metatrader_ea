# import the package
import time
from datetime import datetime, timedelta
# from mt5linux import MetaTrader5

# # connecto to the server
# mt5 = MetaTrader5(
#     # host = 'localhost' (default)
#     # port = 18812       (default)
# )
import MetaTrader5 as mt5
import requests

SEPARATOR_NUMBER_STRING = '999'
BASE_CONTROLLER_URL = 'http://127.0.0.1:8000/'




def send_order_request(request):
    print(f'\n\t[Sending request]: {request}')
    result = mt5.order_send(request)

    if not result:
        print(f'\t\t[Error]: {mt5.last_error()}')

    elif result.comment != 'Request executed':
        print(f'\t\t[Error]: {result.comment}')

    else:
        print(f'\t[OK]: {result.comment}')

    
    return result


def open_trade(symbol, volume, order_type, stop_loss, take_profit, magic_number):
    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': symbol,
        'volume': volume,
        'type': order_type,
        'price': get_market_price_by_order_type_symbol(order_type,symbol),
        'sl': stop_loss,
        'tp': take_profit,
        'magic': magic_number,
        'comment': 'Python EA'
    }
    return send_order_request(request)

def get_market_price_by_order_type_symbol(mt5_order_type_code,symbol):
    
    if mt5.ORDER_TYPE_SELL == mt5_order_type_code:
        return mt5.symbol_info_tick(symbol).bid

    elif mt5.ORDER_TYPE_BUY == mt5_order_type_code:
        return mt5.symbol_info_tick(symbol).ask
    
    else:
        raise Exception('Invalid code')

def close_trade_by_position(position):
    order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'type': order_type,
        'price': get_market_price_by_order_type_symbol(order_type,position.symbol),
        'symbol': position.symbol,
        'volume': position.volume,
        'position':position.ticket,
        'magic': position.magic,

    }
    return send_order_request(request)



def update_trade(position_ticket, symbol, stop_loss, take_profit, magic_number):
    request = {
        'action': mt5.TRADE_ACTION_SLTP,
        'position': position_ticket,
        'symbol': symbol,
        'sl': stop_loss,
        'tp': take_profit,
        'magic': magic_number,
    }
    return send_order_request(request)



def get_signal_from_api(master_id, source_id):
    headers = {'Content-Type': 'application/json'}
    url = f'{BASE_CONTROLLER_URL}/master_traders/{source_id}/{master_id}'
    print(f'Calling api {url} to get info')
    resp = requests.get(url=url
                        , headers=headers)

    if resp.status_code in [requests.codes.created, requests.codes.ok]:
        return resp.json()['signals']
    raise Exception('Cannot get data from server')


def normalize_symbol(raw_symbol):
    return f"{raw_symbol.replace('/', '')}"


def process_signals_from_master_trader(master_trader_id, signals):
    magic_number_prefix = f'{master_trader_id}{SEPARATOR_NUMBER_STRING}'
    magic_numbers_from_signals = []

    for signal in signals:
        signal['magic_numbers'] = int(f'{magic_number_prefix}{signal["signal_id"]}')
        magic_numbers_from_signals.append(signal['magic_numbers'])

    open_copied_positions_dict = {position.magic: position for position in mt5.positions_get() if
                                  str(position.magic).startswith(magic_number_prefix)}



    open_copied_position_to_be_closed_dict = {magic_number: position for magic_number, position in
                                              open_copied_positions_dict.items() if
                                              magic_number not in magic_numbers_from_signals}
    
    closed_copied_deals_dict = {deal.magic: deal for deal in mt5.history_deals_get((datetime.today()-timedelta(days=100)),
                                                                                datetime.now()+timedelta(days=100)) if
                            str(deal.magic).startswith(magic_number_prefix) and not open_copied_positions_dict.get(deal.magic)}
    
    for signal in signals:
        signal_magic_number = signal['magic_numbers']

        is_this_signal_created_but_closed = closed_copied_deals_dict.get(signal_magic_number)
        is_this_signal_created = open_copied_positions_dict.get(signal_magic_number)

        if is_this_signal_created_but_closed:
            print(f"Signal {signal_magic_number} will be ignored as it belongs to closed deal")
            continue

        elif is_this_signal_created:
            # Check to need to update or ignore as exis already
            exist_open_position = open_copied_positions_dict.get(signal_magic_number)
            is_up_to_date = (exist_open_position.sl == signal['stop_loss']
                             and exist_open_position.tp == signal['take_profit'])
            if is_up_to_date:
                print(f"Signal {signal_magic_number} will be ignored as it is created with same information")
                continue

            print(f"Signal {signal_magic_number} will update the position {exist_open_position.ticket}")
            update_trade(
                position_ticket=exist_open_position.ticket,
                symbol=normalize_symbol(signal['symbol']),
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit'],
                magic_number=signal_magic_number,
            )

        else:
            print(f"Signal {signal_magic_number} will create new trade")
            order_type = mt5.ORDER_TYPE_BUY if signal['type'] == 'BUY' else mt5.ORDER_TYPE_SELL

            open_trade(symbol=normalize_symbol(signal['symbol']),
                       order_type=order_type,
                       volume=signal['size'],
                       stop_loss=signal['stop_loss'],
                       take_profit=signal['take_profit'],
                       magic_number=signal_magic_number,
                       )

    for _, position in open_copied_position_to_be_closed_dict.items():
        print(f"The position created by old Signal {position.magic} will be closed")
        close_trade_by_position(position)


def main():
    master_trader_id = '404656'
    source = 'zulu'

    while True:
        signals_from_api = get_signal_from_api(master_trader_id, source)
        print(f'\nGet signals {signals_from_api}\n')
        process_signals_from_master_trader(master_trader_id, signals_from_api[0:])
        time.sleep(30)
        print('START----------------------------')


if __name__ == '__main__':
    mt5.initialize()
    mt5.terminal_info()
    main()
    mt5.shutdown()
