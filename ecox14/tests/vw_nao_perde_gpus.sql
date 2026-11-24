-- Passa quando devolve ZERO linhas.
-- A view agrega as GPUs por ano. Se o join multiplicar ou perder linhas, a soma nao bate
-- com as GPUs que tem ano informado na fato.
with soma as (
    select sum(gpus_lancadas) as na_view from {{ ref('vw_ano_gpu_llm') }}
),
fato as (
    select count(*) as na_fato from {{ ref('fato_gpu') }} where ano is not null
)
select na_view, na_fato
from soma, fato
where na_view <> na_fato
