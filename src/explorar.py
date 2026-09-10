from pathlib import Path

import pandas as pd
from data_profiling import ProfileReport

RELATORIOS = Path("relatorios")


def mais_recente(bronze: str, padrao: str) -> Path:
    arquivos = sorted(Path(bronze).glob(padrao))
    if not arquivos:
        raise FileNotFoundError(f"bronze vazia: {bronze}")
    return arquivos[-1]


def _ler_csv(caminho: Path) -> pd.DataFrame:
    # so consegui resolver esse problema de formataçao com fallback (utilzei o claude porque nao consegui de jeito nenhum manualmente)
    # O CSV do LLM contém caracteres Windows-1252 (ex: byte 0xb8 em "Common crawl · BigQuery").
    # latin-1 aceita qualquer byte de 0-255, então nunca falha como fallback.
    try:
        return pd.read_csv(caminho, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(caminho, encoding="latin-1")


def gerar(caminho: Path) -> Path:
    df = _ler_csv(caminho)
    perfil = ProfileReport(df, title=caminho.name)
    RELATORIOS.mkdir(exist_ok=True)
    saida = RELATORIOS / f"{caminho.stem}.html"
    perfil.to_file(saida)
    return saida


def main():
    fontes = [
        ("dados/bronze/gpu", "gpuDATA_*.csv"),
        ("dados/bronze/llm", "llmDATA_*.csv"),
    ]
    for bronze, padrao in fontes:
        caminho = mais_recente(bronze, padrao)
        print("perfilando:", caminho.name)
        print(gerar(caminho))


if __name__ == "__main__":
    main()
