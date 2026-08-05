import json
import os

class Vault:
    def __init__(self):
        # Starting trading pot
        self.balance = 1000.0

        # Price data for each coin (filled externally)
        self.data = {
            "BTC": [],
            "ETH": [],
            "SOL": [],
            "XRP": [],
            "ADA": []
        }

        # Vault skim storage
        self.vault_value = 0.0

    def load(self):
        if os.path.exists("vault.json"):
            with open("vault.json", "r") as f:
                saved = json.load(f)
                self.balance = saved.get("balance", self.balance)
                self.vault_value = saved.get("vault_value", self.vault_value)
                self.data = saved.get("data", self.data)

    def save(self):
        with open("vault.json", "w") as f:
            json.dump({
                "balance": self.balance,
                "vault_value": self.vault_value,
                "data": self.data
            }, f, indent=2)
