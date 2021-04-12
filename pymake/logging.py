import logging

GREEN = "\x1b[32;21m"
GREY = "\x1b[38;21m"
YELLOW = "\x1b[33;21m"
RED = "\x1b[31;21m"
BOLD_RED = "\x1b[31;1m"
RESET = "\x1b[0m"


class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    def format(self, record: logging.LogRecord):
        formatter = logging.Formatter({
            logging.DEBUG: GREEN,
            logging.INFO: GREY,
            logging.WARNING: YELLOW,
            logging.ERROR: RED,
            logging.CRITICAL: BOLD_RED
        }[record.levelno]
            + "%(levelname)s [%(pathname)s:%(lineno)d]: %(message)s"
            + RESET)
        return formatter.format(record)


logger = logging.getLogger('pymake')
handler = logging.StreamHandler()
handler.setFormatter(CustomFormatter())
logger.addHandler(handler)
