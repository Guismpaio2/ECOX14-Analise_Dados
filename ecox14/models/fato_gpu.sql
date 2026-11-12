-- Grao: uma linha por GPU em cada interface de barramento (modelo + interface_barramento).
-- processing_power_gflops fica de fora: a escala muda entre eras (ver README).
select
    model as modelo,
    bus_interface as interface_barramento,
    manufacturer as fabricante,
    ano_lancamento as ano,
    transistors_million as transistores_milhoes,
    die_size_mm2 as area_die_mm2,
    densidade_transistores,
    tdp_watts,
    tdp_watts_extremo,
    tdp_watts_z
from {{ source('prata', 'gpu') }}
