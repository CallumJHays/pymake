from logging import *

GREEN = "\x1b[32;21m"
GREY = "\x1b[38;5;245m"
YELLOW = "\x1b[33;21m"
RED = "\x1b[31;21m"
BLUE = "\x1b[36;21m"
BOLD_RED = "\x1b[31;1m"
RESET = "\x1b[0m"


class CustomFormatter(Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    def format(self, record: LogRecord):
        frame = getattr(record, 'frame', None)
        if frame:
            # calling frame override requested
            record.pathname = frame.filename
            record.lineno = frame.lineno
            record.funcName = frame.function

        if record.pathname.startswith('/home/'):
            record.pathname = f'~/{"/".join(record.pathname.split("/")[3:])}'

        formatter = Formatter({
            DEBUG: GREEN,
            INFO: GREY,
            WARNING: YELLOW,
            ERROR: RED,
            CRITICAL: BOLD_RED
        }[record.levelno]
            + "%(levelname)s [%(pathname)s:%(lineno)d]: %(message)s"
            + RESET)
        return formatter.format(record)


logger = getLogger('pymake')
handler = StreamHandler()
handler.setFormatter(CustomFormatter())
logger.addHandler(handler)
