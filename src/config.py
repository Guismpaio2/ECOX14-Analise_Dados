"""Configuracao central do pipeline de dados."""

import logging
from datetime import datetime
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent

DADOS = RAIZ / "dados"
BRONZE = DADOS / "bronze"
PRATA = DADOS / "prata"
OURO = DADOS / "ouro"
RELATORIOS = RAIZ / "relatorios"
LOGS = RAIZ / "logs"

BRONZE_GPU = BRONZE / "gpu"
BRONZE_LLM = BRONZE / "llm"

KAGGLE_CACHE_GPU = BRONZE_GPU / "Kaggle_cache"
KAGGLE_CACHE_LLM = BRONZE_LLM / "Kaggle_cache"

FONTES = {
    "gpu": {
        "dataset": "riyagarg0314/gpu-specs-database-nvidia-and-amd-1995-2026",
        "bronze_dir": BRONZE_GPU,
        "prefixo": "gpuDATA",
        "cache_dir": KAGGLE_CACHE_GPU,
        "padrao": "gpuDATA_*.csv",
    },
    "llm": {
        "dataset": "jainaru/llms-data-2018-2024",
        "bronze_dir": BRONZE_LLM,
        "prefixo": "llmDATA",
        "cache_dir": KAGGLE_CACHE_LLM,
        "padrao": "llmDATA_*.csv",
    },
}

ARQUIVO_LOG = LOGS / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
ARQUIVO_LOG_LATEST = LOGS / "pipeline_latest.log"


def configurar_log(nivel=logging.INFO):
    LOGS.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=nivel,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(ARQUIVO_LOG, encoding="utf-8"),
            logging.FileHandler(ARQUIVO_LOG_LATEST, encoding="utf-8", mode="w"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def criar_pastas():
    for pasta in (
        BRONZE_GPU,
        BRONZE_LLM,
        KAGGLE_CACHE_GPU,
        KAGGLE_CACHE_LLM,
        PRATA,
        OURO,
        RELATORIOS,
        LOGS,
    ):
        pasta.mkdir(parents=True, exist_ok=True)
