"""Consultas do painel. Todo SQL de leitura mora aqui, nunca na tela (painel.py).

O banco e aberto em modo somente leitura: o painel consome a Ouro e nao altera nada.
Valores vindos da tela entram como parametros (?), nunca concatenados no texto da consulta.
"""

from pathlib import Path

import duckdb


RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "dados" / "ouro" / "projeto.duckdb"


def _consultar(sql, parametros=None):
    con = duckdb.connect(str(BANCO), read_only=True)
    try:
        return con.execute(sql, parametros or []).df()
    finally:
        con.close()


def faixa_de_anos():
    """Primeiro e ultimo ano que tem alguma GPU ou LLM lancados."""
    return _consultar(
        """
        select min(ano) as primeiro, max(ano) as ultimo
        from ouro.vw_ano_gpu_llm
        where gpus_lancadas > 0 or llms_lancados > 0
        """
    ).iloc[0]


def serie_anual(inicio, fim):
    """Uma linha por ano: GPUs e LLMs lancados e os valores de cada lado."""
    return _consultar(
        """
        select ano, gpus_lancadas, gpus_com_gflops, gflops_mediana_gpu, gflops_maximo_gpu,
               densidade_mediana_gpu, llms_lancados, parametros_mediana_llm, parametros_maximo_llm
        from ouro.vw_ano_gpu_llm
        where ano between ? and ?
        order by ano
        """,
        [inicio, fim],
    )


def gpus_do_ano(ano, limite):
    """GPUs de um ano com GFLOPS de unidade confirmada, da mais forte para a mais fraca."""
    return _consultar(
        """
        select modelo, fabricante, interface_barramento, gflops_corrigido, unidade_gflops
        from ouro.fato_gpu
        where ano = ? and gflops_corrigido is not null
        order by gflops_corrigido desc
        limit ?
        """,
        [ano, limite],
    )


def llms_do_ano(ano, limite):
    """LLMs de um ano com numero de parametros informado, do maior para o menor."""
    return _consultar(
        """
        select modelo, empresa, parametros, tokens
        from ouro.fato_llm
        where ano = ? and parametros is not null
        order by parametros desc
        limit ?
        """,
        [ano, limite],
    )
