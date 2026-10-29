import json
import logging
import os
import shutil
from datetime import date, datetime
from pathlib import Path

import kagglehub

import config

log = logging.getLogger(__name__)


def baixar(dataset: str, cache: Path):
    cache.mkdir(exist_ok=True, parents=True)
    os.environ["KAGGLEHUB_CACHE"] = str(cache)
    pasta = kagglehub.dataset_download(dataset)
    log.info("dataset %s baixado em: %s", dataset, pasta)
    return Path(pasta)


def localizar(pasta):
    arquivos = list(pasta.glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError("nenhum CSV")
    log.info("arquivos encontrados: %s", [a.name for a in arquivos])
    return arquivos[0]


def copiar(origem: Path, bronze_dir: Path, prefixo: str):
    bronze_dir.mkdir(parents=True, exist_ok=True)
    hoje = date.today().strftime("%Y%m%d")
    destino = bronze_dir / f"{prefixo}_{hoje}.csv"
    shutil.copy(origem, destino)
    log.info("arquivo copiado para: %s", destino)
    return destino


def registrar(origem: Path, destino: Path, dataset: str, bronze_dir: Path):
    info = {
        "fonte": dataset,
        "arquivo_origem": origem.name,
        "arquivo_bronze": destino.name,
        "extraido_em": datetime.now().isoformat(),
    }
    (bronze_dir / "infoDATASET.json").write_text(json.dumps(info, indent=2), encoding="utf-8")


def ingerir_fonte(nome_fonte: str):
    fonte = config.FONTES[nome_fonte]
    log.info("ingestao da fonte: %s", nome_fonte)
    pasta = baixar(fonte["dataset"], fonte["cache_dir"])
    origem = localizar(pasta)
    destino = copiar(origem, fonte["bronze_dir"], fonte["prefixo"])
    registrar(origem, destino, fonte["dataset"], fonte["bronze_dir"])


def main():
    for nome in ("gpu", "llm"):
        ingerir_fonte(nome)


if __name__ == "__main__":
    config.configurar_log()
    config.criar_pastas()
    main()
