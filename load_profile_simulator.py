# load_profile_simulator.py
#
# Simulatore mosaik per profili di carico elettrico orari.
#
# Ogni entità mosaik rappresenta:
# - un singolo profilo di consumo
# - un singolo agente di mercato
# - un singolo wallet blockchain
#
# Il simulatore:
# - legge un file CSV con dati in Watt (W)
# - restituisce la potenza assorbita in kW
# - aggiorna il valore a ogni slot orario (1h)
#
# Non è presente alcun fattore di scala:
# le quantità scambiate sono quelle del singolo agente.

import itertools
import pandas as pd
import mosaik_api_v3


# -------------------------------------------------------------------
# META-DATA MOSAIK
# -------------------------------------------------------------------
# Descrive a mosaik:
# - il tipo di simulatore
# - i modelli disponibili
# - parametri e attributi delle entità
#
META = {
    "api_version": "3.0",

    # time-based: il simulatore avanza con step temporali fissi
    "type": "time-based",

    "models": {
        "LoadProfile": {
            "public": True,

            # Parametri assegnati alla creazione dell'entità
            "params": [
                "profile_id",  # nome della colonna del CSV
            ],

            # Attributi dinamici prodotti a ogni step
            "attrs": [
                "P_load[kW]",  # potenza assorbita nello slot orario
            ],
        },
    },
}


class LoadProfileSimulator(mosaik_api_v3.Simulator):
    """
    Simulatore mosaik per profili di carico orari.

    CSV atteso:
    - colonne: profili di consumo
    - riga 0: identificativi (NON dati orari)
    - righe 1–8760: valori orari in Watt (W)

    Output:
    - P_load[kW] per ogni ora simulata
    """

    def __init__(self):
        super().__init__(META)

        # ID del simulatore assegnato da mosaik
        self.sid = None

        # Dimensione dello step temporale (secondi)
        self.step_size = None

        # DataFrame con i dati orari (8760 righe)
        self.data = None

        # Stato interno delle entità: eid -> dict
        self.entities = {}

        # Contatore per ID univoci delle entità
        self.eid_counter = itertools.count()

        # Cache dei valori calcolati nello step corrente
        self.cache = {}

    # ----------------------------------------------------------------
    # INIT
    # ----------------------------------------------------------------
    def init(self, sid, csv_path, step_size=3600, **kwargs):
        """
        Inizializzazione del simulatore.
        - Carica CSV
        - Ignora la riga di intestazione
        - Controlla che ci siano 8760 ore × 10 profili
        """
        self.sid = sid
        self.step_size = step_size

        # Caricamento CSV (pandas legge automaticamente la prima riga come intestazione)
        df = pd.read_csv(csv_path)

        # Rimuove eventuali righe completamente vuote
        df = df.dropna(how="all")

        # Controllo: 8760 righe (ore), 10 colonne (profili 0–9)
        # Se ci sono 8761 righe → la prima è identificativa
        if len(df) == 8761:
            df = df.iloc[1:].reset_index(drop=True)

        # Se ce n'è una in meno (caso reale che stai vedendo)
        elif len(df) == 8759:
            raise ValueError(
                "CSV ha 8759 righe: manca un'ora. "
                "Controlla DST o dati mancanti."
            )

        if len(df) != 8760:
            raise ValueError(
                f"Numero righe inatteso: {len(df)} (atteso 8760)"
            )

        # Salva i dati
        self.data = df.astype(float)

        return META

    # ----------------------------------------------------------------
    # CREATE
    # ----------------------------------------------------------------
    def create(self, num, model, **model_params):
        """
        Creazione delle entità LoadProfile.

        Ogni entità:
        - è associata a una colonna del CSV
        - rappresenta un agente/wallet
        """

        entities = []

        for _ in range(num):
            eid = f"{model}_{next(self.eid_counter)}"

            self.entities[eid] = {
                "profile_id": model_params["profile_id"],
                "P_load[kW]": 0.0,
            }

            entities.append({
                "eid": eid,
                "type": model,
                "rel": []
            })

        return entities

    # ----------------------------------------------------------------
    # STEP
    # ----------------------------------------------------------------
    def step(self, time, inputs, max_advance=None):
        """
        Aggiornamento dello stato a ogni step temporale.

        - time è espresso in secondi dall'inizio simulazione
        - 1 step = 1 ora
        - il valore viene letto dal CSV e convertito in kW
        """

        # Conversione tempo mosaik → indice orario
        hour_idx = int(time // self.step_size) % len(self.data)

        self.cache = {}

        for eid, ent in self.entities.items():
            profile = ent["profile_id"]

            # Valore letto dal CSV in Watt
            p_w = self.data.iloc[hour_idx][profile]

            # Conversione W → kW
            p_kw = p_w / 1000.0

            ent["P_load[kW]"] = p_kw
            self.cache[eid] = p_kw

        # Richiesta del prossimo step
        return time + self.step_size

    # ----------------------------------------------------------------
    # GET_DATA
    # ----------------------------------------------------------------
    def get_data(self, outputs):
        """
        Restituisce a mosaik gli attributi richiesti
        da altri simulatori (es. MarketSimulator).
        """

        data = {}

        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr == "P_load[kW]":
                    data[eid][attr] = self.cache.get(eid, 0.0)

        return data
