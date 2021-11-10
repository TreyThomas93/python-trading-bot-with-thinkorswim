import logging
from logging.handlers import RotatingFileHandler

# ['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__',
# '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', 'args', 'created', 'exc_info', 'exc_text', 'filename', 'funcName', 'getMessage', 'levelname', 'levelno', 'lineno', 'module', 'msecs', 'msg', 'name', 'pathname', 'process', 'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName']


class MultiFileHandler(RotatingFileHandler):

    def __init__(self, filename, mode, encoding=None, delay=0):

        RotatingFileHandler.__init__(
            self, filename, mode, maxBytes=10000, backupCount=1, encoding=None, delay=0)

    def emit(self, record):

        if "log" in dir(record) and not record.log:

            return

        self.change_file(record.levelname)

        logging.FileHandler.emit(self, record)

    def change_file(self, levelname):

        file_id = None

        if levelname == "WARNING":

            file_id = "logs/warning.log"

        elif levelname == "ERROR":

            file_id = "logs/error.log"

        elif levelname == "DEBUG":

            file_id = "logs/debug.log"

        elif levelname == "INFO":

            file_id = "logs/info.log"

        if file_id is not None:

            self.stream.close()

            self.baseFilename = file_id

            self.stream = self._open()
