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

            logger.ERROR(f"ACCOUNT ID: {self.account_id} TRADER: {self.user['Name']}")

    return wrapper