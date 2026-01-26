import mosaik_api_v3
from web3 import Web3
import json
from time import sleep

META = {
    "api_version": "3.0",
    "type": "hybrid",
    "models": {
        "DAMarket": {
            "public": True,
            "params": ["rpc_url", "contract_address", "abi_path", "private_keys"],
            "attrs": ["slot"],  # slot corrente (ora)
        },
    },
}


class DAMarketSimulator(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(META)
        self.smart_meters = {}
        self.slot = 0
        self.cache = {}
        self.step_size = 3600

    def init(self, sid, step_size=3600, rpc_url=None, contract_address=None, abi_path=None, private_keys=None, **kwargs):
        self.step_size = step_size

        # --- Connessione Web3 ---
        if rpc_url is None or contract_address is None or abi_path is None:
            raise ValueError("RPC, contract_address e abi_path devono essere forniti")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise RuntimeError(f"Cannot connect to RPC: {rpc_url}")

        # --- Carica ABI ---
        with open(abi_path) as f:
            self.contract_abi = json.load(f)["abi"]
        self.contract = self.w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=self.contract_abi)

        # --- Private keys dict ---
        self.private_keys = {Web3.to_checksum_address(addr): key for addr, key in private_keys.items()}

        return META

    def create(self, num, model, **model_params):
        eid = f"DAMarket_{num}"
        self.cache[eid] = {"slot": 0}
        return [{"eid": eid, "type": model, "rel": []}]

    def step(self, time, inputs, max_advance=None):
        """
        - Legge P_net_DA dagli SmartMeter
        - Piazza ordini sulla blockchain
        - Aggiorna P_DA_committed sugli SmartMeter
        """
        self.slot = int(time // self.step_size)

        # Raccogli tutti i netti DA dagli smart meter
        net_da_orders = {}
        for eid, attrs in inputs.items():
            if "P_net_DA[kW]" in attrs:
                net_da_orders[eid] = attrs["P_net_DA[kW]"]

        # --- Invio ordini al contratto blockchain ---
        for sm_eid, P_net in net_da_orders.items():
            if sm_eid not in self.private_keys:
                continue
            acct = Web3.to_checksum_address(sm_eid[-42:])  # assume che l'ultimo addr sia l'indirizzo
            private_key = self.private_keys[acct]

            # Decide tipo ordine
            is_sell = P_net > 0
            kWh = abs(P_net)
            price_eth = 0.01  # esempio: prezzo fisso, si può migliorare

            try:
                self.place_order_onchain(acct, private_key, is_sell, kWh, price_eth, self.slot)
            except Exception as e:
                print(f"Error placing order for {sm_eid}: {e}")

        # --- Esegui slot ---
        try:
            executor = next(iter(self.private_keys.keys()))
            self.execute_slot_onchain(executor, self.private_keys[executor], self.slot)
        except Exception as e:
            print(f"Error executing slot {self.slot}: {e}")

        # --- Aggiorna P_DA_committed sui SmartMeter ---
        trades_list = self.contract.functions.getTrades(self.slot).call()
        for t in trades_list:
            seller, buyer, kwh, price_wei, ts = t
            for sm_eid in self.cache:
                if sm_eid.endswith(seller):
                    self.cache[sm_eid]["P_DA_committed[kW]"] = kwh
                if sm_eid.endswith(buyer):
                    self.cache[sm_eid]["P_DA_committed[kW]"] = -kwh

        return time + self.step_size

    def get_data(self, outputs):
        return {
            eid: {attr: self.cache.get(eid, {}).get(attr, 0.0) for attr in attrs}
            for eid, attrs in outputs.items()
        }

    # ------------------------
    # Funzioni blockchain
    # ------------------------
    def safe_nonce(self, addr):
        return self.w3.eth.get_transaction_count(addr)

    def sign_and_send(self, tx_dict, private_key):
        signed = self.w3.eth.account.sign_transaction(tx_dict, private_key=private_key)
        raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
        tx_hash = self.w3.eth.send_raw_transaction(raw)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt

    def place_order_onchain(self, account, private_key, is_sell, kWh, price_eth, slot):
        price_wei = self.w3.to_wei(price_eth, "ether")
        value = 0
        if not is_sell:
            value = int(kWh * price_wei)
        tx = self.contract.functions.placeOrder(is_sell, int(kWh), int(price_wei), slot).build_transaction({
            "from": account,
            "value": value,
            "gas": 600000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.safe_nonce(account),
            "chainId": 31337,
        })
        receipt = self.sign_and_send(tx, private_key)
        return receipt

    def execute_slot_onchain(self, executor_account, private_key, slot):
        tx = self.contract.functions.executeSlot(slot).build_transaction({
            "from": executor_account,
            "gas": 1500000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.safe_nonce(executor_account),
            "chainId": 31337,
        })
        receipt = self.sign_and_send(tx, private_key)
        return receipt
