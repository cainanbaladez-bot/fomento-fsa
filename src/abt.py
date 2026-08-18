"""
Loader da ABT enriquecida com as 4 dimensões de seleção.

Junta a tabela analítica (obra-nível) à classificação de chamadas
(auto + overrides manuais). Toda análise por lógica de seleção (P1–P9)
entra por aqui — assim, quando a classificação muda (overrides), basta
re-rodar e todas as análises refletem a correção.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config as C
from src.fontes import destino_midia


def carregar_abt(apenas_periodo: bool = True,
                 apenas_classificadas: bool = False) -> pd.DataFrame:
    abt = pd.read_parquet(C.OUT_TABELAS / "abt_obra_fsa.parquet")

    clas = pd.read_csv(C.OUT_CURADORIA / "classificacao_chamadas.csv")
    dims = clas[["chamada", "macro_categoria", "grau_automatismo",
                 "criterio_pontuacao", "elo_decisor", "destino", "origem",
                 "confianca"]].rename(
        columns={"chamada": "chamada_publica",
                 "destino": "destino_chamada",
                 "confianca": "confianca_classif"})
    abt = abt.merge(dims, on="chamada_publica", how="left")

    # destino-mídia por obra (Cinema/TV/Outros), do segmento real da ANCINE
    abt["destino_obra"] = abt["segmento_destinacao_inicial"].map(destino_midia)

    if apenas_periodo:
        lo, hi = C.PERIODO
        # eixo = ano de início de produção (mesmo recorte do painel_exato).
        # fallback para ano_ref se ano_producao_inicial faltar.
        _ano = abt["ano_producao_inicial"] if "ano_producao_inicial" in abt.columns else abt["ano_ref"]
        if "ano_producao_inicial" in abt.columns:
            _ano = abt["ano_producao_inicial"].fillna(abt["ano_ref"])
        abt = abt[(_ano >= lo) & (_ano <= hi)].copy()
    if apenas_classificadas:
        abt = abt[abt["grau_automatismo"].notna()].copy()
    return abt
