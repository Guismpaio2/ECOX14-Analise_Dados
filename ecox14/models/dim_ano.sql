-- Grao: uma linha por ano. Calendario completo, do primeiro ao ultimo ano das duas fontes.
with anos as (
    select ano_lancamento as ano from {{ source('prata', 'gpu') }}
    union all
    select ano_lancamento as ano from {{ source('prata', 'llm') }}
),

limites as (
    select min(ano) as primeiro, max(ano) as ultimo from anos
),

calendario as (
    select cast(unnest(range(primeiro, ultimo + 1)) as integer) as ano
    from limites
)

select ano, ano // 10 * 10 as decada
from calendario
