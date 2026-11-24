-- Grao: uma linha por GPU em cada interface de barramento (modelo + interface_barramento).
-- gflops_corrigido ja vem na unidade certa (GFLOPS); o valor bruto da fonte fica fora.
-- Nulo quando a unidade nao pode ser confirmada (ver unidade_gflops e o README).
select
    model as modelo,
    -- 233 GPUs nao tem interface na fonte: entram como 'nao informada' em vez de sumir do grao.
    coalesce(bus_interface, 'nao informada') as interface_barramento,
    manufacturer as fabricante,
    ano_lancamento as ano,
    transistors_million as transistores_milhoes,
    die_size_mm2 as area_die_mm2,
    densidade_transistores,
    gflops_corrigido,
    unidade_gflops,
    tdp_watts,
    tdp_watts_extremo,
    tdp_watts_z
from {{ source('prata', 'gpu') }}
