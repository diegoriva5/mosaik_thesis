import pandas as pd
import numpy as np

INPUT_FILE = "load_istat_social_groups.csv"
OUTPUT_FILE = "rt_consumes.csv"

# Carica il CSV
df = pd.read_csv(INPUT_FILE)

# Header e prima colonna intatti
col_ids = df.columns
row_ids = df.iloc[:, 0]

# Dati interni
data = df.iloc[1:, 1:].astype(float).reset_index(drop=True)

modified = data.copy()

# Probabilità di modifica
p = 0.10

# Parametri della gaussiana
mu = 15.5      # picco alle 15-16
sigma = 2.0    # larghezza della curva

for i in range(len(data)):
    hour = i % 24

    # Peso gaussiano per l'ora
    w = np.exp(-((hour - mu) ** 2) / (2 * sigma ** 2))

    # Aumento massimo scalato dalla gaussiana
    max_increase = 2000 * w

    for j in range(data.shape[1]):
        x = data.iat[i, j]

        if np.random.rand() < p:
            if np.random.rand() < 0.5:
                # Aumento proporzionale al peso gaussiano
                delta = np.random.uniform(0, max_increase)
                modified.iat[i, j] = x + delta
            else:
                # Diminuzione proporzionale al peso gaussiano
                delta = np.random.uniform(0, x * w)
                modified.iat[i, j] = x - delta
        else:
            modified.iat[i, j] = x

# Ricostruzione finale
df_out = pd.concat([row_ids, modified], axis=1)
df_out.columns = col_ids

df_out.to_csv(OUTPUT_FILE, index=False)