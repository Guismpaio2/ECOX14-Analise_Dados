from datetime import datetime
from pathlib import Path

import pandas as pd

import limpeza

BRONZE = Path("dados/bronze/gpu")
PRATA = Path("dados/prata")
PADRAO = "gpuDATA_*.csv"

ANO_MINIMO = 1980
ANO_MAXIMO = 2026
ANO_ESCALA = 2015
LIMITE_BILHOES = 100


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


def converter_tipos(df):
    for coluna in ["transistors_million", "die_size_mm2", "core_clock_mhz",
                   "memory_clock_mhz", "processing_power_gflops", "tdp_watts"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    df["manufacturer"] = df["manufacturer"].astype("category")
    return df


def tratar_datas(df):
    """Separa a data completa do ano, e recupera o ano gravado como nanossegundo.

    Em 11 linhas a fonte gravou o ANO como nanossegundos desde 1970
    (ex: '1970-01-01 00:00:00.000001986' significa 1986). Nao e uma data
    de verdade, entao launch_date fica ausente e o ano vai para ano_lancamento.
    """
    texto = df["launch_date"].astype("string")
    ano_em_ns = pd.to_numeric(
        texto.str.extract(r"^1970-01-01 00:00:00\.(\d{9})$")[0], errors="coerce")
    data = pd.to_datetime(texto.where(ano_em_ns.isna()), errors="coerce")

    ano = data.dt.year.astype("Float64")
    ano = ano.fillna(ano_em_ns)
    fora = ano.notna() & ~ano.between(ANO_MINIMO, ANO_MAXIMO)
    print("anos fora de", ANO_MINIMO, "-", ANO_MAXIMO, ":", fora.sum())
    ano = ano.mask(fora)
    print("anos recuperados de nanossegundos:", ano_em_ns.notna().sum())

    df["launch_date"] = data.dt.date
    df["ano_lancamento"] = ano.astype("Int64")
    print("ano_lancamento ausente:", df["ano_lancamento"].isna().sum())
    return df


def anular_area_copiada(df):
    """Nas linhas AMD Instinct a fonte repetiu o numero de transistores (em
    bilhoes) na coluna die_size_mm2 (ex: 58,0 e 58,0 na MI250). Area igual a
    transistores, num chip pos-2015, e copia: a area real e desconhecida.
    Roda ANTES de corrigir a escala dos transistores."""
    copiada = (df["die_size_mm2"] == df["transistors_million"]) & (df["ano_lancamento"] >= ANO_ESCALA)
    df.loc[copiada, "die_size_mm2"] = pd.NA
    print("die_size_mm2 copiada de transistors_million (virou ausente):", copiada.sum())
    return df


def corrigir_escala_transistores(df):
    """A partir de 2015 a fonte passa a gravar transistors_million em BILHOES.

    Ex: 5,47 em vez de 5470 (media por ano: 1020 em 2014, 5,47 em 2015).
    Regra: lancamento >= 2015 e valor < 100 (nenhuma GPU dessas gera tem menos
    de 100 milhoes de transistores) vira valor * 1000.
    """
    ajustar = (df["ano_lancamento"] >= ANO_ESCALA) & (df["transistors_million"] < LIMITE_BILHOES)
    df.loc[ajustar, "transistors_million"] *= 1000
    print("transistors_million corrigidos de bilhoes para milhoes:", ajustar.sum())
    return df


def padronizar_interface(df):
    """bus_interface traz 'x' e o sinal '×' misturados (PCIe 3.0 x16 / ×16).

    chave_texto serve para comparar e agrupar; o rotulo original fica na tabela.
    O sinal '×' nao tem decomposicao ASCII, por isso e trocado antes.
    """
    antes = df["bus_interface"].nunique()
    trocado = df["bus_interface"].str.replace("×", "x", regex=False)
    df["bus_interface_chave"] = limpeza.chave_texto(trocado)
    print("bus_interface distintos:", antes, "->", df["bus_interface_chave"].nunique())
    return df


def calcular_densidade_transistores(df):
    """Transistores (milhoes) por mm2 de die.

    Serve a pergunta norteadora: mede o quanto cada geracao de GPU
    empacota por area, comparavel entre eras e fabricantes.
    Ausente quando falta transistores, falta area ou a area e zero.

    Nao usei GFLOPS por watt: processing_power_gflops muda de escala por volta
    de 2016 (RTX 3090 Ti = 33,5, claramente TFLOPS), entao a razao seria enganosa.
    """
    area = df["die_size_mm2"].where(df["die_size_mm2"] > 0)
    df["densidade_transistores"] = df["transistors_million"] / area
    print("densidade_transistores calculada:", df["densidade_transistores"].notna().sum())
    print(df["densidade_transistores"].describe())
    return df


def salvar(df):
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "gpu.parquet"
    df.to_parquet(destino, index=False)
    print("salvo em:", destino, df.shape)
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
    df = converter_tipos(df)
    df = tratar_datas(df)
    df = anular_area_copiada(df)
    df = corrigir_escala_transistores(df)
    df = padronizar_interface(df)
    # Chave composta: o mesmo modelo pode ter PCI e AGP como linhas separadas (dados corretos)
    df = limpeza.conferir_chave(df, ["model", "bus_interface"])
    df = calcular_densidade_transistores(df)
    for coluna in ["tdp_watts", "processing_power_gflops"]:
        df = limpeza.marcar_extremos(df, coluna)
        df = limpeza.marcar_zscore(df, coluna)
    destino = salvar(df)
    registrar(origem, destino, antes, len(df), [
        "espacos removidos de nomes de coluna e de texto (limpeza.tirar_espacos)",
        "colunas numericas convertidas com errors=coerce (invalidos viram NaN)",
        "manufacturer tipada como category",
        "launch_date convertida para date; 11 anos gravados como nanossegundos recuperados em ano_lancamento (Int64)",
        "die_size_mm2 igual a transistors_million (copia da fonte, linhas AMD Instinct) anulada",
        "transistors_million: de 2015 em diante a fonte grava em bilhoes; valores < 100 multiplicados por 1000",
        "bus_interface_chave criada com chave_texto (x e × unificados); rotulo original mantido",
        "chave model+bus_interface: repeticoes removidas, fica a primeira ocorrencia",
        "atributo derivado densidade_transistores = transistors_million / die_size_mm2",
        "gflops_por_watt descartado: processing_power_gflops muda de escala (GFLOPS para TFLOPS) a partir de ~2016",
        "tdp_watts e processing_power_gflops marcados por IQR e z-score",
    ])


if __name__ == "__main__":
    main()
