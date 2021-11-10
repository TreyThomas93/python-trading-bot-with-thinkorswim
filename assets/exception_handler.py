# EXCEPTION HANDLER DECORATOR FOR HANDLER EXCEPTIONS AND LOGGING THEM
from assets.helper_functions import modifiedAccountID
import traceback


def exception_handler(func):

    def wrapper(self, *args, **kwargs):

        logger = self.logger

        try:

            return func(self, *args, **kwargs)

        except Exception as e:

            msg = f"{self.user['Name']} - {modifiedAccountID(self.account_id)} - {traceback.format_exc()}"

            logger.error(msg)

    return wrapper
