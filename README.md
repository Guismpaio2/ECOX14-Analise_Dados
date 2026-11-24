# ECOX14 — Análise de Dados: GPUs e LLMs

Projeto da disciplina ECOX14 — Tópicos em Programação (UNIFEI), em engenharia de dados: um pipeline que vai do arquivo bruto ao dado confiável, com testes, documentação e um painel.

**Pergunta norteadora:** *Como as GPUs estão evoluindo em comparação com o desenvolvimento das IAs?*

As duas fontes só se encontram pelo **tempo**: o ano de lançamento de cada GPU e de cada modelo de linguagem.

## Sumário

- [Como executar](#como-executar) (um único comando, a partir da raiz)
- [Arquitetura](#arquitetura)
- [Resposta atual à pergunta norteadora](#resposta-atual-à-pergunta-norteadora)
- [Testes e documentação](#testes-e-documentação)
- [Painel](#painel)
- [Fontes de dados](#fontes-de-dados)
- [Decisões de tratamento](#decisões-de-tratamento)
- [Modelagem da camada Ouro](#modelagem-da-camada-ouro)
- [Defeitos conhecidos das fontes](#defeitos-conhecidos-das-fontes)
- [Limitações](#limitações)
- [Estrutura do repositório](#estrutura-do-repositório)

## Como executar

Requisitos: Python 3.13 (versão usada no desenvolvimento) e um token de API do Kaggle, que é usado na ingestão.

```bash
# 1. Ambiente virtual e dependências (a partir da raiz do projeto)
python3.13 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Token do Kaggle (uma vez por máquina; nunca versione este valor)
export KAGGLE_API_TOKEN="seu_token"

# 3. O pipeline inteiro, com um comando só
python src/pipeline.py
```

O comando executa, em ordem, as etapas abaixo. Se uma etapa falhar, o pipeline para nela.

| Etapa | O que faz | Saída |
|-------|-----------|-------|
| `ingestao` | baixa os dois datasets do Kaggle e copia para a Bronze, com a data no nome | `dados/bronze/` |
| `exploracao` | gera o relatório de perfil de cada fonte | `relatorios/*.html` |
| `transformacao` | limpa e tipa as duas fontes e registra a proveniência | `dados/prata/*.parquet`, `dados/prata/proveniencia.jsonl` |
| `carga` | abre o banco e carrega a Prata | `dados/ouro/projeto.duckdb` (esquema `prata`) |
| `modelagem` | roda `dbt run` (constrói a Ouro), `dbt test` (testes) e `dbt docs generate` (documentação) | esquema `ouro` no mesmo banco |

Para retomar a partir de uma etapa (útil para refazer só a Ouro):

```bash
python src/pipeline.py carga        # carga + modelagem
python src/pipeline.py modelagem    # só dbt run, dbt test e docs
```

Para recomeçar do zero, apague `dados/ouro/projeto.duckdb`: ele se reconstrói a partir da Prata.

## Arquitetura

```
 Kaggle ──► BRONZE ──► PRATA ──────────────► OURO (dbt) ──► PAINEL
 (API)      CSV        Parquet + DuckDB       modelos SQL     Streamlit
            intacto    limpeza, tipos,        testes, docs    só leitura
                       proveniência           dim, fatos, view
 ◄──────────── src/pipeline.py: um comando, uma etapa por vez ────────────►
```

- **Bronze:** cópia fiel do CSV da fonte, datada no nome. Nada é corrigido aqui. Uma extração nova não apaga a anterior.
- **Prata:** cada defeito da fonte virou uma função em `src/`. A proveniência de cada execução fica em `dados/prata/proveniencia.jsonl`.
- **Ouro:** construída com **dbt** a partir de `ecox14/models/`. Quem constrói é o dbt, não o Python: o Python só abre o banco e carrega a Prata.
- **Painel:** consumidor da Ouro. Abre o banco em modo somente leitura e não cria nem altera nada.

O banco é um arquivo DuckDB (`dados/ouro/projeto.duckdb`): não há servidor. O profile do dbt fica versionado em `ecox14/profiles.yml`, com caminho relativo, então nada precisa ser configurado em `~/.dbt`.

## Resposta atual à pergunta norteadora

A Ouro responde à pergunta com uma linha por ano, na view `ouro.vw_ano_gpu_llm`. Na janela em que as duas fontes se sobrepõem (2018 a 2024):

| Ano | GPUs lançadas | GPUs com GFLOPS confirmado | GFLOPS da GPU mais forte | LLMs lançados | Maior LLM (bilhões de parâmetros) |
|-----|---------------|----------------------------|--------------------------|---------------|-----------------------------------|
| 2018 | 17 | 6 | 24.883 | 3 | 0,3 |
| 2020 | 16 | 6 | 32.000 | 3 | 175 |
| 2022 | 15 | 9 | 73.236 | 60 | 540 |
| 2024 | 6 | 6 | 47.002 | 99 | 2.000 |

Leitura: de 2018 a 2024 a GPU mais forte do ano cresceu cerca de **2 vezes** em GFLOPS, enquanto o maior LLM cresceu **mais de 6.000 vezes** em parâmetros e o número de LLMs lançados por ano foi de 3 para 99. A densidade mediana de transistores por mm² das GPUs também quintuplicou no período (24 para 121).

**Limitações dessa resposta:** a amostra de GPUs com GFLOPS confirmado é pequena por ano (6 a 17), a série de LLMs termina em 2024, e as duas fontes medem coisas diferentes. Por isso a resposta é **direcional**, não estatística. O painel mostra o `n` de cada ano para o leitor julgar.

## Testes e documentação

Os testes ficam em dois lugares, e o `dbt test` roda dentro da etapa `modelagem`: se um teste falhar, o pipeline para.

**Testes prontos**, declarados em `ecox14/models/schema.yml` (o dbt escreve a consulta):

- `not_null` e `unique` na chave de cada modelo (`dim_ano.ano`, `fato_llm.modelo`, `vw_ano_gpu_llm.ano`);
- `relationships`: todo `ano` de `fato_gpu` e `fato_llm` existe em `dim_ano`;
- `accepted_values` na coluna `unidade_gflops`.

**Testes escritos à mão**, em `ecox14/tests/`. Cada um passa quando devolve **zero linhas**:

| Teste | Confere |
|-------|---------|
| `grao_fato_gpu.sql` | a chave composta `modelo + interface_barramento` não se repete |
| `grao_fato_llm.sql` | cada modelo de LLM aparece uma vez |
| `gflops_plausivel.sql` | nenhum GFLOPS é zero, negativo ou acima de 200.000 (sinal de unidade errada) |
| `unidade_gflops_coerente.sql` | valor corrigido vazio **se e só se** a unidade não foi confirmada |
| `vw_nao_perde_gpus.sql` | a view não perde nem multiplica GPUs ao agregar por ano |

Para ver as linhas que falharam, sem parar o pipeline: `cd ecox14 && dbt test --store-failures --profiles-dir .`

**Documentação gerada do código:**

```bash
cd ecox14
dbt docs generate --profiles-dir .
dbt docs serve --profiles-dir .      # abre o site com o grafo dos modelos e a descrição de cada coluna
```

A descrição de cada coluna está no `schema.yml`, ao lado do teste. Ela não é escrita duas vezes: ou está certa, ou o código mudou junto.

**Inspecionar os dados (opcional):** a interface do DuckDB mostra o conteúdo das tabelas no navegador.

```bash
duckdb -ui dados/ouro/projeto.duckdb   # com o DuckDB CLI instalado (ex.: brew install duckdb)
```

Feche o painel e o pipeline antes: o DuckDB trava o arquivo enquanto uma escrita está aberta.

## Painel

```bash
streamlit run dashboard/painel.py      # a partir da raiz, com o pipeline já executado
```

O painel tem três partes: um recorte de anos, uma tabela anual e as GPUs e LLMs mais fortes de um ano escolhido. Separação do código:

- `dashboard/consultas.py`: todo o SQL de leitura. Os valores da tela entram como parâmetros (`?`), nunca concatenados.
- `dashboard/painel.py`: só a tela. Não tem SQL.

O banco é aberto com `read_only=True`: se alguém escrever uma consulta que altera dados, o DuckDB recusa.

## Fontes de dados

| Camada | Dataset | Origem | Tamanho bruto |
|--------|---------|--------|---------------|
| Bronze | `dados/bronze/gpu/gpuDATA_YYYYMMDD.csv` | Kaggle: `riyagarg0314/gpu-specs-database-nvidia-and-amd-1995-2026` | 1.943 linhas × 13 colunas |
| Bronze | `dados/bronze/llm/llmDATA_YYYYMMDD.csv` | Kaggle: `jainaru/llms-data-2018-2024` | 342 linhas × 11 colunas |

Os CSVs da Bronze não são versionados (ficam na máquina, e a ingestão os reconstrói). A proveniência de cada transformação é versionada em `dados/prata/proveniencia.jsonl`.

## Decisões de tratamento

Funções genéricas (sem nome de fonte) ficam em `src/limpeza.py`; as específicas ficam no script de cada fonte.

### GPU (Kaggle): chave `model` + `bus_interface`

- Espaços removidos de nomes de coluna e de texto (`limpeza.tirar_espacos`).
- Colunas numéricas convertidas com `errors="coerce"`; `manufacturer` tipada como `category`.
- `launch_date` convertida para `date`. Em 11 linhas a fonte gravou o **ano como nanossegundos** (`1970-01-01 00:00:00.000001986` = 1986): o ano é recuperado em `ano_lancamento` (`Int64`).
- `bus_interface` mistura `x` e `×` (`PCIe 3.0 x16` / `×16`): 110 grafias viram 94 em `bus_interface_chave` (`limpeza.chave_texto`). O rótulo original é mantido.
- Chave composta `model` + `bus_interface`: 88 repetições removidas, fica a primeira ocorrência.
- `transistors_million`: de 2015 em diante a fonte grava em **bilhões** (5,47 em vez de 5470). 141 valores < 100 são multiplicados por 1000. Conferido: RTX 4090 = 76.300 milhões.
- `die_size_mm2` igual a `transistors_million` em chip pós-2015 (linhas AMD Instinct) é cópia da fonte: 13 valores anulados.
- **`processing_power_gflops`: a unidade é corrigida linha a linha** (ver a seção seguinte).
- `tdp_watts` e `gflops_corrigido` marcados por IQR e z-score: extremos sinalizados, não removidos.

#### Unidade do GFLOPS: a descoberta e a correção

A suspeita inicial era de uma troca de unidade ao longo dos anos. Os dados mostram algo mais específico: a fonte **mistura GFLOPS e TFLOPS (×1000) linha a linha**, não por época. O mesmo modelo aparece com `12,995` e `13.270` em anos vizinhos, e em 2019 há valores de GPUs antigas e modernas nas duas unidades. Não há valores em MFLOPS (a menor escala que aparece é a de GFLOPS).

Como a própria fonte não diz a unidade de cada linha, a correção usa uma referência física que está na tabela: **GFLOPS teórico = shaders × 2 × clock do core (MHz) / 1000**. Para cada linha:

1. Calcula-se o teórico a partir de `core_config` (shaders) e `core_clock_mhz`.
2. Compara-se o valor da fonte com duas hipóteses: GFLOPS (sem mudança) e TFLOPS (×1000). Fica a hipótese mais próxima do teórico.
3. Se nenhuma fica a menos de 3× do teórico, a linha fica **sem valor corrigido**. Isso cobre GPUs sem clock e a precisão FP64 do Pascal, que vale 1/64 do teórico e não é uma questão de unidade.

Resultado (Prata, 1.855 linhas):

| `unidade_gflops` | Linhas | Significado |
|------------------|--------|-------------|
| `GFLOPS` | 439 | a fonte já estava em GFLOPS |
| `TFLOPS convertido` | 153 | a fonte estava em TFLOPS; multiplicado por 1000 |
| `inconclusivo` | 66 | longe do teórico nas duas hipóteses (ex.: FP64 do Pascal) |
| `sem referencia` | 1.197 | sem clock do core ou `core_config` não interpretável |

Ou seja: **592 GPUs (32%) têm GFLOPS confirmado**. A cobertura é a principal limitação da métrica e aparece na view (`gpus_com_gflops`). Escolhemos não preencher as demais com palpite.

Validação: RTX 3090 (10.496 shaders × 2 × 1.395 MHz = 29.286 GFLOPS) e RTX 4090 (16.384 × 2 × 2.235 = 73.236) batem com a fonte depois da conversão de TFLOPS; GTX 680 (1.536 × 2 × 1.006 = 3.090) bate sem conversão.

### LLM (Kaggle): chave `Model`

- Espaços removidos de nomes de coluna (corrige `Tokens `) e de texto.
- `Comapany` renomeada para `Company`: erro de digitação da fonte original.
- Valores `TBA` substituídos por `NaN`: eram ausentes mascarados como texto.
- `Ratio` vem como `20:01` ou `286:01:00` (razão 20:1 lida como hora). Guarda-se o número antes do `:` (238 de 340 na Prata; a razão `Tokens / Parameters` tem mediana ≈ 1, o que valida a leitura).
- `Release Date` vem como `YY-Mon` (`24-Apr` = abril de 2024; o Excel inverteu `Apr-24`). Só há mês e ano, então não se cria data: ficam `ano_lancamento` e `mes_lancamento` (`Int64`).
- `Parameters` está em **bilhões** em toda a fonte (GPT-1 = 0,117; GPT-4 = 1.760): não há mistura de escala.
- Chave `Model`: 2 duplicatas removidas.
- `Parameters` e `ALScore` marcados por IQR e z-score.

### Atributos derivados

- **`ano_lancamento`** (GPU e LLM): ano inteiro. É a chave de junção entre as fontes. Ausente quando a fonte não informa.
- **`densidade_transistores`** (GPU): `transistors_million / die_size_mm2`, em milhões de transistores por mm². Mostra quanto cada geração empacota por área, comparável entre eras.
- **`gflops_corrigido`** e **`unidade_gflops`** (GPU): poder de processamento na unidade confirmada, e como essa unidade foi decidida. Entram na Ouro.

## Modelagem da camada Ouro

### Tabelas

| Tabela | Tipo | Grão (uma linha é…) |
|--------|------|---------------------|
| `ouro.dim_ano` | dimensão | um ano, do primeiro ao último ano das duas fontes, sem buracos |
| `ouro.fato_gpu` | fato | uma GPU em uma interface de barramento (`modelo` + `interface_barramento`) |
| `ouro.fato_llm` | fato | um modelo de LLM (`modelo`) |
| `ouro.vw_ano_gpu_llm` | view | um ano, com GPUs e LLMs agregados (resposta à pergunta norteadora) |

`fato_gpu.ano` e `fato_llm.ano` apontam para `dim_ano.ano`. Os modelos se referenciam com `ref()` e as tabelas da Prata são declaradas como `source()` em `ecox14/models/sources.yml`: o dbt deduz a ordem de execução sozinho.

### Decisões de modelagem

- **Ano ausente não é órfão.** 624 GPUs e 8 LLMs não têm ano de lançamento. Ficam na fato com `ano` nulo, em vez de descartadas. Os testes de `relationships` ignoram nulos.
- **Interface ausente vira `nao informada`.** 233 GPUs não trazem interface na fonte. Elas continuam no grão, com esse rótulo, em vez de sumirem.
- **Agregar antes do join.** A view agrega cada fato por ano antes de juntar: juntar as duas direto multiplicaria as linhas e distorceria as medianas. O teste `vw_nao_perde_gpus` confere isso.
- **Sem `dim_empresa`.** A pergunta é sobre tempo. O fabricante e a empresa do LLM ficam como texto na fato.
- **Texto descritivo do LLM (arquitetura, notas, playground) fica fora da fato.** Não é medida nem chave.

## Defeitos conhecidos das fontes

### GPU (Kaggle)

- `launch_date` com timestamp completo; em 11 linhas o ano vem como nanossegundos desde 1970.
- `transistors_million` muda de milhões para bilhões a partir de 2015; `die_size_mm2` copia os transistores nas linhas AMD Instinct.
- **`processing_power_gflops` mistura GFLOPS e TFLOPS linha a linha** (ver [Unidade do GFLOPS](#unidade-do-gflops-a-descoberta-e-a-correção)).
- Valores FP64 (1/64 do teórico) aparecem em GPUs Pascal, misturados aos FP32.
- `core_clock_mhz`, `memory_clock_mhz` e `processing_power_gflops` têm valores ausentes.
- `core_config` tem grafias variadas (`1:1:1`, `2× 128:64:16:16`, `2944:184:64: 46:368:46`), por isso a leitura é tolerante.
- Mesmo modelo aparece em mais de uma interface (PCI e AGP): a chave é composta.

### LLM (Kaggle)

- `Comapany` tem erro de digitação; `Tokens ` tem espaço no nome.
- `TBA` (To Be Announced) é usado no lugar de ausentes em diversas colunas.
- `Ratio` e `Release Date` foram corrompidos pelo Excel (`20:01`, `24-Apr`).
- `Parameters` e `Tokens` são mistas (números e `TBA`).

## Limitações

- **Cobertura da métrica de GFLOPS:** só 32% das GPUs têm valor confirmado. A correção é conservadora de propósito: é melhor ter menos dados certos do que mais dados com unidade chutada.
- **Amostra por ano:** com 6 a 17 GPUs com GFLOPS confirmado por ano, cada mediana anual é instável. A view mostra o `n` para isso.
- **Duas medidas diferentes:** GFLOPS e densidade medem a GPU; parâmetros medem o modelo de linguagem. A comparação é direcional, não causal.
- **Janela curta do LLM:** a fonte cobre 2018 a 2024. A série de LLMs não cresce depois de 2024.
- **Sem dados pessoais:** as duas fontes são públicas e agregadas por modelo; nenhuma linha identifica pessoas.

## Estrutura do repositório

```
.
├── README.md
├── requirements.txt
├── src/                    Python: ingestão, exploração, prata, carga e o orquestrador
│   ├── pipeline.py         ponto de entrada (python src/pipeline.py)
│   ├── config.py           caminhos e configuração de log
│   ├── ingerir.py          Kaggle → Bronze
│   ├── explorar.py         perfil automático (relatorios/)
│   ├── limpeza.py          funções genéricas de limpeza
│   ├── transformar_gpu.py  Bronze → Prata (GPU), com a correção de GFLOPS
│   ├── transformar_llm.py  Bronze → Prata (LLM)
│   └── carga.py            abre o banco e carrega a Prata
├── ecox14/                 projeto dbt: constrói a Ouro
│   ├── dbt_project.yml
│   ├── profiles.yml        profile do banco (versionado, caminho relativo)
│   ├── models/             dim_ano, fato_gpu, fato_llm, vw_ano_gpu_llm, schema.yml
│   └── tests/              testes escritos à mão
├── dashboard/              painel Streamlit (consumidor da Ouro)
│   ├── consultas.py        todo o SQL de leitura
│   └── painel.py           só a tela
└── dados/                  Bronze, Prata e Ouro (gerados; ver .gitignore)
```

Gerados e não versionados: `dados/bronze/*.csv`, `dados/prata/*.parquet`, `dados/ouro/projeto.duckdb`, `relatorios/`, `logs/`, `ecox14/target/`.
