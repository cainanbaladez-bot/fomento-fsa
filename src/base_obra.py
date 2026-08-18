# -*- coding: utf-8 -*-
"""
base_obra.py — base obra-nível do projeto: RIDAB PRIMÁRIO + legado TAPA-BURACO.

Princípio (decisão Cainan 2026-06-04): a fonte primária é o RIDAB (data/ridab_cleaned,
via src.fontes). O legado (painel_exato/base_nivel_obra) entra só como TAPA-BURACO onde o
RIDAB não casa de forma limpa — comprovado na exploração:
  - FSA-contrato ↔ CPB casa só ~60% por título no RIDAB (fsa_atas_resultados quase vazio);
  - renúncia ↔ obra não tem CPB (só título/CNPJ);
  - soft power (crítica, citações, IMDb, wiki) NÃO existe no RIDAB.
Esses campos vêm do legado, já casados, com proveniência marcada.

RIDAB-nativo aqui (limpo, por CPB):
  - PÚBLICO observado → bilheteria_por_filme_ano (chave cpb_roe);
  - BILHETERIA em R$ → público × PMI (preco_ingresso.pmi_real_2024, real base 2024).
    Obs.: o RIDAB não traz receita de bilheteria em R$; só público (ingressos) + preço médio.
    Logo a bilheteria R$ RIDAB é PÚBLICO × PREÇO MÉDIO — uma estimativa observada, sinalizada.

Uso:   from src.base_obra import build ;  df = build()
Rodar: .\.venv\Scripts\python.exe src\base_obra.py   (imprime cobertura + comparação c/ legado)
"""
import re
import sys
from pathlib import Path
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
import config as C            # noqa: E402
from src import fontes as F   # noqa: E402

# Legado vendorizado (tapa-buraco): universo FSA-cinema + FSA/renúncia casados + soft power
PAINEL = _ROOT / "painel_exato" / "resultados" / "datasets" / "base_nivel_obra.csv"


def _kcpb(s) -> str:
    """Normaliza CPB/cpb_roe para chave de join (só alfanumérico, maiúsculo)."""
    return re.sub(r"[^0-9A-Za-z]", "", str(s)).upper()


def bilheteria_ridab() -> pd.DataFrame:
    """Bilheteria 100% RIDAB por CPB: público observado e R$ = Σ_ano (público × PMI_ano)."""
    bf = F.cl_local("bilheteria_por_filme_ano")[["cpb_roe", "ano", "publico"]].copy()
    bf["publico"] = pd.to_numeric(bf["publico"], errors="coerce").fillna(0)
    bf["ano"] = pd.to_numeric(bf["ano"], errors="coerce")
    pmi = F.cl_local("preco_ingresso")[["ano", "pmi_real_2024"]].copy()
    pmi["ano"] = pd.to_numeric(pmi["ano"], errors="coerce")
    pmi["pmi_real_2024"] = pd.to_numeric(pmi["pmi_real_2024"], errors="coerce")
    bf = bf.merge(pmi, on="ano", how="left")
    bf["rs"] = bf["publico"] * bf["pmi_real_2024"]
    g = (bf.groupby("cpb_roe")
           .agg(publico_ridab=("publico", "sum"), bilheteria_ridab_rs=("rs", "sum"))
           .reset_index())
    g["_k"] = g["cpb_roe"].map(_kcpb)
    return g[["_k", "publico_ridab", "bilheteria_ridab_rs"]]


def build() -> pd.DataFrame:
    """Base obra-nível. Esqueleto legado (tapa-buraco) + bilheteria RIDAB sobreposta.
    Colunas-chave novas: publico_ridab, bilheteria_ridab_rs, bilheteria_rs, bilheteria_fonte."""
    o = pd.read_csv(PAINEL, sep=";", encoding="utf-8-sig")
    o["_k"] = o["CPB"].map(_kcpb)
    br = bilheteria_ridab()
    df = o.merge(br, on="_k", how="left")

    tem_ridab = df["bilheteria_ridab_rs"].notna() & (df["publico_ridab"].fillna(0) > 0)
    df["bilheteria_fonte"] = tem_ridab.map({True: "RIDAB (público×PMI)", False: "legado"})
    # valor usado: RIDAB onde casou; senão a bilheteria deflacionada do legado (tapa-buraco)
    _leg_bil = pd.to_numeric(df.get("bilheteria_deflac"), errors="coerce")
    df["bilheteria_rs"] = df["bilheteria_ridab_rs"].where(tem_ridab, _leg_bil)
    return df


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    df = build()
    cine = df[pd.to_numeric(df["investimento_fsa_deflac"], errors="coerce").fillna(0) > 0]
    cob = (df["bilheteria_fonte"] == "RIDAB (público×PMI)").mean()
    cob_c = (cine["bilheteria_fonte"] == "RIDAB (público×PMI)").mean()
    print("=" * 72)
    print("base_obra — RIDAB primário + legado tapa-buraco")
    print("=" * 72)
    print(f"obras na base (legado, esqueleto): {len(df)} | FSA-cinema: {len(cine)}")
    print(f"bilheteria via RIDAB (público×PMI): geral {cob:.0%} | FSA-cinema {cob_c:.0%}"
          f"  (resto = tapa-buraco legado)")
    m = cine[cine["bilheteria_fonte"].str.startswith("RIDAB")].copy()
    m["_leg"] = pd.to_numeric(m["bilheteria_deflac"], errors="coerce")
    r, l = m["bilheteria_ridab_rs"].sum() / 1e6, m["_leg"].sum() / 1e6
    print(f"Σ bilheteria FSA-cinema c/ match — RIDAB público×PMI: R$ {r:,.0f} mi | "
          f"legado: R$ {l:,.0f} mi | razão {r / l:.2f}")
    print(f"Σ público FSA-cinema (RIDAB observado): {m['publico_ridab'].sum() / 1e6:,.1f} mi espectadores")
