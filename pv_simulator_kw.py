import itertools
import mosaik_api_v3

meta = {
    "api_version": "3.0",
    "type": "hybrid",
    "models": {
        "PVKW": {
            "public": True,
            "params": [
                "latitude",
                "area",
                "efficiency",
                "el_tilt",
                "az_tilt",
                "max_kW",  # limite del contatore (6, 9, 12 kW)
            ],
            "attrs": [
                "P[kW]",       # output active power [kW]
                "DNI[W/m2]",   # input direct normal insolation [W/m2]
            ],
        },
    },
}


class PVSimulatorKW(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(meta)
        self._entities = {}
        self.eid_counters = {}
        self.cache = {}

    def init(self, sid, start_date=None, step_size=900, **kwargs):
        self.sid = sid
        self.step_size = step_size  # in secondi
        return self.meta

    def create(self, num, model, **model_params):
        counter = self.eid_counters.setdefault(model, itertools.count())
        entities = []

        for _ in range(num):
            eid = f"{model}_{next(counter)}"
            self._entities[eid] = {
                **model_params,
                "P[kW]": 0,
                "irradiance": 0,
            }
            entities.append({'eid': eid, 'type': model, 'rel': []})

        return entities

    def step(self, time, inputs, max_advance=None):
        self.cache = {}
        for eid, attrs in inputs.items():
            irr = attrs.get("DNI[W/m2]", {}).get(0, 0)  # prende il primo valore
            ent = self._entities[eid]
            ent["irradiance"] = irr

            # Potenza teorica
            P_theor = irr * ent["area"] * ent["efficiency"] / 1000.0  # W -> kW

            # Limite contatore
            max_kw = ent.get("max_kW", 6)
            ent["P[kW]"] = min(P_theor, max_kw)

            self.cache[eid] = ent["P[kW]"]

        return time + self.step_size

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr == "P[kW]":
                    data[eid][attr] = self.cache.get(eid, 0)
        return data
