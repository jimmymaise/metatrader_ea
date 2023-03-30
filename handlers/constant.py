from enum import Enum


class SymbolFillingModeEnum(Enum):
    # https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants#enum_symbol_info_integer
    SYMBOL_FILLING_FOK = 1
    SYMBOL_FILLING_IOC = 2
    SYMBOL_FILLING_ALL = 3


class Common:
    SUCCESS_REQUEST_COMMENTS = ["Request executed", "Request executed partially"]
    MAPPING_FILLING_MODE_SYBOL_TO_ORDER = {
        "SYMBOL_FILLING_FOK": ["ORDER_FILLING_FOK"],
        "SYMBOL_FILLING_IOC": ["ORDER_FILLING_IOC"],
        "SYMBOL_FILLING_ALL": ["ORDER_FILLING_FOK", "ORDER_FILLING_IOC"],
    }
