# -*- coding: utf-8 -*-
"""
73_indicadores.py — NÚMEROS-ÂNCORA do ensaio, recalculados na regra de 2026-07-25
(dois universos + denominador de investimento público TOTAL) e comparados com os
números da versão anterior (régua "687 obras, receita zero entra, ÷ só FSA").

Não escreve texto: imprime o DIFF e grava outputs/bases/indicadores.json para os
builders (60/61/62/63) lerem em vez de hardcodar número.
"""
import os
import sys
import json
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASES = os.path.join(BASE, 'outputs', 'bases')

ob = pd.read_parquet(os.path.join(BASES, 'base_obras.parquet'))
ch = pd.read_parquet(os.path.join(BASES, 'base_chamadas.parquet'))
pr = pd.read_parquet(os.path.join(BASES, 'base_produtoras.parquet'))

apl = ob[ob.universo_aplicacao]
ret = ob[ob.universo_retorno]
fsa_apl = apl[apl.inv_fsa > 0]          # recorte FSA (comparável ao antigo 687)
fsa_ret = ret[ret.inv_fsa > 0]

G = {}

# ── Parte I · c1 ───────────────────────────────────────────────────────────────
G['obras_aplicacao'] = int(len(apl))
G['obras_retorno'] = int(len(ret))
G['obras_fsa_aplicacao'] = int(len(fsa_apl))
G['obras_fsa_retorno'] = int(len(fsa_ret))
G['empresas_aplicacao'] = int(len(pr))
G['empresas_fsa'] = int((pr.inv_fsa > 0).sum())

G['inv_total_retorno_mi'] = float(ret.inv_total.sum() / 1e6)
G['inv_fsa_retorno_mi'] = float(ret.inv_fsa.sum() / 1e6)
G['inv_renuncia_retorno_mi'] = float(ret.inv_renuncia.sum() / 1e6)
G['inv_total_aplicacao_mi'] = float(apl.inv_total.sum() / 1e6)
G['inv_fora_retorno_mi'] = float(apl[~apl.universo_retorno].inv_total.sum() / 1e6)
G['obras_fora_retorno'] = int((~apl.universo_retorno).sum())

G['receita_ref_mi'] = float(ret.receita_ref.sum() / 1e6)
G['bilheteria_obs_mi'] = float(ret.bilheteria_obs.sum() / 1e6)
G['janelas_crt_mi'] = float(ret.janelas_crt.sum() / 1e6)
G['pct_receita_estimada'] = float(100 * ret.janelas_crt.sum() / ret.receita_ref.sum())

G['retorno_dom'] = float(ret.receita_ref.sum() / ret.inv_total.sum())
G['retorno_dom_obs'] = float(ret.bilheteria_obs.sum() / ret.inv_total.sum())
G['retorno_dom_fsa_recorte'] = float(fsa_ret.receita_ref.sum() / fsa_ret.inv_total.sum())
G['taxa_estreia'] = float(len(ret) / len(apl))

G['publico_mi'] = float(ret.publico_domestico.sum() / 1e6)
G['sessoes_mi'] = float(ret.sessoes_total.sum() / 1e6)
G['cobertura_publico'] = float(100 * (ret.publico_domestico > 0).mean())

G['n_sinal_intl'] = int(ret.tem_intl.sum())
G['pct_sinal_intl'] = float(100 * ret.tem_intl.mean())
G['n_festivais'] = int((ret.pontuacao_festivais > 0).sum())
G['n_lumiere'] = int((ret.adm_eu_lumiere > 0).sum())
G['admissoes_europa_mi'] = float(ret.adm_eu_lumiere.sum() / 1e6)
G['n_vod'] = int((ret.vod_n_plataformas > 0).sum())

# ── Parte II · c2 / c3 / c4 ────────────────────────────────────────────────────
cat = ch.set_index('grupo')
for k, lab in [('dist', 'Bilheteria · Distribuidora'), ('prod', 'Bilheteria · Produtora'),
               ('fest', 'Festivais · Pontuação'), ('autofest', 'Automático Festivais'),
               ('autobil', 'Automático Bilheteria'), ('coprod', 'Coprodução Intl'),
               ('arranjos', 'Arranjos Regionais'), ('addon', 'Add-on FSA (Compl./Comerc.)')]:
    if lab in cat.index:
        r = cat.loc[lab]
        G[f'cat_{k}_ret_dom'] = float(r.retorno_dom)
        G[f'cat_{k}_ret_intl'] = float(r.retorno_intl_medio)
        G[f'cat_{k}_n'] = int(r.n_retorno)
        G[f'cat_{k}_estreia'] = float(r.taxa_estreia)
        G[f'cat_{k}_pct_intl'] = float(r.pct_sinal_intl)

for lab, key in [('FSA puro', 'fsa_puro'), ('Misto FSA+Renúncia', 'misto'),
                 ('Renúncia pura', 'renuncia_pura')]:
    g = ret[ret.instrumento == lab]
    ga = apl[apl.instrumento == lab]
    G[f'inst_{key}_n'] = int(len(g))
    G[f'inst_{key}_ret_dom'] = float(g.receita_ref.sum() / g.inv_total.sum())
    G[f'inst_{key}_pct_intl'] = float(100 * g.tem_intl.mean())
    G[f'inst_{key}_estreia'] = float(len(g) / len(ga)) if len(ga) else np.nan

# misto com FSA majoritário (>50% do investimento vindo do FSA)
mm = ret[(ret.instrumento == 'Misto FSA+Renúncia') & (ret.inv_fsa > ret.inv_renuncia)]
G['misto_fsa_maj_n'] = int(len(mm))
G['misto_fsa_maj_pct_intl'] = float(100 * mm.tem_intl.mean())
G['misto_fsa_maj_ret_dom'] = float(mm.receita_ref.sum() / mm.inv_total.sum())

# ── Parte III · c6 / c7 / c8 ───────────────────────────────────────────────────
G['produtoras_retorno_carteira'] = float(pr.receita_ref.sum() / pr.inv_total.sum())
G['produtoras_uma_obra_pct'] = float(100 * (pr.n_obras == 1).mean())
rec = pr[pr.n_obras > 1]
G['produtoras_recorrentes_share'] = float(100 * rec.inv_total.sum() / pr.inv_total.sum())
G['produtoras_mediana_inv'] = float(pr.inv_total.median())
G['produtoras_mediana_inv_anual'] = float(pr.inv_total.median() / 10)

# quintis de ticket — no recorte FSA, pelo APORTE DO FUNDO (a pergunta do c7 é
# sobre o ticket do FSA, não sobre o dinheiro público total da obra)
q = fsa_apl[fsa_apl.inv_fsa > 0].copy()
q['quintil'] = pd.qcut(q.inv_fsa, 5, labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
qq = q.groupby('quintil', observed=True).agg(
    n=('cpb', 'size'), ticket_med=('inv_fsa', 'median'),
    estreia=('universo_retorno', 'mean'),
    publico=('publico_domestico', 'sum'), inv=('inv_fsa', 'sum'))
qq['pub_por_mi'] = qq.publico / (qq.inv / 1e6)
G['quintil_q1_estreia'] = float(qq.loc['Q1', 'estreia'] * 100)
G['quintil_q5_estreia'] = float(qq.loc['Q5', 'estreia'] * 100)
G['quintil_q1_ticket'] = float(qq.loc['Q1', 'ticket_med'])
G['quintil_q5_ticket'] = float(qq.loc['Q5', 'ticket_med'])
G['quintil_q1_pub_por_mi'] = float(qq.loc['Q1', 'pub_por_mi'])
G['quintil_q5_pub_por_mi'] = float(qq.loc['Q5', 'pub_por_mi'])
G['quintil_razao_conversao'] = float(qq.loc['Q5', 'pub_por_mi'] / qq.loc['Q1', 'pub_por_mi'])


def gini(x):
    x = np.sort(np.asarray(x, float))
    k = len(x)
    return (2 * np.sum(np.arange(1, k + 1) * x) / (k * x.sum())) - (k + 1) / k \
        if x.sum() else np.nan


G['gini_inv_produtora'] = float(gini(pr.inv_total))
# c8 fala do FSA por produtora — mantém a população do fundo p/ comparabilidade
prf = pr[pr.inv_fsa > 0]
G['gini_fsa_produtora'] = float(gini(prf.inv_fsa))
G['gini_bilheteria_obra'] = float(gini(ret[ret.bilheteria_obs > 0].bilheteria_obs))
G['top10_share_fsa'] = float(100 * prf.nlargest(10, 'inv_fsa').inv_fsa.sum()
                             / prf.inv_fsa.sum())
G['top10_share'] = float(100 * pr.nlargest(10, 'inv_total').inv_total.sum()
                         / pr.inv_total.sum())
d1 = prf.nlargest(max(1, len(prf) // 10), 'inv_fsa').inv_fsa.sum()
G['decil_superior_share_fsa'] = float(100 * d1 / prf.inv_fsa.sum())
G['decil_superior_share'] = float(
    100 * pr.nlargest(max(1, len(pr) // 10), 'inv_total').inv_total.sum()
    / pr.inv_total.sum())
uf = apl[apl.uf != ''].groupby('uf').inv_total.sum()
uf_fsa = fsa_apl[fsa_apl.uf != ''].groupby('uf').inv_fsa.sum()
G['rj_sp_share'] = float(100 * uf.reindex(['RJ', 'SP']).fillna(0).sum() / uf.sum())
G['rj_sp_share_fsa'] = float(100 * uf_fsa.reindex(['RJ', 'SP']).fillna(0).sum()
                             / uf_fsa.sum())
G['cobertura_uf'] = float(100 * (apl.uf != '').mean())

# ── Parte III · c5 concentração por decil, c6 escala e renovação ──────────────
# Números que o texto das perguntas 5 e 6 cita e que antes só existiam na redação.
# Todos saem das bases canônicas; nenhum é digitado à mão.
_pr = pr.sort_values('inv_total', ascending=False).reset_index(drop=True)
_n = len(_pr)
_ndec = max(1, _n // 10)
G['grupos_carteira'] = int(_n)
G['decil_sup_n'] = int(_ndec)
G['decil_sup_share'] = float(100 * _pr.head(_ndec).inv_total.sum() / _pr.inv_total.sum())
G['metade_baixo_n'] = int(_n - _n // 2)
G['metade_baixo_share'] = float(
    100 * _pr.tail(_n - _n // 2).inv_total.sum() / _pr.inv_total.sum())
_dec = [_pr.iloc[i] for i in np.array_split(np.arange(_n), 10)]
G['decil1_media_mi'] = float(_dec[0].inv_total.mean() / 1e6)
G['decil2_media_mi'] = float(_dec[1].inv_total.mean() / 1e6)
G['decil10_media_mil'] = float(_dec[-1].inv_total.mean() / 1e3)
G['oitenta_pct_share'] = float(
    100 * _pr.tail(_n - 2 * _ndec).inv_total.sum() / _pr.inv_total.sum())

# ritmo das empresas (universo de retorno — obra que chegou à sala)
_gr = ret.groupby('cnpj_produtora').cpb.nunique()
G['grupos_retorno'] = int(len(_gr))
G['grupos_uma_obra'] = int((_gr == 1).sum())
G['grupos_3mais'] = int((_gr >= 3).sum())
G['grupos_ritmo_anual'] = int((_gr >= 10).sum())
G['ritmo_mediano_decada'] = float(_gr.median())
G['obras_ano_media'] = float(len(ret) / 10)
G['ticket_medio_obra_mi'] = float(ret.inv_total.mean() / 1e6)
G['divisao_igual_anual_mil'] = float(pr.inv_total.sum() / max(1, len(_gr)) / 10 / 1e3)

# capacidade de carga: piso por obra, ritmo e renovação (recorte FSA-cinema)
_f = apl[apl.inv_fsa > 0].copy()
G['obras_fsa_cinema'] = int(len(_f))
G['obras_fsa_ano'] = float(len(_f) / 10)
G['ticket_fsa_mediano_mi'] = float(_f.inv_fsa.median() / 1e6)
for _lo, _hi, _tag in [(0, 1e6, 'ate1mi'), (1e6, 2e6, '1a2mi'), (2e6, 3e6, '2a3mi'),
                       (3e6, 5e6, '3a5mi'), (5e6, 1e12, 'mais5mi')]:
    _s = _f[(_f.inv_fsa > _lo) & (_f.inv_fsa <= _hi)]
    if len(_s):
        G[f'piso_{_tag}_n'] = int(len(_s))
        G[f'piso_{_tag}_estreia'] = float(100 * (_s.bilheteria_obs.fillna(0) > 0).mean())
        G[f'piso_{_tag}_publico_med'] = float(_s.publico_domestico.median())

_at = pr[pr.n_obras_recorte > 0] if 'n_obras_recorte' in pr.columns else pr
G['empresas_periodo'] = int(len(_at))
G['empresas_ritmo5'] = int((_at.n_obras_recorte >= 5).sum())     if 'n_obras_recorte' in _at.columns else 0
_nov = _at[_at.ano_primeira >= 2014] if 'ano_primeira' in _at.columns else _at.iloc[:0]
G['entrantes_periodo'] = int(len(_nov))
G['entrantes_ano'] = float(len(_nov) / 10)
G['entrantes_repetiram'] = int((_nov.n_obras_recorte >= 2).sum())     if 'n_obras_recorte' in _nov.columns else 0
G['entrantes_sobrevivencia_pct'] = float(
    100 * G['entrantes_repetiram'] / G['entrantes_periodo']) if G['entrantes_periodo'] else 0.0

# teto de mercado: quanto a sala brasileira já absorve
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src import fontes as F
    _bi = F.cl_local('bilheteria_por_filme_ano')
    _br = _bi[_bi.cpb_roe.astype(str).str.startswith('B')]
    _br = _br[(_br.ano >= 2014) & (_br.ano <= 2023)]
    _tot = _bi[(_bi.ano >= 2014) & (_bi.ano <= 2023)]
    G['filmes_br_ano'] = float(_br.groupby('ano').cpb_roe.nunique().median())
    _pf = _br.groupby('cpb_roe').publico.sum()
    G['filmes_br_abaixo_10k_pct'] = float(100 * (_pf < 10000).mean())
    G['filmes_br_acima_100k_pct'] = float(100 * (_pf > 100000).mean())
    G['share_publico_br'] = float(100 * _br.publico.sum() / _tot.publico.sum())
except Exception as _e:                                              # pragma: no cover
    print('  ! teto de mercado não calculado:', _e)

# ── DIFF com a régua anterior ──────────────────────────────────────────────────
ANTIGO = {
    'obras (régua principal)': (687, G['obras_retorno']),
    'empresas': (445, G['empresas_aplicacao']),
    'investimento na conta (R$ mi)': (1925, G['inv_total_retorno_mi']),
    '  dos quais FSA (R$ mi)': (1119, G['inv_fsa_retorno_mi']),
    'receita de referência (R$ mi)': (614, G['receita_ref_mi']),
    '  bilheteria observada (R$ mi)': (528, G['bilheteria_obs_mi']),
    '  janelas CRT (R$ mi)': (86, G['janelas_crt_mi']),
    'RETORNO DOMÉSTICO': (0.55, G['retorno_dom']),
    '  só observado': (0.47, G['retorno_dom_obs']),
    'público (mi)': (26.6, G['publico_mi']),
    'sinal internacional (nº obras)': (157, G['n_sinal_intl']),
    'sinal internacional (%)': (23, G['pct_sinal_intl']),
    '  em festivais': (146, G['n_festivais']),
    '  com bilheteria na Europa': (41, G['n_lumiere']),
    '  em VOD': (32, G['n_vod']),
    'cat. Bilheteria·Distribuidora — dom': (0.80, G['cat_dist_ret_dom']),
    'cat. Bilheteria·Distribuidora — intl': (3.9, G['cat_dist_ret_intl']),
    'cat. Bilheteria·Produtora — dom': (0.43, G['cat_prod_ret_dom']),
    'cat. Festivais·Pontuação — dom': (0.02, G['cat_fest_ret_dom']),
    'cat. Festivais·Pontuação — intl': (3.8, G['cat_fest_ret_intl']),
    'cat. Automático Festivais — intl': (7.1, G['cat_autofest_ret_intl']),
    'instr. FSA puro — dom': (0.10, G['inst_fsa_puro_ret_dom']),
    'instr. Misto — dom': (0.38, G['inst_misto_ret_dom']),
    'instr. Renúncia pura — dom': (0.74, G['inst_renuncia_pura_ret_dom']),
    'instr. Renúncia pura — % intl': (8, G['inst_renuncia_pura_pct_intl']),
    'instr. Misto FSA-maj — % intl': (29, G['misto_fsa_maj_pct_intl']),
    'quintil inferior — % estreia': (32, G['quintil_q1_estreia']),
    'quintil superior — % estreia': (97, G['quintil_q5_estreia']),
    'conversão público Q5/Q1 (×)': (4.0, G['quintil_razao_conversao']),
    'Gini do FSA por produtora': (0.58, G['gini_fsa_produtora']),
    'Gini da bilheteria por obra': (0.92, G['gini_bilheteria_obra']),
    'top 10 produtoras (% do FSA)': (15, G['top10_share_fsa']),
    'décimo superior (% do FSA)': (41, G['decil_superior_share_fsa']),
    'RJ+SP (% do FSA)': (60, G['rj_sp_share_fsa']),
    'produtoras com 1 obra (%)': (70, G['produtoras_uma_obra_pct']),
    'recorrentes (% do dinheiro)': (62, G['produtoras_recorrentes_share']),
}

print('=' * 86)
print('DIFF DOS NÚMEROS-ÂNCORA  ·  régua antiga → régua nova (dois universos, inv. total)')
print('=' * 86)
print(f'{"indicador":<40} {"antes":>12} {"agora":>12}   {"variação":>12}')
print('-' * 86)
for k, (velho, novo) in ANTIGO.items():
    var = '' if velho in (None, 0) else f'{(novo/velho - 1)*100:+.0f}%'
    fmt = '.2f' if abs(novo) < 20 else ',.0f'
    print(f'{k:<40} {velho:>12} {novo:>12{fmt}}   {var:>12}')

print('\n' + '=' * 86)
print('NOVOS NÚMEROS DA REGRA (não existiam na versão anterior)')
print('=' * 86)
print(f'  universo de aplicação          {G["obras_aplicacao"]} obras · '
      f'R$ {G["inv_total_aplicacao_mi"]:,.0f} mi')
print(f'  universo de retorno            {G["obras_retorno"]} obras · '
      f'R$ {G["inv_total_retorno_mi"]:,.0f} mi ({G["taxa_estreia"]*100:.0f}% de estreia)')
print(f'  fora do retorno (sem renda)    {G["obras_fora_retorno"]} obras · '
      f'R$ {G["inv_fora_retorno_mi"]:,.0f} mi aplicados sem renda encontrada')
print(f'  recorte FSA no universo ret.   {G["obras_fsa_retorno"]} obras · '
      f'retorno {G["retorno_dom_fsa_recorte"]:.2f}')
print(f'  retorno de carteira produtoras {G["produtoras_retorno_carteira"]:.2f} '
      f'({G["empresas_aplicacao"]} empresas)')

with open(os.path.join(BASES, 'indicadores.json'), 'w', encoding='utf-8') as f:
    json.dump(G, f, ensure_ascii=False, indent=1)
print(f'\nSalvo: outputs/bases/indicadores.json ({len(G)} chaves)')
