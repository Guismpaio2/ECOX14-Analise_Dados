"""Painel: GPUs x LLMs, ano a ano. So mostra; as consultas estao em consultas.py.

Rodar, a partir da raiz do projeto (com o pipeline ja executado):
    streamlit run dashboard/painel.py
"""

import altair as alt
import streamlit as st

import consultas


st.set_page_config(page_title="GPUs x LLMs", layout="wide")
st.title("Como as GPUs evoluem em comparacao com as IAs?")

primeiro, ultimo = consultas.faixa_de_anos()[["primeiro", "ultimo"]].astype(int)
inicio, fim = st.sidebar.slider(
    "Periodo", min_value=int(primeiro), max_value=int(ultimo), value=(2016, 2025)
)
anos = list(range(fim, inicio - 1, -1))
# 2024 e o ultimo ano com LLM na fonte; por padrao o detalhe mostra os dois lados.
ano = st.sidebar.selectbox("Ano para detalhar", anos, index=anos.index(2024) if 2024 in anos else 0)
limite = st.sidebar.slider("Modelos por lista", 5, 20, 10)

serie = consultas.serie_anual(inicio, fim)

colunas = st.columns(3)
colunas[0].metric("GPUs no periodo", int(serie["gpus_lancadas"].sum()))
colunas[1].metric("GPUs com GFLOPS confirmado", int(serie["gpus_com_gflops"].sum()))
colunas[2].metric("LLMs no periodo", int(serie["llms_lancados"].sum()))

esquerda, direita = st.columns(2)
with esquerda:
    st.subheader("Poder de processamento: GPU mais forte do ano")
    grafico = (
        alt.Chart(serie.dropna(subset=["gflops_maximo_gpu"]))
        .mark_line(point=True, color="#1f77b4")
        .encode(
            x=alt.X("ano:O", title="Ano de lancamento"),
            y=alt.Y("gflops_maximo_gpu:Q", title="GFLOPS (escala log)",
                    scale=alt.Scale(type="log")),
            tooltip=["ano", "gflops_maximo_gpu", "gpus_com_gflops"],
        )
    )
    st.altair_chart(grafico, width=True)
    st.caption("So entram GPUs com unidade de GFLOPS confirmada pelo teorico (shaders x 2 x clock).")

with direita:
    st.subheader("Tamanho do maior LLM do ano")
    grafico = (
        alt.Chart(serie.dropna(subset=["parametros_maximo_llm"]))
        .mark_line(point=True, color="#d62728")
        .encode(
            x=alt.X("ano:O", title="Ano de lancamento"),
            y=alt.Y("parametros_maximo_llm:Q", title="Parametros, em bilhoes (escala log)",
                    scale=alt.Scale(type="log")),
            tooltip=["ano", "parametros_maximo_llm", "llms_lancados"],
        )
    )
    st.altair_chart(grafico, width=True)
    st.caption("Parametros na escala da fonte: bilhoes. A serie cobre so 2018 a 2024.")

st.subheader("Tabela anual")
tabela = serie.rename(columns={
    "ano": "Ano",
    "gpus_lancadas": "GPUs lancadas",
    "gpus_com_gflops": "GPUs com GFLOPS",
    "gflops_mediana_gpu": "GFLOPS mediana",
    "gflops_maximo_gpu": "GFLOPS maximo",
    "densidade_mediana_gpu": "Densidade mediana (mi transistores/mm2)",
    "llms_lancados": "LLMs lancados",
    "parametros_mediana_llm": "Parametros mediana (bi)",
    "parametros_maximo_llm": "Parametros maximo (bi)",
}).round(1)
st.dataframe(tabela, hide_index=True, width=True)

st.subheader(f"Em {ano}")
gpus, llms = st.columns(2)
with gpus:
    st.markdown("**GPUs mais fortes (GFLOPS)**")
    st.dataframe(consultas.gpus_do_ano(ano, limite), hide_index=True, width=True)
with llms:
    st.markdown("**LLMs com mais parametros (bilhoes)**")
    st.dataframe(consultas.llms_do_ano(ano, limite), hide_index=True, width=True)

st.caption(
    "Fontes: GPU Specs Database (Nvidia e AMD, 1995-2026) e LLMs Data (2018-2024), ambas do Kaggle. "
    "Camada Ouro em dados/ouro/projeto.duckdb, construida com dbt. Dados lidos em modo somente leitura."
)
