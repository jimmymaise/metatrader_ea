# import the package
import json
import time
import requests
import MetaTrader5 as mt5
from multiprocessing import Process

from handlers.logger import Logger
from handlers.mt5_handler import Mt5Handler
from handlers.mt5_handler import Mt5Setting

SEPARATOR_NUMBER_STRING = '752'
BASE_CONTROLLER_URL = 'http://127.0.0.1:8000/'


class TradingFromSignal:
    def __init__(self, mt5_setting: Mt5Setting):
        self.logger = Logger(mt5_setting.log_file_path).get_logger()

        self.mt5_handler = Mt5Handler(mt5, self.logger, mt5_setting)
        self.mt5_setting = mt5_setting
        self.logger.error(mt5.last_error())

    def normalize_symbol(self, raw_symbol):
        return f"{raw_symbol.replace('/', '')}{self.mt5_setting.symbol_postfix}"

    def get_signal_from_api(self, master_id, source_id):
        headers = {'Content-Type': 'application/json'}
        url = f'{BASE_CONTROLLER_URL}/master_traders/{source_id}/{master_id}'
        self.logger.info(f'Calling api {url} to get info')

        resp = requests.get(url=url, headers=headers)

        if resp.status_code in [requests.codes.created, requests.codes.ok]:
            return resp.json()['signals']

        raise Exception(f'[Error] Cannot get data from server:'
                        f' Status code {resp.status_code}, {resp.json()}')

    def process_signals_from_master_trader(self, master_trader_id, signals):
        magic_number_prefix = f'{master_trader_id}{SEPARATOR_NUMBER_STRING}'
        magic_numbers_from_signals = []

        for signal in signals:
            signal['magic_numbers'] = int(
                f'{magic_number_prefix}{signal["signal_id"]}')
            magic_numbers_from_signals.append(signal['magic_numbers'])

        open_copied_positions_dict = {position.magic: position for position in
                                      self.mt5_handler.get_current_open_position() if
                                      str(position.magic).startswith(magic_number_prefix)}

        open_copied_position_to_be_closed_dict = {magic_number: position for magic_number, position in
                                                  open_copied_positions_dict.items() if
                                                  magic_number not in magic_numbers_from_signals}

        closed_copied_deals_dict = {deal.magic: deal for deal in
                                    self.mt5_handler.get_history_deal_within_x_days(10) if
                                    (is_deal_created_by_bot_and_closed :=
                                     str(deal.magic).startswith(
                                         magic_number_prefix) and not open_copied_positions_dict.get(
                                         deal.magic)
                                     )
                                    }

        for signal in signals:
            signal_magic_number = signal['magic_numbers']

            is_this_signal_created_but_closed = closed_copied_deals_dict.get(
                signal_magic_number)
            is_this_signal_created = open_copied_positions_dict.get(
                signal_magic_number)

            if is_this_signal_created_but_closed:
                self.logger.warning(
                    f"Signal {signal_magic_number} will be IGNORED as it belongs to closed deal")
                continue

            elif is_this_signal_created:
                # Check to need to update or ignore as exis already
                exist_open_position = open_copied_positions_dict.get(
                    signal_magic_number)
                is_up_to_date = (exist_open_position.sl == signal['stop_loss']
                                 and exist_open_position.tp == signal['take_profit'])
                if is_up_to_date:
                    self.logger.warning(
                        f"Signal {signal_magic_number} will be IGNORED as it is created with same information")
                    continue

                self.logger.info(
                    f"Signal {signal_magic_number} will UPDATE the position {exist_open_position.ticket}")
                self.mt5_handler.update_trade(
                    position_ticket=exist_open_position.ticket,
                    symbol=self.normalize_symbol(signal['symbol']),
                    stop_loss=signal['stop_loss'],
                    take_profit=signal['take_profit'],
                    magic_number=signal_magic_number,
                )

            else:
                self.logger.info(
                    f"Signal {signal_magic_number} will CREATE new trade")

                order_type = mt5.ORDER_TYPE_BUY if signal['type'] == 'BUY' else mt5.ORDER_TYPE_SELL

                self.mt5_handler.open_trade(symbol=self.normalize_symbol(signal['symbol']),
                                            order_type=order_type,
                                            volume=signal['size'],
                                            stop_loss=signal['stop_loss'],
                                            take_profit=signal['take_profit'],
                                            magic_number=signal_magic_number,
                                            )

        for _, position in open_copied_position_to_be_closed_dict.items():
            self.logger.warning(
                f"The position created by old Signal {position.magic} will be closed")
            self.mt5_handler.close_trade_by_position(position)

    def run(self):
        master_trader_id = self.mt5_setting.master_trader_id
        source = self.mt5_setting.source
        try:
            while True:
                signals_from_api = self.get_signal_from_api(
                    master_trader_id, source)

                self.logger.info('-------------START---------------')

                self.logger.info(f'\nGet signals {signals_from_api}\n')
                self.process_signals_from_master_trader(
                    master_trader_id, signals_from_api[0:])

                self.logger.info('--------------END----------------')

                time.sleep(30)
        finally:
            self.logger.info('--------------SHUTDOWN MT5---------------')
            self.mt5_handler.shutdown()


def worker(mt5_setting):
    bot = TradingFromSignal(mt5_setting)
    bot.run()


if __name__ == '__main__':
    with open('./terminal_login.json') as content:
        terminals = json.load(content)
    procs = []
    mt5_settings = [Mt5Setting(**terminal) for terminal in terminals]

    for mt5_setting in mt5_settings:
        proc = Process(target=worker, args=(mt5_setting,))
        procs.append(proc)
        proc.start()

    for proc in procs:
        proc.join()
