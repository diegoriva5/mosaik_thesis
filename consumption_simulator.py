# consumption_simulator.py
import mosaik_api
import csv

META = {
    "api_version": "3.0",
    "type": "time-based",
    "models": {
        "Load": {
            "public": True,
            "params": ["csv_file"],
            "attrs": ["P_load[kW]"],
        }
    },
}


class Simulator(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.entities = {}
        self.profiles = {}  # dict: eid → list of (time, value)

    def init(self, sid, time_resolution=None, step_size=900, **kwargs):
        self.step_size = step_size
        return self.meta

    def create(self, num, model, csv_file, **kwargs):
        created = []
        for _ in range(num):
            eid = f"Load_{len(self.entities)}"
            # carica il profilo
            profile = []
            with open(csv_file, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # assumo colonne 'time' (int, secondi) e 'P_load[kW]'
                    profile.append((int(row["time"]), float(row["P_load[kW]"])))
            self.profiles[eid] = profile
            self.entities[eid] = {"profile": profile}
            created.append({"eid": eid, "type": model})
        return created

    def step(self, time, inputs):
        outputs = {}
        for eid, ent in self.entities.items():
            # trova nel profilo il valore relativo al time corrente (o ultimo ≤ time)
            vals = [p for p in ent["profile"] if p[0] <= time]
            p_load = vals[-1][1] if vals else 0.0
            outputs[eid] = {"P_load[kW]": p_load}
        return outputs

    def get_data(self, outputs):
        data = {}
        for eid in outputs:
            ent = self.entities[eid]
            # potenza corrente
            # (il valore è già nell’ultimo step)
            p = ent["profile"][-1][1] if ent["profile"] else 0.0
            data[eid] = {"P_load[kW]": p}
        return data
