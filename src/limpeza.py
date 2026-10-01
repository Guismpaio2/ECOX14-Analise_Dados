"""Funcoes de limpeza que servem a qualquer fonte."""

import json

import pandas as pd


def tirar_espacos(df):
    df.columns = df.columns.str.strip()
    for c in df.select_dtypes(include="object"):
        df[c] = df[c].str.strip()
    return df


def chave_texto(serie):
    """Versao comparavel de um texto: sem acento,
    sem espaco sobrando e tudo em minuscula."""
    s = serie.str.strip().str.lower()
    s = s.str.normalize("NFKD")
    s = s.str.encode("ascii", errors="ignore")
    return s.str.decode("utf-8")


def aplicar_mapa(serie, mapa):
    """Troca variantes pelo valor canonico.
    O que nao estiver no mapa fica como esta."""
    return serie.replace(mapa)


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


def conferir_chave(df, chave):
    """Mostra quem repetiu a chave antes de apagar. Fica a primeira ocorrencia."""
    repetidas = df.duplicated(subset=chave).sum()
    print("chaves repetidas:", repetidas)
    if repetidas:
        print(df[df.duplicated(subset=chave, keep=False)])
    return df.drop_duplicates(subset=chave)


def registrar(caminho, info):
    """Acrescenta uma linha de proveniencia (jsonl) ao historico."""
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")
