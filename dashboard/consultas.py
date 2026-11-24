"""Consultas do painel. Todo SQL de leitura mora aqui, nunca na tela (painel.py).

O banco e aberto em modo somente leitura: o painel consome a Ouro e nao altera nada.
Valores vindos da tela entram como parametros (?), nunca concatenados no texto da consulta.
Quando o filtro de fabricante e "Todos", o parametro chega como None e a condicao e ignorada.
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
    """Primeiro e ultimo ano com alguma GPU ou LLM."""
    return _consultar(
        """
        select min(ano) as primeiro, max(ano) as ultimo
        from ouro.vw_ano_gpu_llm
        where gpus_lancadas > 0 or llms_lancados > 0
        """
    ).iloc[0]


def fabricantes():
    return _consultar("select distinct fabricante from ouro.fato_gpu order by fabricante")["fabricante"].tolist()


def visao_geral(inicio, fim, fabricante):
    """Contagens do periodo e das GPUs sem ano de lancamento (que ficam fora de qualquer periodo)."""
    return _consultar(
        """
        select
            count(*) filter (where ano between ? and ?) as gpus_no_periodo,
            count(*) filter (where ano is null) as gpus_sem_ano,
            count(*) filter (where ano between ? and ? and gflops_corrigido is not null) as gpus_com_gflops,
            count(*) filter (where ano between ? and ? and tdp_watts is not null) as gpus_com_tdp,
            count(*) filter (where ano between ? and ? and transistores_milhoes is not null) as gpus_com_transistores,
            max(gflops_corrigido) filter (where ano between ? and ?) as gflops_maximo
        from ouro.fato_gpu
        where (? is null or fabricante = ?)
        """,
        [inicio, fim] * 5 + [fabricante, fabricante],
    ).iloc[0]


def visao_llm(inicio, fim):
    return _consultar(
        """
        select
            count(*) as llms,
            count(parametros) as llms_com_parametros,
            count(tokens) as llms_com_tokens,
            max(parametros) as parametros_maximo
        from ouro.fato_llm
        where ano between ? and ?
        """,
        [inicio, fim],
    ).iloc[0]


def serie_gpu(inicio, fim, fabricante):
    """Por ano: quantas GPUs e os valores medianos e maximos de cada indicador."""
    return _consultar(
        """
        select
            ano,
            count(*) as gpus,
            count(gflops_corrigido) as gpus_com_gflops,
            median(gflops_corrigido) as gflops_mediana,
            max(gflops_corrigido) as gflops_maximo,
            count(tdp_watts) as gpus_com_tdp,
            median(tdp_watts) as tdp_mediana,
            count(transistores_milhoes) as gpus_com_transistores,
            median(transistores_milhoes) as transistores_mediana,
            median(densidade_transistores) as densidade_mediana
        from ouro.fato_gpu
        where ano between ? and ?
          and (? is null or fabricante = ?)
        group by ano
        order by ano
        """,
        [inicio, fim, fabricante, fabricante],
    )


def serie_llm(inicio, fim):
    """Por ano: quantos LLMs e os valores medianos e maximos de cada indicador."""
    return _consultar(
        """
        select
            ano,
            count(*) as llms,
            count(parametros) as llms_com_parametros,
            median(parametros) as parametros_mediana,
            max(parametros) as parametros_maximo,
            count(tokens) as llms_com_tokens,
            median(tokens) as tokens_mediana
        from ouro.fato_llm
        where ano between ? and ?
        group by ano
        order by ano
        """,
        [inicio, fim],
    )


def cobertura_gpu(inicio, fim, fabricante):
    """Share de GPUs com cada dado informado, por ano (0 a 1). Mostra onde a fonte nao traz o dado."""
    return _consultar(
        """
        select
            ano,
            count(*) as gpus,
            avg((ano is not null)::int) as ano_informado,
            avg((gflops_corrigido is not null)::int) as gflops_confirmado,
            avg((tdp_watts is not null)::int) as tdp,
            avg((transistores_milhoes is not null)::int) as transistores,
            avg((area_die_mm2 is not null)::int) as area_do_die
        from ouro.fato_gpu
        where ano between ? and ?
          and (? is null or fabricante = ?)
        group by ano
        order by ano
        """,
        [inicio, fim, fabricante, fabricante],
    )


def cobertura_llm(inicio, fim):
    return _consultar(
        """
        select
            ano,
            count(*) as llms,
            avg((parametros is not null)::int) as parametros,
            avg((tokens is not null)::int) as tokens,
            avg((alscore is not null)::int) as alscore
        from ouro.fato_llm
        where ano between ? and ?
        group by ano
        order by ano
        """,
        [inicio, fim],
    )


def motivos_gflops(inicio, fim, fabricante):
    """Por que cada GPU ficou sem GFLOPS confirmado (ou com a unidade convertida)."""
    return _consultar(
        """
        select fabricante, unidade_gflops, count(*) as gpus
        from ouro.fato_gpu
        where ano between ? and ?
          and (? is null or fabricante = ?)
        group by fabricante, unidade_gflops
        order by fabricante, gpus desc
        """,
        [inicio, fim, fabricante, fabricante],
    )


def gpus_do_ano(ano, limite, fabricante):
    return _consultar(
        """
        select modelo, fabricante, interface_barramento, gflops_corrigido, unidade_gflops,
               tdp_watts, transistores_milhoes
        from ouro.fato_gpu
        where ano = ?
          and (? is null or fabricante = ?)
        order by gflops_corrigido desc nulls last, transistores_milhoes desc nulls last
        limit ?
        """,
        [ano, fabricante, fabricante, limite],
    )


def llms_do_ano(ano, limite):
    return _consultar(
        """
        select modelo, empresa, parametros, tokens, alscore
        from ouro.fato_llm
        where ano = ?
        order by parametros desc nulls last
        limit ?
        """,
        [ano, limite],
    )


def empresas_llm(inicio, fim, limite):
    return _consultar(
        """
        select empresa, count(*) as llms
        from ouro.fato_llm
        where ano between ? and ?
        group by empresa
        order by llms desc
        limit ?
        """,
        [inicio, fim, limite],
    )


def maior_llm(inicio, fim):
    """O LLM com mais parametros no periodo, com nome e ano."""
    return _consultar(
        """
        select modelo, empresa, ano, parametros
        from ouro.fato_llm
        where ano between ? and ? and parametros is not null
        order by parametros desc
        limit 1
        """,
        [inicio, fim],
    ).iloc[0]


def maior_gpu(inicio, fim, fabricante):
    """A GPU com mais GFLOPS confirmados no periodo."""
    return _consultar(
        """
        select modelo, fabricante, ano, gflops_corrigido
        from ouro.fato_gpu
        where ano between ? and ? and gflops_corrigido is not null
          and (? is null or fabricante = ?)
        order by gflops_corrigido desc
        limit 1
        """,
        [inicio, fim, fabricante, fabricante],
    ).iloc[0]
