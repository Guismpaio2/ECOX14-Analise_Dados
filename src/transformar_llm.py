from datetime import datetime
import logging

import pandas as pd

import config
import limpeza

BRONZE = config.FONTES["llm"]["bronze_dir"]
PRATA = config.PRATA
PADRAO = config.FONTES["llm"]["padrao"]

MESES = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
         "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}

log = logging.getLogger(__name__)


def carregar():
    arquivos = sorted(BRONZE.glob(PADRAO))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE}")
    caminho = arquivos[-1]
    # CSV usa encoding Windows-1252 — byte 0xb8 em "Common crawl · BigQuery"
    try:
        df = pd.read_csv(caminho, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(caminho, encoding="latin-1")
    log.info("lido: %s %s", caminho.name, df.shape)
    log.debug("colunas: %s", df.columns.tolist())
    log.debug("ausentes: %s", df.isna().sum().to_dict())
    return df, caminho


def renomear_colunas(df):
    # Corrige erro de digitação original da fonte
    return df.rename(columns={"Comapany": "Company"})


def tratar_tba(df):
    # "TBA" (To Be Announced) foi usado no lugar de ausentes em toda a tabela — não são NaN reais
    return df.replace("TBA", pd.NA)


def converter_ratio(df):
    """Ratio vem como '20:01' ou '286:01:00': e a razao 20:1 / 286:1 lida como hora.

    O numero antes do primeiro ':' e a razao tokens/parametros. Converter direto
    com to_numeric apagava a coluna inteira.
    """
    df["Ratio"] = pd.to_numeric(
        df["Ratio"].astype("string").str.extract(r"^(\d+):")[0], errors="coerce")
    log.info("Ratio recuperada: %s de %s", df["Ratio"].notna().sum(), len(df))
    return df


def converter_tipos(df):
    for coluna in ["Parameters", "Tokens", "ALScore"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    return df


def converter_data_lancamento(df):
    """Release Date vem como 'YY-Mon' ('24-Apr'): e abril de 2024, nao dia 24.

    O Excel inverteu 'Apr-24'. Os prefixos vao de 18 a 24 e nunca passam de 31,
    o que bate com o periodo 2018-2024 do dataset. So ha mes e ano, entao a
    data nao e criada: ficam duas colunas inteiras.
    """
    partes = df["Release Date"].astype("string").str.extract(r"^(\d{2})-([A-Za-z]{3})$")
    df["ano_lancamento"] = (2000 + pd.to_numeric(partes[0])).astype("Int64")
    df["mes_lancamento"] = partes[1].map(MESES).astype("Int64")
    log.info("ano_lancamento ausente: %s", df["ano_lancamento"].isna().sum())
    log.debug("ano_lancamento distribuicao: %s", df["ano_lancamento"].value_counts().sort_index().to_dict())
    return df


def salvar(df):
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "llm.parquet"
    df.to_parquet(destino, index=False)
    log.info("salvo em: %s %s", destino, df.shape)
    return destino


def registrar(origem, destino, antes, depois, decisoes):
    limpeza.registrar(PRATA / "proveniencia.jsonl", {
        "origem": origem.name,
        "arquivo_prata": destino.name,
        "linhas_antes": antes,
        "linhas_depois": depois,
        "decisoes": decisoes,
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    })


def main():
    df, origem = carregar()
    antes = len(df)
    df = limpeza.tirar_espacos(df)
    df = renomear_colunas(df)
    df = tratar_tba(df)
    df = converter_ratio(df)
    df = converter_tipos(df)
    df = converter_data_lancamento(df)
    df = limpeza.conferir_chave(df, "Model")
    for coluna in ["Parameters", "ALScore"]:
        if df[coluna].notna().sum() > 3:
            df = limpeza.marcar_extremos(df, coluna)
            df = limpeza.marcar_zscore(df, coluna)
    destino = salvar(df)
    registrar(origem, destino, antes, len(df), [
        "espacos removidos de nomes de coluna (corrige 'Tokens ') e de texto (limpeza.tirar_espacos)",
        "Comapany renomeada para Company (erro de digitacao da fonte original)",
        "valores TBA substituidos por NaN (eram ausentes mascarados como texto)",
        "Ratio recuperada: '20:01' e '286:01:00' eram razoes lidas como hora; guardado o numero antes do ':'",
        "Parameters, Tokens, ALScore convertidas para numerico com coerce",
        "Release Date 'YY-Mon' convertida em ano_lancamento e mes_lancamento (Int64); nao e data completa",
        "chave Model: duplicatas removidas",
        "Parameters e ALScore marcados por IQR e z-score",
    ])


if __name__ == "__main__":
    config.configurar_log()
    config.criar_pastas()
    main()
