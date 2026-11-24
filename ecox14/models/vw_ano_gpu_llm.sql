{{ config(materialized='view') }}

-- Grao: uma linha por ano. Resposta a pergunta norteadora: como as GPUs evoluem
-- em comparacao com o lancamento de LLMs.
-- Cada fato e agregada antes do join: juntar as duas direto multiplicaria as linhas
-- e distorceria as medianas.
with gpu as (
    select ano,
           count(*) as gpus_lancadas,
           -- gflops_corrigido ignora nulos: so entram GPUs com unidade confirmada
           count(gflops_corrigido) as gpus_com_gflops,
           median(gflops_corrigido) as gflops_mediana_gpu,
           max(gflops_corrigido) as gflops_maximo_gpu,
           median(densidade_transistores) as densidade_mediana_gpu
    from {{ ref('fato_gpu') }}
    where ano is not null
    group by ano
),

llm as (
    select ano,
           count(*) as llms_lancados,
           median(parametros) as parametros_mediana_llm,
           max(parametros) as parametros_maximo_llm
    from {{ ref('fato_llm') }}
    where ano is not null
    group by ano
)

select
    d.ano,
    d.decada,
    coalesce(g.gpus_lancadas, 0) as gpus_lancadas,
    coalesce(g.gpus_com_gflops, 0) as gpus_com_gflops,
    g.gflops_mediana_gpu,
    g.gflops_maximo_gpu,
    g.densidade_mediana_gpu,
    coalesce(l.llms_lancados, 0) as llms_lancados,
    l.parametros_mediana_llm,
    l.parametros_maximo_llm
from {{ ref('dim_ano') }} d
left join gpu g on g.ano = d.ano
left join llm l on l.ano = d.ano
order by d.ano
