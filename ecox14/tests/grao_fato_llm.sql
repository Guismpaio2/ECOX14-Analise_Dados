-- Passa quando devolve ZERO linhas.
-- Grao de fato_llm: um modelo por linha.
select modelo, count(*) as repeticoes
from {{ ref('fato_llm') }}
group by modelo
having count(*) > 1
