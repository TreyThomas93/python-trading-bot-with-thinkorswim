# EXCEPTION HANDLER DECORATOR FOR HANDLER EXCEPTIONS AND LOGGING THEM

from assets.logger import Logger

logger = Logger()

def exception_handler(func):

    def wrapper(self, *args, **kwargs):

        try:
            
            return func(self, *args, **kwargs)

        except KeyError:

            pass

        except ValueError:

            pass

        except TypeError:

            pass

        except AttributeError:

            pass

        except Exception:

            class_name = self.__class__.__name__

            acceptable_classes = ["Tasks", "LiveTrader"]

            if class_name in acceptable_classes:

                logger.ERROR(f"ACCOUNT ID: {self.account_id} TRADER: {self.user['Name']} CLASSNAME: {class_name}")

            else:

                logger.ERROR(f"CLASSNAME: {class_name}")

    return wrapper