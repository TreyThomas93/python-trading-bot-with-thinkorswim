import pytz
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import os

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

path = Path(THIS_FOLDER)

load_dotenv(dotenv_path=f"{path.parent}/config.env")

TIMEZONE = os.getenv('TIMEZONE')

def getDatetime():

    dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

    dt = dt.astimezone(pytz.timezone(TIMEZONE))

    return datetime.strptime(dt.strftime(
        "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")

def selectSleep():
        """
        PRE-MARKET(0400 - 0930 ET): 5 SECONDS
        MARKET OPEN(0930 - 1600 ET): 5 SECONDS
        AFTER MARKET(1600 - 2000 ET): 5 SECONDS

        WEEKENDS: 60 SECONDS
        WEEKDAYS(2000 - 0400 ET): 60 SECONDS

        EVERYTHING WILL BE BASED OFF CENTRAL TIME

        OBJECTIVE IS TO FREE UP UNNECESSARY SERVER USAGE
        """

        dt = getDatetime()

        day = dt.strftime("%a")

        tm = dt.strftime("%H:%M:%S")

        weekends = ["Sat", "Sun"]

        # IF CURRENT TIME GREATER THAN 8PM AND LESS THAN 4AM, OR DAY IS WEEKEND, THEN RETURN 60 SECONDS
        if tm > "20:00" or tm < "04:00" or day in weekends:

            return 60

        # ELSE RETURN 5 SECONDS
        return 5

def modifiedAccountID(account_id):

    return '*' * (len(str(account_id)) - 4) + str(account_id)[-4:]