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
python dados/bronze/ingerir.py

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

### GPU (Kaggle)
- Espaços removidos de nomes de coluna e de texto.
- `launch_date` convertida para `date` — timestamp nanosegundo descartado (só a data importa).
- Colunas numéricas (`transistors_million`, `die_size_mm2`, `core_clock_mhz`, `memory_clock_mhz`, `processing_power_gflops`, `tdp_watts`) convertidas com `errors="coerce"` — valores inválidos viram NaN.
- Chave composta `model` + `bus_interface`: duplicatas idênticas removidas. Motivo: o mesmo modelo com interfaces diferentes (PCI, AGP) são registros legítimos separados.
- `tdp_watts` e `processing_power_gflops` marcados por IQR e z-score — valores extremos sinalizados, não removidos (GPUs antigas vs. modernas têm diferença natural de escala).

### LLM (Kaggle)
- Espaços removidos de nomes de coluna (corrige `Tokens `) e de texto.
- `Comapany` renomeada para `Company` — erro de digitação da fonte original.
- Valores `TBA` substituídos por `NaN`. Motivo: eram ausentes mascarados como texto, impedindo análises numéricas.
- `Parameters`, `Tokens`, `Ratio`, `ALScore` convertidas para numérico com `errors="coerce"`.
- Chave `Model`: duplicatas removidas.
- `Parameters` e `ALScore` marcados por IQR e z-score.

## Defeitos conhecidos das fontes

### GPU (Kaggle)

- `launch_date` armazenado com timestamp completo (ex: `1995-09-30 00:00:00.000000000`) — precisa ser convertido para `date` na prata.
- Colunas `core_clock_mhz`, `memory_clock_mhz` e `processing_power_gflops` apresentam valores ausentes.
- Existem registros duplicados por interface de barramento: o mesmo modelo de GPU aparece uma vez para PCI e outra para AGP — decidir na prata se mantém linhas separadas ou agrega.
- Coluna `core_config` armazena texto no formato `1:1:1` (shader:TMU:ROP) — não é numérica diretamente.

### LLM (Kaggle)

- Coluna `Comapany` tem erro de digitação no nome (deveria ser `Company`).
- Coluna `Tokens ` tem espaço extra no final do nome.
- Valores `TBA` (To Be Announced) são usados no lugar de ausentes em diversas colunas — não são `NaN` reais, o que impede análises numéricas diretas.
- `Release Date` contém `TBA` em vez de ausentes, impedindo parsing automático como data.
- Colunas `Parameters` e `Tokens` são mistas (números e texto `TBA`) — precisam de limpeza antes de usar como numéricas.
