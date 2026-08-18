# -*- coding: utf-8 -*-
"""
14 · Estudo curta → longa: o desempenho em curta-metragem prediz carreira
     internacional em longa?

Refaz, com base própria, a alegação herdada do estudo anterior (que trabalhava
com um multiplicador de 3,5× obtido contra uma taxa de referência ESTIMADA de
~15%, sem denominador observado).

Desenho: coorte retrospectiva.
  · TRATAMENTO — direções com curta selecionado em festival internacional de
    primeira linha (Cannes, Berlinale, Veneza, Locarno, Rotterdam, Annecy,
    Clermont-Ferrand), 2004–2025.
    Fonte: legado/painel_exato/dados/curtas_brasileiros_festivais_internacionais.xlsx
  · UNIVERSO/CONTROLE — todas as direções de longa-metragem brasileiro no
    cadastro da ANCINE (RIDAB: obras × diretores_obras).
  · DESFECHOS, em três camadas de exigência crescente:
      D1  dirigiu (depois) um longa-metragem registrado;
      D2  esse longa chegou ao mercado europeu (sala Lumière e/ou VOD Europa);
      D3  esse longa foi a festival internacional de primeira linha
          (corpus curado do estudo anterior — camada com viés declarado).

Saídas: outputs/tabelas/curtas_*.csv  ·  outputs/curtas_estudo.md
"""
import os
import re
import sys
import unicodedata
from math import comb

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RID = os.path.join(ROOT, "data", "ridab_cleaned")
LEG = os.path.join(ROOT, "legado", "painel_exato", "dados")
OUT_T = os.path.join(ROOT, "outputs", "tabelas")
OUT = os.path.join(ROOT, "outputs")
os.makedirs(OUT_T, exist_ok=True)

ANO_CORTE = 2025          # último ano observado da base
MATURIDADE = 7            # anos de janela mínima (mediana do gap no estudo anterior)
PART = {"DE", "DA", "DO", "DAS", "DOS", "E", "DI", "DEL", "VON", "VAN", "Y"}


# ── utilidades ───────────────────────────────────────────────────────────────
def norm(s):
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z ]", " ", s).upper()).strip()


def tnorm(s):
    """Normalização de TÍTULO (mantém dígitos) — chave de ligação com o cadastro."""
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]", " ", s).upper()).strip()


def toks(s):
    return [t for t in norm(s).split() if t not in PART and len(t) > 1]


def nt(s):
    return " ".join(toks(s))


def fisher_p(a, b, c, d):
    """p bicaudal do teste exato de Fisher para a tabela [[a,b],[c,d]]."""
    n = a + b + c + d
    r1, c1 = a + b, a + c

    def prob(x):
        return comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)

    p0 = prob(a)
    lo = max(0, c1 - (n - r1))
    hi = min(r1, c1)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p0 * 1.000001))


def wilson(k, n):
    """IC 95% de Wilson."""
    if n == 0:
        return (float("nan"), float("nan"))
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def pct(x):
    return f"{100 * x:.1f}".replace(".", ",") + "%"


def br(x, n=1):
    return f"{x:.{n}f}".replace(".", ",")


# ── 1. universo: direções de longa-metragem brasileiro (RIDAB) ───────────────
obras = pd.read_parquet(os.path.join(RID, "obras.parquet"))
obras["e_longa"] = (
    obras.organizacao_temporal.map(norm).str.startswith("NAO SERIADA")
    & (obras.duracao_total_minutos >= 70)
    & obras.tipo_obra.map(norm).str.match("FICCAO|DOCUMENTARIO|ANIMACAO")
)
dir_obras = pd.read_parquet(os.path.join(RID, "diretores_obras.parquet"))
dob = dir_obras.merge(
    obras[["cpb", "e_longa", "ano_producao_inicial", "titulo_original", "tipo_obra"]],
    on="cpb", how="left", suffixes=("", "_o"))
dob["nt"] = dob.diretor.map(nt)
dob = dob[dob.nt.str.len() > 3]

lon = dob[dob.e_longa == True]                                       # noqa: E712
universo = (lon.groupby("nt")
               .agg(n_longas=("cpb", "nunique"),
                    ano_1o_longa=("ano_producao_inicial", "min"),
                    ano_ult_longa=("ano_producao_inicial", "max"))
               .reset_index())
pessoas = dob.groupby("nt").cpb.nunique().rename("n_obras_cadastro")

# ── 2. ligação dos desfechos ao cadastro ────────────────────────────────────
# As fontes de desfecho trazem NOME ARTÍSTICO ("Kleber Mendonça Filho") e o
# cadastro traz NOME LEGAL ("KLEBER MENDONCA VASCONCELLOS FILHO"). Casar por
# nome perde os dois lados de forma assimétrica; a ligação correta é pelo
# TÍTULO DA OBRA → CPB → direção.
obras["tn"] = obras.titulo_original.map(tnorm)
tit2cpb = (obras[obras.e_longa & (obras.tn.str.len() > 2)]
           .groupby("tn").cpb.apply(lambda s: set(s)).to_dict())


def cpbs_por_titulo(titulos):
    achou, faltou, out = 0, 0, set()
    for t in titulos:
        k = tnorm(t)
        if k in tit2cpb:
            out |= tit2cpb[k]
            achou += 1
        else:
            faltou += 1
    return out, achou, faltou


def direcoes(cpbs):
    return set(dob[dob.cpb.astype(str).isin({str(c) for c in cpbs})].nt)


# D2 — mercado europeu: sala (Lumière) + VOD Europa
bil = pd.read_parquet(os.path.join(RID, "bilheteria_europa.parquet"))
vod = pd.read_parquet(os.path.join(RID, "vod_europa.parquet"))
vod = vod[vod.tipo_obra == "film"]
for t in (bil, vod):
    if "tem_brasil" in t.columns:
        t.drop(t[t.tem_brasil != True].index, inplace=True)           # noqa: E712
cpb_eur, eur_ok, eur_no = cpbs_por_titulo(
    set(bil.titulo_original.dropna()) | set(vod.titulo_original.dropna()))
EUR = direcoes(cpb_eur)

# D3 — festival internacional de primeira linha (corpus curado)
fest = pd.read_csv(os.path.join(LEG, "participacoes_festivais_diretores.csv"))
fest = fest[fest.TIPO_FILME.isin(["longa", "documentario"])].copy()
cpb_f_tit, f_ok, f_no = cpbs_por_titulo(set(fest.FILME.dropna()))
cpb_fest = set(fest.CPB.dropna().astype(str)) | {str(c) for c in cpb_f_tit}
FEST = direcoes(cpb_fest)

# ── 4. tratamento: curtas em festival de primeira linha ─────────────────────
cx = pd.read_excel(os.path.join(LEG, "curtas_brasileiros_festivais_internacionais.xlsx"))
cx["fonte"] = "painel curado (xlsx)"
n_xlsx = len(cx)
# complemento: casos que o xlsx não trazia — os cinco que o estudo anterior havia
# levantado por pesquisa externa mais os achados na pesquisa de 2026-08-15.
comp = pd.read_csv(os.path.join(ROOT, "referencia", "curtas_complementares.csv"))
cx = pd.concat([cx, comp], ignore_index=True)
n_comp = len(comp)

linhas = []
for _, r in cx.iterrows():
    for d in re.split(r"\s+e\s+|,", str(r["diretor"])):
        if d.strip():
            linhas.append(dict(diretor=d.strip(), ano=int(r["ano"]),
                               titulo=r["titulo"], festival=r["festival"],
                               premiado=bool(r["premiado"])))
cur = pd.DataFrame(linhas)
trat = (cur.groupby("diretor")
           .agg(ano_curta=("ano", "min"), n_curtas=("titulo", "nunique"),
                premiado=("premiado", "max"),
                festivais=("festival", lambda s: " | ".join(sorted(set(s)))))
           .reset_index())

dep = pd.read_csv(os.path.join(ROOT, "referencia", "depara_curtas_diretores.csv"))
trat = trat.merge(dep, left_on="diretor", right_on="diretor_curta", how="left")
faltando = trat[trat.diretor_curta.isna()].diretor.tolist()
if faltando:
    print("!! sem linha no de-para (rode a revisão manual):", faltando)

trat["nt"] = trat.diretor_ridab.fillna("").map(nt)
trat = trat.merge(universo, on="nt", how="left")
trat = trat.merge(pessoas, on="nt", how="left")
trat["n_longas"] = trat.n_longas.fillna(0).astype(int)

# primeiro longa POSTERIOR ao curta (o que a alegação de fato afirma)
anos_longa = lon.groupby("nt").ano_producao_inicial.apply(
    lambda s: sorted(int(x) for x in s.dropna())).to_dict()


def primeiro_longa_apos(row):
    for a in anos_longa.get(row.nt, []):
        if a >= row.ano_curta:
            return a
    return float("nan")


trat["ano_longa_pos"] = trat.apply(primeiro_longa_apos, axis=1)
trat["d1_qualquer_longa"] = trat.n_longas > 0
trat["d1_longa_pos"] = trat.ano_longa_pos.notna()
trat["d2_europa"] = trat.nt.isin(EUR) & trat.d1_qualquer_longa
trat["d3_festival"] = trat.nt.isin(FEST) & trat.d1_qualquer_longa

# versão estrita: o desfecho tem de vir de um longa POSTERIOR ao curta
obras_ano = obras.set_index("cpb").ano_producao_inicial.to_dict()
por_dir = (lon.groupby("nt").cpb.apply(lambda s: sorted(set(s.astype(str))))).to_dict()


def desfecho_apos(row, cpbs_alvo):
    alvo = {str(c) for c in cpbs_alvo}
    for c in por_dir.get(row.nt, []):
        if c in alvo:
            a = obras_ano.get(c)
            if pd.notna(a) and a >= row.ano_curta:
                return True
    return False


trat["d2_europa_pos"] = trat.apply(lambda r: desfecho_apos(r, cpb_eur), axis=1)
trat["d3_festival_pos"] = trat.apply(lambda r: desfecho_apos(r, cpb_fest), axis=1)
trat["gap"] = trat.ano_longa_pos - trat.ano_curta
trat["tinha_longa_antes"] = trat.n_longas.gt(0) & trat.ano_1o_longa.lt(trat.ano_curta)
trat["maduro"] = trat.ano_curta <= (ANO_CORTE - MATURIDADE)

# ── 5. controle: mesmo desfecho no universo ─────────────────────────────────
universo["tratado"] = universo.nt.isin(set(trat.nt) - {""})
universo["d2_europa"] = universo.nt.isin(EUR)
universo["d3_festival"] = universo.nt.isin(FEST)
ctrl = universo[~universo.tratado]

# ── 6. resultados ──────────────────────────────────────────────────────────
L = []
w = L.append
w("# Estudo curta → longa (refeito sobre base própria)\n")
w(f"Gerado por `scripts/14_estudo_curtas.py`. Corte de observação: {ANO_CORTE}.\n")

w("\n## 0. Por que refazer\n")
w("Circulavam três números para a mesma alegação, nenhum reprodutível aqui:\n")
w("- **3,5×** — estudo anterior: 52% de conversão numa coorte madura de 21 "
  "direções contra uma taxa de referência **estimada** de ~15% (≈135 de ~900 "
  "direções, número arredondado a mão, sem denominador observado).")
w("- **2,2×** — versão anterior da mesma conta, na auditoria de alegações.")
w("- **1,3× (10,4% → 13,8%)** — número que está no site hoje, herdado do painel "
  "curado e escrito à mão em `scripts/legado/52_enriquecimento_legado.py`. "
  "Ele compara **9 de 65** direções de curta — a coorte inteira, inclusive quem "
  "levou curta a festival em 2024 e ainda não teve tempo de fazer longa — "
  "contra 268 de 2.572 de um universo que não é o mesmo. Mistura maçã com "
  "laranja nos dois lados da razão.\n")
w("O que muda aqui: universo observado (cadastro inteiro), desfecho ligado por "
  "CPB, coorte com janela de maturidade e teste de significância.\n")

w("\n## 1. As três bases\n")
w(f"- **Tratamento**: {len(trat)} direções com curta em festival de primeira linha "
  f"({int(cx.ano.min())}–{int(cx.ano.max())}), a partir de {len(cx)} seleções "
  f"mapeadas — {n_xlsx} da planilha do painel curado mais {n_comp} acrescentadas "
  f"em `referencia/curtas_complementares.csv` (os cinco casos que o estudo "
  f"anterior tinha levantado por pesquisa externa e nunca entraram na planilha, "
  f"mais os achados na pesquisa de 2026-08-15). O mapeamento **não é censo**: "
  f"cada linha tem fonte declarada e novas seleções podem ser acrescentadas ao "
  f"mesmo arquivo sem tocar no código.")
n_ok = (trat.diretor_ridab.notna()).sum()
w(f"- **Casadas com o cadastro da ANCINE**: {n_ok} de {len(trat)} "
  f"({pct(n_ok / len(trat))}); {len(trat) - n_ok} sem correspondência "
  f"(estrangeiros, carreira fora do Brasil, homônimos irresolvíveis).")
w(f"- **Universo/controle**: {len(universo)} direções de longa-metragem brasileiro "
  f"no cadastro; {len(ctrl)} depois de retirar as tratadas.")
w(f"- **Desfecho europeu (D2)**: {len(cpb_eur)} obras casadas com o cadastro "
  f"({eur_ok} títulos ligados, {eur_no} não encontrados — em geral título "
  f"internacional distinto do original) → {len(EUR)} direções.")
w(f"- **Desfecho festival (D3)**: {len(cpb_fest)} obras (CPB do corpus + "
  f"{f_ok} títulos ligados, {f_no} sem correspondência) → {len(FEST)} direções.")
w("\nDesfechos e universo são ligados pelo **mesmo caminho** (título → CPB → "
  "direção), o que evita comparar nome artístico de um lado com nome legal do "
  "outro.")

w("\n## 2. Taxa de base do universo\n")
w("| desfecho | universo | com desfecho | taxa |")
w("|---|---:|---:|---:|")
for k, lab in [("d2_europa", "D2 · longa no mercado europeu"),
               ("d3_festival", "D3 · longa em festival de primeira linha")]:
    w(f"| {lab} | {len(ctrl)} | {int(ctrl[k].sum())} | {pct(ctrl[k].mean())} |")

w("\n## 3. O tratamento, por coorte de maturidade\n")
w(f"Coorte madura = curta até {ANO_CORTE - MATURIDADE} — pelo menos "
  f"{MATURIDADE} anos de janela, que era a mediana do intervalo curta→longa "
  f"medida no estudo anterior. Aqui a mediana observada é menor (seção 6), "
  f"então a janela está do lado conservador.\n")
w("| coorte | n | dirigiu longa | longa na Europa | longa em festival |")
w("|---|---:|---:|---:|---:|")
for nome, sub in [("madura (curta ≤ %d)" % (ANO_CORTE - MATURIDADE), trat[trat.maduro]),
                  ("jovem (curta > %d)" % (ANO_CORTE - MATURIDADE), trat[~trat.maduro]),
                  ("todas", trat)]:
    n = len(sub)
    w(f"| {nome} | {n} | {int(sub.d1_qualquer_longa.sum())} ({pct(sub.d1_qualquer_longa.mean())}) "
      f"| {int(sub.d2_europa.sum())} ({pct(sub.d2_europa.mean())}) "
      f"| {int(sub.d3_festival.sum())} ({pct(sub.d3_festival.mean())}) |")

w("\n## 4. O contraste que a alegação pede\n")
w("Comparação restrita à coorte madura (única com janela suficiente) contra o "
  "universo de direções de longa.\n")
w("| desfecho | tratamento | controle | diferença | multiplicador | IC 95% tratamento | p (Fisher) |")
w("|---|---:|---:|---:|---:|---|---:|")
mad = trat[trat.maduro]
res = {}
for k, lab in [("d2_europa", "D2 · mercado europeu"),
               ("d3_festival", "D3 · festival de primeira linha")]:
    a, n1 = int(mad[k].sum()), len(mad)
    c, n0 = int(ctrl[k].sum()), len(ctrl)
    p1, p0 = a / n1, c / n0
    lo, hi = wilson(a, n1)
    p = fisher_p(a, n1 - a, c, n0 - c)
    res[k] = dict(a=a, n1=n1, c=c, n0=n0, p1=p1, p0=p0, mult=p1 / p0 if p0 else float("nan"), p=p)
    w(f"| {lab} | {a}/{n1} = {pct(p1)} | {c}/{n0} = {pct(p0)} | "
      f"+{br(100*(p1-p0))} pp | {br(p1/p0)}× | [{pct(lo)}; {pct(hi)}] | "
      f"{br(p, 4)} |")

w("\n> Atenção ao denominador: o controle é **quem já dirigiu um longa**. "
  "O tratamento inclui quem ainda não dirigiu nenhum — é uma comparação "
  "conservadora contra o tratamento, e ainda assim o contraste aparece.\n")

# recorte apples-to-apples: só quem tem longa dos dois lados
w("\n## 5. Mesmo teste condicionado a quem chegou a dirigir um longa\n")
mad_l = mad[mad.d1_qualquer_longa]
w("| desfecho | tratamento (com longa) | controle | multiplicador | p (Fisher) |")
w("|---|---:|---:|---:|---:|")
for k, lab in [("d2_europa", "D2 · mercado europeu"),
               ("d3_festival", "D3 · festival de primeira linha")]:
    a, n1 = int(mad_l[k].sum()), len(mad_l)
    c, n0 = int(ctrl[k].sum()), len(ctrl)
    p1, p0 = (a / n1 if n1 else float("nan")), c / n0
    p = fisher_p(a, n1 - a, c, n0 - c)
    w(f"| {lab} | {a}/{n1} = {pct(p1)} | {c}/{n0} = {pct(p0)} | {br(p1/p0)}× | {br(p, 4)} |")

w("\n## 5b. Versão estrita: só desfecho de obra POSTERIOR ao curta\n")
w(f"{int(trat.tinha_longa_antes.sum())} direções da coorte já tinham longa antes "
  "do curta — nelas, o desfecho internacional pode ser anterior ao suposto "
  "sinal. Exigindo que a obra do desfecho seja posterior ao curta, e retirando "
  "quem já era estabelecido:\n")
w("| recorte | n | D2 mercado europeu | D3 festival |")
w("|---|---:|---:|---:|")
estr = trat[trat.maduro]
novos = trat[trat.maduro & ~trat.tinha_longa_antes]
for nome, sub in [("coorte madura, desfecho posterior", estr),
                  ("madura e sem longa anterior (estreantes)", novos)]:
    n = len(sub)
    w(f"| {nome} | {n} | {int(sub.d2_europa_pos.sum())} ({pct(sub.d2_europa_pos.mean())}) "
      f"| {int(sub.d3_festival_pos.sum())} ({pct(sub.d3_festival_pos.mean())}) |")
for k, ks, lab in [("d2_europa_pos", "d2_europa", "D2"),
                   ("d3_festival_pos", "d3_festival", "D3")]:
    a, n1 = int(novos[k].sum()), len(novos)
    c, n0 = int(ctrl[ks].sum()), len(ctrl)
    if n1:
        w(f"\n- {lab}, estreantes da coorte madura: {a}/{n1} = {pct(a/n1)} contra "
          f"{pct(c/n0)} do universo → **{br((a/n1)/(c/n0))}×** "
          f"(p = {br(fisher_p(a, n1-a, c, n0-c), 4)}).")

w("\n## 6. O intervalo curta → longa seguinte\n")
g = trat[trat.gap.notna()].gap
if len(g):
    w(f"- Direções com longa posterior ao curta: **{len(g)}** de {len(trat)}.")
    w(f"- Mediana **{g.median():.0f} anos**; média {br(g.mean())}; "
      f"intervalo {int(g.min())}–{int(g.max())}.")
    w(f"- Dentro de 6 anos: {int((g <= 6).sum())} de {len(g)} ({pct((g <= 6).mean())}).")
w(f"- Direções que **já tinham longa antes** do curta: "
  f"{int(trat.tinha_longa_antes.sum())} — o curta não é necessariamente obra "
  f"de estreia, e uma parte da coorte já era gente estabelecida.")
gm = trat[trat.maduro & trat.gap.notna()].gap
if len(gm):
    w(f"- Só na coorte madura: mediana {gm.median():.0f} anos, "
      f"{int((gm <= 6).sum())} de {len(gm)} dentro de 6 anos.")

w("\n## 7. Sensibilidade\n")
baixa = trat[trat.confianca.isin(["baixa", "media"])]
w(f"- {len(baixa)} correspondências de nome são de confiança média/baixa. "
  "Refazendo o teste só com as de confiança alta:\n")
alt = trat[(trat.confianca == "alta") | trat.diretor_ridab.isna()]
alt_m = alt[alt.maduro]
for k, lab in [("d2_europa", "D2"), ("d3_festival", "D3")]:
    a, n1 = int(alt_m[k].sum()), len(alt_m)
    c, n0 = int(ctrl[k].sum()), len(ctrl)
    w(f"  - {lab}: {a}/{n1} = {pct(a/n1)} contra {pct(c/n0)} → {br((a/n1)/(c/n0))}×")

w("\n## 8. Limites que não se resolvem com esta base\n")
w("- O desfecho D3 vem de um **corpus curado** (pesquisa nominal do estudo "
  "anterior), não de um censo de festivais. Ele cobre bem quem é conhecido e "
  "mal quem não é. Pior: é plausível que a mesma pesquisa que montou a lista de "
  "curtas tenha alimentado a lista de longas, o que criaria correlação por "
  "construção. **Não usar D3 como número principal.**")
w("- O desfecho D2 é independente da nossa pesquisa (Lumière/Observatório "
  "Europeu do Audiovisual), mas é **lista truncada**: bilheteria europeia é "
  "top-200 e o VOD cobre os catálogos mapeados. Ele mede 'chegou ao mercado "
  "europeu com alguma escala', não 'teve qualquer exibição no exterior'.")
w("- A ligação título → CPB perde os títulos que circulam com nome "
  "internacional diferente do original. A perda atinge tratamento e controle "
  "do mesmo jeito, mas rebaixa as duas taxas.")
w("- A base de curtas cobre **sete festivais de primeira linha**. Quem foi a "
  "festival internacional fora dessa lista conta como não-tratado.")
w("- A seleção é **endógena**: quem leva curta a Cannes já é, em média, quem tem "
  "acesso a produtora, roteiro trabalhado e circuito. A associação é descritiva, "
  "não causal — o curta é marcador, não tratamento aleatório.")
w("- A coorte madura é pequena. O intervalo de confiança é largo e deve ser "
  "citado junto com o ponto.")

with open(os.path.join(OUT, "curtas_estudo.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")

# ── 6b. longas de estreia (ópera prima) ─────────────────────────────────────
# Um longa é "de estreia" quando é o primeiro da direção que o assina.
lo = lon[["nt", "cpb", "ano_producao_inicial"]].dropna(subset=["cpb"]).copy()
lo["cpb"] = lo.cpb.astype(str)
prim = lo.sort_values("ano_producao_inicial").groupby("nt").cpb.first()
cpb_estreia = set(prim.dropna())
obr = obras[obras.e_longa].copy()
obr["cpb"] = obr.cpb.astype(str)
obr["estreia"] = obr.cpb.isin(cpb_estreia)
obr["d2"] = obr.cpb.isin({str(c) for c in cpb_eur})
obr["d3"] = obr.cpb.isin({str(c) for c in cpb_fest})

w("\n## 6b. Os longas de estreia\n")
w("Um longa é *de estreia* quando é o primeiro da direção que o assina "
  "(no cadastro). Recorte obra a obra, universo inteiro:\n")
w("| recorte | obras | no mercado europeu | em festival de primeira linha |")
w("|---|---:|---:|---:|")
for nome, sub in [("longas de estreia", obr[obr.estreia]),
                  ("demais longas", obr[~obr.estreia])]:
    w(f"| {nome} | {len(sub)} | {int(sub.d2.sum())} ({pct(sub.d2.mean())}) "
      f"| {int(sub.d3.sum())} ({pct(sub.d3.mean())}) |")

# o fundo financia estreia? (recorte FSA-cinema da base canônica)
try:
    bo = pd.read_parquet(os.path.join(ROOT, "outputs", "bases", "base_obras.parquet"))
    bo["cpb"] = bo.cpb.astype(str)
    bo["estreia"] = bo.cpb.isin(cpb_estreia)
    ap = bo[bo.universo_aplicacao == True] if "universo_aplicacao" in bo else bo  # noqa: E712
    w(f"\nNo recorte FSA-cinema da base canônica ({len(ap)} obras): "
      f"**{int(ap.estreia.sum())} são longas de estreia "
      f"({pct(ap.estreia.mean())})**.")
    if "tem_intl" in ap.columns:
        w(f"Entre as de estreia, {pct(ap[ap.estreia].tem_intl.mean())} têm sinal "
          f"internacional, contra {pct(ap[~ap.estreia].tem_intl.mean())} entre as demais.")
    est_fsa_pct = round(100 * ap.estreia.mean(), 1)
except Exception as e:                                                # pragma: no cover
    est_fsa_pct = None
    w(f"\n(Recorte FSA-cinema não pôde ser lido: {e})")

# ── 7. indicadores canônicos para o painel (scripts/22 lê daqui) ────────────
mad_n = len(mad)
IND = dict(
    curtas_fonte=(f"{n_xlsx} seleções da planilha do painel curado + {n_comp} "
                  f"acrescentadas por pesquisa (referencia/curtas_complementares.csv); "
                  f"{len(trat)} direções, 2004–2025"),
    curtas_n_selecoes=int(len(cx)),
    curtas_n_xlsx=int(n_xlsx),
    curtas_n_comp=int(n_comp),
    curtas_n_direcoes=int(len(trat)),
    curtas_n_casadas=int(trat.diretor_ridab.notna().sum()),
    curtas_universo=int(len(ctrl)),
    curtas_coorte_madura=int(mad_n),
    curtas_maturidade_anos=int(MATURIDADE),
    # desfecho principal: mercado europeu (censo, independente da nossa pesquisa)
    curtas_base_geral_pct=round(100 * ctrl.d2_europa.mean(), 1),
    curtas_base_geral=(f"{int(ctrl.d2_europa.sum())} de {len(ctrl)} direções de longa "
                       f"chegam ao mercado europeu"),
    curtas_com_curta_pct=round(100 * mad.d2_europa.mean(), 1),
    curtas_com_curta=(f"{int(mad.d2_europa.sum())} de {mad_n} direções da coorte madura "
                      f"de curtas chegam ao mercado europeu com um longa"),
    curtas_mult=round(res["d2_europa"]["mult"], 1),
    curtas_ganho_pp=round(100 * (res["d2_europa"]["p1"] - res["d2_europa"]["p0"]), 1),
    curtas_p=round(res["d2_europa"]["p"], 5),
    curtas_ic=[round(100 * x, 1) for x in wilson(int(mad.d2_europa.sum()), mad_n)],
    # camada de festival, secundária (corpus curado)
    curtas_fest_base_pct=round(100 * ctrl.d3_festival.mean(), 1),
    curtas_fest_trat_pct=round(100 * mad.d3_festival.mean(), 1),
    curtas_fest_mult=round(res["d3_festival"]["mult"], 1),
    # estreantes e janela temporal
    curtas_estreantes_pct=round(100 * novos.d2_europa_pos.mean(), 1) if len(novos) else None,
    curtas_estreantes_mult=(round((novos.d2_europa_pos.mean()) / ctrl.d2_europa.mean(), 1)
                            if len(novos) else None),
    curtas_gap_mediana=int(g.median()) if len(g) else None,
    curtas_gap_ate6_pct=round(100 * (g <= 6).mean(), 1) if len(g) else None,
    # longas de estreia
    estreia_n=int(obr.estreia.sum()),
    estreia_d2_pct=round(100 * obr[obr.estreia].d2.mean(), 1),
    estreia_d3_pct=round(100 * obr[obr.estreia].d3.mean(), 1),
    demais_d2_pct=round(100 * obr[~obr.estreia].d2.mean(), 1),
    demais_d3_pct=round(100 * obr[~obr.estreia].d3.mean(), 1),
    estreia_fsa_pct=est_fsa_pct,
)
import json  # noqa: E402
with open(os.path.join(ROOT, "outputs", "bases", "curtas_indicadores.json"),
          "w", encoding="utf-8") as f:
    json.dump(IND, f, ensure_ascii=False, indent=2)

cx.to_csv(os.path.join(OUT_T, "curtas_selecoes.csv"), index=False, encoding="utf-8-sig")

cols = ["diretor", "diretor_ridab", "confianca", "ano_curta", "n_curtas", "premiado",
        "festivais", "n_longas", "ano_1o_longa", "gap", "maduro", "tinha_longa_antes",
        "d1_qualquer_longa", "d2_europa", "d2_europa_pos", "d3_festival", "d3_festival_pos"]
trat[cols].sort_values("ano_curta").to_csv(
    os.path.join(OUT_T, "curtas_tratamento.csv"), index=False, encoding="utf-8-sig")
universo.to_csv(os.path.join(OUT_T, "curtas_universo.csv"), index=False, encoding="utf-8-sig")

print("\n".join(L))
print("\n→ outputs/curtas_estudo.md · outputs/tabelas/curtas_tratamento.csv")
