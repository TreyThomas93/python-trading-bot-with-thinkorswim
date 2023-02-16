from datetime import datetime
import logging


class Formatter(logging.Formatter):

    """override logging.Formatter to use an naive datetime object"""

    def formatTime(self, _, datefmt=None) -> str:
        dt = datetime.utcnow()

        s = None
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            try:
                s = dt.isoformat(timespec='milliseconds')
            except TypeError:
                s = dt.isoformat()

        return s

    def formatMessage(self, record: logging.LogRecord) -> str:
        # print(record.levelname)
        return super().formatMessage(record)
