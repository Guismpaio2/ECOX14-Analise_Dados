from datetime import datetime
import logging

import pandas as pd

import config
import limpeza

BRONZE = config.FONTES["gpu"]["bronze_dir"]
PRATA = config.PRATA
PADRAO = config.FONTES["gpu"]["padrao"]

ANO_MINIMO = 1980
ANO_MAXIMO = 2026
ANO_ESCALA = 2015
LIMITE_BILHOES = 100

log = logging.getLogger(__name__)


def carregar():
    arquivos = sorted(BRONZE.glob(PADRAO))
    if not arquivos:
        raise FileNotFoundError(f"nada em {BRONZE}")
    caminho = arquivos[-1]
    df = pd.read_csv(caminho)
    log.info("lido: %s %s", caminho.name, df.shape)
    log.debug("colunas: %s", df.columns.tolist())
    log.debug("ausentes: %s", df.isna().sum().to_dict())
    return df, caminho


def converter_tipos(df):
    for coluna in [
        "transistors_million",
        "die_size_mm2",
        "core_clock_mhz",
        "memory_clock_mhz",
        "processing_power_gflops",
        "tdp_watts",
    ]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    df["manufacturer"] = df["manufacturer"].astype("category")
    return df


def tratar_datas(df):
    """Separa a data completa do ano e recupera ano gravado como nanossegundo."""
    texto = df["launch_date"].astype("string")
    ano_em_ns = pd.to_numeric(
        texto.str.extract(r"^1970-01-01 00:00:00\.(\d{9})$")[0], errors="coerce"
    )
    data = pd.to_datetime(texto.where(ano_em_ns.isna()), errors="coerce")

    ano = data.dt.year.astype("Float64")
    ano = ano.fillna(ano_em_ns)
    fora = ano.notna() & ~ano.between(ANO_MINIMO, ANO_MAXIMO)
    log.info("anos fora de %s-%s: %s", ANO_MINIMO, ANO_MAXIMO, fora.sum())
    ano = ano.mask(fora)
    log.info("anos recuperados de nanossegundos: %s", ano_em_ns.notna().sum())

    df["launch_date"] = data.dt.date
    df["ano_lancamento"] = ano.astype("Int64")
    log.info("ano_lancamento ausente: %s", df["ano_lancamento"].isna().sum())
    return df


def anular_area_copiada(df):
    """Anula area copiada de transistores em linhas de GPU pos-2015."""
    copiada = (df["die_size_mm2"] == df["transistors_million"]) & (
        df["ano_lancamento"] >= ANO_ESCALA
    )
    df.loc[copiada, "die_size_mm2"] = pd.NA
    log.info(
        "die_size_mm2 copiada de transistors_million (virou ausente): %s",
        copiada.sum(),
    )
    return df


def corrigir_escala_transistores(df):
    """Corrige de bilhoes para milhoes em chips lancados a partir de 2015."""
    ajustar = (df["ano_lancamento"] >= ANO_ESCALA) & (
        df["transistors_million"] < LIMITE_BILHOES
    )
    df.loc[ajustar, "transistors_million"] *= 1000
    log.info("transistors_million corrigidos de bilhoes para milhoes: %s", ajustar.sum())
    return df


def padronizar_interface(df):
    """Unifica grafias de bus_interface para comparacao."""
    antes = df["bus_interface"].nunique()
    trocado = df["bus_interface"].astype("string").str.replace("×", "x", regex=False)
    df["bus_interface_chave"] = limpeza.chave_texto(trocado)
    log.info("bus_interface distintos: %s -> %s", antes, df["bus_interface_chave"].nunique())
    return df


def calcular_densidade_transistores(df):
    """Transistores (milhoes) por mm2 de die."""
    area = df["die_size_mm2"].where(df["die_size_mm2"] > 0)
    df["densidade_transistores"] = df["transistors_million"] / area
    log.info(
        "densidade_transistores calculada: %s",
        df["densidade_transistores"].notna().sum(),
    )
    log.debug(
        "densidade_transistores describe: %s",
        df["densidade_transistores"].describe().to_dict(),
    )
    return df


def salvar(df):
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "gpu.parquet"
    df.to_parquet(destino, index=False)
    log.info("salvo em: %s %s", destino, df.shape)
    return destino


def registrar(origem, destino, antes, depois, decisoes):
    limpeza.registrar(
        PRATA / "proveniencia.jsonl",
        {
            "origem": origem.name,
            "arquivo_prata": destino.name,
            "linhas_antes": antes,
            "linhas_depois": depois,
            "decisoes": decisoes,
            "transformado_em": datetime.now().isoformat(timespec="seconds"),
        },
    )


def main():
    df, origem = carregar()
    antes = len(df)
    df = limpeza.tirar_espacos(df)
    df = converter_tipos(df)
    df = tratar_datas(df)
    df = anular_area_copiada(df)
    df = corrigir_escala_transistores(df)
    df = padronizar_interface(df)
    df = limpeza.conferir_chave(df, ["model", "bus_interface"])
    df = calcular_densidade_transistores(df)
    for coluna in ["tdp_watts", "processing_power_gflops"]:
        df = limpeza.marcar_extremos(df, coluna)
        df = limpeza.marcar_zscore(df, coluna)
    destino = salvar(df)
    registrar(
        origem,
        destino,
        antes,
        len(df),
        [
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
        ],
    )


if __name__ == "__main__":
    config.configurar_log()
    config.criar_pastas()
    main()
