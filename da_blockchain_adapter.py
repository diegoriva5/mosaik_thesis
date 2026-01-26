import subprocess
import json

class DABlockchainAdapter:
    def __init__(self, hardhat_path="blockchain/hardhat"):
        self.path = hardhat_path

    def submit_orders(self, slot, orders):
        """
        orders = {
            "Home_0": +1.2,
            "Home_1": -0.5,
        }
        """
        payload = {
            "slot": slot,
            "orders": orders
        }

        result = subprocess.run(
            ["npx", "hardhat", "run", "scripts/clearMarket.js"],
            cwd=self.path,
            input=json.dumps(payload),
            text=True,
            capture_output=True
        )

        return json.loads(result.stdout)
