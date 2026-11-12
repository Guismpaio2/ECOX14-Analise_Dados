"""Carga: abre o banco DuckDB e monta as camadas Prata e Ouro dentro dele."""

import logging

import duckdb

import config


log = logging.getLogger(__name__)

BANCO = config.OURO / "projeto.duckdb"
PRATA_GPU = config.PRATA / "gpu.parquet"
PRATA_LLM = config.PRATA / "llm.parquet"


def conectar():
    """Abre (ou cria) o arquivo do banco. Nao ha servidor: o banco e esse arquivo."""
    config.OURO.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(BANCO))
    log.info("banco aberto: %s", BANCO)
    return con


def criar_esquemas(con):
    con.execute("CREATE SCHEMA IF NOT EXISTS prata")
    con.execute("CREATE SCHEMA IF NOT EXISTS ouro")


def carregar_prata(con):
    """Le os Parquet direto para tabelas. Nada e importado: os tipos ja estao no arquivo."""
    for tabela, arquivo in (("gpu", PRATA_GPU), ("llm", PRATA_LLM)):
        caminho = arquivo.as_posix()
        con.execute(f"""
            CREATE OR REPLACE TABLE prata.{tabela} AS
            SELECT * FROM read_parquet('{caminho}')
        """)
        log.info("prata.%s carregada de %s", tabela, arquivo.name)


def construir_ouro(con):
    """Cria as tabelas da Ouro. O grao de cada uma esta descrito no README."""
    # dim_ano: uma linha por ano, do primeiro ao ultimo ano das duas fontes, sem buracos.
    con.execute("""
        CREATE OR REPLACE TABLE ouro.dim_ano AS
        WITH anos AS (
            SELECT ano_lancamento AS ano FROM prata.gpu
            UNION ALL
            SELECT ano_lancamento AS ano FROM prata.llm
        ),
        limites AS (
            SELECT min(ano) AS primeiro, max(ano) AS ultimo FROM anos
        ),
        calendario AS (
            SELECT CAST(unnest(range(primeiro, ultimo + 1)) AS INTEGER) AS ano
            FROM limites
        )
        SELECT ano, ano // 10 * 10 AS decada FROM calendario
    """)

    # fato_gpu: uma linha por GPU em cada interface de barramento.
    # processing_power_gflops fica de fora: a escala muda entre eras (ver README).
    con.execute("""
        CREATE OR REPLACE TABLE ouro.fato_gpu AS
        SELECT
            model AS modelo,
            bus_interface AS interface_barramento,
            manufacturer AS fabricante,
            ano_lancamento AS ano,
            transistors_million AS transistores_milhoes,
            die_size_mm2 AS area_die_mm2,
            densidade_transistores,
            tdp_watts,
            tdp_watts_extremo,
            tdp_watts_z
        FROM prata.gpu
    """)

    # fato_llm: uma linha por modelo de LLM.
    con.execute("""
        CREATE OR REPLACE TABLE ouro.fato_llm AS
        SELECT
            "Model" AS modelo,
            "Company" AS empresa,
            ano_lancamento AS ano,
            mes_lancamento AS mes,
            "Parameters" AS parametros,
            "Tokens" AS tokens,
            "Ratio" AS razao_tokens_parametros,
            "ALScore" AS alscore,
            Parameters_extremo AS parametros_extremo,
            Parameters_z AS parametros_z,
            ALScore_extremo AS alscore_extremo,
            ALScore_z AS alscore_z
        FROM prata.llm
    """)

    # vw_ano_gpu_llm: resposta a pergunta norteadora, uma linha por ano.
    # Cada fato e agregada antes do join: juntar as duas direto multiplicaria as linhas
    # e distorceria as medianas.
    con.execute("""
        CREATE OR REPLACE VIEW ouro.vw_ano_gpu_llm AS
        WITH gpu AS (
            SELECT ano,
                   count(*) AS gpus_lancadas,
                   median(densidade_transistores) AS densidade_mediana_gpu
            FROM ouro.fato_gpu
            WHERE ano IS NOT NULL
            GROUP BY ano
        ),
        llm AS (
            SELECT ano,
                   count(*) AS llms_lancados,
                   median(parametros) AS parametros_mediana_llm
            FROM ouro.fato_llm
            WHERE ano IS NOT NULL
            GROUP BY ano
        )
        SELECT
            d.ano,
            d.decada,
            coalesce(g.gpus_lancadas, 0) AS gpus_lancadas,
            g.densidade_mediana_gpu,
            coalesce(l.llms_lancados, 0) AS llms_lancados,
            l.parametros_mediana_llm
        FROM ouro.dim_ano d
        LEFT JOIN gpu g ON g.ano = d.ano
        LEFT JOIN llm l ON l.ano = d.ano
        ORDER BY d.ano
    """)
    log.info("ouro construida: dim_ano, fato_gpu, fato_llm, vw_ano_gpu_llm")


def main():
    con = conectar()
    try:
        criar_esquemas(con)
        carregar_prata(con)
        construir_ouro(con)
    finally:
        con.close()


if __name__ == "__main__":
    config.configurar_log()
    config.criar_pastas()
    main()
