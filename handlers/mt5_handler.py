import datetime
from handlers.constant import SymbolFillingModeEnum, Common, ReturnCodeTradeServer
from handlers.classes import Mt5Setting


class Mt5Handler:
    def __init__(self, mt5, logger, mt5_setting: Mt5Setting):
        self.mt5 = mt5
        setup = mt5.initialize(
            login=mt5_setting.login_id,
            server=mt5_setting.server,
            password=mt5_setting.password,
            path=mt5_setting.setup_path,
        )
        self.logger = logger
        self.mt5_setting = mt5_setting
        self.prefered_order_type_filling_name = mt5_setting.type_filling
        self.copied_volume_coefficient = mt5_setting.copied_volume_coefficient or 1
        self.max_allowed_order_age_to_copy_in_minutes = mt5_setting.max_allowed_order_age_to_copy_in_minutes

        if not setup or not self.mt5.terminal_info():
            raise Exception(
                f"{self.mt5.last_error()} with setting {mt5_setting}")
        self.logger.debug(self.mt5.terminal_info())
        self.bot_info = self.get_bot_info()

        self.ea_name = mt5_setting.bot_name or "Python EA"

    def convert_to_broker_symbol_format(self, api_signal_symbol):
        symbol = f"{api_signal_symbol}{self.mt5_setting.symbol_postfix}".replace(
            "/", "")
        return symbol

    def enable_symbol(self, symbol):
        if not self.is_symbol_exists(symbol):
            raise Exception(
                f'Symbol {symbol} does not exist in this terminal {self.mt5_setting.server}')

        selected = self.mt5.symbol_select(symbol, True)

        if not selected:
            raise Exception(
                f"Exception: Failed to select {symbol}, error code ={self.mt5.last_error()}"
            )

        return symbol

    def get_bot_info(self):
        terminal_info = self.mt5.terminal_info()
        account_info = self.mt5.account_info()
        return {
            "setup_path": terminal_info.path,
            "data_path": terminal_info.data_path,
            "account_name": account_info.name,
            "login": account_info.login,
            "server": account_info.server,
            "prefered_order_type_filling_name": self.prefered_order_type_filling_name,
            "copied_volume_coefficient": self.copied_volume_coefficient
        }

    def _get_filling_type_by_volume_symbol(self, symbol):
        symbol_filling_type_name = SymbolFillingModeEnum(
            self.mt5.symbol_info(symbol).filling_mode
        ).name

        allowed_order_filling_types = Common.MAPPING_FILLING_MODE_SYBOL_TO_ORDER[
            symbol_filling_type_name
        ]
        if self.prefered_order_type_filling_name in allowed_order_filling_types:
            return getattr(self.mt5, self.prefered_order_type_filling_name)

        else:
            self.logger.debug(
                f"Cannot use prefered order filling type: {self.prefered_order_type_filling_name} as it is not allowed"
                f".Trying to use allowed filling type {allowed_order_filling_types[0]}"
            )
            return getattr(self.mt5, allowed_order_filling_types[0])

    def _get_volume_with_copied_volume_coefficient(self, volume, symbol):
        calculated_volume = round(volume * self.copied_volume_coefficient, 2)
        symbol_info = self.mt5.symbol_info(symbol)

        if calculated_volume > symbol_info.volume_max:
            return symbol_info.max

        elif calculated_volume < symbol_info.volume_min:
            return symbol_info.volume_min

        else:
            return calculated_volume

    def _get_server_enum(self, retcode):
        try:
            return ReturnCodeTradeServer(retcode)
        except Exception:
            self.logger.error(f'Cannot detect server return code {retcode}')
            return None

    def _validate_result(self, request, result):
        if not result:
            return self.logger.error(
                f"\t\t[Error]: {self.mt5.last_error()}\nBot info: {self.get_bot_info()}")

        retcode = result[0]
        retcode_enum = self._get_server_enum(retcode)

        if not retcode_enum:
            return self.logger.error(
                f"Unknown result as cann't get retcode for({retcode})")

        if retcode not in Common.SUCCESSFUL_MT5_TRADE_RETCODE:
            return self.logger.error(
                f"Order failed. Retcode: {retcode_enum.name} ({retcode})")

        if (
                result.comment not in Common.SUCCESS_REQUEST_COMMENTS
                and result.comment not in request["comment"]
        ):
            return self.logger.warning(
                f"\t\t[Probally Error Retcode: {retcode_enum.name} ({retcode})] Request comment is {result.comment}\nBot info: {self.get_bot_info()}")

        return self.logger.debug(
            f"\t[OK Retcode: {retcode_enum.name} ({retcode})]: {result.comment}")

    def close_trade_by_position(self, position):
        # Determine the order type to use when closing a position
        # If the position is a buy, use sell; otherwise, use buy
        closing_order_type = (
            self.mt5.ORDER_TYPE_SELL
            if position.type == self.mt5.ORDER_TYPE_BUY
            else self.mt5.ORDER_TYPE_BUY
        )

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "type": closing_order_type,
            "price": self.get_market_price_by_order_type_symbol(
                closing_order_type, position.symbol
            ),
            "symbol": position.symbol,
            "volume": position.volume,
            "position": position.ticket,
            "magic": position.magic,
            "comment": self.get_ea_comment(),
            "type_filling": self._get_filling_type_by_volume_symbol(position.symbol),
        }
        return self.send_order_request(request)

    def is_symbol_exists(self, symbol: str) -> bool:
        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info is None:
            return False
        else:
            return True

    def open_trade(
            self, symbol, volume, order_type, stop_loss, take_profit, magic_number
    ):
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": self._get_volume_with_copied_volume_coefficient(volume, symbol),
            "type": order_type,
            "price": self.get_market_price_by_order_type_symbol(order_type, symbol),
            "sl": stop_loss,
            "tp": take_profit,
            "magic": magic_number,
            "comment": self.get_ea_comment(),
            "type_filling": self._get_filling_type_by_volume_symbol(symbol),
        }
        request = {k: v for k, v in request.items() if v is not None}
        result = self.send_order_request(request)
        if result and (order_ticket := getattr(result, "order", None)):
            self.logger.debug(
                f"Created order with ticket {order_ticket} (magic number {magic_number})"
            )
        else:
            self.logger.error(
                f"[Error] Cannot create order \nBot info: {self.get_bot_info()}")

    def get_market_price_by_order_type_symbol(self, mt5_order_type_code, symbol):
        symbol_info_tick = self.mt5.symbol_info_tick(symbol)

        if not symbol_info_tick:
            raise Exception("Cannot get tick. Perhaps the market is closed")

        if self.mt5.ORDER_TYPE_SELL == mt5_order_type_code:
            return self.mt5.symbol_info_tick(symbol).bid

        elif self.mt5.ORDER_TYPE_BUY == mt5_order_type_code:
            return self.mt5.symbol_info_tick(symbol).ask

        else:
            raise Exception(f"Invalid code: {mt5_order_type_code}")

    def get_ea_login(self):
        account_info = self.mt5.account_info()
        return f'{account_info.login}@{account_info.server}({account_info.name})'

    def get_ea_comment(self):
        return f"EA {self.mt5.account_info().login}"

    def update_trade(
            self, position_ticket, symbol, stop_loss, take_profit, magic_number
    ):
        request = {
            "action": self.mt5.TRADE_ACTION_SLTP,
            "position": position_ticket,
            "symbol": symbol,
            "sl": stop_loss,
            "tp": take_profit,
            "magic": magic_number,
            "comment": self.get_ea_comment(),
        }
        request = {k: v for k, v in request.items() if v is not None}
        return self.send_order_request(request)

    def send_order_request(self, request):
        self.logger.debug(
            f"\n\t[Sending request for account {self.get_ea_login()}]\n {request}\n")
        result = self.mt5.order_send(request)
        self._validate_result(request, result)
        return result

    def get_history_deal_within_x_days(self, x_days):
        start_time = datetime.datetime.now(
            datetime.timezone.utc) - datetime.timedelta(days=x_days)
        # as this library has with end time.  Perhaps time zone diff
        end_time = datetime.datetime.now(
            datetime.timezone.utc) + datetime.timedelta(days=2)

        return self.mt5.history_deals_get(start_time, end_time)

    def get_current_open_position(self):
        return self.mt5.positions_get()

    def get_server_time(self):
        symbol = self.enable_symbol(self.convert_to_broker_symbol_format
                                    ("EURUSD"))
        now = datetime.datetime.now(datetime.timezone.utc)
        ticks = self.mt5.copy_ticks_range(
            symbol, now - datetime.timedelta(seconds=60), now, self.mt5.COPY_TICKS_ALL)

        if len(ticks) > 0:
            return ticks[-1][0]
        else:
            self.logger.error(
                "No ticks received. Cannot determine server time.")
            return None

    def shutdown(self):
        self.logger.info(f"{self.get_bot_info()}")
        self.mt5.shutdown()
