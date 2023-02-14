

class User:

    def __init__(self, name: str, clientId: str, username: str, password: str, accounts: dict):
        self.name = name
        self.clientId = clientId
        self.accounts = accounts

    def toJson(self):
        return {
            "name": self.name,
            "clientId": self.clientId,
            "accounts": self.accounts
        }

    @classmethod
    def fromJson(cls, json: dict):
        instance = cls(
            name=json["name"],
            clientId=json["clientId"],
            accounts=json["accounts"]
        )
        return instance

    def __str__(self) -> str:
        return f"""User(
            name: {self.name},
            clientId: {self.clientId},
            accounts: {self.accounts}
        )"""
