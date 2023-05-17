
from abc import ABC
from dataclasses import _MISSING_TYPE, dataclass, fields
from enum import Enum
from typing import List, Optional

from handlers.constant import Common


class BaseDataClass(ABC):
    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if field.default is not _MISSING_TYPE and value is None:
                setattr(self, field.name, field.default)


class TradeType(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class BotConfig(BaseDataClass):
    base_controller_url: str
    log_folder_path: str
    log_level: str
    separator_number_string: str = Common.SEPRATOR_NUMBER_STRING


@dataclass
class TradeSignal(BaseDataClass):
    id: int
    external_signal_id: str
    symbol: str
    type: str
    size: float
    time: str
    price_order: float
    market_price: float
    stop_loss: Optional[float] = Common.DEFAULT_STOP_LOSS
    take_profit: Optional[float] = Common.DEFAULT_TAKE_PROFIT
    magic_numbers: Optional[int] = 0
    time_diff: Optional[float] = 0.0
    price_diff: Optional[float] = 0.0


@dataclass
class MasterTrader(BaseDataClass):
    external_trader_id: str
    source: str
    signals: List[TradeSignal]
    invalid_symbol_signal_count: Optional[int] = 0


@dataclass
class Mt5Setting(BaseDataClass):
    server: str
    login_id: int
    password: str
    setup_path: str
    copied_volume_coefficient: float
    symbol_postfix: str
    master_traders: dict
    bot_name: str
    type_filling: str
    max_allowed_order_age_to_copy_in_minutes: int
    max_allowed_price_difference_in_pips: float
