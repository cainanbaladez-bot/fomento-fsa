"""
Configuração central de caminhos — Análise Empírica FSA 2014–2023.

Boa prática: nenhum dado é duplicado dentro deste projeto. Tudo é lido,
no momento da análise, direto das bases de origem (RIDAB + projeto legado).
Se as pastas mudarem de lugar, basta editar aqui.
"""
from __future__ import annotations
from pathlib import Path

# Raiz deste projeto
PROJ = Path(__file__).resolve().parent

# ── Fontes externas (NÃO versionadas aqui; lidas in loco) ────────────────────
DESKTOP = PROJ.parent

# RIDAB — hub de dados públicos (dados-audiovisual-br)
RIDAB = DESKTOP / "dados-audiovisual-br"
RIDAB_CLEANED = RIDAB / "pipelines" / "output" / "cleaned"   # *.parquet limpos
RIDAB_CATALOG = RIDAB / "catalog" / "datasets.yaml"          # verdade do catálogo

# Projeto legado — primeira análise de fomento (tem dados que o RIDAB não tem:
# crítica, IMDb, prestígio de diretores, clusters de produtoras, sinais de ROI)
LEGADO = DESKTOP / "fomento-audiovisual"
LEGADO_DADOS = LEGADO / "dados"
LEGADO_RAW = LEGADO / "raw"
LEGADO_APOIO = LEGADO / "tabelas_apoio"
LEGADO_RESULT = LEGADO / "resultados"

# ── Snapshot local dos dados RIDAB (cópia, projeto self-contained) ───────────
DATA = PROJ / "data"
DATA_CLEANED = DATA / "ridab_cleaned"   # parquets limpos copiados do RIDAB
DATA_RAW = DATA / "ridab_raw"           # arquivos-fonte OCA (recuperam o que o
                                        # cleaned perdeu: captado/CNPJ investidor)

# ── Referência / overrides manuais (curadoria humana, persistente) ───────────
REFERENCIA = PROJ / "referencia"
REFERENCIA.mkdir(parents=True, exist_ok=True)
OVERRIDES_CHAMADAS = REFERENCIA / "overrides_chamadas.csv"

# ── Saídas deste projeto (versionadas) ───────────────────────────────────────
OUT = PROJ / "outputs"
OUT_CURADORIA = OUT / "curadoria"
OUT_EDA = OUT / "eda"
OUT_TABELAS = OUT / "tabelas"
OUT_FIGS = OUT / "figuras"

for _d in (OUT, OUT_CURADORIA, OUT_EDA, OUT_TABELAS, OUT_FIGS):
    _d.mkdir(parents=True, exist_ok=True)

# ── Parâmetros de análise ────────────────────────────────────────────────────
PERIODO = (1995, 2024)        # janela verificável do estudo — por ANO DE INÍCIO DE PRODUÇÃO
                              # (mesmo escopo do painel_exato: obras com FSA, sem piso efetivo, teto 2024)
DEFLATOR_BASE = 2024          # IPCA base para valores reais
