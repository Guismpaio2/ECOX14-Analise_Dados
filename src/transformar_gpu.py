from datetime import datetime
import logging
import re

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
# Quanto o valor da fonte pode se afastar do teorico (shaders x 2 x clock) e ainda ser aceito.
# Cobre clock de boost e diferencas de arredondamento. Acima disso a linha fica sem valor.
LIMITE_FATOR_GFLOPS = 3.0

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


def _shaders(core_config):
    """Shaders (CUDA cores) a partir de core_config: '2× 128:64:16:16' -> 256, '2944:184:64:...' -> 2944."""
    if not isinstance(core_config, str):
        return float("nan")
    m = re.match(r"^\s*(?:(\d+)\s*[×x]\s*)?(\d+)\s*:", core_config)
    if not m:
        return float("nan")
    return (int(m.group(1)) if m.group(1) else 1) * int(m.group(2))


def _distancia_fator(razao):
    """Quantas vezes a razao esta longe de 1, sempre >= 1 (2 e 0,5 ficam ambos em 2)."""
    return razao.where(razao >= 1, 1 / razao)


def corrigir_unidade_gflops(df):
    """Confere processing_power_gflops contra o valor teorico em GFLOPS.

    A fonte mistura GFLOPS e TFLOPS (x1000) linha a linha, nao por epoca: o mesmo modelo
    aparece com 12,995 e com 13.270. O teorico vem de shaders x 2 x clock do core (MHz),
    que estao na propria fonte. A unidade (1 ou x1000) mais proxima do teorico vence.
    Se nenhuma fica a menos de LIMITE_FATOR_GFLOPS, a linha fica sem valor corrigido.
    Valores de FP64 (1/64 do teorico, Pascal) tambem caem em 'inconclusivo'.
    """
    shaders = df["core_config"].map(_shaders).astype("float")
    teorico = (shaders * 2 * df["core_clock_mhz"].astype("float") / 1000).where(lambda s: s > 0)
    valor = df["processing_power_gflops"].astype("float").where(lambda s: s > 0)
    df["gflops_teorico"] = teorico

    dist_gflops = _distancia_fator(valor / teorico)
    dist_tflops = _distancia_fator(valor * 1000 / teorico)
    usa_tflops = dist_tflops < dist_gflops
    dist = dist_gflops.where(~usa_tflops, dist_tflops)
    aceito = dist <= LIMITE_FATOR_GFLOPS

    df["gflops_corrigido"] = valor.where(~usa_tflops, valor * 1000).where(aceito)
    unidade = pd.Series("sem referencia", index=df.index, dtype="object")
    unidade = unidade.mask(teorico.notna() & valor.notna(), "inconclusivo")
    unidade = unidade.mask(aceito & ~usa_tflops, "GFLOPS")
    unidade = unidade.mask(aceito & usa_tflops, "TFLOPS convertido")
    df["unidade_gflops"] = unidade

    log.info("unidade_gflops: %s", unidade.value_counts().to_dict())
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
    df = corrigir_unidade_gflops(df)
    for coluna in ["tdp_watts", "gflops_corrigido"]:
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
            "processing_power_gflops misturava GFLOPS e TFLOPS (x1000) linha a linha: gflops_teorico = shaders x 2 x clock do core; gflops_corrigido fica com a unidade mais proxima do teorico (unidade_gflops registra a escolha); linhas longe de ambas (ex.: FP64 do Pascal) ou sem clock ficam sem valor",
            "tdp_watts e gflops_corrigido marcados por IQR e z-score",
        ],
    )


if __name__ == "__main__":
    config.configurar_log()
    config.criar_pastas()
    main()
