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


def main():
    con = conectar()
    try:
        criar_esquemas(con)
        carregar_prata(con)
    finally:
        con.close()


if __name__ == "__main__":
    config.configurar_log()
    config.criar_pastas()
    main()
