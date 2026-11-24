-- Passa quando devolve ZERO linhas.
-- Grao de fato_gpu: uma GPU em cada interface de barramento. A chave e composta,
-- por isso nao ha teste pronto: a consulta e escrita aqui.
select modelo, interface_barramento, count(*) as repeticoes
from {{ ref('fato_gpu') }}
group by modelo, interface_barramento
having count(*) > 1
