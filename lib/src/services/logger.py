

from datetime import datetime
import os
from termcolor import colored, cprint


class LoggerService:

    def __init__(self) -> None:
        self.format = "{dt} [{level}] {message}"
        self.pathToLogsDirectory = f"{os.path.abspath(os.path.dirname(__file__))}".replace(
            'services', '/utils/logs')

    def __output(self, level, message) -> str:
        output = self.format.format(dt=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                                    level=level, message=message)

        color = None
        # https://github.com/termcolor/termcolor
        match level:
            case "INFO":
                color = "green"
            case "WARNING":
                color = "yellow"
            case "ERROR":
                color = "red"
            case "CRITICAL":
                color = "magenta"
            case _:
                color = "white"

        cprint(output, on_color='on_' + color, attrs=["bold"])
        return output

    def __addToLog(self, level: str, output: str):
        output = output.replace("\n", "")
        with open(self.pathToLogsDirectory + f"/{level.lower()}.log", "a+") as file:
            file.write(output + "\n")

    def info(self, message: str, log: bool = True):
        output = self.__output("INFO", message)

        if log:
            self.__addToLog(level="INFO", output=output)

    def error(self, message: str, log: bool = True):
        output = self.__output("ERROR", message)

        if log:
            self.__addToLog(level="ERROR", output=output)
