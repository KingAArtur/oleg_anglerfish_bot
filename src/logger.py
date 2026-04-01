from abc import ABC
import logging
import datetime


def set_handler(logger: logging.Logger, handler: logging.Handler):
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s | %(message)s',
        datefmt='%m-%d-%Y %H:%M:%S',
    )
    logger.handlers.clear()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class Logger(ABC):
    def __init__(self):
        pass

    def debug(self, msg: str):
        raise NotImplementedError

    def info(self, msg: str):
        raise NotImplementedError

    def warning(self, msg: str):
        raise NotImplementedError

    def error(self, msg: str):
        raise NotImplementedError


class BaseLogger(Logger):
    def __init__(self, name: str):
        super().__init__()

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        set_handler(self.logger, logging.StreamHandler())

    def _logger(self):
        return self.logger

    def debug(self, msg: str):
        self._logger().debug(msg)

    def info(self, msg: str):
        self._logger().info(msg)

    def warning(self, msg: str):
        self._logger().warning(msg)

    def error(self, msg: str):
        self._logger().error(msg)


class FileLogger(BaseLogger):
    def __init__(self, name: str, filename: str):
        super().__init__(name=name)

        handler = logging.FileHandler(filename=filename)
        set_handler(self.logger, handler)


class DateFileLogger(FileLogger):
    def __init__(self, name: str, filename: str):
        self.filename = filename
        self.date = datetime.date.today()
        super().__init__(name=name, filename=self._name_with_date(self.filename, self.date))

    @staticmethod
    def _name_with_date(filename: str, date: datetime.date) -> str:
        if '.' not in filename:
            return f"{filename}_{date}"

        name, extension = '.'.join(filename.split(".")[:-1]), filename.split(".")[-1]
        return f"{name}_{date}.{extension}"

    def _logger(self):
        if self.date != datetime.date.today():
            self.date = datetime.date.today()

            handler = logging.FileHandler(filename=self._name_with_date(self.filename, self.date))
            set_handler(self.logger, handler)

        return self.logger
