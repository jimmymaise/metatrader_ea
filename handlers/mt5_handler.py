class Mt5Handler:
    def __init__(self, mt5, logger, ea_name=None):
        self.mt5 = mt5
        mt5.initialize()
        mt5.terminal_info()
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
            'comment': f'Made by {self.ea_name}'
        }
        return self.send_order_request(request)

    def open_trade(self, symbol, volume, order_type, stop_loss, take_profit, magic_number):
        request = {
            'action': self.mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': volume,
            'type': order_type,
            'price': self.get_market_price_by_order_type_symbol(order_type, symbol),
            'sl': stop_loss,
            'tp': take_profit,
            'magic': magic_number,
            'comment': f'Made by {self.ea_name}'
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
            self.logger.info(f'\t\t[Error]: {self.mt5.last_error()}')

        elif result.comment not in ['Request executed']:
            self.logger.info(f'\t\t[Error]: {result.comment}')

        else:
            self.logger.info(f'\t[OK]: {result.comment}')

        return result

    def shutdown(self):
        self.mt5.shutdown()
