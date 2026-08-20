from pathlib import Path

import pandas as pd

base_dir = Path(__file__).resolve().parent
path = base_dir.parent / "dados" / "bronze" / "gpu" / "gpu_database.csv"

df = pd.read_csv(path)

print(df.shape)