# EXCEPTION HANDLER DECORATOR FOR HANDLER EXCEPTIONS AND LOGGING THEM

from assets.logger import Logger

logger = Logger()

def exception_handler(func):

    def wrapper(self, *args, **kwargs):

        class_name = self.__class__.__name__

        try:
            
            return func(self, *args, **kwargs)

        except KeyError:

            logger.ERROR(f"ACCOUNT ID: {self.account_id} TRADER: {self.user['Name']} CLASSNAME: {class_name}")

        except ValueError:

            logger.ERROR(f"ACCOUNT ID: {self.account_id} TRADER: {self.user['Name']} CLASSNAME: {class_name}")

        except TypeError:

            logger.ERROR(f"ACCOUNT ID: {self.account_id} TRADER: {self.user['Name']} CLASSNAME: {class_name}")

        except AttributeError:

            logger.ERROR(f"ACCOUNT ID: {self.account_id} TRADER: {self.user['Name']} CLASSNAME: {class_name}")

        except Exception:

            acceptable_classes = ["Tasks", "LiveTrader"]

            if class_name in acceptable_classes:

                logger.ERROR(f"ACCOUNT ID: {self.account_id} TRADER: {self.user['Name']} CLASSNAME: {class_name}")

            else:

                logger.ERROR(f"CLASSNAME: {class_name}")

    return wrapper