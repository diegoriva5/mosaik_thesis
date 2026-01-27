# load_profile_RT_simulator.py
#
# Simulatore mosaik per profili di carico elettrico REAL-TIME (RT).
#
# Ogni entità mosaik rappresenta:
# - un singolo profilo di consumo
# - un singolo agente di mercato
# - un singolo wallet blockchain
#
# Il simulatore:
# - legge un file CSV con dati REALI in Watt (W)
# - restituisce la potenza assorbita in kW
# - aggiorna il valore a ogni slot orario (1h)

import itertools
import pandas as pd
import mosaik_api_v3


# -------------------------------------------------------------------
# META-DATA MOSAIK
# -------------------------------------------------------------------
META = {
    "api_version": "3.0",

    # time-based: avanzamento a step temporali fissi
    "type": "time-based",

    "models": {
        "LoadProfileRT": {
            "public": True,

            # Parametri alla creazione
            "params": [
                "profile_id",  # nome colonna CSV
            ],

            # Attributi dinamici
            "attrs": [
                "P_load_RT[kW]",  # consumo reale orario
            ],
        },
    },
}


class LoadProfileRTSimulator(mosaik_api_v3.Simulator):
    """
    Simulatore mosaik per profili di carico REAL-TIME.

    CSV atteso:
    - colonne: profili di consumo
    - righe 1–8760: valori orari in Watt (W)

    Output:
    - P_load_RT[kW] per ogni ora simulata
    """

    def __init__(self):
        super().__init__(META)

        self.sid = None
        self.step_size = None
        self.data = None

        # Stato interno entità
        self.entities = {}

        # Cache valori step corrente
        self.cache = {}

        self.eid_counter = itertools.count()

    # ----------------------------------------------------------------
    # INIT
    # ----------------------------------------------------------------
    def init(self, sid, csv_path, step_size=3600, **kwargs):
        self.sid = sid
        self.step_size = step_size

        df = pd.read_csv(csv_path)
        df = df.dropna(how="all")

        if len(df) == 8761:
            df = df.iloc[1:].reset_index(drop=True)
        elif len(df) == 8759:
            raise ValueError(
                "CSV ha 8759 righe: manca un'ora (DST o dato mancante)"
            )

        if len(df) != 8760:
            raise ValueError(
                f"Numero righe inatteso: {len(df)} (atteso 8760)"
            )

        self.data = df.astype(float)

        return META

    # ----------------------------------------------------------------
    # CREATE
    # ----------------------------------------------------------------
    def create(self, num, model, **model_params):
        entities = []
        profile_id = model_params["profile_id"]

        for _ in range(num):
            eid = f"Home_{profile_id}"

            self.entities[eid] = {
                "profile_id": profile_id,
                "P_load_RT[kW]": 0.0,
            }

            entities.append({
                "eid": eid,
                "type": model,
                "rel": [],
            })

        return entities

    # ----------------------------------------------------------------
    # STEP
    # ----------------------------------------------------------------
    def step(self, time, inputs, max_advance=None):
        """
        Lettura REAL-TIME:
        - usa direttamente l'indice orario corrente
        """

        hour_idx = int(time // self.step_size) % len(self.data)

        self.cache = {}

        for eid, ent in self.entities.items():
            profile = ent["profile_id"]

            p_w = self.data.iloc[hour_idx][profile]
            p_kw = p_w / 1000.0

            print(f"[Load RT] time={time}, eid={eid}, "
                  f"hour_idx={hour_idx}, P_load_RT={p_kw:.3f} kW")

            ent["P_load_RT[kW]"] = p_kw
            self.cache[eid] = p_kw

        return time + self.step_size

    # ----------------------------------------------------------------
    # GET_DATA
    # ----------------------------------------------------------------
    def get_data(self, outputs):
        data = {}

        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr == "P_load_RT[kW]":
                    data[eid][attr] = self.cache.get(eid, 0.0)

        return data
