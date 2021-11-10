# EXCEPTION HANDLER DECORATOR FOR HANDLER EXCEPTIONS AND LOGGING THEM
from assets.helper_functions import modifiedAccountID
import logging


def exception_handler(func):

    def wrapper(self, *args, **kwargs):

        class_name = self.__class__.__name__

        try:

            return func(self, *args, **kwargs)

        except Exception as e:

            msg = f"{class_name} - {self.user['Name']} - {modifiedAccountID(self.account_id)} - {e}"

            logging.error(msg)

    return wrapper
