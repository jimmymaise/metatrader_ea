from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class Mt5Setting:
    server: str
    login_id: int
    password: str
    setup_path: str
    symbol_postfix: str
    master_trader_id: str
    source: str
    bot_name: str
    type_filling:str


class Mt5Handler:
    def __init__(self, mt5, logger, mt5_setting: Mt5Setting = None, ea_name=None):
        self.mt5 = mt5
        self.filling_type= mt5.ORDER_FILLING_IOC
        if mt5_setting:
            setup = mt5.initialize(login=mt5_setting.login_id,
                                   server=mt5_setting.server,
                                   password=mt5_setting.password,
                                   path=mt5_setting.setup_path)
            self.type_filling = getattr(mt5,mt5_setting.type_filling)


        else:
            setup = mt5.initialize()

        if not setup:
            raise Exception(
                f'{self.mt5.last_error()} with setting {mt5_setting}')

        print(mt5.terminal_info())

        self.logger = logger
        self.ea_name = ea_name or 'Python EA'

    def close_trade_by_position(self, position):
        # Determine the order type to use when closing a position
        # If the position is a buy, use sell; otherwise, use buy
        closing_order_type = self.mt5.ORDER_TYPE_SELL \
            if position.type == self.mt5.ORDER_TYPE_BUY else self.mt5.ORDER_TYPE_BUY

        request = {
            'action': self.mt5.TRADE_ACTION_DEAL,
            'type': closing_order_type,
            'price': self.get_market_price_by_order_type_symbol(closing_order_type, position.symbol),
            'symbol': position.symbol,
            'volume': position.volume,
            'position': position.ticket,
            'magic': position.magic,
            'comment': f'Made by {self.ea_name}',
            'type_filling': self.type_filling

        }
        return self.send_order_request(request)

    def open_trade(self, symbol, volume, order_type, stop_loss, take_profit, magic_number):
        selected = self.mt5.symbol_select(symbol, True)

        if not selected:
            raise Exception(
                f"Exception: Failed to select {symbol}, error code ={self.mt5.last_error()}")

        request = {
            'action': self.mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': volume,
            'type': order_type,
            'price': self.get_market_price_by_order_type_symbol(order_type, symbol),
            'sl': stop_loss,
            'tp': take_profit,
            'magic': magic_number,
            'comment': f'Made by {self.ea_name}',
            'type_filling': self.type_filling

        }
        return self.send_order_request(request)

    def get_market_price_by_order_type_symbol(self, mt5_order_type_code, symbol):
        symbol_info_tick = self.mt5.symbol_info_tick(symbol)

        if not symbol_info_tick:
            raise Exception('Cannot get tick. Perhaps the market is closed')

        if self.mt5.ORDER_TYPE_SELL == mt5_order_type_code:
            return self.mt5.symbol_info_tick(symbol).bid

        elif self.mt5.ORDER_TYPE_BUY == mt5_order_type_code:
            return self.mt5.symbol_info_tick(symbol).ask

        else:
            raise Exception(f'Invalid code: {mt5_order_type_code}')

    def update_trade(self, position_ticket, symbol, stop_loss, take_profit, magic_number):
        request = {
            'action': self.mt5.TRADE_ACTION_SLTP,
            'position': position_ticket,
            'symbol': symbol,
            'sl': stop_loss,
            'tp': take_profit,
            'magic': magic_number,
            'comment': f'Made by {self.ea_name}'

        }
        return self.send_order_request(request)

    def send_order_request(self, request):
        self.logger.info(f'\n\t[Sending request]: {request}')
        result = self.mt5.order_send(request)

        if not result:
            self.logger.error(f'\t\t[Error]: {self.mt5.last_error()}')

        elif result.comment not in ['Request executed'] and result.comment not in request['comment']:
            self.logger.warning(f'\t\t[Result Comment]: {result.comment}')

        else:
            self.logger.info(f'\t[OK]: {result.comment}')

        return result

    def get_history_deal_within_x_days(self, x_days):
        start_time = datetime.today() - timedelta(days=x_days)
        # as this library has with end time.  Perhaps time zone diff
        end_time = datetime.now() + timedelta(days=2)

        return self.mt5.history_deals_get(start_time, end_time)

    def get_current_open_position(self):
        return self.mt5.positions_get()

    def shutdown(self):
        self.mt5.shutdown()
