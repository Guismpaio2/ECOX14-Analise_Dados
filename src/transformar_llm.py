import json
from datetime import datetime
from pathlib import Path

import pandas as pd

BRONZE = Path("dados/bronze/llm")
PRATA = Path("dados/prata")
PADRAO = "llmDATA_*.csv"


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
    print("lido:", caminho.name, df.shape)
    print(df.columns.tolist())
    print(df.isna().sum())
    return df, caminho


def tirar_espacos(df):
    # Corrige "Tokens " (espaço no nome) e espaços em valores de texto
    df.columns = df.columns.str.strip()
    for coluna in df.select_dtypes(include="object"):
        df[coluna] = df[coluna].str.strip()
    return df


def renomear_colunas(df):
    # Corrige erro de digitação original da fonte
    return df.rename(columns={"Comapany": "Company"})


def tratar_tba(df):
    # "TBA" (To Be Announced) foi usado no lugar de ausentes em toda a tabela — não são NaN reais
    return df.replace("TBA", pd.NA)


def converter_tipos(df):
    for coluna in ["Parameters", "Tokens", "Ratio", "ALScore"]:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    return df


def conferir_chave(df, chave="Model"):
    repetidas = df[chave].duplicated().sum()
    print("chaves repetidas:", repetidas)
    if repetidas:
        print(df[df[chave].duplicated(keep=False)])
    return df.drop_duplicates(subset=chave)


def limites_iqr(serie):
    q1 = serie.quantile(0.25)
    q3 = serie.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def marcar_extremos(df, coluna):
    baixo, alto = limites_iqr(df[coluna].dropna())
    df[coluna + "_extremo"] = (df[coluna] < baixo) | (df[coluna] > alto)
    print(coluna, df[coluna + "_extremo"].sum())
    return df


def marcar_zscore(df, coluna, limite=3):
    z = (df[coluna] - df[coluna].mean()) / df[coluna].std()
    df[coluna + "_z"] = z.abs() > limite
    print(coluna, "z acima de", limite, ":", df[coluna + "_z"].sum())
    return df


def salvar(df):
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "llm.parquet"
    df.to_parquet(destino, index=False)
    print("salvo em:", destino, df.shape)
    return destino


def registrar(origem, destino, antes, depois, decisoes):
    info = {
        "origem": origem.name,
        "arquivo_prata": destino.name,
        "linhas_antes": antes,
        "linhas_depois": depois,
        "decisoes": decisoes,
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho = PRATA / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")


def main():
    df, origem = carregar()
    antes = len(df)
    df = tirar_espacos(df)
    df = renomear_colunas(df)
    df = tratar_tba(df)
    df = converter_tipos(df)
    df = conferir_chave(df)
    for coluna in ["Parameters", "ALScore"]:
        if coluna in df.columns and df[coluna].notna().sum() > 3:
            df = marcar_extremos(df, coluna)
            df = marcar_zscore(df, coluna)
    destino = salvar(df)
    registrar(origem, destino, antes, len(df), [
        "espacos removidos de nomes de coluna (corrige 'Tokens ') e de texto",
        "Comapany renomeada para Company (erro de digitacao da fonte original)",
        "valores TBA substituidos por NaN (eram ausentes mascarados como texto)",
        "Parameters, Tokens, Ratio, ALScore convertidas para numerico com coerce",
        "chave Model: duplicatas removidas",
        "Parameters e ALScore marcados por IQR e z-score",
    ])


if __name__ == "__main__":
    main()
