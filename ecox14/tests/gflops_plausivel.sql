-- Passa quando devolve ZERO linhas.
-- Nenhuma GPU de consumo ou datacenter passa de algumas centenas de TFLOPS (200.000 GFLOPS).
-- Um valor acima disso e sinal de unidade errada que escapou da correcao.
select modelo, interface_barramento, gflops_corrigido
from {{ ref('fato_gpu') }}
where gflops_corrigido <= 0 or gflops_corrigido > 200000
