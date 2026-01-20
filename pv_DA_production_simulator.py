# pv_DA_production_simulator.py
#
# Simulatore mosaik per previsioni Day-Ahead
# della produzione fotovoltaica oraria.
#
# Ogni entità mosaik rappresenta:
# - una singola abitazione (Home_i)
# - un singolo profilo PV
#
# Il simulatore:
# - legge un file CSV con dati in Watt (W)
# - restituisce la potenza prevista in kW
# - aggiorna il valore a ogni slot orario (1h)
#
# Non è presente alcun fattore di scala.

import itertools
import pandas as pd
import mosaik_api_v3


# -------------------------------------------------------------------
# META-DATA MOSAIK
# -------------------------------------------------------------------
META = {
    "api_version": "3.0",

    # time-based: il simulatore avanza con step temporali fissi
    "type": "time-based",

    "models": {
        "PV_DA_Production": {
            "public": True,

            # Parametri assegnati alla creazione dell'entità
            "params": [
                "profile_id",  # nome della colonna del CSV
            ],

            # Attributi dinamici prodotti a ogni step
            "attrs": [
                "PV_DA_Prod_Prediction[kW]",
            ],
        },
    },
}


class PVDAProductionSimulator(mosaik_api_v3.Simulator):
    """
    Simulatore mosaik per previsioni orarie
    di produzione fotovoltaica Day-Ahead.

    CSV atteso:
    - colonne: profili PV (0–9)
    - righe 1–8760: valori orari in Watt (W)

    Output:
    - PV_DA_Prod_Prediction[kW] per ogni ora simulata
    """

    def __init__(self):
        super().__init__(META)

        self.sid = None
        self.step_size = None

        # DataFrame con i dati orari (8760 righe)
        self.data = None

        # Stato interno delle entità: eid -> dict
        self.entities = {}

        # Contatore per ID univoci
        self.eid_counter = itertools.count()

        # Cache dei valori calcolati nello step corrente
        self.cache = {}

    # ----------------------------------------------------------------
    # INIT
    # ----------------------------------------------------------------
    def init(self, sid, csv_path, step_size=3600, **kwargs):
        """
        Inizializzazione:
        - carica CSV
        - verifica consistenza temporale
        """
        self.sid = sid
        self.step_size = step_size

        df = pd.read_csv(csv_path)
        df = df.dropna(how="all")

        # Gestione intestazione / righe extra
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
        """
        Crea una entità PV_DA_Production
        associata a una colonna del CSV.
        """

        entities = []
        profile_id = model_params["profile_id"]

        for _ in range(num):
            # Uniforme a LoadProfileSimulator
            eid = f"Home_{profile_id}"

            self.entities[eid] = {
                "profile_id": profile_id,
                "PV_DA_Prod_Prediction[kW]": 0.0,
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
        Aggiornamento a ogni step temporale.

        - 1 step = 1 ora
        - lettura dal CSV
        - conversione W → kW
        """

        hour_idx = int(time // self.step_size) % len(self.data)

        self.cache = {}

        for eid, ent in self.entities.items():
            profile = ent["profile_id"]

            # Valore in Watt
            p_w = self.data.iloc[hour_idx][profile]

            # Conversione W → kW
            p_kw = p_w / 1000.0
            print(f"[PV_DA] time={time}, eid={eid}, value={p_kw}")

            ent["PV_DA_Prod_Prediction[kW]"] = p_kw
            self.cache[eid] = p_kw

        return time + self.step_size

    # ----------------------------------------------------------------
    # GET_DATA
    # ----------------------------------------------------------------
    def get_data(self, outputs):
        """
        Restituisce i dati richiesti dagli altri simulatori.
        """

        data = {}

        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr == "PV_DA_Prod_Prediction[kW]":
                    data[eid][attr] = self.cache.get(eid, 0.0)

        return data
