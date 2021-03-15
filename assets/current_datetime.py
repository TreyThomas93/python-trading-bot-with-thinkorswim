# imports
import pytz
from datetime import datetime


def getDatetime():

    dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

    dt_central = dt.astimezone(pytz.timezone('US/Central'))

    return datetime.strptime(dt_central.strftime(
        "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
