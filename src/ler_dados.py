from pathlib import Path

import pandas as pd

BRONZE = Path("dados/bronze/gpu")
PADRAO = "gpuDATA_*.csv"

arquivos = sorted(BRONZE.glob(PADRAO))
if not arquivos:
    raise FileNotFoundError(f"nenhum arquivo {PADRAO} em {BRONZE}")

df = pd.read_csv(arquivos[-1])
print(arquivos[-1].name, df.shape)