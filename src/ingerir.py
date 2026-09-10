import json
import os
import shutil
from datetime import date, datetime
from pathlib import Path

import kagglehub


CACHE = Path.cwd() / "dados/bronze/gpu/Kaggle_cache"
# CACHE = Path.cwd() / "dados/bronze/llm/Kaggle_cache"
CACHE.mkdir(exist_ok=True, parents=True)

os.environ["KAGGLEHUB_CACHE"] = str(CACHE)

DATASET = "riyagarg0314/gpu-specs-database-nvidia-and-amd-1995-2026"
# DATASET = "jainaru/llms-data-2018-2024"

BRONZE = Path("dados/bronze/gpu")
# BRONZE = Path("dados/bronze/llm")

PREFIXO = "gpuDATA"
# PREFIXO = "llmDATA"


def baixar():
    pasta = kagglehub.dataset_download(DATASET)
    print("baixado em:", pasta)
    return Path(pasta)


def localizar(pasta):
    arquivos = list(pasta.glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError("nenhum CSV")
    print("encontrados:", [a.name for a in arquivos])
    return arquivos[0]


def copiar(origem):
    BRONZE.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y%m%d")
    destino = BRONZE / f"{PREFIXO}_{hoje}.csv"
    shutil.copy(origem, destino)
    print("copiado para:", destino)
    return destino


def registrar(origem, destino):
    info = {
        "fonte": DATASET,
        "arquivo_origem": origem.name,
        "arquivo_bronze": destino.name,
        "extraido_em": datetime.now().isoformat(),
    }
    (BRONZE / "infoDATASET.json").write_text(json.dumps(info, indent=2))


def main():
    pasta = baixar()
    origem = localizar(pasta)
    destino = copiar(origem)
    registrar(origem, destino)


if __name__ == "__main__":
    main()
