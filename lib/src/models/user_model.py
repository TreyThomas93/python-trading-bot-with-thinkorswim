

class User:

    def __init__(self, name: str, clientId: str, username: str, password: str, accounts: dict):
        self.name = name
        self.clientId = clientId
        self.username = username
        self.password = password
        self.accounts = accounts

    def toJson(self):
        return {
            "name": self.name,
            "clientId": self.clientId,
            "username": self.username,
            "password": self.password,
            "accounts": self.accounts
        }

    @classmethod
    def fromJson(cls, json: dict):
        instance = cls(
            name=json["name"],
            clientId=json["clientId"],
            username=json["username"],
            password=json["password"],
            accounts=json["accounts"]
        )
        return instance

    def __str__(self) -> str:
        return f"""User(
            name: {self.name},
            clientId: {self.clientId},
            username: {self.username},
            password: {self.password},
            accounts: {self.accounts}
        )"""
