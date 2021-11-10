from datetime import datetime
import logging

class Formatter(logging.Formatter):

    """override logging.Formatter to use an naive datetime object"""

    def formatTime(self, record, datefmt=None):

        dt = datetime.utcnow()

        if datefmt:

            s = dt.strftime(datefmt)

        else:

            try:

                s = dt.isoformat(timespec='milliseconds')
                
            except TypeError:

                s = dt.isoformat()

        return s