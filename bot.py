import datetime
import json
import time
from multiprocessing import Process

import dateutil.parser
import MetaTrader5 as mt5
import requests
from dacite import from_dict

from handlers.classes import BotConfig, MasterTrader, TradeSignal, TradeType
from handlers.logger import Logger
from handlers.mt5_handler import Mt5Handler, Mt5Setting


class TradingFromSignal:
    def __init__(self, mt5_setting: Mt5Setting, bot_config: BotConfig):
        now = datetime.datetime.now()
        formatted_date = now.strftime("%Y-%m-%d_%H_%M_%S")
        log_file_path = (
            f"{bot_config.log_folder_path}/{mt5_setting.bot_name}/{formatted_date}.log"
        )
        self.logger = Logger(
            log_file_path=log_file_path, message_prefix=f'{mt5_setting.login_id}::{mt5_setting.bot_name}', log_level=bot_config.log_level
        ).get_logger()

        self.mt5_handler = Mt5Handler(mt5, self.logger, mt5_setting)
        self.mt5_setting = mt5_setting
        self.logger.info(mt5.last_error())
        self.mt5_handler.get_ea_login()
        self.bot_info = (
            f"{self.mt5_handler.get_ea_login()}"
            f"(copy:{mt5_setting.master_traders} with copied_volume_coefficient {mt5_setting.copied_volume_coefficient})"
        )
        self.bot_name = mt5_setting.bot_name
        self.bot_config = bot_config
        self.mt5_handler.get_server_time()

    def calculate_price_differences_in_pips(self, signal):

        mt5_order_type_code = self.mt5_handler.mt5.ORDER_TYPE_BUY if signal.type == TradeType.BUY \
            else self.mt5_handler.mt5.ORDER_TYPE_SELL

        current_price = self.mt5_handler.get_market_price_by_order_type_symbol(
            mt5_order_type_code, signal.symbol)
        price_difference = abs(current_price - signal.price_order)
        if 'JPY' in signal.symbol:
            price_difference_in_pips = 100 * price_difference
        else:
            price_difference_in_pips = 10_000 * price_difference
        signal.price_diff = price_difference_in_pips

        return price_difference_in_pips, current_price, signal.price_order

    def calculate_time_diff_between_signal_order_date_and_now(self, signal):
        server_time = datetime.datetime.fromtimestamp(self.mt5_handler.get_server_time(
        ), datetime.timezone.utc) if self.mt5_handler.get_server_time() else None

        current_time = server_time or datetime.datetime.now(
            datetime.timezone.utc)
        signal_time = dateutil.parser.parse(signal.time)
        time_difference = current_time - signal_time
        signal.time_diff = time_difference
        return time_difference, current_time, signal_time

    def validate_signal_order_date_for_copied(self, signal: TradeSignal):
        time_difference, current_time, signal_time = self.calculate_time_diff_between_signal_order_date_and_now(
            signal)
        max_allowed_order_age_to_copy_in_minutes = self.mt5_setting.max_allowed_order_age_to_copy_in_minutes
        is_time_valid_to_copy = time_difference <= datetime.timedelta(
            minutes=max_allowed_order_age_to_copy_in_minutes)
        if not is_time_valid_to_copy:
            self.logger.error(
                f'\n\tTime is not valid as:\n \t\t\t'
                f'time_difference={str(time_difference)} ({time_difference.total_seconds() / 60} minutes),current_time={str(current_time)},signal_time={signal_time},{max_allowed_order_age_to_copy_in_minutes=}')

        return is_time_valid_to_copy

    def validate_price_for_copied(self, signal: TradeSignal):
        price_difference_in_pips, current_price, signal_price = self.calculate_price_differences_in_pips(
            signal)
        max_allowed_price_difference_in_pips = self.mt5_setting.max_allowed_price_difference_in_pips
        is_price_valid_to_copy = price_difference_in_pips <= max_allowed_price_difference_in_pips
        if not is_price_valid_to_copy:
            self.logger.error(
                f'\n\tPrice is not valid as:\n \t\t\t'
                f'{price_difference_in_pips=},{current_price=},{signal_price=},{max_allowed_price_difference_in_pips=}')
        return is_price_valid_to_copy

    def valid_signal_for_copied(self, signal: TradeSignal):
        return self.validate_price_for_copied(signal) and self.validate_signal_order_date_for_copied(signal)

    def get_master_trader_data_from_api(self, source_id, master_ids) -> list[MasterTrader]:
        master_ids_str = ','.join(map(str, master_ids))
        headers = {"Content-Type": "application/json"}
        url = f"{self.bot_config.base_controller_url}/master_traders/?source={source_id}&external_trader_ids={master_ids_str}"
        self.logger.info(f"Calling api {url} to get info")

        resp = requests.get(url=url, headers=headers)
        master_traders = []

        if resp.status_code in [requests.codes.created, requests.codes.ok]:
            for master_trader_from_api in resp.json():
                master_trader = MasterTrader(
                    source=master_trader_from_api['source'], external_trader_id=master_trader_from_api['external_trader_id'], signals=[])

                for signal in master_trader_from_api["signals"]:
                    signal['symbol'] = self.mt5_handler.convert_to_broker_symbol_format(
                        signal['symbol'])
                    try:
                        self.mt5_handler.enable_symbol(signal['symbol'])
                    except Exception as e:
                        self.logger.debug(
                            f"Signal {master_trader.external_trader_id}:{signal['external_signal_id']} will be IGNORED as we cannot enable this symbol as {e}"
                        )
                        master_trader.invalid_symbol_signal_count += 1
                        continue
                    master_trader.signals.append(TradeSignal(**signal))

                master_traders.append(master_trader)

            return master_traders
        raise Exception(
            f"[Error] Cannot get data from server: {url}"
            f" Status code {resp.status_code}"
        )

    @staticmethod
    def is_up_to_date_stop_loss_take_profit(position, signal: TradeSignal):
        if position.sl == signal.stop_loss and position.tp == signal.take_profit:
            return True
        if None not in [position.sl, signal.stop_loss, position.tp, signal.take_profit]:
            return round(position.sl, 5) == round(
                signal.stop_loss, 5
            ) and round(signal.tp, 5) == round(
                signal.take_profit, 5
            )
        return False

    def process_signals_from_master_trader(self, master_trader_id: str, signals: list[TradeSignal]):
        magic_number_prefix = (
            f"{master_trader_id}{self.bot_config.separator_number_string}"
        )
        magic_numbers_from_signals = []

        for signal in signals:
            signal.magic_numbers = int(
                f'{magic_number_prefix}{signal.external_signal_id}'
            )
            magic_numbers_from_signals.append(signal.magic_numbers)

        open_copied_positions_dict = {
            position.magic: position
            for position in self.mt5_handler.get_current_open_position()
            if str(position.magic).startswith(magic_number_prefix)
        }

        open_copied_position_to_be_closed_dict = {
            magic_number: position
            for magic_number, position in open_copied_positions_dict.items()
            if magic_number not in magic_numbers_from_signals
        }

        closed_copied_deals_dict = {
            deal.magic: deal
            for deal in self.mt5_handler.get_history_deal_within_x_days(10)
            if (
                is_deal_created_by_bot_and_closed := str(deal.magic).startswith(
                    magic_number_prefix
                )
                and not open_copied_positions_dict.get(deal.magic)
            )
        }

        for signal in signals:
            signal_info = f"{master_trader_id}:{signal.external_signal_id}"
            signal_magic_number = signal.magic_numbers

            is_this_signal_created_but_closed = closed_copied_deals_dict.get(
                signal_magic_number
            )
            is_this_signal_created = open_copied_positions_dict.get(
                signal_magic_number)

            if is_this_signal_created_but_closed:
                closed_deal = closed_copied_deals_dict.get(signal_magic_number)
                self.logger.warning(
                    f"Signal {signal_info} will be IGNORED as it belongs to closed deal"
                    f"(magic number {signal_magic_number}, ticket {closed_deal.ticket},"
                    f" position {closed_deal.position_id}, time {datetime.datetime.fromtimestamp(closed_deal.time)})"
                )
                continue

            elif is_this_signal_created:
                # Check to need to update or ignore as exis already
                exist_open_position = open_copied_positions_dict.get(
                    signal_magic_number
                )
                is_up_to_date = self.is_up_to_date_stop_loss_take_profit(
                    exist_open_position, signal)
                if is_up_to_date:
                    self.logger.debug(
                        f"Signal {signal_info} will be IGNORED as it is created with same information with the ticket {exist_open_position.ticket}"
                        f"(magic number {signal_magic_number})"
                    )
                    continue

                self.logger.debug(
                    f"Signal {signal_info} will UPDATE the position {exist_open_position.ticket}."
                    f"(magic number {signal_magic_number})\n"
                    f"New stop lost/take profit: {signal.stop_loss}/{signal.take_profit}\n"
                    f"Old stop lost/take profit: {exist_open_position.sl}/{exist_open_position.tp}"
                )
                self.mt5_handler.update_trade(
                    position_ticket=exist_open_position.ticket,
                    symbol=signal.symbol,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    magic_number=signal_magic_number,
                )
            elif not self.valid_signal_for_copied(signal):
                self.logger.error(
                    f"Signal {signal_info} will be IGNORE instead of Create as open time or price is not sutable with condition")

            else:
                self.logger.debug(
                    f"Signal {signal_info} will CREATE new trade with {signal.price_diff=} pips, signal.time_diff {str(signal.time_diff)}")

                order_type = (
                    mt5.ORDER_TYPE_BUY
                    if signal.type == "BUY"
                    else mt5.ORDER_TYPE_SELL
                )

                self.mt5_handler.open_trade(
                    symbol=signal.symbol,
                    order_type=order_type,
                    volume=signal.size,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    magic_number=signal_magic_number,
                )

        for _, position in open_copied_position_to_be_closed_dict.items():
            self.logger.info(
                f"The position created by old Signal {position.magic} will be closed"
            )
            self.mt5_handler.close_trade_by_position(position)

    def run(self):
        master_traders = self.mt5_setting.master_traders
        exception = None
        try:
            while True:
                self.logger.info("-------------START---------------")
                self.logger.info(f"Bot info {self.bot_info}")
                for source, master_trader_ids in master_traders.items():
                    if not master_trader_ids:
                        self.logger.debug(
                            f"Source {source} has no master trader id")
                        continue

                    master_trader_data_from_api = self.get_master_trader_data_from_api(
                        source, master_trader_ids)

                    for master_trader in master_trader_data_from_api:
                        master_signals = master_trader.signals
                        if master_trader.invalid_symbol_signal_count:
                            self.logger.error(
                                f"\n[{source}:{master_trader.external_trader_id}] Have  {master_trader.invalid_symbol_signal_count} invalid symbol signal(s)\n"
                            )

                        self.logger.debug(
                            f"\n[{source}:{master_trader.external_trader_id}] Get {len(master_signals)} valid symbol signal(s):\n{master_signals}\n"
                        )

                        self.process_signals_from_master_trader(
                            master_trader.external_trader_id, master_signals
                        )

                self.logger.debug(
                    f"\nDetail bot info:\n{self.mt5_handler.get_bot_info()}")
                self.logger.info("--------------END----------------")

                time.sleep(1)
        except Exception as e:
            exception = e
            self.logger.error(e)
        finally:
            self.logger.info(
                f"Bot info {self.bot_info} is going to shutdown with exception {exception}")
            self.logger.info("--------------SHUTDOWN MT5---------------")
            self.mt5_handler.shutdown()


def worker(mt5_setting: Mt5Setting, bot_config: BotConfig):
    bot = TradingFromSignal(mt5_setting, bot_config)
    bot.run()


def validate_mt5_settings(mt5_settings: list[Mt5Setting]):
    setup_paths = []
    accounts = []
    for mt5_setting in mt5_settings:
        account = f'{mt5_setting.server}|{mt5_setting.login_id}'

        if mt5_setting.setup_path in setup_paths:
            raise Exception(
                f'The setup {mt5_setting.setup_path} is already used')

        if account in accounts:
            raise Exception(
                f'The account {account} is already used. Use only one terminal for one account')

        setup_paths.append(mt5_setting.setup_path)
        accounts.append(account)


def bot_runner():
    try:
        with open("./terminal_login.json") as content:
            config = json.load(content)
    except Exception as e:
        raise Exception(
            f'Cannot parse terminal_login.json. Check it again {e}')

    bot_config = from_dict(data_class=BotConfig, data=config)
    terminals = config["terminals"]
    procs = []
    mt5_settings = [Mt5Setting(**terminal) for terminal in terminals]
    validate_mt5_settings(mt5_settings)

    for mt5_setting in mt5_settings:
        proc = Process(target=worker, args=(mt5_setting, bot_config))
        procs.append(proc)
        proc.start()

    for proc in procs:
        proc.join()


if __name__ == "__main__":
    bot_runner()
