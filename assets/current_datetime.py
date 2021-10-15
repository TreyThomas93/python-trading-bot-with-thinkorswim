# imports
import pytz
from datetime import datetime


def getDatetime():

    dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

    dt_eastern = dt.astimezone(pytz.timezone('US/Eastern'))

    return datetime.strptime(dt_eastern.strftime(
        "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
