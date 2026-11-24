-- Passa quando devolve ZERO linhas.
-- So pode haver valor corrigido quando a unidade foi confirmada, e so pode ficar
-- vazio quando a unidade NAO foi confirmada. Pega uma inconsistencia entre as duas colunas.
select modelo, interface_barramento, unidade_gflops, gflops_corrigido
from {{ ref('fato_gpu') }}
where (gflops_corrigido is null) <> (unidade_gflops in ('inconclusivo', 'sem referencia'))
