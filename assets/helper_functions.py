import pytz
from datetime import datetime

# PLACE YOUR TIMEZONE HERE (VIEW PYTZ DOCS FOR YOUR CORRECT TIMEZONE FORMAT)
timezone = "US/Central"

def getDatetime():

    dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

    dt = dt.astimezone(pytz.timezone(timezone))

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

        dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

        dt = dt.astimezone(pytz.timezone(timezone)) 

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