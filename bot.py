import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from multiprocessing import Process
from typing import Dict, Optional
from dateutil import parser
from typing import Generator

import MetaTrader5 as mt5
import requests
from dacite import from_dict

from handlers.logger import Logger
from handlers.mt5_handler import Mt5Handler, Mt5Setting
from enum import Enum


class TradeType(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class BotConfig:
    base_controller_url: str
    log_folder_path: str
    separator_number_string: str = "00"


@dataclass
class TradeSignal:
    id: int
    external_signal_id: str
    symbol: str
    trade_type: str = field(init=False)
    size: float
    time: str
    price_order: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    market_price: float
    magic_numbers:  Optional[float]


class TradingFromSignal:
    def __init__(self, mt5_setting: Mt5Setting, bot_config: BotConfig):
        now = datetime.now()
        formatted_date = now.strftime("%Y-%m-%d_%H_%M_%S")
        log_file_path = (
            f"{bot_config.log_folder_path}/{mt5_setting.bot_name}/{formatted_date}.log"
        )
        self.logger = Logger(
            log_file_path=log_file_path, message_prefix=f'{mt5_setting.login_id}::{mt5_setting.bot_name}'
        ).get_logger()

        self.mt5_handler = Mt5Handler(mt5, self.logger, mt5_setting)
        self.mt5_setting = mt5_setting
        self.logger.error(mt5.last_error())
        self.mt5_handler.get_ea_login()
        self.bot_info = (
            f"{self.mt5_handler.get_ea_login()}"
            f"(copy:{mt5_setting.source}/{mt5_setting.master_trader_id} with copied_volume_cofficient {mt5_setting.copied_volume_cofficient})"
        )
        self.bot_name = mt5_setting.bot_name
        self.bot_config = bot_config
        self.mt5_handler.get_server_time()

    def normalize_symbol(self, raw_symbol):
        return f"{raw_symbol.replace('/', '')}{self.mt5_setting.symbol_postfix}"

    def validate_price_for_copied(self, signal: TradeSignal, symbol: str):
        tick = self.mt5.symbol_info_tick(symbol)
        current_price = tick.ask if signal.trade_type == TradeType.BUY else tick.bid
        price_difference = abs(current_price - signal.price_order)
        max_allowed_price_difference_in_pips = self.self.mt5_setting.max_allowed_price_difference_in_pips
        is_price_valid_to_copy = price_difference <= max_allowed_price_difference_in_pips
        if not is_price_valid_to_copy:
            self.logger.error(
                f'Price is not valid as {price_difference=},{current_price=},{signal.price_order=},{max_allowed_price_difference_in_pips=}')
        return is_price_valid_to_copy

    def validate_signal_order_date_for_copied(self, signal: TradeSignal):
        server_time = datetime.fromtimestamp(self.mt5_handler.get_server_time(
        )) if self.mt5_handler.get_server_time() else None

        current_time = server_time or datetime.now()
        time_difference = current_time - parser.parse(signal.time)
        max_allowed_order_age_to_copy_in_minutes = self.mt5_setting.max_allowed_order_age_to_copy_in_minutes
        is_time_valid_to_copy = time_difference <= datetime.timedelta(
            minutes=max_allowed_order_age_to_copy_in_minutes)
        if not is_time_valid_to_copy:
            self.logger.error(
                f'Price is not valid as {time_difference=},{current_time=},{signal.price_time=},{max_allowed_order_age_to_copy_in_minutes=}')

        return is_time_valid_to_copy

    def valid_signal_for_copied(self, signal: TradeSignal):
        return self.validate_price_for_copied(signal, signal.symbol) and self.validate_signal_order_date_for_copied(signal)

    def get_signal_from_api(self, master_id, source_id) -> Generator[TradeSignal]:
        headers = {"Content-Type": "application/json"}
        url = f"{self.bot_config.base_controller_url}/master_traders/{source_id}/{master_id}"
        self.logger.info(f"Calling api {url} to get info")

        resp = requests.get(url=url, headers=headers)

        if resp.status_code in [requests.codes.created, requests.codes.ok]:
            for signal in resp.json()["signals"]:
                signal['symbol'] = self.mt5_handler.convert_to_broker_symbol_format(
                    signal['symbol'])
                yield TradeSignal(signal)

        raise Exception(
            f"[Error] Cannot get data from server:"
            f" Status code {resp.status_code}, {resp.json()}"
        )

    def process_signals_from_master_trader(self, master_trader_id: str, signals: list[TradeSignal]):
        magic_number_prefix = (
            f"{master_trader_id}{self.bot_config.separator_number_string}"
        )
        magic_numbers_from_signals = []

        for signal in signals:
            signal["magic_numbers"] = int(
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
                    f" position {closed_deal.position_id}, time {datetime.fromtimestamp(closed_deal.time)})"
                )
                continue

            elif is_this_signal_created:
                # Check to need to update or ignore as exis already
                exist_open_position = open_copied_positions_dict.get(
                    signal_magic_number
                )
                is_up_to_date = round(exist_open_position.sl, 5) == round(
                    signal["stop_loss"], 5
                ) and round(exist_open_position.tp, 5) == round(
                    signal["take_profit"], 5
                )
                if is_up_to_date:
                    self.logger.warning(
                        f"Signal {signal_info} will be IGNORED as it is created with same information with the ticket {exist_open_position.ticket}"
                        f"(magic number {signal_magic_number})"
                    )
                    continue

                self.logger.info(
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
                self.logger.info(
                    f"Signal {signal_magic_number} will be IGNORE instead of Create as open time or price is not sutable with condition")

            else:
                self.logger.info(
                    f"Signal {signal_magic_number} will CREATE new trade")

                order_type = (
                    mt5.ORDER_TYPE_BUY
                    if signal["type"] == "BUY"
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
            self.logger.warning(
                f"The position created by old Signal {position.magic} will be closed"
            )
            self.mt5_handler.close_trade_by_position(position)

    def run(self):
        master_trader_id = self.mt5_setting.master_trader_id
        source = self.mt5_setting.source
        try:
            while True:
                signals_from_api = self.get_signal_from_api(
                    master_trader_id, source)

                self.logger.info("-------------START---------------")
                self.logger.info(f"Bot info {self.bot_info}")

                self.logger.info(
                    f"\nGet {len(signals_from_api)} signal(s):\n{signals_from_api}\n"
                )
                self.process_signals_from_master_trader(
                    master_trader_id, signals_from_api
                )

                self.logger.info(
                    f"\nDetail bot info:\n{self.mt5_handler.get_bot_info()}")
                self.logger.info("--------------END----------------")

                time.sleep(30)
        finally:
            self.logger.info(f"Bot info {self.bot_info} is going to shutdown")
            self.logger.info("--------------SHUTDOWN MT5---------------")
            self.mt5_handler.shutdown()


def worker(mt5_setting: Mt5Setting, bot_config: BotConfig):
    bot = TradingFromSignal(mt5_setting, bot_config)
    bot.run()


def bot_runner():
    with open("./terminal_login.json") as content:
        config = json.load(content)

    bot_config = from_dict(data_class=BotConfig, data=config)
    terminals = config["terminals"]
    procs = []
    mt5_settings = [Mt5Setting(**terminal) for terminal in terminals]

    for mt5_setting in mt5_settings:
        proc = Process(target=worker, args=(mt5_setting, bot_config))
        procs.append(proc)
        proc.start()

    for proc in procs:
        proc.join()


if __name__ == "__main__":
    bot_runner()
