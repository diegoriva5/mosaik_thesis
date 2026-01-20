import pandas as pd
import numpy as np

INPUT_FILE = "csv_data/load_istat_social_groups.csv"
OUTPUT_FILE = "pv_DA_production_prediction.csv"

# Carica il CSV per ottenere la struttura
df = pd.read_csv(INPUT_FILE)

# Header e prima colonna intatti
col_ids = df.columns
row_ids = df.iloc[:, 0]

# Dati interni (usati solo per la forma)
data = df.iloc[1:, 1:].astype(float).reset_index(drop=True)

modified = data.copy()

# Per PV production, genera valori casuali con pattern giornaliero
# Probabilità di modifica (qui usata per generare nuovi valori)
p = 1.0  # Sempre genera nuovi valori

# Parametri della gaussiana per PV (picco a mezzogiorno)
mu = 12.0      # picco alle 12
sigma = 2.0    # larghezza della curva

for i in range(len(data)):
    hour = i % 24

    # Peso gaussiano per l'ora (massima produzione a mezzogiorno)
    w = np.exp(-((hour - mu) ** 2) / (2 * sigma ** 2))

    # Produzione massima scalata dalla gaussiana
    max_production = 5000 * w

    for j in range(data.shape[1]):
        # Genera produzione casuale tra 0 e max_production
        val = np.random.uniform(0, max_production)

        # Arrotonda alla prima cifra decimale in Watt e assicurati >= 0
        val = max(0, round(val, 1))  # precisione 0.1 W

        modified.iat[i, j] = val

# Ricostruzione finale
df_out = pd.concat([row_ids, modified], axis=1)
df_out.columns = col_ids

df_out.to_csv(OUTPUT_FILE, index=False)