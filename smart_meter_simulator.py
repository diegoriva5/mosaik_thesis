import mosaik_api_v3


META = {
    "api_version": "3.0",
    "type": "hybrid",
    "models": {
        "SmartMeter": {
            "public": True,
            "params": ["profile_id"],
            "attrs": [
                # Input / misure
                "P_PV_RT_Production[kW]",   # Energia prodotta dal PV in RT
                "P_load_DA_Prevision[kW]",  # Energia prevista in DA
                "P_load_RT[kW]",            # Energia consumata reale in RT

                # Commit di mercato
                "P_DA_committed[kW]",   # Energia acquistata/venduta Day-Ahead
                "P_RT_committed[kW]",   # Energia acquistata/venduta Real-Time

                # Output calcolati
                "P_net_DA[kW]",          # Bilancio netto Day-Ahead
                "P_net_phys_RT[kW]",     # Bilancio fisico Real-Time
                "P_net_RT[kW]",          # Bilancio netto Real-Time
            ],
        },
    },
}


class SmartMeterSimulator(mosaik_api_v3.Simulator):

    def __init__(self):
        super().__init__(META)
        self.entities = {}
        self.cache = {}

    def init(self, sid, step_size=3600, **kwargs):
        self.step_size = step_size
        return META

    def create(self, num, model, **model_params):
        pid = model_params["profile_id"]
        eid = f"Home_{pid}_SmartMeter"

        self.entities[eid] = {
            "P_PV_RT_Production[kW]": 0.0,
            "P_load_DA_Prevision[kW]": 0.0,
            "P_load_RT[kW]": 0.0,

            # Commit (per ora nulli)
            "P_DA_committed[kW]": 0.0,
            "P_RT_committed[kW]": 0.0,

            # Calcolati
            "P_net_DA[kW]": 0.0,
            "P_net_phys_RT[kW]": 0.0,
            "P_net_RT[kW]": 0.0,
        }

        return [{
            "eid": eid,
            "type": model,
            "rel": [],
        }]

    def step(self, time, inputs, max_advance=None):
        self.cache = {}

        for eid, ent in self.entities.items():
            attrs = inputs.get(eid, {})

            def read(attr):
                d = attrs.get(attr, {})
                return list(d.values())[0] if d else ent[attr]

            # Lettura input
            P_pv = read("P_PV_RT_Production[kW]")
            P_load_DA = read("P_load_DA_Prevision[kW]")
            P_load_RT = read("P_load_RT[kW]")
            P_DA = read("P_DA_committed[kW]")
            P_RT = read("P_RT_committed[kW]")

            # Calcoli
            P_net_DA = P_pv - P_load_DA
            P_net_phys_RT = P_pv - P_load_RT
            P_net_RT = P_net_phys_RT - P_DA - P_RT

            ent.update({
                "P_PV_RT_Production[kW]": P_pv,
                "P_load_DA_Prevision[kW]": P_load_DA,
                "P_load_RT[kW]": P_load_RT,
                "P_DA_committed[kW]": P_DA,
                "P_RT_committed[kW]": P_RT,
                "P_net_DA[kW]": P_net_DA,
                "P_net_phys_RT[kW]": P_net_phys_RT,
                "P_net_RT[kW]": P_net_RT,
            })

            self.cache[eid] = ent.copy()

        return time + self.step_size

    def get_data(self, outputs):
        return {
            eid: {
                attr: self.cache.get(eid, {}).get(attr, 0.0)
                for attr in attrs
            }
            for eid, attrs in outputs.items()
        }
