import json
from datetime import datetime
from pathlib import Path

import pandas as pd

BRONZE = Path("dados/bronze/gpu")
PRATA = Path("dados/prata")
PADRAO = "gpuDATA_*.csv"


def carregar():
    arquivos = sorted(BRONZE.glob(PADRAO))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE}")
    caminho = arquivos[-1]
    df = pd.read_csv(caminho)
    print("lido:", caminho.name, df.shape)
    print(df.columns.tolist())
    print(df.isna().sum())
    return df, caminho


def tirar_espacos(df):
    df.columns = df.columns.str.strip()
    for coluna in df.select_dtypes(include="object"):
        df[coluna] = df[coluna].str.strip()
    return df


def converter_tipos(df):
    # launch_date vem com timestamp completo (ex: "1995-09-30 00:00:00.000000000") — só a data importa
    df["launch_date"] = pd.to_datetime(df["launch_date"], errors="coerce").dt.date
    for coluna in ["transistors_million", "die_size_mm2", "core_clock_mhz",
                   "memory_clock_mhz", "processing_power_gflops", "tdp_watts"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    return df


def conferir_chave(df):
    # Chave composta: o mesmo modelo pode ter PCI e AGP como linhas separadas (dados corretos)
    chave = ["model", "bus_interface"]
    repetidas = df.duplicated(subset=chave).sum()
    print("chaves repetidas:", repetidas)
    if repetidas:
        print(df[df.duplicated(subset=chave, keep=False)])
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
    destino = PRATA / "gpu.parquet"
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
    df = converter_tipos(df)
    df = conferir_chave(df)
    for coluna in ["tdp_watts", "processing_power_gflops"]:
        df = marcar_extremos(df, coluna)
        df = marcar_zscore(df, coluna)
    destino = salvar(df)
    registrar(origem, destino, antes, len(df), [
        "espacos removidos de nomes de coluna e de texto",
        "launch_date convertida para date (nanosegundos descartados)",
        "colunas numericas convertidas com errors=coerce (invalidos viram NaN)",
        "chave composta model+bus_interface: duplicatas identicas removidas",
        "tdp_watts e processing_power_gflops marcados por IQR e z-score",
    ])


if __name__ == "__main__":
    main()
