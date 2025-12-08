# smart_meter.py
import mosaik_api

META = {
    "api_version": "3.0",
    "type": "time-based",
    "models": {
        "Meter": {
            "public": True,
            "params": [],
            "attrs": ["P_pv[kW]", "P_load[kW]"],
        }
    },
}


class Simulator(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.entities = {}

    def init(self, sid, time_resolution=None, step_size=900, **kwargs):
        self.step_size = step_size
        return self.meta

    def create(self, num, model, **kwargs):
        created = []
        for _ in range(num):
            eid = f"Meter_{len(self.entities)}"
            self.entities[eid] = {"P_pv": 0.0, "P_load": 0.0}
            created.append({"eid": eid, "type": model})
        return created

    def step(self, time, inputs):
        outputs = {}
        for eid, inp in inputs.items():
            # prendi valori PV e consumi se presenti
            pv = inp.get("P[kW]", [0.0])
            load = inp.get("P_load[kW]", [0.0])
            pv = pv[-1] if isinstance(pv, list) else pv
            load = load[-1] if isinstance(load, list) else load
            self.entities[eid]["P_pv"] = pv
            self.entities[eid]["P_load"] = load
            outputs[eid] = {
                "P_pv[kW]": pv,
                "P_load[kW]": load,
                # potresti aggiungere anche outputs come P_from_grid, P_to_grid, bilancio, ecc.
            }
        return outputs

    def get_data(self, outputs):
        data = {}
        for eid in outputs:
            ent = self.entities[eid]
            data[eid] = {
                "P_pv[kW]": ent["P_pv"],
                "P_load[kW]": ent["P_load"],
            }
        return data
