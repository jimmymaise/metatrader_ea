import logging
import os


class Logger:
    def __init__(self, logger_name=__name__, log_file_path=None, message_prefix="", log_level="DEBUG"):
        # Create a logger object
        self._logger = logging.getLogger(logger_name)

        level = getattr(logging, log_level.upper(), logging.DEBUG)

        self._logger.setLevel(logging.DEBUG)
        self.message_prefix = message_prefix

        # Check if handlers are already configured
        if not self._logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)

            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s")
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)

            if log_file_path:
                if not os.path.exists(os.path.dirname(log_file_path)):
                    os.makedirs(os.path.dirname(log_file_path))
                file_handler = logging.FileHandler(log_file_path)
                file_handler.setLevel(level)

                file_handler.setFormatter(formatter)
                self._logger.addHandler(file_handler)

    def get_logger(self):
        return self

    def info(self, message):
        self._logger.info(f"{self.message_prefix}|{message}")

    def debug(self, message):
        self._logger.debug(f"{self.message_prefix}|{message}")

    def warning(self, message):
        self._logger.warning(f"{self.message_prefix}|{message}")

    def error(self, message):
        self._logger.error(f"{self.message_prefix}|{message}")
