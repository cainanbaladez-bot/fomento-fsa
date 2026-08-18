"""
Loaders das fontes — acesso único e tipado às bases RIDAB e legado.

Toda análise deste projeto importa daqui. Nada de ler parquet/csv solto nos
scripts: garante proveniência rastreável e um único ponto de manutenção.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config as C  # noqa: E402


# ── RIDAB ────────────────────────────────────────────────────────────────────
def ridab(tabela: str) -> pd.DataFrame:
    """Lê uma tabela limpa do RIDAB pelo nome (com ou sem .parquet)."""
    nome = tabela if tabela.endswith(".parquet") else f"{tabela}.parquet"
    fp = C.RIDAB_CLEANED / nome
    if not fp.exists():
        raise FileNotFoundError(f"Tabela RIDAB não encontrada: {fp}")
    return pd.read_parquet(fp)


def cl_local(tabela: str) -> pd.DataFrame:
    """Lê do snapshot LOCAL (data/ridab_cleaned/) — projeto self-contained."""
    nome = tabela if tabela.endswith(".parquet") else f"{tabela}.parquet"
    return pd.read_parquet(C.DATA_CLEANED / nome)


def ridab_listar() -> list[str]:
    """Lista todas as tabelas .parquet limpas do RIDAB."""
    return sorted(p.stem for p in C.RIDAB_CLEANED.glob("*.parquet"))


def ridab_catalogo() -> dict:
    """Carrega o catálogo datasets.yaml (verdade dos metadados RIDAB)."""
    import yaml
    with open(C.RIDAB_CATALOG, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Legado (projeto fomento-audiovisual) ─────────────────────────────────────
def legado(rel: str) -> pd.DataFrame:
    """Lê um arquivo do projeto legado por caminho relativo à raiz dele.
    Ex.: legado('dados/critica_obras.csv')."""
    fp = C.LEGADO / rel
    if not fp.exists():
        raise FileNotFoundError(f"Arquivo legado não encontrado: {fp}")
    if fp.suffix.lower() == ".csv":
        return pd.read_csv(fp)
    if fp.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(fp)
    if fp.suffix.lower() == ".parquet":
        return pd.read_parquet(fp)
    raise ValueError(f"Formato não suportado: {fp.suffix}")


# ── Deflação (IPCA base 2024) ────────────────────────────────────────────────
def deflator() -> pd.DataFrame:
    """Série IPCA com fator base 2024, do RIDAB."""
    return ridab("deflator_ipca")


# ── Destino-mídia: segmento ANCINE → {Cinema, TV, Outros} ────────────────────
def destino_midia(segmento) -> str:
    """Mapeia o segmento de destinação da obra para a mídia final.
    Cinema = salas; TV = TV aberta/paga/VoD; Outros = roteiro/dev/demais objetos."""
    s = str(segmento).upper()
    if "SALAS DE EXIBI" in s:
        return "Cinema"
    if any(p in s for p in ["TV PAGA", "ASSINATURA", "TV ABERTA",
                            "RADIODIFUS", "POR DEMANDA", "VOD"]):
        return "TV"
    return "Outros"
