# Uma política de fomento baseada em evidências — FSA 2014–2023

Avaliação empírica do desempenho **doméstico** e **internacional** das obras de
cinema financiadas com recurso público federal brasileiro. Dados e scripts são
abertos: qualquer evidência aqui pode ser testada, verificada ou refutada.

**Pergunta central:** qual prática de fomento trouxe os melhores resultados
mensuráveis, e a que custo e instabilidade?

Dois artefatos publicados:

| arquivo | o que é |
|---|---|
| [`site/ensaio.html`](site/ensaio.html) | o texto — o argumento, em sete perguntas |
| [`site/evidencias.html`](site/evidencias.html) | o painel de dados — os agregados do fomento, com tabelas ordenáveis e dispersões |

## A regra que governa todos os números

1. **Dois universos.** Só entra na conta de retorno a obra com as **duas
   pontas** — financiamento e renda. Sem renda encontrada, o financiamento
   também sai do denominador. Universo de **aplicação** = 985 obras (estreia,
   pulverização, concentração); universo de **retorno** = 855 obras (todos os
   indicadores de desempenho).
2. **O denominador é todo o dinheiro público**: FSA + renúncia captada. Nunca só
   FSA.
3. **O internacional é condicionado ao doméstico** — a obra primeiro existe em
   sala no Brasil, depois se mede festival, Lumière e VOD.
4. **O escopo é cinema.** Séries financiadas por renúncia (cadastro = TV) ficam
   fora.
5. **Deflação:** IPCA, base R$ dez/2024, sempre.
6. **Observado × estimado** sempre separados e declarados. A receita de
   referência soma bilheteria observada com uma estimativa das demais janelas
   por faixa de CRT; a parcela estimada é declarada em toda tabela.

## Como reproduzir, do RIDAB ao painel

### 1. Baixar os dados

Os microdados vêm do **RIDAB — Repositório Independente dos Dados do Audiovisual
Brasileiro**, que reúne e limpa os dados abertos da ANCINE (OCA, PDA, SADIS,
FSA), do Observatório Europeu do Audiovisual (Lumière) e do IBGE:

- portal: <https://riabr-dados.github.io/riab/>
- dados: <https://huggingface.co/datasets/riabr/ridab>

Baixe o snapshot limpo para `data/ridab_cleaned/` (parquets) e os brutos usados
na recuperação da renúncia para `data/ridab_raw/`. Essas duas pastas não são
versionadas aqui — são grandes e reprodutíveis a partir da fonte. O manifesto
com os hashes do snapshot usado está em [`data/MANIFESTO.md`](data/MANIFESTO.md).

### 2. Preparar o ambiente

```bash
python -m venv .venv
.venv/Scripts/pip install pandas pyarrow numpy plotly kaleido openpyxl
```

### 3. Rodar o pipeline

```bash
.venv/Scripts/python scripts/10_base_obras.py       # RIDAB → base de obras
.venv/Scripts/python scripts/11_base_chamadas.py    # classificação das chamadas
.venv/Scripts/python scripts/12_base_produtoras.py  # carteira por grupo econômico
.venv/Scripts/python scripts/13_indicadores.py      # os números-âncora
.venv/Scripts/python scripts/22_site_evidencias.py  # → site/evidencias.html
```

Cada script imprime o que mudou em relação à rodada anterior. O `13` imprime um
diff contra a régua antiga, para que qualquer mudança de critério apareça.

### 4. Conferir

O painel sai em `site/evidencias.html`. Para servir localmente:

```bash
python -m http.server 8788 --directory site
```

## O que tem em cada pasta

```
scripts/10–13        RIDAB → bases canônicas
scripts/14           estudo curta → longa (coorte retrospectiva)
scripts/22           bases → painel de dados
scripts/site_base.py tema, helpers de figura e o registro das perguntas
src/                 loaders (fontes.py lê o snapshot local do RIDAB)
outputs/bases/       AS BASES CANÔNICAS — é daqui que todo número sai
outputs/tabelas/     tabelas intermediárias, obra a obra
referencia/          curadoria humana: overrides de chamadas, de-para de nomes
data/legado/         insumos do estudo anterior que o painel ainda consome
site/                os dois artefatos publicados
```

## As bases canônicas

Tudo que o painel mostra sai de quatro arquivos em `outputs/bases/`:

| base | grão | o que traz |
|---|---|---|
| `base_obras` | obra (CPB) | investimento, bilheteria, receita de referência, sinal internacional, os dois universos |
| `base_chamadas` | chamada pública | as quatro dimensões da lógica de seleção do edital |
| `base_produtoras` | grupo econômico | carteira, retorno de carteira, perfil |
| `indicadores.json` | — | os números-âncora, um por chave, sem formatação |

Nenhum número do painel é digitado à mão: todos vêm de `indicadores.json` ou das
bases. Mudou o critério, rode o `13` e leia o diff que ele imprime.

## Limites declarados

- O público observado cobre 73% das obras — as médias por real são **piso**, não
  teto.
- 14% da receita de referência é estimativa por faixa de CRT, sempre identificada.
- O sinal internacional cobre 23% das obras; crítica 57%; presença na Wikipedia 22%.
- O país de exibição fora da Europa e a circulação em VOD são hoje invisíveis ao
  dado público.
- As associações são **descritivas**. O fundo escolhe quem já tem trajetória, de
  modo que nada aqui identifica efeito causal.

## Licença

Código sob MIT. Os dados derivam de fontes públicas (ANCINE/OCA, Observatório
Europeu do Audiovisual, IBGE) e seguem as licenças de origem; a compilação em
bases derivadas é distribuída como CC-BY.
