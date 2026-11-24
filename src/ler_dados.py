import logging

import pandas as pd

import config

log = logging.getLogger(__name__)


def main(fonte="gpu"):
    bronze = config.FONTES[fonte]["bronze_dir"]
    padrao = config.FONTES[fonte]["padrao"]
    arquivos = sorted(bronze.glob(padrao))
    if not arquivos:
        raise FileNotFoundError(f"nenhum arquivo {padrao} em {bronze}")

    df = pd.read_csv(arquivos[-1])
    log.info("arquivo mais recente %s: %s", arquivos[-1].name, df.shape)


if __name__ == "__main__":
    config.configurar_log()
    main()