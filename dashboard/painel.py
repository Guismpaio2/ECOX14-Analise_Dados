"""Painel: GPUs e modelos de linguagem (LLMs), ano a ano.

So monta a tela. Todo o SQL esta em consultas.py.

Rodar, a partir da raiz do projeto, com o pipeline ja executado:
    streamlit run dashboard/painel.py
"""

import altair as alt
import pandas as pd
import streamlit as st

import consultas


COR_GPU = "#B5532A"       # laranja queimado
COR_LLM = "#1F6F78"       # verde-petroleo
COR_SEM_DADO = "#E7E2D8"  # bege claro: celula sem dado
COR_TEXTO = "#4A4A4A"

st.set_page_config(page_title="GPUs e modelos de linguagem", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 2.2rem; max-width: 1280px; }
      h1, h2, h3 { font-family: Georgia, "Times New Roman", serif; font-weight: 600; letter-spacing: -0.2px; }
      .lede { font-size: 1.05rem; color: #4A4A4A; line-height: 1.55; max-width: 62rem; }
      .nota { font-size: 0.9rem; color: #6B6B6B; line-height: 1.5; }
      .faltando { border-left: 4px solid #B5532A; padding: 0.35rem 0 0.35rem 0.9rem; margin: 0.6rem 0; }
      [data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
    </style>
    """,
    unsafe_allow_html=True,
)


def inteiro(x):
    """Numero com separador de milhar no padrao brasileiro."""
    if x is None or pd.isna(x):
        return "sem dado"
    return f"{int(round(x)):,}".replace(",", ".")


def percentual(x):
    if x is None or pd.isna(x):
        return "sem dado"
    return f"{x * 100:.0f}%"


def aviso_sem_dado(texto):
    st.markdown(f'<div class="faltando"><span class="nota">{texto}</span></div>', unsafe_allow_html=True)


@st.cache_data(ttl=300, show_spinner=False)
def periodo_da_fonte():
    faixa = consultas.faixa_de_anos()
    return int(faixa["primeiro"]), int(faixa["ultimo"])


primeiro, ultimo = periodo_da_fonte()

# ----------------------------------------------------------------- cabecalho
st.title("GPUs e modelos de linguagem, ano a ano")
st.markdown(
    '<p class="lede">Como as placas de vídeo evoluíram enquanto os modelos de linguagem se multiplicavam? '
    "Este painel cruza duas fontes do Kaggle pelo ano de lançamento. Onde a fonte não traz um dado, "
    "o painel mostra <b>sem dado</b> em vez de preencher com um número.</p>",
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------- filtros
with st.sidebar:
    st.header("Filtros")
    inicio, fim = st.slider("Período de lançamento", primeiro, ultimo, (2016, 2025))
    fabricante_escolhido = st.radio(
        "Fabricante de GPU", ["Todos", "Nvidia", "AMD"], horizontal=True,
        help="Vale só para as GPUs. A fonte de LLMs não traz fabricante de chip.",
    )
    fabricante = None if fabricante_escolhido == "Todos" else fabricante_escolhido
    escala_log = st.toggle("Escala logarítmica", value=True,
                           help="Use quando um valor é centenas de vezes maior que outro.")
    anos_periodo = list(range(fim, inicio - 1, -1))
    ano = st.selectbox("Ano para detalhar", anos_periodo,
                       index=anos_periodo.index(2024) if 2024 in anos_periodo else 0)
    limite = st.slider("Itens por lista", 5, 25, 10)
    st.caption("Fontes: GPU Specs Database (Nvidia e AMD, 1995–2026) e LLMs Data (2018–2024), ambas do Kaggle.")

# ----------------------------------------------------------------- dados
visao = consultas.visao_geral(inicio, fim, fabricante)
visao_llm = consultas.visao_llm(inicio, fim)
serie_g = consultas.serie_gpu(inicio, fim, fabricante)
serie_l = consultas.serie_llm(inicio, fim)
cob_g = consultas.cobertura_gpu(inicio, fim, fabricante)
cob_l = consultas.cobertura_llm(inicio, fim)
motivos = consultas.motivos_gflops(inicio, fim, fabricante)
top_empresas = consultas.empresas_llm(inicio, fim, 10)
maior_gpu = consultas.maior_gpu(inicio, fim, fabricante)
maior_llm = consultas.maior_llm(inicio, fim)

# ----------------------------------------------------------------- KPIs
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric(
    "GPUs no período", inteiro(visao["gpus_no_periodo"]),
    help=f"Lançadas entre {inicio} e {fim}. Ficam fora do período {inteiro(visao['gpus_sem_ano'])} "
         "GPUs que a fonte não traz com ano de lançamento.",
    border=True,
)
pct_gflops = visao["gpus_com_gflops"] / visao["gpus_no_periodo"] if visao["gpus_no_periodo"] else float("nan")
k2.metric(
    "GFLOPS confirmado", percentual(pct_gflops),
    help=f"{inteiro(visao['gpus_com_gflops'])} de {inteiro(visao['gpus_no_periodo'])} GPUs. "
         "Sem clock ou sem shaders na fonte, a unidade não pode ser confirmada.",
    border=True,
)
k3.metric(
    "Maior GFLOPS",
    inteiro(maior_gpu["gflops_corrigido"]) if pd.notna(maior_gpu["gflops_corrigido"]) else "sem dado",
    help=(f"{maior_gpu['modelo']} ({maior_gpu['fabricante']}, {int(maior_gpu['ano'])})"
          if pd.notna(maior_gpu["ano"]) else "Nenhuma GPU com GFLOPS confirmado no recorte."),
    border=True,
)
k4.metric(
    "LLMs no período", inteiro(visao_llm["llms"]),
    help=f"{inteiro(visao_llm['llms'] - visao_llm['llms_com_parametros'])} sem número de parâmetros na fonte.",
    border=True,
)
k5.metric(
    "Maior LLM",
    f"{inteiro(maior_llm['parametros'])} bi" if pd.notna(maior_llm["parametros"]) else "sem dado",
    help=(f"{maior_llm['modelo']} ({maior_llm['empresa']}, {int(maior_llm['ano'])}). "
          "Número da fonte, não verificado.") if pd.notna(maior_llm["ano"]) else None,
    border=True,
)

aba_evolucao, aba_falta, aba_ano, aba_tabelas = st.tabs(
    ["Evolução", "Onde faltam dados", "Ano a ano", "Tabelas e download"]
)


# ----------------------------------------------------------------- graficos
def escala(tipo_log):
    return alt.Scale(type="log") if tipo_log else alt.Scale(zero=True)


def serie_com_amostra(df, coluna, n_coluna, cor, titulo, eixo):
    """Linha por ano. Ponto cheio com 5 ou mais amostras; vazado com menos de 5."""
    base = df.dropna(subset=[coluna]).copy()
    if base.empty:
        return None
    linha = alt.Chart(base).mark_line(color=cor, strokeWidth=2.2).encode(
        x=alt.X("ano:O", title="Ano de lançamento", axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{coluna}:Q", title=eixo, scale=escala(escala_log)),
    )
    campos = [alt.Tooltip("ano:O", title="Ano"),
              alt.Tooltip(f"{coluna}:Q", title=eixo, format=",.1f"),
              alt.Tooltip(f"{n_coluna}:Q", title="Amostras")]
    cheios = alt.Chart(base[base[n_coluna] >= 5]).mark_point(color=cor, filled=True, size=70).encode(
        x="ano:O", y=f"{coluna}:Q", tooltip=campos)
    vazios = alt.Chart(base[base[n_coluna] < 5]).mark_point(color=cor, filled=False, size=70, strokeWidth=2).encode(
        x="ano:O", y=f"{coluna}:Q", tooltip=campos)
    return (linha + cheios + vazios).properties(title=titulo, height=290)


def mostrar_ou_avisar(grafico, aviso):
    if grafico is None:
        aviso_sem_dado(aviso)
    else:
        st.altair_chart(grafico, width="stretch")


# ----------------------------------------------------------------- aba 1: evolucao
with aba_evolucao:
    st.subheader("Desempenho e tamanho, ano a ano")
    g1, g2 = st.columns(2)
    with g1:
        longo = serie_g.melt(
            id_vars=["ano", "gpus_com_gflops"], value_vars=["gflops_maximo", "gflops_mediana"],
            var_name="medida", value_name="gflops",
        ).replace({"medida": {"gflops_maximo": "Mais forte do ano", "gflops_mediana": "Mediana do ano"}})
        longo = longo.dropna(subset=["gflops"])
        if longo.empty:
            aviso_sem_dado("Nenhuma GPU do recorte tem GFLOPS confirmado.")
        else:
            st.altair_chart(
                alt.Chart(longo).mark_line(point=True, strokeWidth=2.2).encode(
                    x=alt.X("ano:O", title="Ano de lançamento", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("gflops:Q", title="GFLOPS (FP32 teórico)", scale=escala(escala_log)),
                    color=alt.Color("medida:N", title=None,
                                    scale=alt.Scale(domain=["Mais forte do ano", "Mediana do ano"],
                                                    range=[COR_GPU, "#D9A27F"]),
                                    legend=alt.Legend(orient="top")),
                    strokeDash=alt.StrokeDash("medida:N", legend=None,
                                              scale=alt.Scale(domain=["Mais forte do ano", "Mediana do ano"],
                                                              range=[[1, 0], [4, 3]])),
                    tooltip=[alt.Tooltip("ano:O", title="Ano"), alt.Tooltip("medida:N", title="Medida"),
                             alt.Tooltip("gflops:Q", title="GFLOPS", format=",.0f"),
                             alt.Tooltip("gpus_com_gflops:Q", title="GPUs com GFLOPS confirmado")],
                ).properties(title="GPUs: poder de processamento", height=320),
                width="stretch",
            )
        st.markdown(
            '<p class="nota">Só entram GPUs com unidade confirmada. Anos com poucas GPUs confirmadas oscilam muito: '
            "veja a contagem na aba Tabelas.</p>",
            unsafe_allow_html=True,
        )
    with g2:
        longo_l = serie_l.melt(
            id_vars=["ano", "llms_com_parametros"], value_vars=["parametros_maximo", "parametros_mediana"],
            var_name="medida", value_name="parametros",
        ).replace({"medida": {"parametros_maximo": "Maior do ano", "parametros_mediana": "Mediana do ano"}})
        longo_l = longo_l.dropna(subset=["parametros"])
        if longo_l.empty:
            aviso_sem_dado("Nenhum LLM do recorte tem número de parâmetros.")
        else:
            st.altair_chart(
                alt.Chart(longo_l).mark_line(point=True, strokeWidth=2.2).encode(
                    x=alt.X("ano:O", title="Ano de lançamento", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("parametros:Q", title="Parâmetros (bilhões)", scale=escala(escala_log)),
                    color=alt.Color("medida:N", title=None,
                                    scale=alt.Scale(domain=["Maior do ano", "Mediana do ano"],
                                                    range=[COR_LLM, "#8CC3C7"]),
                                    legend=alt.Legend(orient="top")),
                    strokeDash=alt.StrokeDash("medida:N", legend=None,
                                              scale=alt.Scale(domain=["Maior do ano", "Mediana do ano"],
                                                              range=[[1, 0], [4, 3]])),
                    tooltip=[alt.Tooltip("ano:O", title="Ano"), alt.Tooltip("medida:N", title="Medida"),
                             alt.Tooltip("parametros:Q", title="Bilhões", format=",.1f"),
                             alt.Tooltip("llms_com_parametros:Q", title="LLMs com parâmetros")],
                ).properties(title="LLMs: tamanho dos modelos", height=320),
                width="stretch",
            )
        st.markdown(
            '<p class="nota">A mediana mostra o típico; o maior modelo mostra o topo. '
            "Desde 2022 o típico fica perto de 13 bilhões, enquanto o topo cresce.</p>",
            unsafe_allow_html=True,
        )

    st.subheader("Quantos itens foram lançados por ano")
    contagem = pd.concat([
        serie_g[["ano", "gpus"]].rename(columns={"gpus": "quantidade"}).assign(tipo="GPUs"),
        serie_l[["ano", "llms"]].rename(columns={"llms": "quantidade"}).assign(tipo="LLMs"),
    ])
    if contagem["quantidade"].sum() == 0:
        aviso_sem_dado("Nenhum lançamento no recorte.")
    else:
        st.altair_chart(
            alt.Chart(contagem).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                x=alt.X("ano:O", title="Ano de lançamento", axis=alt.Axis(labelAngle=0)),
                xOffset="tipo:N",
                y=alt.Y("quantidade:Q", title="Itens lançados"),
                color=alt.Color("tipo:N", title=None,
                                scale=alt.Scale(domain=["GPUs", "LLMs"], range=[COR_GPU, COR_LLM]),
                                legend=alt.Legend(orient="top")),
                tooltip=["ano", "tipo", "quantidade"],
            ).properties(height=260),
            width="stretch",
        )
    st.markdown(
        '<p class="nota">A fonte de GPUs tem poucas dezenas de lançamentos por ano: ela é uma amostra, '
        "não o mercado inteiro. Compare a tendência, não o número absoluto.</p>",
        unsafe_allow_html=True,
    )

    st.subheader("Mais transistores, mais consumo")
    t1, t2 = st.columns(2)
    with t1:
        mostrar_ou_avisar(
            serie_com_amostra(serie_g, "transistores_mediana", "gpus_com_transistores", COR_GPU,
                              "Transistores (mediana, milhões)", "milhões"),
            "Nenhuma GPU do recorte tem transistores informados.",
        )
    with t2:
        mostrar_ou_avisar(
            serie_com_amostra(serie_g, "tdp_mediana", "gpus_com_tdp", COR_GPU,
                              "Consumo (TDP, mediana em watts)", "watts"),
            "Nenhuma GPU do recorte tem consumo (TDP) informado.",
        )
    st.markdown(
        '<p class="nota">Ponto cheio: 5 ou mais GPUs no ano. Ponto vazado: menos de 5, leia com cuidado.</p>',
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------- aba 2: onde faltam dados
with aba_falta:
    st.subheader(f"Onde a fonte não traz o dado, {inicio}–{fim}")
    st.markdown(
        '<p class="lede">Cada célula mostra a parte das linhas do ano que tem aquele dado. '
        "A célula bege é <b>sem dado</b>: a conta não existe, não é zero.</p>",
        unsafe_allow_html=True,
    )

    nomes_g = {
        "ano_informado": "GPU · ano de lançamento",
        "gflops_confirmado": "GPU · GFLOPS confirmado",
        "tdp": "GPU · consumo (TDP)",
        "transistores": "GPU · transistores",
        "area_do_die": "GPU · área do die",
    }
    nomes_l = {"parametros": "LLM · parâmetros", "tokens": "LLM · tokens", "alscore": "LLM · AL Score"}
    partes = []
    for coluna, nome in nomes_g.items():
        parte = cob_g[["ano", coluna, "gpus"]].rename(columns={coluna: "cobertura", "gpus": "itens"})
        partes.append(parte.assign(indicador=nome))
    for coluna, nome in nomes_l.items():
        parte = cob_l[["ano", coluna, "llms"]].rename(columns={coluna: "cobertura", "llms": "itens"})
        partes.append(parte.assign(indicador=nome))
    cobertura = pd.concat(partes, ignore_index=True)
    cobertura["texto"] = cobertura["cobertura"].map(percentual)

    ordem = list(nomes_g.values()) + list(nomes_l.values())
    base_mapa = alt.Chart(cobertura).encode(
        x=alt.X("ano:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("indicador:N", title=None, sort=ordem),
    )
    mapa = base_mapa.mark_rect(stroke="white", strokeWidth=1).encode(
        color=alt.Color("cobertura:Q", title="Parte com dado",
                        scale=alt.Scale(domain=[0, 0.5, 1], range=[COR_SEM_DADO, "#E9A27A", COR_GPU]),
                        legend=alt.Legend(format=".0%")),
        tooltip=[alt.Tooltip("indicador:N", title="Dado"), alt.Tooltip("ano:O", title="Ano"),
                 alt.Tooltip("texto:N", title="Com dado"), alt.Tooltip("itens:Q", title="Itens no ano")],
    )
    rotulos = base_mapa.mark_text(fontSize=11, color=COR_TEXTO).encode(text="texto:N")
    st.altair_chart((mapa + rotulos).properties(height=330), width="stretch")

    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("**Por que uma GPU fica sem GFLOPS confirmado**")
        if motivos.empty:
            aviso_sem_dado("Nenhuma GPU no recorte.")
        else:
            legivel = motivos.replace({"unidade_gflops": {
                "GFLOPS": "Confirmado em GFLOPS",
                "TFLOPS convertido": "Convertido de TFLOPS",
                "inconclusivo": "Inconclusivo (longe do teórico)",
                "sem referencia": "Sem clock ou shaders",
            }})
            st.altair_chart(
                alt.Chart(legivel).mark_bar().encode(
                    y=alt.Y("fabricante:N", title=None),
                    x=alt.X("gpus:Q", title="GPUs"),
                    color=alt.Color("unidade_gflops:N", title=None,
                                    scale=alt.Scale(range=["#B5532A", "#E9A27A", "#8C8C8C", "#D8CFC2"]),
                                    legend=alt.Legend(orient="bottom", columns=2)),
                    tooltip=["fabricante", "unidade_gflops", "gpus"],
                ).properties(height=190),
                width="stretch",
            )
            sem_ref = motivos[motivos["unidade_gflops"] == "sem referencia"].groupby("fabricante")["gpus"].sum()
            total = motivos.groupby("fabricante")["gpus"].sum()
            resumo = " · ".join(
                f"{f}: {inteiro(sem_ref.get(f, 0))} de {inteiro(total[f])} sem clock ou shaders" for f in total.index
            )
            st.markdown(f'<p class="nota">{resumo}</p>', unsafe_allow_html=True)
    with c2:
        st.markdown("**O que fica de fora da conta**")
        st.markdown(
            f"""
            <div class="faltando"><span class="nota"><b>{inteiro(visao['gpus_sem_ano'])} GPUs</b> sem ano de lançamento
            na fonte. Não entram em nenhum período.</span></div>
            <div class="faltando"><span class="nota"><b>{inteiro(visao['gpus_no_periodo'] - visao['gpus_com_gflops'])} GPUs</b>
            do período sem GFLOPS confirmado.</span></div>
            <div class="faltando"><span class="nota"><b>{inteiro(visao_llm['llms'] - visao_llm['llms_com_parametros'])} LLMs</b>
            do período sem número de parâmetros.</span></div>
            <div class="faltando"><span class="nota"><b>{inteiro(visao_llm['llms'] - visao_llm['llms_com_tokens'])} LLMs</b>
            do período sem tokens.</span></div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="nota">Na fonte de LLMs, “TBA” (a ser anunciado) aparece no lugar de dado faltante. '
            "Esses casos viraram ausentes no projeto.</p>",
            unsafe_allow_html=True,
        )

    st.markdown("**Empresas com mais LLMs no período**")
    if top_empresas.empty:
        aviso_sem_dado("Nenhum LLM no período.")
    else:
        st.altair_chart(
            alt.Chart(top_empresas).mark_bar(color=COR_LLM, cornerRadiusEnd=3).encode(
                y=alt.Y("empresa:N", sort="-x", title=None),
                x=alt.X("llms:Q", title="LLMs lançados"),
                tooltip=["empresa", "llms"],
            ).properties(height=260),
            width="stretch",
        )
        st.markdown(
            '<p class="nota">Os nomes vêm como estão na fonte. “Google” e “Google DeepMind” aparecem separados: '
            "não foram unificados.</p>",
            unsafe_allow_html=True,
        )


# ----------------------------------------------------------------- aba 3: ano a ano
with aba_ano:
    st.subheader(f"Lançamentos de {ano}")
    gpus_ano = consultas.gpus_do_ano(ano, limite, fabricante)
    llms_ano = consultas.llms_do_ano(ano, limite)
    linha_g = serie_g[serie_g["ano"] == ano]
    linha_l = serie_l[serie_l["ano"] == ano]
    n_gpu = int(linha_g["gpus"].iloc[0]) if not linha_g.empty else 0
    n_llm = int(linha_l["llms"].iloc[0]) if not linha_l.empty else 0
    com_gflops = int(linha_g["gpus_com_gflops"].iloc[0]) if n_gpu else 0
    com_params = int(linha_l["llms_com_parametros"].iloc[0]) if n_llm else 0

    a, b, c_, d = st.columns(4)
    a.metric("GPUs no ano", inteiro(n_gpu), border=True)
    b.metric("GPUs com GFLOPS", inteiro(com_gflops), border=True)
    c_.metric("LLMs no ano", inteiro(n_llm), border=True)
    d.metric("LLMs com parâmetros", inteiro(com_params), border=True)

    # tabelas em largura total, uma depois da outra: as colunas ficam legiveis
    esquerda = direita = st.container()
    with esquerda:
        st.markdown("**GPUs do ano, da mais forte para a mais fraca**")
        if n_gpu == 0:
            aviso_sem_dado(f"Nenhuma GPU de {ano} no recorte de fabricante escolhido.")
        elif com_gflops == 0:
            aviso_sem_dado(f"Nenhuma das {n_gpu} GPUs de {ano} tem GFLOPS confirmado. "
                           "A lista abaixo está ordenada por transistores, quando a fonte traz.")
        st.dataframe(
            gpus_ano, hide_index=True, width="stretch",
            column_config={
                "modelo": st.column_config.TextColumn("Modelo"),
                "fabricante": st.column_config.TextColumn("Fabricante"),
                "interface_barramento": st.column_config.TextColumn("Interface"),
                "gflops_corrigido": st.column_config.NumberColumn("GFLOPS", format="%.0f"),
                "unidade_gflops": st.column_config.TextColumn("Como foi medido"),
                "tdp_watts": st.column_config.NumberColumn("TDP (W)", format="%.0f"),
                "transistores_milhoes": st.column_config.NumberColumn("Transistores (mi)", format="%.0f"),
            },
        )
    with direita:
        st.markdown("**LLMs do ano, dos maiores para os menores**")
        if n_llm == 0:
            aviso_sem_dado(f"Nenhum LLM da fonte foi lançado em {ano}. A fonte de LLMs cobre 2018 a 2024.")
        elif com_params == 0:
            aviso_sem_dado(f"Os {n_llm} LLMs de {ano} não têm número de parâmetros na fonte.")
        st.dataframe(
            llms_ano, hide_index=True, width="stretch",
            column_config={
                "modelo": st.column_config.TextColumn("Modelo"),
                "empresa": st.column_config.TextColumn("Empresa"),
                "parametros": st.column_config.NumberColumn("Parâmetros (bi)", format="%.1f"),
                "tokens": st.column_config.NumberColumn("Tokens", format="%.0f"),
                "alscore": st.column_config.NumberColumn("AL Score", format="%.1f"),
            },
        )
    st.markdown(
        '<p class="nota">Parâmetros e tokens de modelos fechados vêm da fonte e não foram verificados: '
        "trate como estimativa.</p>",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------- aba 4: tabelas
with aba_tabelas:
    st.subheader("Tabelas do recorte")
    st.markdown("**GPUs por ano**")
    st.dataframe(
        serie_g, hide_index=True, width="stretch",
        column_config={
            "ano": st.column_config.NumberColumn("Ano", format="%d"),
            "gpus": st.column_config.NumberColumn("GPUs"),
            "gpus_com_gflops": st.column_config.NumberColumn("Com GFLOPS"),
            "gflops_mediana": st.column_config.NumberColumn("GFLOPS (mediana)", format="%.0f"),
            "gflops_maximo": st.column_config.NumberColumn("GFLOPS (máximo)", format="%.0f"),
            "gpus_com_tdp": st.column_config.NumberColumn("Com TDP"),
            "tdp_mediana": st.column_config.NumberColumn("TDP (mediana, W)", format="%.0f"),
            "gpus_com_transistores": st.column_config.NumberColumn("Com transistores"),
            "transistores_mediana": st.column_config.NumberColumn("Transistores (mediana, mi)", format="%.0f"),
            "densidade_mediana": st.column_config.NumberColumn("Densidade (mi/mm²)", format="%.1f"),
        },
    )
    st.markdown("**LLMs por ano**")
    st.dataframe(
        serie_l, hide_index=True, width="stretch",
        column_config={
            "ano": st.column_config.NumberColumn("Ano", format="%d"),
            "llms": st.column_config.NumberColumn("LLMs"),
            "llms_com_parametros": st.column_config.NumberColumn("Com parâmetros"),
            "parametros_mediana": st.column_config.NumberColumn("Parâmetros (mediana, bi)", format="%.1f"),
            "parametros_maximo": st.column_config.NumberColumn("Parâmetros (máximo, bi)", format="%.1f"),
            "llms_com_tokens": st.column_config.NumberColumn("Com tokens"),
            "tokens_mediana": st.column_config.NumberColumn("Tokens (mediana)", format="%.0f"),
        },
    )
    d1, d2 = st.columns(2)
    d1.download_button("Baixar tabela de GPUs (CSV)", serie_g.to_csv(index=False).encode("utf-8"),
                       "gpus_por_ano.csv", "text/csv", width="stretch")
    d2.download_button("Baixar tabela de LLMs (CSV)", serie_l.to_csv(index=False).encode("utf-8"),
                       "llms_por_ano.csv", "text/csv", width="stretch")

with st.expander("Como ler este painel"):
    st.markdown(
        """
- **GFLOPS**: operações de ponto flutuante por segundo. Medida teórica de desempenho da GPU.
  A fonte mistura GFLOPS e TFLOPS. O projeto confere cada linha contra shaders × 2 × clock e
  converte quando precisa. Sem essa conferência, a linha fica como *sem dado*.
- **Parâmetros**: números que um modelo aprende, em bilhões. Mais parâmetros costuma indicar um modelo maior.
- **Mediana** é o valor do meio: um outlier não a empurra. **Máximo** é o topo: um único modelo o altera.
- **Amostras**: com poucos itens por ano, a média e o máximo mudam muito de um ano para o outro.
- **Filtro de fabricante** vale só para GPUs.
        """
    )
