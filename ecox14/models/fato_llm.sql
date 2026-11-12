-- Grao: uma linha por modelo de LLM.
select
    "Model" as modelo,
    "Company" as empresa,
    ano_lancamento as ano,
    mes_lancamento as mes,
    "Parameters" as parametros,
    "Tokens" as tokens,
    "Ratio" as razao_tokens_parametros,
    "ALScore" as alscore,
    Parameters_extremo as parametros_extremo,
    Parameters_z as parametros_z,
    ALScore_extremo as alscore_extremo,
    ALScore_z as alscore_z
from {{ source('prata', 'llm') }}
