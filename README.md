# ECOX14 — Análise de Dados: GPUs e LLMs

Projeto desenvolvido na disciplina ECOX14 — Tópicos em Programação (UNIFEI).

## Fontes de dados

| Camada | Dataset | Origem |
|--------|---------|--------|
| Bronze | `dados/bronze/gpu/gpuDATA_YYYYMMDD.csv` | Kaggle: `riyagarg0314/gpu-specs-database-nvidia-and-amd-1995-2026` |
| Bronze | `dados/bronze/llm/llmDATA_YYYYMMDD.csv` | Kaggle: `jainaru/llms-data-2018-2024` |

## Como reproduzir

```bash
# 1. Criar e ativar ambiente virtual
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Ingerir dados da camada bronze
python src/ingerir.py   # alterne GPU/LLM comentando as linhas no topo do arquivo

# 4. Gerar relatórios de exploração automatizada
python src/explorar.py
# Os relatórios HTML são salvos em relatorios/ (não versionados)
```

## Como reproduzir a camada Prata

```bash
python src/transformar_gpu.py
python src/transformar_llm.py
# Gera dados/prata/gpu.parquet, dados/prata/llm.parquet e dados/prata/proveniencia.jsonl
```

## Decisões de tratamento

Funções genéricas (sem nome de fonte) ficam em `src/limpeza.py`; as específicas ficam no script de cada fonte.

### GPU (Kaggle) — chave: `model` + `bus_interface`
- Espaços removidos de nomes de coluna e de texto (`limpeza.tirar_espacos`).
- Colunas numéricas convertidas com `errors="coerce"`; `manufacturer` tipada como `category`.
- `launch_date` convertida para `date`. Em 11 linhas a fonte gravou o **ano como nanossegundos** (`1970-01-01 00:00:00.000001986` = 1986): `launch_date` fica ausente e o ano é recuperado em `ano_lancamento` (`Int64`).
- `bus_interface` mistura `x` e `×` (`PCIe 3.0 x16` / `×16`): 110 grafias viram 94 em `bus_interface_chave` (`limpeza.chave_texto`). O rótulo original é mantido.
- Chave composta `model` + `bus_interface`: 88 repetições removidas, fica a primeira ocorrência. No bruto nenhuma linha é 100% idêntica, então essas repetições podem diferir em outras colunas.
- `transistors_million`: de 2015 em diante a fonte grava em **bilhões** (5,47 em vez de 5470). 141 valores < 100 multiplicados por 1000. Conferido: RTX 4090 = 76.300 milhões.
- `die_size_mm2` igual a `transistors_million` em chip pós-2015 (linhas AMD Instinct) é cópia da fonte: 13 valores anulados.
- `tdp_watts` e `processing_power_gflops` marcados por IQR e z-score: extremos sinalizados, não removidos (GPUs antigas e modernas têm escalas naturalmente diferentes).
- **`processing_power_gflops` não é confiável entre eras**: a partir de ~2016 parece mudar de GFLOPS para TFLOPS (RTX 3090 Ti = 33,5; mediana por ano cai de 1161 em 2015 para 9,5 em 2021). Não foi corrigida nem usada em atributos derivados.

### LLM (Kaggle) — chave: `Model`
- Espaços removidos de nomes de coluna (corrige `Tokens `) e de texto.
- `Comapany` renomeada para `Company` — erro de digitação da fonte original.
- Valores `TBA` substituídos por `NaN`: eram ausentes mascarados como texto.
- `Ratio` vem como `20:01` ou `286:01:00` (razão 20:1 lida como hora) e a conversão antiga apagava a coluna toda (340 de 340 vazias). Agora guarda-se o número antes do `:` (238 de 340 na Prata; a razão `Tokens / Parameters / Ratio` tem mediana ≈ 1, o que valida a leitura).
- `Release Date` vem como `YY-Mon` (`24-Apr` = abril de 2024; o Excel inverteu `Apr-24`). Só há mês e ano, então não se cria data: ficam `ano_lancamento` e `mes_lancamento` (`Int64`); 8 ausentes (eram `TBA`).
- `Parameters`, `Tokens`, `ALScore` convertidas para numérico com `errors="coerce"`.
- Chave `Model`: 2 duplicatas removidas.
- `Parameters` e `ALScore` marcados por IQR e z-score.

## Atributos derivados

### ano_lancamento (GPU e LLM)
Ano de lançamento inteiro. Serve de chave de junção entre as duas fontes, que só se encontram pelo tempo. Ausente quando a fonte não informa a data (GPU: 624 linhas; LLM: 8).

### densidade_transistores (GPU)
`transistors_million / die_size_mm2`, em milhões de transistores por mm². Serve à pergunta norteadora: mostra quanto cada geração empacota por área, comparável entre eras (de 0,01 em 1995 a ~125 na RTX 4090). Ausente quando faltam transistores ou área, ou a área é zero.
Descartado: `gflops_por_watt`, por causa da mudança de escala de `processing_power_gflops` descrita acima.

## Defeitos conhecidos das fontes

### GPU (Kaggle)

- `launch_date` armazenado com timestamp completo (ex: `1995-09-30 00:00:00.000000000`); em 11 linhas o ano vem como nanossegundos desde 1970.
- `transistors_million` muda de milhões para bilhões a partir de 2015; `die_size_mm2` copia os transistores nas linhas AMD Instinct; `processing_power_gflops` muda de escala por volta de 2016.
- Colunas `core_clock_mhz`, `memory_clock_mhz` e `processing_power_gflops` apresentam valores ausentes.
- Existem registros duplicados por interface de barramento: o mesmo modelo de GPU aparece uma vez para PCI e outra para AGP — decidir na prata se mantém linhas separadas ou agrega.
- Coluna `core_config` armazena texto no formato `1:1:1` (shader:TMU:ROP) — não é numérica diretamente.

### LLM (Kaggle)

- Coluna `Comapany` tem erro de digitação no nome (deveria ser `Company`).
- Coluna `Tokens ` tem espaço extra no final do nome.
- Valores `TBA` (To Be Announced) são usados no lugar de ausentes em diversas colunas — não são `NaN` reais, o que impede análises numéricas diretas.
- `Release Date` contém `TBA` em vez de ausentes, impedindo parsing automático como data.
- `Ratio` e `Release Date` foram corrompidos pelo Excel (`20:01`, `24-Apr`).
- Colunas `Parameters` e `Tokens` são mistas (números e texto `TBA`) — precisam de limpeza antes de usar como numéricas.
