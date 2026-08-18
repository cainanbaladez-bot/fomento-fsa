# -*- coding: utf-8 -*-
"""
62_site_evidencias.py — SITE FINAL · PAINEL DE EVIDÊNCIAS (site/evidencias.html).

v3 (mudanças.docx + pedido estrutural): layout de PAINEL no modelo do painel legado
(curado pelo Cainan) — menu lateral fixo à esquerda com as 8 alegações agrupadas nas
4 partes; o conteúdo abre em ABAS (uma alegação por aba, roteamento por hash). Cada aba
começa com a abertura da alegação (como testei → figuras → veredito tipado → ressalvas +
"o que derrubaria" → reproduza no RIDAB) e incorpora as VISUALIZAÇÕES CURADAS do painel
legado — quadrantes, dispersões, rankings de filmes e produtoras — recalculadas com a
base atual (decisão registrada: migrar o desenho, recomputar os números).

Abas anexas: Visão geral · Soft power · Contra-alegações · Proposições · Glossário ·
Metodologia · Dados abertos. Gráficos desenham ao ativar a aba (Plotly local, 1×).
"""
import os
import re
import sys
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, 'scripts'))
import site_base as S                                                             # noqa: E402
from site_base import (br, style, DL, section, tabela, metodologia, repro,        # noqa: E402
                       stat, stat_grid)
from src import fontes as F                                                       # noqa: E402

T1 = os.path.join(BASE, 'data', 'legado', 'texto1_resultados')
T2 = os.path.join(BASE, 'data', 'legado', 'texto2_resultados')
T3 = os.path.join(BASE, 'data', 'legado', 'texto3_resultados')
T4 = os.path.join(BASE, 'data', 'legado', 'texto4_resultados')
EL = os.path.join(BASE, 'data', 'legado', 'enriquecimento_legado')
ENS = 'ensaio.html'
HFP = S.RIDAB_HF_PATH


def js(p, n):
    return json.load(open(os.path.join(p, n), encoding='utf-8'))


def cs(p, n, **kw):
    return pd.read_csv(os.path.join(p, n), sep=';', **kw)


# ════════════════════════ INSUMOS ════════════════════════
gnd, gni, gns = js(T1, 'grandes_numeros_dominico.json'), js(T1, 'grandes_numeros_internacional.json'), js(T1, 'grandes_numeros_softpower.json')
gnm = js(T1, 'grandes_numeros_macro.json')
gn2, gn3, gn4 = js(T2, 'grandes_numeros_texto2.json'), js(T3, 'grandes_numeros_texto3.json'), js(T4, 'grandes_numeros_texto4.json')
GL = js(EL, 'grandes_numeros_legado.json')
# curtas → longas: estudo REFEITO sobre base própria (scripts/14_estudo_curtas.py).
# Substitui os números herdados do painel curado (1,3× / 10,4%→13,8%), que
# comparavam a coorte inteira de curtas contra um universo diferente.
CU = json.load(open(os.path.join(BASE, 'outputs', 'bases', 'curtas_indicadores.json'), encoding='utf-8'))

dcat = cs(T1, 'dom_por_categoria.csv')
dinst = cs(T1, 'dom_por_instrumento.csv')
iinst = cs(T1, 'intl_por_instrumento.csv')
icat, itop = cs(T1, 'intl_por_categoria.csv'), cs(T1, 'intl_top_obras.csv')
scat, stop = cs(T1, 'softpower_por_categoria.csv'), cs(T1, 'softpower_top_obras.csv')
dg = cs(T1, 'dom_por_grupo_financiamento.csv')
mp = cs(T1, 'macro_panel_ano.csv')
dcrit = cs(T2, 'dim_criterio.csv').rename(columns={'criterio': 'k'}).set_index('k')
delo = cs(T2, 'dim_elo.csv').rename(columns={'elo': 'k'}).set_index('k')
M = cs(T2, 'matriz_combinacoes.csv')
QT = cs(T3, 'ticket_quintis.csv')
GA = cs(T3, 'gini_por_ano.csv')
LZ = cs(T3, 'lorenz_fsa.csv')
TT = cs(T3, 'tipologia_produtoras.csv').rename(columns={'tipo': 'k'})
PTO = cs(T3, 'produtoras_tipologia_obra.csv')          # por PRODUTORA: cnpj, fsa_mi, receita_crt_mi, tipo…
VA = cs(T4, 'fsa_aporte_por_ano.csv')
RA = cs(T4, 'regras_por_ano.csv')
MX = cs(T4, 'mecanismo_por_ano.csv', index_col=0)
AP = cs(T4, 'aporte_vs_producao.csv')
GF = cs(EL, 'grupos_financiamento.csv').rename(columns={'grupo': 'k'}).set_index('k')
# GF (legado, régua antiga) é recomputado da base canônica logo após ela carregar
# — ver bloco "GF canônico" abaixo. Fica aqui só pelas colunas de esquema.
PR = cs(EL, 'proliferacao_ano.csv')
abt = pd.read_parquet(os.path.join(BASE, 'outputs', 'tabelas', 'abt_obra_fsa.parquet'))

# ── BASE CANÔNICA (regra 2026-07-25: dois universos + investimento público total,
#    escopo cinema sem TV). O painel passa a medir a MESMA população do ensaio;
#    os nomes de coluna antigos são mantidos como alias para não reescrever as
#    81 figuras. `universo_retorno` é o filtro de tudo que é razão de retorno.
_OB = pd.read_parquet(os.path.join(BASE, 'outputs', 'bases', 'base_obras.parquet'))
_OB = _OB[_OB.universo_aplicacao].copy()
BNO = _OB.rename(columns={
    'cnpj_produtora': 'CNPJ_produtora',
    'inv_fsa': 'investimento_fsa_deflac',
    'inv_renuncia': 'investimento_renuncia_total_deflac',
    'inv_total': 'investimento_total_deflac',
    'bilheteria_obs': 'bilheteria_deflac',
    'receita_ref': 'receita_total_deflac',
    'roi_internacional_0_100': 'roi_internacional_0_100',
    'adm_eu_lumiere': 'adm_eu_lumiere',
})
BNO['CPB'] = BNO['cpb']

# ── GF canônico: os 4 grupos por composição do financiamento, recalculados na
#    regra nova (universo de RETORNO; retorno = receita ÷ investimento total) ──
_r = BNO[BNO.universo_retorno].copy()


def _g4(r):
    f, n = r.investimento_fsa_deflac > 0, r.investimento_renuncia_total_deflac > 0
    if f and not n:
        return 'FSA puro'
    if f and n:
        return 'FSA+Renúncia · FSA maj.' if r.investimento_fsa_deflac > r.investimento_renuncia_total_deflac \
            else 'FSA+Renúncia · Ren. maj.'
    return 'Renúncia pura'


# ── TIPOLOGIA DE PRODUTORAS — metodologia ORIGINAL, base canônica (2026-08-08) ─
# Substitui `texto3_resultados/tipologia_*.csv` (tipologia de 6 tipos que esta
# análise havia inventado, com sinal internacional BINÁRIO — inflava a "vitrine
# internacional" de 27 para 99 grupos, mediana do composto 5,7). Volta a valer a
# classificação escrita e testada do estudo anterior (fomento-audiovisual/
# scripts/02::_classificar_cluster), calculada em `scripts/12` e agora agregada
# por GRUPO ECONÔMICO. O heatmap "fusão desfecho × perfil de captação" foi
# REMOVIDO: validava a tipologia contra um K-means da própria análise, era
# circular. Denominador aqui é o dinheiro público total (FSA + renúncia), não só
# FSA — os nomes de coluna antigos ficam como alias para não reescrever as figuras.
_PR = pd.read_parquet(os.path.join(BASE, 'outputs', 'bases',
                                   'base_produtoras.parquet'))
PTO = _PR.rename(columns={'grupo': 'cnpj', 'perfil': 'tipo'}).assign(
    fsa_mi=lambda d: d.inv_total / 1e6,
    receita_crt_mi=lambda d: d.receita_ref / 1e6,
    pub_por_mi_fsa=lambda d: d.publico / (d.inv_total / 1e6).replace(0, np.nan),
    tem_intl=lambda d: d.n_sinal_intl > 0,
    pct_sala=lambda d: 100 * d.taxa_estreia,
    s16_perfil=lambda d: np.where(d.pre_2006, 'Anterior a 2006', 'Nasceu no ciclo do FSA'))
ORDEM_TIPO = ['Duplo Retorno', 'Retorno Doméstico', 'Retorno Internacional',
              'Fomento Baixo Retorno', 'Pequeno Porte com algum retorno',
              'Pequeno Porte sem retorno']
_inv_tot = PTO.inv_total.sum()
TT = (PTO.groupby('tipo').apply(lambda g: pd.Series({
    'n_produtoras': len(g), 'n_obras': int(g.n_obras.sum()),
    'fsa_mi': g.inv_total.sum() / 1e6,
    'pct_fsa': 100 * g.inv_total.sum() / _inv_tot,
    'ticket_med_mi': g.inv_total.median() / 1e6,
    'receita_crt_mi': g.receita_ref.sum() / 1e6,
    'roi_fsa_crt': g.receita_ref.sum() / g.inv_total.sum(),
    'pub_por_mi_fsa': g.publico.sum() / (g.inv_total.sum() / 1e6),
    'pct_intl': 100 * (g.n_sinal_intl > 0).mean(),
    'n_obras_med': g.n_obras.median(),
    'pct_recorrente': 100 * (g.n_obras > 1).mean(),
    'pct_pre2006': 100 * g.pre_2006.mean(),
})).reindex(ORDEM_TIPO).dropna(how='all').reset_index().rename(columns={'tipo': 'k'}))

# mapa CNPJ → perfil do grupo (os blocos que agregam obras por CNPJ precisam dele
# para não deixar sem perfil os CNPJs que foram fundidos num grupo)
_GMAP = pd.read_csv(os.path.join(BASE, 'outputs', 'bases',
                                 'grupo_economico_map.csv'), sep=';', dtype=str)
PERFIL_POR_CNPJ = dict(zip(_GMAP.cnpj_produtora.str.zfill(14), _GMAP.perfil))

_r['k'] = _r.apply(_g4, axis=1)
GF = _r.groupby('k').apply(lambda g: pd.Series({
    'n': len(g),
    'roi_dom': g.receita_total_deflac.sum() / g.investimento_total_deflac.sum(),
    'pct_intl': 100 * g.tem_intl.mean(),
    'inv_mi': g.investimento_total_deflac.sum() / 1e6,
    'receita_mi': g.receita_total_deflac.sum() / 1e6,
}))

# Gini por ano, recalculado na base canônica (FSA por produtora, universo aplicação)
_ga = BNO[BNO.investimento_fsa_deflac > 0]


def _gini(x):
    import numpy as _np
    x = _np.sort(_np.asarray(x, float))
    k = len(x)
    return (2 * _np.sum(_np.arange(1, k + 1) * x) / (k * x.sum())) - (k + 1) / k \
        if x.sum() else float('nan')


GA = pd.DataFrame([
    {'ano': a, 'gini': _gini(g.groupby('CNPJ_produtora').investimento_fsa_deflac.sum())}
    for a, g in _ga.groupby('ano') if g.CNPJ_produtora.nunique() > 5]).sort_values('ano')
IND = json.load(open(os.path.join(BASE, 'outputs', 'bases', 'indicadores.json'),
                    encoding='utf-8'))

# nomes de produtoras (CNPJ → razão social, via RIDAB fomento_fsa)
_ff = F.cl_local('fomento_fsa')[['cnpj_produtora', 'razao_social_produtora']].dropna()
_ff['cnpj'] = _ff.cnpj_produtora.astype(str).str.replace(r'\D', '', regex=True).str.zfill(14)
NOME = (_ff.groupby('cnpj')['razao_social_produtora'].first().str.title().str.slice(0, 34).to_dict())
PTO['cnpj_n'] = PTO.cnpj.astype(str).str.replace(r'\D', '', regex=True).str.zfill(14)
PTO['nome'] = PTO.cnpj_n.map(NOME).fillna('CNPJ ' + PTO.cnpj_n.str.slice(0, 8))
BNO['cnpj_n'] = BNO.CNPJ_produtora.astype(str).str.replace(r'\D', '', regex=True).str.zfill(14)

# ── RIDAB ao vivo (cadeia · benchmark · condecine · RAIS) ──
AMAX = 2024
sa = F.cl_local('salas_exibicao_evolucao'); sa['ano'] = pd.to_numeric(sa['ano'], errors='coerce')
cx = F.cl_local('complexos_cinematograficos_evolucao'); cx['ano'] = pd.to_numeric(cx['ano'], errors='coerce')
salas = sa[sa.status == 'ABERTA'].groupby('ano').size()
cplx = cx[cx.status == 'ABERTO'].groupby('ano').size()
anos_pk = [a for a in salas.index if 2014 <= a <= AMAX]
salas_y = [int(salas.loc[a]) for a in anos_pk]
cplx_y = [int(cplx.loc[a]) for a in anos_pk]
pi = F.cl_local('preco_ingresso'); pi = pi[(pi.ano >= 2014) & (pi.ano <= AMAX) & (pi.fonte != 'fallback')].sort_values('ano')
queda_real = 100 * (pi.iloc[-1].pmi_real_2024 / pi.iloc[0].pmi_real_2024 - 1)
bd = F.cl_local('bilheteria_diaria_distribuidora_filme_ano')
dist = bd.groupby('distribuidora')['publico_total'].sum().sort_values(ascending=False)
top5 = 100 * dist.head(5).sum() / dist.sum()
MAJORS = ['DISNEY', 'WARNER', 'COLUMBIA', 'FOX FILM', 'PARAMOUNT', 'UNIVERSAL', 'SONY']
def is_major(n): return any(m in str(n).upper() for m in MAJORS)
majors_share = 100 * dist[[is_major(d) for d in dist.index]].sum() / dist.sum()
be = F.cl_local('bilheteria_diaria_exibidora_ano')
exib = be.groupby('exibidora')['publico_total'].sum().sort_values(ascending=False)
top5_exib = 100 * exib.head(5).sum() / exib.sum()
bm = F.cl_local('bilheteria_diaria_municipio_filme_ano')
bm_br = bm[bm.pais_obra.fillna('').astype(str).str.upper().str.contains('BRASIL', regex=False)]
uf_pub = bm_br.groupby('uf')['publico_total'].sum().sort_values(ascending=False)

arg = F.cl_local('incaa_espectadores_origem').copy()
arg['share_nac'] = 100 * arg.espectadores_nacionais / (arg.espectadores_nacionais + arg.espectadores_estrangeiros)
arg = arg[arg.ano.between(2010, 2023)].sort_values('ano')
arg_recente = arg[arg.ano >= 2018].share_nac.mean()
brm = bm[bm.ano.between(2016, 2024)].copy()
brm['is_br'] = brm.pais_obra.fillna('').astype(str).str.upper().str.contains('BRASIL', regex=False)
brs = brm.groupby(['ano', 'is_br'])['publico_total'].sum().unstack(fill_value=0).sort_index()
brs['share_nac'] = 100 * brs.get(True, 0) / brs.sum(axis=1)
br_recente = brs[brs.index >= 2018].share_nac.mean()
bfi_market = F.cl_local('bfi_uk_film_market')
uk_share_2023 = float(bfi_market[bfi_market.categoria.eq('Theatrical')].iloc[0]['2023_uk_qualifying_film_as_of_total_gross'])
cnc_freq = F.cl_local('cnc_frequentation_salles').copy()
cnc_freq['ano'] = pd.to_numeric(cnc_freq['unnamed_0'], errors='coerce')
fr_adm_2023 = pd.to_numeric(cnc_freq.loc[cnc_freq.ano.eq(2023), 'entrees_millions'], errors='coerce').iloc[0] / 1e6
cnc_ag = F.cl_local('cnc_films_agrees')
fr_films_2023 = int(len(cnc_ag[cnc_ag.ano.eq(2023)]))

ca = F.cl_local('condecine_arrecadacao')
piv = (ca[ca.periodicidade == 'ano']
       .pivot_table(index='ano', columns='recorte_nome', values='valor_brl_nominal', aggfunc='sum')
       .sort_index().fillna(0.0))
anos_cd = piv.index.tolist()
total_cd = piv['Total']
dfl = F.cl_local('deflator_ipca').set_index('ano')['fator_real_2024'].to_dict()
real_cd = {a: total_cd.loc[a] * dfl[a] for a in anos_cd if a in dfl}
anos_real = sorted(real_cd.keys())
teles_share_2024 = 100 * piv.loc[2024, 'Condecine-Teles'] / total_cd.loc[2024]
erosao = 100 * (real_cd[2022] / real_cd[2012] - 1)

raca = F.cl_local('diversidade_audiovisual_emprego_raca_ano')
sexo = F.cl_local('diversidade_audiovisual_emprego_sexo_ano')
rp = raca.pivot_table(index='ano', columns='raca_cor', values='empregos_formais_ativos_31_12', aggfunc='sum')
tot_r = raca.groupby('ano')['total_ano'].first()
rp = rp.div(tot_r, axis=0) * 100
rp['negra'] = rp[['parda', 'preta', 'indigena']].sum(axis=1)
sx = sexo.pivot_table(index='ano', columns='sexo', values='empregos_formais_ativos_31_12', aggfunc='sum')
fem_share = (sx['feminino'] / sexo.groupby('ano')['total_ano'].first() * 100)

sys.path.insert(0, os.path.join(str(F.C.LEGADO), 'scripts'))
import parse_diversidade as PD                                                     # noqa: E402
DIV = PD.compute()
pa, ct = DIV['com_pa'], DIV['sem_pa']
spot = PD.spotlight()

abt['ano_ref'] = pd.to_numeric(abt['ano_ref'], errors='coerce')
for col in ['inv_fsa_r2024', 'publico_domestico']:
    abt[col] = pd.to_numeric(abt[col], errors='coerce')
_seg = abt['segmento_destinacao_inicial'].fillna('').astype(str)
abt_sala = abt[(abt['inv_fsa_r2024'].fillna(0) > 0) & abt['ano_ref'].between(2014, 2023)
               & _seg.str.contains('SALAS DE EXIBI', case=False, regex=False)].copy()
ano_abt = (abt_sala.groupby('ano_ref')
           .agg(obras=('cpb', 'count'), fsa_mi=('inv_fsa_r2024', lambda s: s.sum() / 1e6),
                publico_mi=('publico_domestico', lambda s: s.fillna(0).sum() / 1e6))
           .reset_index().sort_values('ano_ref'))

# ════════════════════════ FIGURAS (abertura das alegações) ════════════════════════
R = S

d1 = dcat.sort_values('roi_dom_fsa_crt')
y1 = [f"{c}<br><span style='font-size:10.5px;color:{R.MUT}'>{int(n)} obras</span>" for c, n in zip(d1.cat, d1.n)]
f_c1 = go.Figure()
f_c1.add_bar(y=y1, x=d1.roi_dom_fsa_crt, orientation='h', name='c/ janelas (CRT, ref.)', marker_color=R.ACCENT)
f_c1.add_bar(y=y1, x=d1.roi_dom_fsa_obs, orientation='h', name='só bilheteria (observado)', marker_color=R.MUT)
f_c1.add_vline(x=1.0, line_dash='dot', line_color=R.CORAL)
style(f_c1, h=430, xtitle='ROI doméstico (receita ÷ FSA) — pontilhado = recuperação total')
f_c1.update_yaxes(automargin=True)

dcomp = dcat.sort_values('receita_crt_mi')
f_jan = go.Figure()
f_jan.add_bar(y=dcomp.cat, x=dcomp.bilheteria_mi, orientation='h', name='bilheteria observada', marker_color=R.GREEN)
f_jan.add_bar(y=dcomp.cat, x=dcomp.janelas_crt_mi, orientation='h', name='janelas estimadas (CRT)', marker_color=R.PURPLE)
f_jan.update_layout(barmode='stack')
style(f_jan, h=400, xtitle='receita doméstica de referência (R$ mi, IPCA dez/2024)')
f_jan.update_yaxes(automargin=True)

f_serie = make_subplots(specs=[[{'secondary_y': True}]])
f_serie.add_bar(x=ano_abt.ano_ref.astype(int), y=ano_abt.fsa_mi, name='FSA contratado (R$ mi, 2024)', marker_color=R.ACCENT)
f_serie.add_scatter(x=ano_abt.ano_ref.astype(int), y=ano_abt.publico_mi, name='público observado (mi)',
                    mode='lines+markers', line=dict(color=R.GOLD, width=3), marker=dict(size=7), secondary_y=True)
style(f_serie, h=400, xtitle='ano de referência', ytitle='FSA contratado (R$ mi, IPCA dez/2024)')
f_serie.update_yaxes(title_text='público observado (mi)', secondary_y=True, gridcolor='rgba(0,0,0,0)')

dcov = dcat.copy()
dcov['cobertura_pub'] = 100 * dcov.n_com_publico / dcov.n
dcov = dcov.sort_values('publico_por_mi_fsa')
covlab = [f"{c}<br><span style='font-size:10.5px;color:{R.MUT}'>{br(cv,0)}% com público observado</span>"
          for c, cv in zip(dcov.cat, dcov.cobertura_pub)]
f_cob = go.Figure(go.Bar(y=covlab, x=dcov.publico_por_mi_fsa, orientation='h', marker_color=R.CYAN,
                         text=[br(v, 0) for v in dcov.publico_por_mi_fsa], textposition='auto'))
style(f_cob, h=420, xtitle='espectadores observados por R$ mi de FSA', showlegend=False)
f_cob.update_yaxes(automargin=True)

cb = dcrit
f_c2a = go.Figure(go.Bar(x=['Bilheteria', 'Festivais'],
                         y=[cb.loc['Bilheteria', 'publico_por_mi_fsa'], cb.loc['Festivais', 'publico_por_mi_fsa']],
                         marker_color=R.GREEN,
                         text=[br(cb.loc['Bilheteria', 'publico_por_mi_fsa'], 0), br(cb.loc['Festivais', 'publico_por_mi_fsa'], 0)],
                         textposition='auto'))
style(f_c2a, h=330, ytitle='espectadores por R$ mi de FSA', title='Régua doméstica', showlegend=False)
f_c2b = go.Figure()
f_c2b.add_bar(x=['Bilheteria', 'Festivais'], y=[cb.loc['Bilheteria', 'pct_com_intl'], cb.loc['Festivais', 'pct_com_intl']],
              name='% com sinal internacional', marker_color=R.CYAN,
              text=[f"{br(cb.loc['Bilheteria','pct_com_intl'],0)}%", f"{br(cb.loc['Festivais','pct_com_intl'],0)}%"], textposition='auto')
f_c2b.add_bar(x=['Bilheteria', 'Festivais'], y=[cb.loc['Bilheteria', 'papers_por_obra'], cb.loc['Festivais', 'papers_por_obra']],
              name='papers acadêmicos/obra', marker_color=R.PURPLE, yaxis='y2',
              text=[br(cb.loc['Bilheteria', 'papers_por_obra'], 1), br(cb.loc['Festivais', 'papers_por_obra'], 1)], textposition='auto')
f_c2b.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False, title='papers/obra', title_font_size=12))
style(f_c2b, h=350, ytitle='% das obras com sinal internacional', title='Régua externa e simbólica')
ic = icat.sort_values('pct_com_intl')
f_ipen = go.Figure(go.Bar(y=ic.cat, x=ic.pct_com_intl, orientation='h', marker_color=R.CYAN,
                          text=[f'{br(v,0)}%' for v in ic.pct_com_intl], textposition='auto'))
style(f_ipen, h=430, xtitle='% das obras da categoria com algum sinal internacional', showlegend=False)
f_ipen.update_yaxes(automargin=True)

MCOLS = [('Doméstico<br>ROI', 'roi_dom_fsa_crt', lambda v: br(v, 2)),
         ('Doméstico<br>Públ./R$mi', 'publico_por_mi_fsa', lambda v: br(v / 1000, 1) + 'k'),
         ('Intl<br>% c/ sinal', 'pct_com_intl', lambda v: f'{br(v, 0)}%'),
         ('Intl<br>Desempenho', 'desemp_intl_medio', lambda v: br(v, 1)),
         ('Soft<br>Crítica', 'critica_media', lambda v: br(v, 2)),
         ('Soft<br>Papers/obra', 'papers_por_obra', lambda v: br(v, 1)),
         ('Soft<br>% presença', 'pct_presenca_intl', lambda v: f'{br(v, 0)}%')]
z = [[M.iloc[r][c + '__norm'] for _, c, _ in MCOLS] for r in range(len(M))]
txt = [[fmt(M.iloc[r][c]) for _, c, fmt in MCOLS] for r in range(len(M))]
f_M = go.Figure(go.Heatmap(z=z, x=[m for m, _, _ in MCOLS], y=M.cat.tolist(), text=txt, texttemplate='%{text}',
                textfont=dict(size=11, color=R.TXT), colorscale=[[0, '#161922'], [0.45, '#2c3566'], [1, R.ACCENT]],
                showscale=False, xgap=3, ygap=3, hovertemplate='%{y}<br>%{x}: %{text}<extra></extra>'))
f_M.update_layout(paper_bgcolor=R.SURF, plot_bgcolor=R.SURF, font=dict(family='Inter', color=R.TXT, size=11),
                  margin=dict(l=170, r=20, t=20, b=40), height=510)
f_M.update_xaxes(side='top', tickfont_size=10.5)
f_M.update_yaxes(autorange='reversed', tickfont_size=11)

de = delo
metr = [('Público/R$mi', 'publico_por_mi_fsa'), ('ROI doméstico', 'roi_dom_fsa_crt'),
        ('Desemp. intl', 'desemp_intl_medio'), ('Presença global', 'pct_presenca_intl'),
        ('Investimento FSA', 'fsa_mi')]
idx = [100 * de.loc['Distribuidora', c] / de.loc['Produtora', c] for _, c in metr]
f_elo = go.Figure()
f_elo.add_bar(y=[m for m, _ in metr], x=[100] * len(metr), orientation='h', name='Produtora (base 100)', marker_color=R.MUT)
f_elo.add_bar(y=[m for m, _ in metr], x=idx, orientation='h', name='Distribuidora', marker_color=R.ACCENT,
              text=[br(v, 0) for v in idx], textposition='auto')
f_elo.update_layout(barmode='overlay')
style(f_elo, h=370, xtitle='índice (Produtora = 100) — acima de 100, distribuidora à frente (inclusive no investimento)')
f_addon = go.Figure()
f_addon.add_bar(x=['Comercialização', 'Complementação'], y=[gn2['comerc_bilh_com'], gn2['compl_bilh_com']],
                name='obras COM o apoio', marker_color=R.GREEN,
                text=[f"R$ {br(gn2['comerc_bilh_com'],0)} mil", f"R$ {br(gn2['compl_bilh_com'],0)} mil"], textposition='auto')
f_addon.add_bar(x=['Comercialização', 'Complementação'], y=[gn2['comerc_bilh_sem'], gn2['compl_bilh_sem']],
                name='obras SEM', marker_color=R.MUT,
                text=[f"R$ {br(gn2['comerc_bilh_sem'],1)}", f"R$ {br(gn2['compl_bilh_sem'],1)}"], textposition='auto')
style(f_addon, h=330, ytitle='bilheteria mediana (R$ mil)', title='Quem recebe apoio à ponta já vendia')

f_pre06 = go.Figure(go.Bar(x=['Produziam antes de 2006', 'Nasceram dentro do ciclo FSA'],
                           y=[GL['pre2006_pct_duplo'], GL['pos2006_pct_duplo']], marker_color=[R.GOLD, R.MUT],
                           text=[f"{br(GL['pre2006_pct_duplo'],1)}%", f"{br(GL['pos2006_pct_duplo'],1)}%"], textposition='auto'))
style(f_pre06, h=330, ytitle='% no cluster Duplo Retorno', title='Entrada que não virou trajetória (série longa)', showlegend=False)
f_tick = go.Figure(go.Bar(x=['Acerto na 1ª obra', 'Sem acerto na 1ª obra'],
                          y=[gn3['ticket_depois_acerto_mi'], gn3['ticket_depois_sem_acerto_mi']], marker_color=[R.GREEN, R.MUT],
                          text=[f"R$ {br(gn3['ticket_depois_acerto_mi'],2)} mi", f"R$ {br(gn3['ticket_depois_sem_acerto_mi'],2)} mi"],
                          textposition='auto'))
style(f_tick, h=320, ytitle='ticket FSA mediano das obras seguintes (R$ mi)', showlegend=False)
f_rec = go.Figure()
f_rec.add_bar(x=['Tira-única (1 obra)', 'Recorrente (2+)'], y=[gn3['pct_tira_unica'], gn3['pct_recorrente']],
              name='% das produtoras', marker_color=R.MUT,
              text=[f"{br(gn3['pct_tira_unica'],0)}%", f"{br(gn3['pct_recorrente'],0)}%"], textposition='auto')
f_rec.add_bar(x=['Tira-única (1 obra)', 'Recorrente (2+)'],
              y=[100 - gn3['fsa_de_recorrentes_pct'], gn3['fsa_de_recorrentes_pct']],
              name='% do FSA', marker_color=R.ACCENT,
              text=[f"{br(100-gn3['fsa_de_recorrentes_pct'],0)}%", f"{br(gn3['fsa_de_recorrentes_pct'],0)}%"], textposition='auto')
style(f_rec, h=320, ytitle='% do total')

# ── Dispersão por CHAMADA (pedido do Cainan 2026-08-09) ───────────────────────
# Uma bolha por chamada pública: retorno doméstico (x) × desempenho internacional
# (y), tamanho pelo dinheiro público aplicado. Complementação e comercialização
# ficam FORA: são aporte sobre filme pronto, entram com denominador parcial e
# distorcem os dois eixos. É a figura da pergunta 2 no ensaio e no DOCX.
_ch = BNO[BNO.universo_retorno].copy()
_ch['_cham'] = _ch.chamada.astype(str).str.strip().str.upper()
_ADDON = _ch._cham.str.contains('COMPLEMENT|COMERCIALIZ|PRODECINE 03|PRODECINE 04', na=False)
_ch = _ch[(~_ADDON) & (_ch._cham != '') & (_ch._cham != 'NAN')]
_agg = _ch.groupby('_cham').apply(lambda g: pd.Series({
    'n': len(g),
    'inv_mi': g.investimento_total_deflac.sum() / 1e6,
    'dom': g.receita_total_deflac.sum() / g.investimento_total_deflac.sum(),
    'intl': g.retorno_intl.mean(),
    'cat': (g.cat_nova.dropna().mode().iloc[0] if g.cat_nova.notna().any() else 'Outras'),
}), include_groups=False).reset_index()
_agg = _agg[_agg.n >= 3].sort_values('inv_mi', ascending=False)
_CORES_CAT = {'Bilheteria \u00b7 Distribuidora': R.CYAN, 'Bilheteria \u00b7 Produtora': R.ACCENT,
              'Festivais \u00b7 Pontua\u00e7\u00e3o': R.PURPLE, 'Autom\u00e1tico Bilheteria': R.GOLD,
              'Autom\u00e1tico Festivais': R.GREEN, 'Arranjos Regionais': R.CORAL,
              'Coprodu\u00e7\u00e3o Intl': '#9aa4bf'}
f_disp_chamada = go.Figure()
for _c, _g in _agg.groupby('cat'):
    f_disp_chamada.add_trace(go.Scatter(
        x=_g.dom, y=_g.intl, mode='markers+text', name=str(_c),
        text=[t.title()[:22] for t in _g._cham], textposition='top center',
        textfont=dict(size=9, color=R.MUT),
        marker=dict(size=(_g.inv_mi ** 0.5) * 2.6 + 9, color=_CORES_CAT.get(_c, R.MUT),
                    line=dict(color=R.BG, width=1), opacity=0.86),
        customdata=np.stack([_g.n, _g.inv_mi], axis=-1),
        hovertemplate='%{text}<br>%{customdata[0]:.0f} obras \u00b7 R$ %{customdata[1]:.0f} mi'
                      '<br>retorno dom\u00e9stico %{x:.2f}<br>internacional %{y:.1f}<extra></extra>'))
f_disp_chamada.add_vline(x=1.0, line_dash='dot', line_color=R.CORAL)
style(f_disp_chamada, h=520, xtitle='retorno dom\u00e9stico (receita \u00f7 dinheiro p\u00fablico)',
      ytitle='desempenho internacional m\u00e9dio (0\u2013100)')

# ── CONDECINE: a regressividade da tarifa por título (2026-08-09) ────────────
# Tarifa do Anexo I da MP 2.228-1/2001 (R$ 3.000 para longa em salas, valor
# nominal de 2001 nunca corrigido) contra a bilheteria de cada filme. A mesma
# obrigação legal para todos: a alíquota efetiva desaba conforme o filme vende.
import re as _re
_ncp = lambda x: _re.sub(r'[^0-9A-Z]', '', str(x).upper())
_crt = pd.read_parquet(os.path.join(BASE, 'data', 'ridab_cleaned',
                                    'crt_obras_nao_publicitarias.parquet'))
_crt['_a'] = pd.to_datetime(_crt.data_emissao_crt, dayfirst=True, errors='coerce').dt.year
_crt = _crt[(_crt._a.between(2014, 2019)) & (_crt.segmento == 'SALAS DE EXIBIÇÃO')].copy()
_d = pd.to_numeric(_crt.duracao_total_minutos, errors='coerce').astype(float)
_crt['tarifa'] = np.select([_d <= 15, _d <= 50], [300.0, 700.0], default=3000.0)
_crt['cpbn'] = _crt.cpb_roe.map(_ncp)
_bo = BNO[BNO.universo_retorno].copy()
_bo['cpbn'] = _bo.CPB.map(_ncp)
_rg = (_crt.merge(_bo[['cpbn', 'titulo', 'bilheteria_deflac']], on='cpbn')
       .drop_duplicates('cpbn'))
_rg = _rg[pd.to_numeric(_rg.bilheteria_deflac, errors='coerce') > 0]
_rg['bil'] = pd.to_numeric(_rg.bilheteria_deflac, errors='coerce')
_rg['aliq'] = 100 * _rg.tarifa / _rg.bil
f_cond_regress = go.Figure()
f_cond_regress.add_trace(go.Scatter(
    x=_rg.bil, y=_rg.aliq, mode='markers', name='filme',
    marker=dict(size=7, color=R.CORAL, opacity=0.62, line=dict(color=R.BG, width=0.6)),
    text=_rg.titulo,
    hovertemplate='%{text}<br>bilheteria R$ %{x:,.0f}<br>a tarifa de R$ 3.000 '
                  'equivale a %{y:.2f}% da renda<extra></extra>'))
f_cond_regress.add_hline(y=1.0, line_dash='dot', line_color=R.MUT,
                         annotation_text='1% da renda do filme',
                         annotation_font=dict(size=10, color=R.MUT))
f_cond_regress.update_xaxes(type='log')
f_cond_regress.update_yaxes(type='log')
style(f_cond_regress, h=470,
      xtitle='bilheteria do filme (R$ de 2024, escala log)',
      ytitle='CONDECINE-Título como % da renda (escala log)', showlegend=False)

CORES_TIPO = {'Duplo Retorno': R.GREEN, 'Retorno Doméstico': R.CYAN,
              'Retorno Internacional': R.PURPLE, 'Fomento Baixo Retorno': R.CORAL,
              'Pequeno Porte com algum retorno': R.GOLD,
              'Pequeno Porte sem retorno': R.MUT}
f_tipo = go.Figure()
for _, r_ in TT.iterrows():
    f_tipo.add_trace(go.Scatter(
        x=[r_.pct_fsa], y=[r_.roi_fsa_crt], mode='markers+text', name=r_.k, text=[r_.k],
        textposition='top center', textfont=dict(size=10.5, color=R.TXT),
        marker=dict(size=r_.n_produtoras ** 0.5 * 3.2 + 7, color=CORES_TIPO.get(r_.k, R.ACCENT),
                    line=dict(color=R.BG, width=1), opacity=0.9),
        customdata=[[r_.n_produtoras, r_.pct_pre2006]],
        hovertemplate='%{text}<br>%{customdata[0]:.0f} grupos<br>%{x:.1f}% do dinheiro público'
                      '<br>retorno %{y:.2f}<br>%{customdata[1]:.0f}% anteriores a 2006<extra></extra>'))
f_tipo.add_hline(y=1.0, line_dash='dot', line_color=R.CORAL)
style(f_tipo, h=450, xtitle='% do dinheiro público que o perfil absorve',
      ytitle='retorno doméstico (receita ÷ dinheiro público)', showlegend=False)

# barras de composição: quanto cada perfil recebeu × quanto devolveu
f_perfil_br = go.Figure()
for _c, _lab in [('pct_fsa', '% do dinheiro público recebido'), (None, '% da receita gerada')]:
    _v = (TT.pct_fsa if _c else 100 * TT.receita_crt_mi / TT.receita_crt_mi.sum())
    f_perfil_br.add_bar(x=TT.k, y=_v, name=_lab,
                        marker_color=R.MUT if _c else R.ACCENT,
                        text=[f'{v:.0f}%' for v in _v], textposition='auto')
f_perfil_br.update_layout(barmode='group')
style(f_perfil_br, h=380, ytitle='% do total')

f_c5fig = go.Figure(go.Bar(
    x=['Todas as direções de longa<br>no cadastro (%d)' % CU['curtas_universo'],
       'Direções com curta em festival<br>de primeira linha (coorte madura, %d)' % CU['curtas_coorte_madura']],
    y=[CU['curtas_base_geral_pct'], CU['curtas_com_curta_pct']], marker_color=[R.MUT, R.CYAN],
    text=[f"{br(CU['curtas_base_geral_pct'],1)}%", f"{br(CU['curtas_com_curta_pct'],1)}%"], textposition='auto'))
f_c5fig.add_scatter(x=['Direções com curta em festival<br>de primeira linha (coorte madura, %d)' % CU['curtas_coorte_madura']],
                    y=[CU['curtas_com_curta_pct']], mode='markers', showlegend=False,
                    marker=dict(color='rgba(0,0,0,0)'),
                    error_y=dict(type='data', symmetric=False,
                                 array=[CU['curtas_ic'][1] - CU['curtas_com_curta_pct']],
                                 arrayminus=[CU['curtas_com_curta_pct'] - CU['curtas_ic'][0]],
                                 color=R.CYAN, thickness=1.4, width=8))
style(f_c5fig, h=350, ytitle='% que chega ao mercado europeu com um LONGA', showlegend=False)

f_c6fig = go.Figure()
f_c6fig.add_bar(x=QT.q_ticket, y=QT.pub_por_mi_fsa, name='espectadores/R$ mi', marker_color=R.GREEN,
                text=[br(v, 0) for v in QT.pub_por_mi_fsa], textposition='auto')
f_c6fig.add_scatter(x=QT.q_ticket, y=QT.pct_sala, name='% que estreia em sala', mode='lines+markers+text',
                    line=dict(color=R.GOLD, width=3), marker=dict(size=9), yaxis='y2',
                    text=[f'{br(v,0)}%' for v in QT.pct_sala], textposition='top center', textfont=dict(color=R.GOLD))
f_c6fig.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False, title='% em sala', range=[0, 110]))
style(f_c6fig, h=390, ytitle='espectadores por R$ mi de FSA', xtitle='quintil de ticket FSA por obra')

f_gini = go.Figure()
f_gini.add_scatter(x=GA.ano, y=GA.gini, mode='lines+markers', name='Gini do FSA no ano',
                   line=dict(color=R.CYAN, width=3), marker=dict(size=7))
f_gini.add_hline(y=IND['gini_fsa_produtora'], line_dash='dash', line_color=R.GOLD,
                 annotation_text=f"período inteiro = {br(IND['gini_fsa_produtora'],2)}",
                 annotation_font_color=R.GOLD, annotation_position='top left')
f_gini.add_hline(y=IND['gini_bilheteria_obra'], line_dash='dot', line_color=R.CORAL,
                 annotation_text=f"bilheteria por obra = {br(IND['gini_bilheteria_obra'],2)} (mercado)",
                 annotation_font_color=R.CORAL, annotation_position='bottom right')
f_gini.update_yaxes(range=[0, 1])
style(f_gini, h=380, xtitle='ano', ytitle='índice de Gini', showlegend=False)
f_prolif = go.Figure()
f_prolif.add_scatter(x=PR.ano, y=PR.n_obras, name='obras fomentadas/ano', mode='lines+markers', line=dict(color=R.ACCENT, width=3))
f_prolif.add_scatter(x=PR.ano, y=PR.n_produtoras, name='produtoras ativas/ano', mode='lines+markers', line=dict(color=R.GOLD, width=3))
style(f_prolif, h=350, xtitle='ano', ytitle='contagem por ano (universo fomentado, base atual 2014+)')
f_lz = go.Figure()
f_lz.add_scatter(x=LZ.p, y=LZ.L, mode='lines', name='distribuição do FSA', line=dict(color=R.ACCENT, width=3),
                 fill='tozeroy', fillcolor='rgba(108,123,247,.12)')
f_lz.add_scatter(x=[0, 1], y=[0, 1], mode='lines', name='igualdade perfeita', line=dict(color=R.MUT, width=1.5, dash='dot'))
style(f_lz, h=370, xtitle='produtoras acumuladas (da menor p/ a maior)', ytitle='FSA acumulado')

f_parque = go.Figure()
f_parque.add_bar(x=anos_pk, y=salas_y, name='salas em operação', marker_color=R.ACCENT,
                 text=[br(v, 0) for v in salas_y], textposition='outside', textfont_size=9.5)
f_parque.add_scatter(x=anos_pk, y=cplx_y, name='complexos (cinemas)', mode='lines+markers',
                     line=dict(color=R.GOLD, width=3), marker=dict(size=7), yaxis='y2')
f_parque.add_vrect(x0=2019.5, x1=2020.5, fillcolor=R.CORAL, opacity=0.10, line_width=0,
                   annotation_text='COVID', annotation_position='top', annotation_font_size=10, annotation_font_color=R.CORAL)
style(f_parque, h=420, xtitle='ano', ytitle='salas em operação')
f_parque.update_layout(yaxis=dict(range=[0, max(salas_y) * 1.18]),
                       yaxis2=dict(title=dict(text='complexos', font=dict(size=12)), overlaying='y', side='right',
                                   showgrid=False, range=[0, max(cplx_y) * 1.18], tickfont=dict(size=11)))
f_preco = go.Figure()
f_preco.add_bar(x=pi.ano, y=pi.pmi_nominal, name='preço médio nominal', marker_color=R.MUT,
                text=[f'{br(v,2)}' for v in pi.pmi_nominal], textposition='outside', textfont_size=9)
f_preco.add_scatter(x=pi.ano, y=pi.pmi_real_2024, name='preço médio real (R$ 2024)', mode='lines+markers',
                    line=dict(color=R.GOLD, width=3), marker=dict(size=8))
style(f_preco, h=370, xtitle='ano', ytitle='preço médio do ingresso (R$)')
f_preco.update_yaxes(range=[0, pi.pmi_nominal.max() * 1.25])
def short_dist(n):
    n = str(n).title()
    for a, b in [('The Walt Disney Company (Brasil) Ltda.', 'Disney'), ('Warner Bros. (South) Inc.', 'Warner Bros.'),
                 ('Columbia Tristar Filmes Do Brasil Ltda', 'Columbia/Sony'), ('Sm Distribuidora De Filmes Ltda', 'SM Distribuidora'),
                 ('Fox Film Do Brasil Ltda', 'Fox Film'), ('Paramount Pictures Brasil Distribuidora De Filmes Ltda', 'Paramount'),
                 ('Universal Pictures International Brazil Ltda.', 'Universal'), ('Freespirit Distribuidora De Filmes Ltda.', 'Freespirit'),
                 ('Wmix Distribuidora Ltda.', 'WMIX'), ('Diamond Films Do Brasil Produ', 'Diamond Films')]:
        if a.lower() in str(n).lower() or b.lower() in str(n).lower():
            return b
    return n[:26]
top10_df = dist.head(10).reset_index()
f_dist = go.Figure(go.Bar(
    y=[short_dist(n) for n in top10_df.distribuidora][::-1],
    x=(top10_df.publico_total / 1e6).tolist()[::-1], orientation='h',
    marker_color=[R.CORAL if is_major(n) else R.ACCENT for n in top10_df.distribuidora][::-1],
    text=[f'{br(v/1e6,1)} mi' for v in top10_df.publico_total][::-1], textposition='auto'))
style(f_dist, h=410, xtitle='público acumulado em sala (milhões) · vermelho = major de Hollywood', showlegend=False)
f_dist.update_yaxes(automargin=True)
top10_exib_df = exib.head(10).reset_index()
f_exib = go.Figure(go.Bar(
    y=[short_dist(n) for n in top10_exib_df.exibidora][::-1],
    x=(top10_exib_df.publico_total / 1e6).tolist()[::-1], orientation='h', marker_color=R.GOLD,
    text=[f'{br(v/1e6,1)} mi' for v in top10_exib_df.publico_total][::-1], textposition='auto'))
style(f_exib, h=410, xtitle='público acumulado em sala (milhões)', showlegend=False)
f_exib.update_yaxes(automargin=True)
f_uf = go.Figure(go.Bar(x=uf_pub.head(12).index.tolist(), y=(uf_pub.head(12) / 1e6).tolist(),
                        marker_color=R.GREEN, text=[f'{br(v/1e6,1)}' for v in uf_pub.head(12)], textposition='auto'))
style(f_uf, h=360, xtitle='UF', ytitle='público de filmes brasileiros (milhões)', showlegend=False)

grupos9 = ['Negros<br><span style="font-size:10px">c/ ação afirmativa</span>',
           'Negros<br><span style="font-size:10px">controle</span>',
           'Mulheres<br><span style="font-size:10px">c/ ação afirmativa</span>',
           'Mulheres<br><span style="font-size:10px">controle</span>']
insc9 = [pa['pct_negro_inscritos'], ct['pct_negro_inscritos'], pa['pct_mulher_inscritas'], ct['pct_mulher_inscritas']]
sel9 = [pa['pct_negro_selecionados'], ct['pct_negro_selecionados'], pa['pct_mulher_selecionadas'], ct['pct_mulher_selecionadas']]
f_pa1 = go.Figure()
f_pa1.add_bar(x=grupos9, y=insc9, name='entre os inscritos', marker_color=R.MUT,
              text=[f'{br(v,1)}%' for v in insc9], textposition='outside', textfont_size=10)
f_pa1.add_bar(x=grupos9, y=sel9, name='entre os selecionados', marker_color=R.GREEN,
              text=[f'{br(v,1)}%' for v in sel9], textposition='outside', textfont_size=10)
style(f_pa1, h=420, ytitle='% do grupo', xtitle='barra verde acima da cinza = a seleção aumentou a representação')
f_pa1.update_yaxes(range=[0, 62])
catsT = ['c/ ação afirmativa', 'controle']
f_pa2 = go.Figure()
f_pa2.add_bar(x=catsT, y=[pa['taxa_selecao_negro'], ct['taxa_selecao_negro']], name='negros', marker_color=R.PURPLE,
              text=[f'{br(pa["taxa_selecao_negro"],1)}%', f'{br(ct["taxa_selecao_negro"],1)}%'], textposition='auto')
f_pa2.add_bar(x=catsT, y=[pa['taxa_selecao_branco'], ct['taxa_selecao_branco']], name='brancos', marker_color=R.MUT,
              text=[f'{br(pa["taxa_selecao_branco"],1)}%', f'{br(ct["taxa_selecao_branco"],1)}%'], textposition='auto')
f_pa2.add_bar(x=catsT, y=[pa['taxa_selecao_mulher'], ct['taxa_selecao_mulher']], name='mulheres', marker_color=R.GOLD,
              text=[f'{br(pa["taxa_selecao_mulher"],1)}%', f'{br(ct["taxa_selecao_mulher"],1)}%'], textposition='auto')
f_pa2.add_bar(x=catsT, y=[pa['taxa_selecao_homem'], ct['taxa_selecao_homem']], name='homens', marker_color=R.CYAN,
              text=[f'{br(pa["taxa_selecao_homem"],1)}%', f'{br(ct["taxa_selecao_homem"],1)}%'], textposition='auto')
style(f_pa2, h=380, ytitle='taxa de seleção (selecionados ÷ inscritos do grupo, %)',
      title='Com cota, negros e mulheres passam a ser selecionados a taxa MAIOR que a dos pares')
anos_emp = rp.index.tolist()
f_rais = go.Figure()
f_rais.add_scatter(x=anos_emp, y=rp['branca'], name='branca', mode='lines+markers', line=dict(color=R.GOLD, width=3))
f_rais.add_scatter(x=anos_emp, y=rp['negra'], name='negra (parda+preta+indígena)', mode='lines+markers', line=dict(color=R.GREEN, width=3))
f_rais.add_scatter(x=anos_emp, y=rp['nao_declarada'], name='não declarada', mode='lines+markers',
                   line=dict(color=R.MUT, width=2, dash='dot'))
style(f_rais, h=360, ytitle='% dos empregos formais do setor', xtitle='ano (RAIS · emprego audiovisual formal)')
f_fem = go.Figure()
f_fem.add_scatter(x=fem_share.index.tolist(), y=fem_share.values, mode='lines+markers',
                  line=dict(color=R.PURPLE, width=3), fill='tozeroy', fillcolor='rgba(167,139,250,.10)')
f_fem.add_hline(y=50, line_dash='dot', line_color=R.MUT, annotation_text='paridade (50%)',
                annotation_font_size=10, annotation_font_color=R.MUT)
style(f_fem, h=320, ytitle='% feminino dos empregos formais', xtitle='ano (RAIS)', showlegend=False)

sc = scat.copy()
sc['pct_pres'] = 100 * sc.n_presenca_intl / sc.n
sc['papers_obra'] = sc.papers_soma / sc.n
f_sp_scatter = go.Figure(go.Scatter(
    x=sc.pct_pres, y=sc.papers_obra, mode='markers+text', text=sc.cat, textposition='top center',
    textfont=dict(size=10, color=R.MUT), customdata=sc.n.astype(int),
    marker=dict(size=sc.n / 6 + 9, color=R.PURPLE, line=dict(color=R.TXT, width=0.5)),
    hovertemplate='%{text}<br>%{x:.1f}% c/ presença intl<br>%{y:.2f} papers/obra<br>%{customdata} obras<extra></extra>'))
style(f_sp_scatter, h=420, xtitle='% das obras com presença internacional (Wikipedia, além de PT/EN)',
      ytitle='citações acadêmicas por obra', showlegend=False)
dims10 = ['Crítica', 'Acadêmico', 'Presença<br>Wikipedia', '— alcance<br>intl (L*)', 'Atenção<br>IMDb']
vals10 = [gns['cobertura_critica_pct'], gns['cobertura_acad_pct'], gns['cobertura_presenca_pct'],
          gns['cobertura_presenca_intl_pct'], gns['cobertura_imdb_pct']]
f_cober = go.Figure(go.Bar(x=dims10, y=vals10, marker_color=[R.ACCENT, R.PURPLE, R.CYAN, R.CYAN, R.GOLD],
                           text=[f'{br(v,0)}%' for v in vals10], textposition='auto'))
style(f_cober, h=340, ytitle='% das 855 obras com sinal', showlegend=False)
st10 = stop.head(10).sort_values('L_nonpten')
f_lstar = go.Figure(go.Bar(y=st10.titulo, x=st10.L_nonpten, orientation='h', marker_color=R.CYAN,
                           text=st10.L_nonpten, textposition='auto'))
style(f_lstar, h=390, xtitle='idiomas na Wikipedia além de PT/EN (L*) — top 10 alcance', showlegend=False)
f_lstar.update_yaxes(automargin=True)
it10 = itop.head(12).sort_values('roi_internacional_0_100')
f_itop = go.Figure(go.Bar(y=it10.titulo, x=it10.roi_internacional_0_100, orientation='h', marker_color=R.PURPLE,
                          customdata=it10.intl_n_mercados,
                          hovertemplate='%{y}<br>Desempenho %{x:.1f}/100<br>%{customdata} mercados<extra></extra>'))
style(f_itop, h=430, xtitle='Retorno Internacional (índice 0–100) — top 12 obras', showlegend=False)
f_itop.update_yaxes(automargin=True)

_di = BNO[BNO.universo_retorno].groupby('instrumento').apply(lambda g: pd.Series({
    'publico_mi': g.publico_domestico.sum() / 1e6,
    'roi_dom_total_crt': g.receita_total_deflac.sum() / g.investimento_total_deflac.sum()}))
di8 = _di.reindex(['FSA puro', 'Misto FSA+Renúncia', 'Renúncia pura'])
ii8 = iinst.set_index('instrumento').reindex(['FSA puro', 'Misto FSA+Renúncia', 'Renúncia pura'])
lbl8 = ['FSA puro', 'Misto<br>FSA+renúncia', 'Renúncia pura']
f_ren1 = go.Figure()
f_ren1.add_bar(x=lbl8, y=di8.publico_mi, name='público (milhões)', marker_color=R.GREEN,
               text=[br(v, 1) for v in di8.publico_mi], textposition='auto')
f_ren1.add_scatter(x=lbl8, y=di8.roi_dom_total_crt, name='ROI doméstico (÷ inv. total)', mode='lines+markers+text',
                   line=dict(color=R.GOLD, width=3), marker=dict(size=10), yaxis='y2',
                   text=[br(v, 2) for v in di8.roi_dom_total_crt], textposition='top center', textfont=dict(color=R.GOLD))
f_ren1.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False,
                                 title='retorno doméstico',
                                 range=[0, max(2.2, float(di8.roi_dom_total_crt.max()) * 1.15)]))
style(f_ren1, h=360, ytitle='público em sala (milhões)', title='Doméstico por instrumento')
ORD_G = ['FSA puro', 'FSA+Renúncia · FSA maj.', 'FSA+Renúncia · Ren. maj.', 'Renúncia pura']
f_ren2 = go.Figure(go.Bar(
    x=[g.replace(' · ', '<br>') for g in ORD_G], y=[GF.loc[g, 'pct_intl'] for g in ORD_G],
    marker_color=[R.CYAN, R.GREEN, R.PURPLE, R.GOLD],
    customdata=[[int(GF.loc[g, 'n']), GF.loc[g, 'roi_dom']] for g in ORD_G],
    text=[f"{br(GF.loc[g,'pct_intl'],0)}%" for g in ORD_G], textposition='auto',
    hovertemplate='%{x}<br>%{y:.1f}% com sinal intl<br>%{customdata[0]} obras · ROI dom %{customdata[1]:.2f}<extra></extra>'))
style(f_ren2, h=360, ytitle='% das obras com sinal internacional',
      title='Quem circula fora: FSA majoritário lidera; renúncia pura quase não cruza', showlegend=False)
f_ren3 = go.Figure()
f_ren3.add_bar(x=lbl8, y=ii8.desemp_intl_medio, name='Desempenho intl (0–100)', marker_color=R.CYAN,
               text=[br(v, 1) for v in ii8.desemp_intl_medio], textposition='auto')
f_ren3.add_bar(x=lbl8, y=ii8.admEU_mil, name='admissões Europa (mil)', marker_color=R.PURPLE, yaxis='y2',
               text=[br(v, 0) for v in ii8.admEU_mil], textposition='auto')
f_ren3.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False, title='admissões EU (mil)', title_font_size=12))
style(f_ren3, h=350, ytitle='Desempenho internacional médio (0–100)', title='Internacional por instrumento')
f_grup = go.Figure(go.Bar(
    x=dg.grupo_fin, y=dg.roi_dom_med, marker_color=[R.GOLD, R.ACCENT, R.CYAN, R.PURPLE],
    customdata=list(zip(dg.n.astype(int), dg.inv_total_bi)),
    text=[f'{br(v,2)}x' for v in dg.roi_dom_med], textposition='auto',
    hovertemplate='%{x}<br>ROI dom. %{y:.2f}x<br>%{customdata[0]} obras · R$ %{customdata[1]:.2f} bi<extra></extra>'))
f_grup.add_hline(y=1.0, line_dash='dot', line_color=R.CORAL)
style(f_grup, h=360, ytitle='ROI doméstico (média ponderada pelo investimento)', showlegend=False)

f_arg = go.Figure()
f_arg.add_bar(x=arg.ano, y=arg.share_nac, marker_color=R.CYAN, text=[f'{br(v,0)}%' for v in arg.share_nac], textposition='auto')
f_arg.add_hline(y=arg.share_nac.mean(), line_dash='dot', line_color=R.MUT,
                annotation_text=f'média {br(arg.share_nac.mean(),0)}%', annotation_font_color=R.MUT, annotation_font_size=10)
style(f_arg, h=370, ytitle='% dos espectadores em filmes nacionais', xtitle='ano (Argentina · INCAA)', showlegend=False)
f_brs = go.Figure()
f_brs.add_bar(x=brs.index.tolist(), y=brs.share_nac, marker_color=R.GREEN,
              text=[f'{br(v,0)}%' for v in brs.share_nac], textposition='auto')
f_brs.add_hline(y=brs.share_nac.mean(), line_dash='dot', line_color=R.MUT,
                annotation_text=f'média {br(brs.share_nac.mean(),0)}%', annotation_font_color=R.MUT, annotation_font_size=10)
style(f_brs, h=360, ytitle='% do público em filmes brasileiros', xtitle='ano (Brasil · RIDAB/ANCINE)', showlegend=False)
REF12 = [('França', 40, R.ACCENT), ('Reino Unido*', round(uk_share_2023), R.PURPLE),
         ('Argentina', round(arg_recente), R.CYAN), ('Brasil', round(br_recente), R.GREEN)]
f_ref = go.Figure(go.Bar(x=[p for p, _, _ in REF12], y=[v for _, v, _ in REF12],
                         marker_color=[c for _, _, c in REF12],
                         text=[f'~{v}%' for _, v, _ in REF12], textposition='auto'))
style(f_ref, h=350, ytitle='participação nacional no mercado (%)',
      title='Ordem de grandeza — fontes/anos/métodos distintos (* UK qualifying inclui superproduções estrangeiras)',
      showlegend=False)

TIPOS_CD = ['Condecine-Teles', 'Condecine-Títulos', 'Condecine-Remessa', 'Dívida Ativa']
for t in TIPOS_CD:
    if t not in piv:
        piv[t] = 0.0
COR_CD = {'Condecine-Teles': R.ACCENT, 'Condecine-Títulos': R.GOLD, 'Condecine-Remessa': R.PURPLE, 'Dívida Ativa': R.MUT}
NOME_CD = {'Condecine-Teles': 'Teles (TV paga / telecom)', 'Condecine-Títulos': 'Títulos (registro de obras)',
           'Condecine-Remessa': 'Remessa (lucro ao exterior)', 'Dívida Ativa': 'Dívida ativa'}
f_cond = go.Figure()
for t in TIPOS_CD:
    f_cond.add_bar(x=anos_cd, y=(piv[t] / 1e9), name=NOME_CD[t], marker_color=COR_CD[t])
f_cond.update_layout(barmode='stack')
f_cond.add_vline(x=2011.5, line_dash='dot', line_color=R.CORAL)
f_cond.add_annotation(x=2011.5, y=2.0, text='Lei da TV Paga (12.485/2011)<br>cria a Condecine-Teles',
                      showarrow=False, font=dict(size=10, color=R.CORAL), xanchor='left', xshift=6)
style(f_cond, h=420, xtitle='ano', ytitle='arrecadação CONDECINE (R$ bilhões, nominal)')
f_creal = go.Figure()
f_creal.add_bar(x=anos_real, y=[real_cd[a] / 1e9 for a in anos_real], marker_color=R.CYAN,
                text=[br(real_cd[a] / 1e9, 1) for a in anos_real], textposition='outside', textfont_size=9)
style(f_creal, h=360, xtitle='ano', ytitle='arrecadação CONDECINE (R$ bi de 2024)', showlegend=False)
sh_cd = (piv['Condecine-Teles'] / total_cd * 100)
sh_cd = sh_cd[[a for a in anos_cd if a >= 2012]]
f_teles = go.Figure()
f_teles.add_scatter(x=sh_cd.index.tolist(), y=sh_cd.values, mode='lines+markers', line=dict(color=R.ACCENT, width=3),
                    fill='tozeroy', fillcolor='rgba(108,123,247,.10)')
f_teles.add_hline(y=sh_cd.mean(), line_dash='dot', line_color=R.MUT,
                  annotation_text=f'média {br(sh_cd.mean(),0)}%', annotation_font_size=10, annotation_font_color=R.MUT)
style(f_teles, h=320, xtitle='ano', ytitle='% da CONDECINE que vem da Teles', showlegend=False)
f_teles.update_yaxes(range=[0, 100])
bridge = pd.DataFrame({'ano': anos_real, 'condecine_real_mi': [real_cd[a] / 1e6 for a in anos_real]})
bridge = bridge.merge(VA[['ano', 'fsa_mi']], on='ano', how='left')
bridge = bridge[bridge.ano.between(2012, 2022)]
f_ponte = go.Figure()
f_ponte.add_bar(x=bridge.ano, y=bridge.condecine_real_mi, name='CONDECINE arrecadada (real)', marker_color=R.CYAN)
f_ponte.add_scatter(x=bridge.ano, y=bridge.fsa_mi, name='aporte FSA comprometido', mode='lines+markers',
                    line=dict(color=R.CORAL, width=3), marker=dict(size=7))
style(f_ponte, h=390, xtitle='ano', ytitle='R$ milhões de 2024',
      title='Fonte arrecadada × FSA aplicado: o dinheiro não vira política automaticamente')

vb = VA[(VA.ano >= 2013) & (VA.ano <= 2023)]
f_frz = go.Figure(go.Bar(x=vb.ano, y=vb.fsa_mi,
                         marker_color=[R.CORAL if a in (2019, 2020, 2021) else R.ACCENT for a in vb.ano],
                         text=[br(v, 0) for v in vb.fsa_mi], textposition='outside'))
f_frz.add_annotation(x=2020, y=vb.fsa_mi.max() * 0.6, text='paralisação<br>2019–2021', showarrow=False,
                     font=dict(color=R.CORAL, size=12.5))
style(f_frz, h=390, ytitle='aporte FSA comprometido (R$ 2024 mi)', xtitle='ano do contrato', showlegend=False)
f_seats = go.Figure()
for nome, q, cor in [('Ministério da Cultura', 2, R.ACCENT), ('Ancine', 1, R.CYAN),
                     ('Agente financeiro (BNDES)', 1, R.PURPLE), ('Indústria audiovisual', 2, R.GREEN)]:
    f_seats.add_bar(y=['Comitê Gestor<br>do FSA'], x=[q], orientation='h', name=f'{nome} ({q})', marker_color=cor,
                    text=[nome], textposition='inside', insidetextanchor='middle', textfont=dict(size=11))
f_seats.update_layout(barmode='stack')
style(f_seats, h=185, xtitle='assentos — 4 de 6 são do poder público; sem PAI aprovado, nada flui', showlegend=False)
f_seats.update_xaxes(dtick=1)
f_regras = go.Figure()
f_regras.add_bar(x=RA.ano, y=RA.n_chamadas, name='chamadas distintas', marker_color=R.ACCENT,
                 text=[br(v, 0) for v in RA.n_chamadas], textposition='auto')
f_regras.add_scatter(x=RA.ano, y=RA.n_mecanismos, name='mecanismos distintos', mode='lines+markers',
                     line=dict(color=R.GOLD, width=3), marker=dict(size=8), yaxis='y2')
f_regras.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False, title='mecanismos', range=[0, 10]))
style(f_regras, h=360, ytitle='nº de chamadas distintas', xtitle='ano')
ordm = [c for c in ['Arranjos Regionais', 'Bilheteria·Produtora', 'Bilheteria·Distribuidora', 'Festivais·Pontuação',
        'Complementação', 'Coprodução', 'Automático Bilheteria', 'Automático Festivais'] if c in MX.columns]
f_mix = go.Figure()
for c, cor in zip(ordm, [R.GOLD, R.CYAN, R.ACCENT, R.PURPLE, R.MUT, R.GREEN, '#f97316', R.CORAL]):
    f_mix.add_bar(x=MX.index, y=MX[c], name=c, marker_color=cor)
f_mix.update_layout(barmode='stack')
style(f_mix, h=400, ytitle='obras por mecanismo (início de produção)', xtitle='ano')
f_defas = go.Figure()
f_defas.add_bar(x=AP.ano, y=AP.aporte_fsa_mi, name='aporte comprometido (FSA total)', marker_color=R.ACCENT, opacity=0.85)
f_defas.add_scatter(x=AP.ano, y=AP.producao_fsa_cinema_mi, name='produção que estreou (FSA-cinema)',
                    mode='lines+markers', line=dict(color=R.GREEN, width=3), marker=dict(size=7), yaxis='y2')
f_defas.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False, title='produção FSA-cinema (R$ mi)', title_font_size=12))
style(f_defas, h=360, ytitle='aporte comprometido (R$ mi)', xtitle='ano')

f_macro = go.Figure()
f_macro.add_vrect(x0=2013.5, x1=2019.5, fillcolor=R.ACCENT, opacity=0.06, line_width=0,
                  annotation_text='overlap 2014–2019 (n=6)', annotation_position='top left',
                  annotation_font_size=10, annotation_font_color=R.MUT)
f_macro.add_scatter(x=mp.ano, y=mp.pib_prod_mi, name='VA cadeia do cinema (R$2024 mi)',
                    line=dict(color=R.GOLD, width=3), connectgaps=False)
f_macro.add_scatter(x=mp.ano, y=mp.fsa_mi, name='FSA (R$2024 mi)', line=dict(color=R.ACCENT, width=3), connectgaps=False)
style(f_macro, h=380, xtitle='ano', ytitle='R$ 2024 milhões')
ex = mp[mp.exporta_usd_mi.notna()].copy()
f_exp = go.Figure()
f_exp.add_bar(x=ex.ano, y=ex.exporta_usd_mi, name='exportação (US$ mi)', marker_color=R.GREEN,
              text=[br(v, 0) for v in ex.exporta_usd_mi], textposition='auto')
f_exp.add_scatter(x=ex.ano, y=ex.saldo_usd_mi, name='saldo comercial (US$ mi)', mode='lines+markers',
                  line=dict(color=R.CORAL, width=3), marker=dict(size=8))
f_exp.add_hline(y=0, line_dash='dot', line_color=R.MUT)
style(f_exp, h=340, xtitle='ano', ytitle='US$ milhões (serviços audiovisuais)')

META_LONGAS, TICKET_DESEJADO, PRODECINE_PAI = 150, 5, 500
f_meta = go.Figure(go.Bar(
    x=['Vale aplicado<br>2019', 'Último PAI<br>Prodecine', 'Meta 150×R$5 mi', 'Pico aplicado<br>2018'],
    y=[gn4['aporte_vale_mi'], PRODECINE_PAI, META_LONGAS * TICKET_DESEJADO, gn4['aporte_pico_mi']],
    marker_color=[R.CORAL, R.GOLD, R.CYAN, R.ACCENT],
    text=[br(gn4['aporte_vale_mi'], 0), br(PRODECINE_PAI, 0), br(META_LONGAS * TICKET_DESEJADO, 0), br(gn4['aporte_pico_mi'], 0)],
    textposition='auto'))
style(f_meta, h=360, ytitle='R$ milhões (dez/2024 quando observado)', showlegend=False,
      title='Escala da proposta: perto do pico histórico, longe do vale')

# ════════════ VISUALIZAÇÕES CURADAS DO PAINEL LEGADO (desenho migrado, dados atuais) ════════════
BNO['bilheteria_deflac'] = pd.to_numeric(BNO['bilheteria_deflac'], errors='coerce')
BNO['investimento_fsa_deflac'] = pd.to_numeric(BNO['investimento_fsa_deflac'], errors='coerce')
BNO['roi_internacional_0_100'] = pd.to_numeric(BNO['roi_internacional_0_100'], errors='coerce')
BNO['adm_eu_lumiere'] = pd.to_numeric(BNO['adm_eu_lumiere'], errors='coerce')
b_fsa = BNO[BNO.investimento_fsa_deflac.fillna(0) > 0].copy()

# Ranking · top 15 obras por bilheteria (retorno doméstico)
tb = b_fsa.nlargest(15, 'bilheteria_deflac').sort_values('bilheteria_deflac')
f_topdom = go.Figure(go.Bar(
    y=[t[:38] for t in tb.titulo], x=tb.bilheteria_deflac / 1e6, orientation='h', marker_color=R.GREEN,
    customdata=list(zip(tb.categoria, tb.ano.astype(int))),
    text=[f'R$ {br(v/1e6,1)} mi' for v in tb.bilheteria_deflac], textposition='auto',
    hovertemplate='%{y}<br>R$ %{x:.1f} mi · %{customdata[0]} · %{customdata[1]}<extra></extra>'))
style(f_topdom, h=470, xtitle='bilheteria deflacionada (R$ mi de 2024) — obras com FSA, top 15', showlegend=False)
f_topdom.update_yaxes(automargin=True)

# Rankings por CATEGORIA DE CHAMADA — SEMPRE EM PAR doméstico·internacional (pedidos 12/07;
# '_tv_excluir' fora, como no restante do painel)
BNO['receita_total_deflac'] = pd.to_numeric(BNO['receita_total_deflac'], errors='coerce')
b_cat = b_fsa[b_fsa.categoria != '_tv_excluir'].copy()
b_cat['receita_total_deflac'] = pd.to_numeric(b_cat['receita_total_deflac'], errors='coerce')
tc_ = (b_cat.groupby('categoria', as_index=False)
       .agg(bilheteria=('bilheteria_deflac', 'sum'), receita=('receita_total_deflac', 'sum'),
            fsa=('investimento_fsa_deflac', 'sum'), admeu=('adm_eu_lumiere', 'sum'),
            int_med=('roi_internacional_0_100', 'mean'), obras=('titulo', 'count')))
tc_['roi_dom'] = tc_.receita / tc_.fsa

_t = tc_.sort_values('bilheteria')
f_rk_cat = go.Figure(go.Bar(
    y=[c[:44] for c in _t.categoria], x=_t.bilheteria / 1e6, orientation='h', marker_color=R.GOLD,
    customdata=list(zip(_t.obras, _t.fsa / 1e6)),
    text=[f'R$ {br(v/1e6,0)} mi' for v in _t.bilheteria], textposition='auto',
    hovertemplate='%{y}<br>bilheteria R$ %{x:.0f} mi · %{customdata[0]} obras · FSA R$ %{customdata[1]:.0f} mi<extra></extra>'))
style(f_rk_cat, h=420, xtitle='bilheteria deflacionada acumulada (R$ mi de 2024) por categoria de chamada', showlegend=False)
f_rk_cat.update_yaxes(automargin=True)

_t = tc_.sort_values('admeu')
f_rk_cat_int = go.Figure(go.Bar(
    y=[c[:44] for c in _t.categoria], x=_t.admeu, orientation='h', marker_color=R.CYAN,
    customdata=list(zip(_t.obras, _t.int_med)),
    text=[br(v, 0) for v in _t.admeu], textposition='auto',
    hovertemplate='%{y}<br>%{x:,.0f} admissões EU · %{customdata[0]} obras · índice intl médio %{customdata[1]:.1f}<extra></extra>'))
style(f_rk_cat_int, h=420, xtitle='admissões em salas na Europa (Lumière) acumuladas por categoria de chamada', showlegend=False)
f_rk_cat_int.update_yaxes(automargin=True)

# O PAR de indicadores principais por categoria (retorno doméstico agregado · retorno internacional médio)
tc5 = tc_[tc_.obras >= 5]
_t = tc5.sort_values('roi_dom')
f_roi_dom_cat = go.Figure(go.Bar(
    y=[c[:44] for c in _t.categoria], x=_t.roi_dom, orientation='h', marker_color=R.GREEN,
    customdata=list(zip(_t.obras,)), text=[br(v, 2) for v in _t.roi_dom], textposition='auto',
    hovertemplate='%{y}<br>retorno doméstico agregado %{x:.2f} · %{customdata[0]} obras<extra></extra>'))
style(f_roi_dom_cat, h=400, xtitle='retorno doméstico agregado (receita de referência ÷ FSA) por categoria — ≥5 obras', showlegend=False)
f_roi_dom_cat.update_yaxes(automargin=True)

_t = tc5.sort_values('int_med')
f_roi_int_cat = go.Figure(go.Bar(
    y=[c[:44] for c in _t.categoria], x=_t.int_med, orientation='h', marker_color=R.CYAN,
    customdata=list(zip(_t.obras,)), text=[br(v, 1) for v in _t.int_med], textposition='auto',
    hovertemplate='%{y}<br>índice internacional médio %{x:.1f} · %{customdata[0]} obras<extra></extra>'))
style(f_roi_int_cat, h=400, xtitle='retorno internacional médio (índice 0–100) por categoria — ≥5 obras', showlegend=False)
f_roi_int_cat.update_yaxes(automargin=True)

# Dispersão · vocação por categoria (anatomia do sistema numa figura)
f_quad_cat = go.Figure(go.Scatter(
    x=tc5.roi_dom, y=tc5.int_med, mode='markers+text',
    marker=dict(size=(tc5.obras ** 0.5) * 4.4, color=R.PURPLE, opacity=0.75, line=dict(width=1, color='#0b0d14')),
    text=[c.replace('FSA ', '')[:26] for c in tc5.categoria], textposition='top center',
    textfont=dict(size=10, color=R.TXT),
    customdata=list(zip(tc5.obras, tc5.fsa / 1e6)),
    hovertemplate='%{text}<br>ret. doméstico %{x:.2f} · índice intl médio %{y:.1f}<br>%{customdata[0]} obras · FSA R$ %{customdata[1]:.0f} mi<extra></extra>'))
style(f_quad_cat, h=470, xtitle='retorno doméstico agregado (receita ÷ FSA)', ytitle='retorno internacional médio (0–100)', showlegend=False)

# Dispersão · investimento FSA × bilheteria por obra (o clássico "dinheiro compra acesso")
disp = b_fsa[(b_fsa.bilheteria_deflac.fillna(0) > 0)].copy()
f_disp = go.Figure(go.Scatter(
    x=disp.investimento_fsa_deflac / 1e6, y=disp.bilheteria_deflac / 1e6, mode='markers',
    marker=dict(size=6, color=[R.CYAN if v > 0 else R.MUT for v in disp.roi_internacional_0_100.fillna(0)],
                opacity=0.55, line=dict(width=0)),
    customdata=list(zip(disp.titulo.str.slice(0, 40), disp.categoria)),
    hovertemplate='%{customdata[0]}<br>FSA R$ %{x:.2f} mi → bilheteria R$ %{y:.2f} mi<br>%{customdata[1]}<extra></extra>'))
f_disp.update_xaxes(type='log')
f_disp.update_yaxes(type='log')
style(f_disp, h=470, xtitle='investimento FSA por obra (R$ mi, log)',
      ytitle='bilheteria (R$ mi, log) · azul = obra com sinal internacional', showlegend=False)

# Quadrante · mecanismos (doméstico × internacional, bolha = FSA)
qm = dcat.set_index('cat').join(icat.set_index('cat')[['pct_com_intl']], how='inner').reset_index()
f_quadm = go.Figure()
for _, r_ in qm.iterrows():
    f_quadm.add_trace(go.Scatter(
        x=[r_['publico_por_mi_fsa']], y=[r_['pct_com_intl']], mode='markers+text', text=[r_['cat']],
        textposition='top center', textfont=dict(size=10, color=R.MUT),
        marker=dict(size=max(r_['fsa_mi'], 5) ** 0.5 * 2.2 + 6, color=R.ACCENT, opacity=0.85,
                    line=dict(color=R.BG, width=1)),
        customdata=[[int(r_['n']), r_['fsa_mi']]],
        hovertemplate='%{text}<br>%{x:.0f} espect./R$mi · %{y:.0f}% intl<br>%{customdata[0]} obras · R$ %{customdata[1]:.0f} mi FSA<extra></extra>'))
_qx_med, _qy_med = float(qm.publico_por_mi_fsa.median()), float(qm.pct_com_intl.median())
f_quadm.add_vline(x=_qx_med, line_dash='dash', line_color='#2a3050')
f_quadm.add_hline(y=_qy_med, line_dash='dash', line_color='#2a3050')
_qy_max = float(qm.pct_com_intl.max())
f_quadm.add_annotation(x=0, y=_qy_max * 0.99, xref='paper', yref='y', text='Vocação internacional',
                       showarrow=False, font=dict(size=11, color='#3d4566'), xanchor='left')
f_quadm.add_annotation(x=0.99, y=_qy_max * 0.99, xref='paper', yref='y', text='Duplo impacto',
                       showarrow=False, font=dict(size=11, color='#3d4566'), xanchor='right')
f_quadm.add_annotation(x=0, y=_qy_med * 0.2, xref='paper', yref='y', text='Baixo retorno detectado',
                       showarrow=False, font=dict(size=11, color='#3d4566'), xanchor='left')
f_quadm.add_annotation(x=0.99, y=_qy_med * 0.2, xref='paper', yref='y', text='Vocação comercial',
                       showarrow=False, font=dict(size=11, color='#3d4566'), xanchor='right')
f_quadm.update_xaxes(type='log')
style(f_quadm, h=490, xtitle='conversão doméstica (espectadores por R$ mi de FSA, log) — tracejado = medianas',
      ytitle='% das obras com sinal internacional · bolha = FSA investido', showlegend=False)

# Quadrante · produtoras (ROI doméstico × desempenho internacional, cor = perfil)
bp = (b_fsa.groupby('cnpj_n')
      .agg(bilheteria=('bilheteria_deflac', lambda s: s.fillna(0).sum()),
           fsa=('investimento_fsa_deflac', 'sum'),
           desemp=('roi_internacional_0_100', 'mean'),
           admeu=('adm_eu_lumiere', lambda s: s.fillna(0).sum()),
           n=('CPB', 'count')).reset_index())
bp = bp.merge(PTO[['cnpj_n', 'nome']], on='cnpj_n', how='left')
bp['tipo'] = bp.cnpj_n.map(PERFIL_POR_CNPJ)
bp['tipo'] = bp.tipo.fillna('Sem classificação')
bq = bp[bp.fsa > 0].copy()
bq['roi_dom'] = bq.bilheteria / bq.fsa
f_quadp = go.Figure()
for tipo, cor in CORES_TIPO.items():
    sub = bq[bq.tipo == tipo]
    if not len(sub):
        continue
    f_quadp.add_trace(go.Scatter(
        x=sub.roi_dom.clip(lower=0.001), y=sub.desemp.fillna(0), mode='markers', name=tipo,
        marker=dict(size=(sub.fsa / 1e6).clip(lower=0.4) ** 0.5 * 3 + 4, color=cor, opacity=0.75,
                    line=dict(width=0)),
        customdata=list(zip(sub.nome, sub.n.astype(int), sub.fsa / 1e6)),
        hovertemplate='%{customdata[0]}<br>ROI dom %{x:.2f} · desemp intl %{y:.1f}<br>%{customdata[1]} obras · R$ %{customdata[2]:.1f} mi FSA<extra></extra>'))
f_quadp.add_vline(x=1.0, line_dash='dot', line_color=R.CORAL)
f_quadp.update_xaxes(type='log')
style(f_quadp, h=500, xtitle='ROI doméstico da produtora (bilheteria ÷ FSA, log) — pontilhado = recuperação',
      ytitle='desempenho internacional médio (0–100) · bolha = FSA · cor = perfil')

# Rankings · produtoras (FSA captado · bilheteria · admissões Europa)
def rank_prod(col, n, cor, fmt):
    t = bp.nlargest(n, col).sort_values(col)
    return go.Figure(go.Bar(
        y=t.nome, x=t[col] / 1e6 if col != 'admeu' else t[col] / 1e3, orientation='h', marker_color=cor,
        customdata=t.n.astype(int),
        text=[fmt(v) for v in t[col]], textposition='auto',
        hovertemplate='%{y}<br>%{customdata} obras<extra></extra>'))
f_rk_fsa = rank_prod('fsa', 15, R.ACCENT, lambda v: f'R$ {br(v/1e6,0)} mi')
style(f_rk_fsa, h=470, xtitle='FSA captado (R$ mi de 2024) — top 15 produtoras', showlegend=False)
f_rk_fsa.update_yaxes(automargin=True)
f_rk_bil = rank_prod('bilheteria', 15, R.GREEN, lambda v: f'R$ {br(v/1e6,0)} mi')
style(f_rk_bil, h=470, xtitle='bilheteria acumulada (R$ mi de 2024) — top 15 produtoras', showlegend=False)
f_rk_bil.update_yaxes(automargin=True)
f_rk_eu = rank_prod('admeu', 10, R.PURPLE, lambda v: f'{br(v/1e3,0)} mil')
style(f_rk_eu, h=390, xtitle='admissões na Europa (mil, Lumière) — top 10 produtoras', showlegend=False)
f_rk_eu.update_yaxes(automargin=True)

# Timeline · investimento FSA por mecanismo × ano
tl = (b_fsa.groupby(['ano', 'categoria'])['investimento_fsa_deflac'].sum().div(1e6)
      .unstack(fill_value=0).sort_index())
tl = tl[[c for c in tl.columns if tl[c].sum() > 0]]
tl = tl.loc[(tl.index >= 2014) & (tl.index <= 2023)]
f_tl = go.Figure()
paleta_tl = [R.GOLD, R.CYAN, R.ACCENT, R.PURPLE, R.GREEN, '#f97316', R.CORAL, R.MUT, '#94a3b8', '#eab308']
for c, cor in zip(tl.columns, paleta_tl * 3):
    f_tl.add_bar(x=tl.index, y=tl[c], name=str(c)[:28], marker_color=cor)
f_tl.update_layout(barmode='stack')
style(f_tl, h=440, xtitle='ano de início de produção', ytitle='FSA por mecanismo (R$ mi de 2024)')

# Concentração · share acumulado do FSA por nº de produtoras
sh = bp.sort_values('fsa', ascending=False).fsa.cumsum() / bp.fsa.sum() * 100
f_shareN = go.Figure(go.Scatter(x=list(range(1, len(sh) + 1)), y=sh.values, mode='lines',
                                line=dict(color=R.CYAN, width=3), fill='tozeroy', fillcolor='rgba(56,189,248,.10)'))
for n_, lab in [(10, 'top 10'), (45, 'top 10%')]:
    if n_ <= len(sh):
        f_shareN.add_annotation(x=n_, y=sh.iloc[n_ - 1], text=f'{lab}: {br(sh.iloc[n_-1],0)}%',
                                showarrow=True, arrowcolor=R.MUT, font=dict(size=10, color=R.TXT), ay=-24)
style(f_shareN, h=380, xtitle='nº de produtoras (da maior para a menor)', ytitle='% acumulado do FSA', showlegend=False)

# ── Retorno internacional · Europa (mapa + top países VOD + cards) ── universo amplo Lumière
ISO2 = {'AT': ('AUT', 'Áustria'), 'BE': ('BEL', 'Bélgica'), 'BG': ('BGR', 'Bulgária'), 'CH': ('CHE', 'Suíça'),
        'CZ': ('CZE', 'Tchéquia'), 'DE': ('DEU', 'Alemanha'), 'DK': ('DNK', 'Dinamarca'), 'EE': ('EST', 'Estônia'),
        'ES': ('ESP', 'Espanha'), 'FI': ('FIN', 'Finlândia'), 'FR': ('FRA', 'França'), 'GB': ('GBR', 'Reino Unido'),
        'GR': ('GRC', 'Grécia'), 'HR': ('HRV', 'Croácia'), 'HU': ('HUN', 'Hungria'), 'IE': ('IRL', 'Irlanda'),
        'IT': ('ITA', 'Itália'), 'LT': ('LTU', 'Lituânia'), 'LV': ('LVA', 'Letônia'), 'MK': ('MKD', 'Macedônia do Norte'),
        'MT': ('MLT', 'Malta'), 'NL': ('NLD', 'Países Baixos'), 'NO': ('NOR', 'Noruega'), 'PL': ('POL', 'Polônia'),
        'PT': ('PRT', 'Portugal'), 'RO': ('ROU', 'Romênia'), 'RS': ('SRB', 'Sérvia'), 'SE': ('SWE', 'Suécia'),
        'SI': ('SVN', 'Eslovênia'), 'SK': ('SVK', 'Eslováquia'), 'TR': ('TUR', 'Turquia')}
ve = F.cl_local('vod_europa')
ve = ve[ve.tem_brasil == True]
vod_pais = ve.groupby('country')['titulo_original'].nunique().sort_values(ascending=False)
vod_pais = vod_pais[[c in ISO2 for c in vod_pais.index]]
vod_titulos = int(ve.titulo_original.nunique())
be2 = F.cl_local('bilheteria_europa')
be2 = be2[be2.tem_brasil == True]
adm_eu_all = pd.to_numeric(be2.admissoes_1996_2026, errors='coerce')
salas_obras_eu, salas_adm_eu = int((adm_eu_all > 0).sum()), adm_eu_all.sum()
f_mapa_eu = go.Figure(go.Choropleth(
    locations=[ISO2[c][0] for c in vod_pais.index], z=vod_pais.values,
    text=[ISO2[c][1] for c in vod_pais.index],
    colorscale=[[0, '#161922'], [0.5, '#33406e'], [1, R.ACCENT]],
    marker_line_color=R.GRID, marker_line_width=0.6,
    colorbar=dict(title=dict(text='títulos', font=dict(size=11)), tickfont=dict(size=10), thickness=12, len=0.8),
    hovertemplate='%{text}<br>%{z} títulos brasileiros em VOD<extra></extra>'))
f_mapa_eu.update_geos(scope='europe', bgcolor=R.SURF, showland=True, landcolor='#12151e',
                      showcountries=True, countrycolor='#232838', showcoastlines=False, showframe=False,
                      lataxis_range=[33, 72], lonaxis_range=[-13, 42])
f_mapa_eu.update_layout(paper_bgcolor=R.SURF, font=dict(family='Inter', color=R.TXT, size=12),
                        margin=dict(l=10, r=10, t=16, b=10), height=470)
top_vod = vod_pais.head(15).sort_values()
f_topvod = go.Figure(go.Bar(y=[ISO2[c][1] for c in top_vod.index], x=top_vod.values, orientation='h',
                            marker_color=R.ACCENT, text=top_vod.values, textposition='auto'))
style(f_topvod, h=460, xtitle='nº de títulos brasileiros em catálogos VOD, por país (Lumière)', showlegend=False)
f_topvod.update_yaxes(automargin=True)
cards_intl = stat_grid([
    stat(f'{br(gni["fest_participacoes_total"],0)}', f'participações em festivais internacionais ({br(gni["n_com_festival"],0)} obras do recorte FSA-cinema)', 'res'),
    stat(f'{br(vod_titulos,0)} <small>títulos</small>', f'brasileiros em VOD na Europa, em {len(vod_pais)} países (Lumière, universo amplo)', 'inv'),
    stat(f'{br(salas_obras_eu,0)} <small>obras</small>', f'brasileiras com bilheteria em salas europeias · {br(salas_adm_eu/1e6,1)} mi de admissões (Lumière/CNC, 1996–2026)', 'inv'),
])

# ── Grupos de financiamento por OBRA (tabela-resumo + dispersão inv×ROI, desenho da Visão Geral curada) ──
BNO['receita_total_deflac'] = pd.to_numeric(BNO['receita_total_deflac'], errors='coerce')
BNO['investimento_total_deflac'] = pd.to_numeric(BNO['investimento_total_deflac'], errors='coerce')
BNO['investimento_renuncia_total_deflac'] = pd.to_numeric(BNO['investimento_renuncia_total_deflac'], errors='coerce')
bg = BNO[(BNO.investimento_total_deflac.fillna(0) > 0)].copy()
_fsa, _ren = bg.investimento_fsa_deflac.fillna(0), bg.investimento_renuncia_total_deflac.fillna(0)
bg['grupo'] = 'FSA puro'
bg.loc[(_fsa == 0) & (_ren > 0), 'grupo'] = 'Renúncia pura'
bg.loc[(_fsa > 0) & (_ren > 0) & (_fsa >= _ren), 'grupo'] = 'FSA+Ren · FSA maj.'
bg.loc[(_fsa > 0) & (_ren > 0) & (_fsa < _ren), 'grupo'] = 'FSA+Ren · Ren. maj.'
COR_G = {'Renúncia pura': R.GOLD, 'FSA puro': R.CYAN, 'FSA+Ren · FSA maj.': R.GREEN, 'FSA+Ren · Ren. maj.': R.PURPLE}
gagg = (bg.groupby('grupo')
        .agg(n=('CPB', 'count'), inv=('investimento_total_deflac', 'sum'),
             bilh=('bilheteria_deflac', lambda s: s.fillna(0).sum()),
             rec=('receita_total_deflac', lambda s: s.fillna(0).sum()),
             intl=('roi_internacional_0_100', 'mean'),
             pct_intl=('roi_internacional_0_100', lambda s: 100 * (s.fillna(0) > 0).mean()))
        .reindex(['Renúncia pura', 'FSA puro', 'FSA+Ren · FSA maj.', 'FSA+Ren · Ren. maj.']))
tab_grupos = tabela(
    ['Grupo', 'Obras', 'Inv. total', 'Bilheteria', 'ROI dom. (pond.)', 'Desemp. intl (méd.)', '% c/ intl'],
    [[g, f'{int(r.n)}', f'R$ {br(r.inv/1e9,2)} bi', f'R$ {br(r.bilh/1e9,2)} bi',
      f'{br(r.rec/r.inv,2)}x', f'{br(r.intl,1)}', f'{br(r.pct_intl,1)}%']
     for g, r in gagg.iterrows()])
dispg = bg[(bg.receita_total_deflac.fillna(0) > 0)].copy()
dispg['roi_dom'] = dispg.receita_total_deflac / dispg.investimento_total_deflac
f_disp_grupo = go.Figure()
for g, cor in COR_G.items():
    sub = dispg[dispg.grupo == g]
    f_disp_grupo.add_trace(go.Scatter(
        x=sub.investimento_total_deflac / 1e6, y=sub.roi_dom, mode='markers', name=g,
        marker=dict(size=6, color=cor, opacity=0.55, line=dict(width=0)),
        customdata=sub.titulo.str.slice(0, 40),
        hovertemplate='%{customdata}<br>inv R$ %{x:.2f} mi · ROI dom %{y:.2f}<extra>' + g + '</extra>'))
f_disp_grupo.add_hline(y=1.0, line_dash='dot', line_color=R.CORAL)
f_disp_grupo.update_xaxes(type='log')
f_disp_grupo.update_yaxes(type='log')
style(f_disp_grupo, h=490, xtitle='investimento total por obra (R$ mi, log)',
      ytitle='ROI doméstico da obra (receita ÷ investimento, log)')

# ── Ranking desempenho internacional por mecanismo ──
icat_o = icat.sort_values('desemp_intl_medio')
f_rank_intl = go.Figure(go.Bar(y=icat_o.cat, x=icat_o.desemp_intl_medio, orientation='h', marker_color=R.PURPLE,
                               text=[br(v, 1) for v in icat_o.desemp_intl_medio], textposition='auto'))
style(f_rank_intl, h=430, xtitle='desempenho internacional médio (0–100) por mecanismo', showlegend=False)
f_rank_intl.update_yaxes(automargin=True)

# ── Chamadas detalhadas (tabela, desenho da aba "Chamadas Detalhadas" curada) ──
ch = (bg[bg.investimento_fsa_deflac.fillna(0) > 0]
      .groupby(['chamada', 'categoria'])
      .agg(obras=('CPB', 'count'), fsa=('investimento_fsa_deflac', 'sum'),
           inv=('investimento_total_deflac', 'sum'),
           rec=('receita_total_deflac', lambda s: s.fillna(0).sum()),
           intl=('roi_internacional_0_100', 'mean'))
      .reset_index().sort_values('obras', ascending=False).head(25))
tab_chamadas = tabela(
    ['Chamada', 'Categoria', 'Obras', 'FSA (mi)', 'ROI dom. (pond.)', 'Desemp. intl'],
    [[str(r.chamada)[:52], str(r.categoria)[:34], f'{int(r.obras)}', f'R$ {br(r.fsa/1e6,1)}',
      f'{br(r.rec/r.inv,2) if r.inv else "—"}x', f'{br(r.intl,1)}']
     for r in ch.itertuples()])

# ── Cards de perfil (desenho dos cluster-cards curados) ──
DESC_TIPO = {
    'Duplo Retorno': 'recupera em sala e circula fora (receita ≥ R$ 2,5 mi e melhor internacional ≥ 13)',
    'Retorno Doméstico': 'receita ≥ R$ 10 mi, ou retorno > 0,6 com receita ≥ R$ 2,5 mi, sem internacional qualificado',
    'Retorno Internacional': 'melhor internacional ≥ 13 sem o piso de receita: prestígio externo, bilheteria pequena',
    'Fomento Baixo Retorno': 'mais de R$ 5 mi recebidos sem retorno em nenhuma das duas dimensões',
    'Pequeno Porte com algum retorno': 'abaixo dos limiares, mas devolveu alguma coisa',
    'Pequeno Porte sem retorno': 'abaixo dos limiares e nenhuma obra chegou à sala'}
cards_tipos = '<div class="clcards">' + ''.join(
    f'<div class="clc" style="border-top-color:{CORES_TIPO.get(r.k, R.ACCENT)}">'
    f'<div class="clc-h"><span>{r.k}</span><b>{int(r.n_produtoras)}</b></div>'
    f'<div class="clc-d">{DESC_TIPO.get(r.k, "")}</div>'
    f'<div class="clc-m"><span>% do FSA</span><b>{br(r.pct_fsa,1)}%</b></div>'
    f'<div class="clc-m"><span>ROI doméstico</span><b>{br(r.roi_fsa_crt,2)}</b></div>'
    f'<div class="clc-m"><span>Espect./R$ mi</span><b>{br(r.pub_por_mi_fsa,0)}</b></div>'
    f'<div class="clc-m"><span>Recorrentes</span><b>{br(r.pct_recorrente,0)}%</b></div></div>'
    for r in TT.itertuples()) + '</div>'

# ── Dispersão produtoras: investimento × ROI doméstico (desenho "Por cluster" curado) ──
bqq = bq.copy()
f_disp_prod = go.Figure()
for tipo, cor in CORES_TIPO.items():
    sub = bqq[bqq.tipo == tipo]
    if not len(sub):
        continue
    f_disp_prod.add_trace(go.Scatter(
        x=sub.fsa / 1e6, y=sub.roi_dom.clip(lower=0.001), mode='markers', name=tipo,
        marker=dict(size=sub.n.clip(upper=30) * 1.6 + 5, color=cor, opacity=0.7, line=dict(width=0)),
        customdata=list(zip(sub.nome, sub.n.astype(int))),
        hovertemplate='%{customdata[0]}<br>FSA R$ %{x:.2f} mi · ROI dom %{y:.2f} · %{customdata[1]} obras<extra></extra>'))
f_disp_prod.add_hline(y=1.0, line_dash='dot', line_color=R.CORAL)
f_disp_prod.update_xaxes(type='log')
f_disp_prod.update_yaxes(type='log')
style(f_disp_prod, h=500, xtitle='FSA captado pela produtora (R$ mi, log)',
      ytitle='ROI doméstico (bilheteria ÷ FSA, log) · bolha = nº de obras')

# ── Tabelas-ranking: top produtoras e top filmes ──
tp = bp.nlargest(20, 'bilheteria')
tab_top_prod = tabela(
    ['#', 'Produtora', 'Perfil', 'Obras', 'FSA (mi)', 'Bilheteria (mi)', 'ROI dom.', 'Desemp. intl'],
    [[f'{i+1}', r.nome, str(r.tipo), f'{int(r.n)}', f'R$ {br(r.fsa/1e6,1)}', f'R$ {br(r.bilheteria/1e6,1)}',
      f'{br(r.bilheteria/r.fsa,2) if r.fsa else "—"}', f'{br(r.desemp,1) if pd.notna(r.desemp) else "—"}']
     for i, r in enumerate(tp.itertuples())])
tf = bg[(bg.investimento_total_deflac >= 1e6) & (bg.receita_total_deflac.fillna(0) > 0)].copy()
tf['roi_dom'] = tf.receita_total_deflac / tf.investimento_total_deflac
tf = tf.nlargest(20, 'roi_dom')
tab_top_filmes = tabela(
    ['#', 'Filme', 'Ano', 'Categoria', 'Inv. (mi)', 'Bilheteria (mi)', 'ROI dom.', 'Desemp. intl'],
    [[f'{i+1}', str(r.titulo)[:40], f'{int(r.ano)}', str(r.categoria)[:30], f'R$ {br(r.investimento_total_deflac/1e6,1)}',
      f'R$ {br((r.bilheteria_deflac or 0)/1e6,1)}', f'{br(r.roi_dom,2)}x',
      f'{br(r.roi_internacional_0_100,1) if pd.notna(r.roi_internacional_0_100) else "—"}']
     for i, r in enumerate(tf.itertuples())])

# ── Ticket anual combinado (fomento anualizado + proxy RLP 15%) — desenho da aba curada ──
tk = (bg.groupby('cnpj_n')
      .agg(fom=('investimento_total_deflac', 'sum'), rec=('receita_total_deflac', lambda s: s.fillna(0).sum()))
      .reset_index())
ANOS_TK = 10
tk['ticket_anual'] = tk.fom / ANOS_TK
tk['rlp_anual'] = 0.15 * tk.rec / ANOS_TK
tk['comb'] = tk.ticket_anual + tk.rlp_anual
BINS = [0, 100e3, 200e3, 300e3, 500e3, 750e3, 1e6, 1.5e6, 2e6, 3e6, 5e6, 10e6, float('inf')]
LABELS = ['0–100k', '100–200k', '200–300k', '300–500k', '500–750k', '750k–1M', '1–1,5M', '1,5–2M', '2–3M', '3–5M', '5–10M', '10M+']
tk['faixa'] = pd.cut(tk.comb, bins=BINS, labels=LABELS, right=False)
hist_tk = tk.faixa.value_counts().reindex(LABELS).fillna(0).astype(int)
CORES_TK = [R.CORAL] * 4 + [R.GOLD] * 2 + [R.GREEN] * 3 + ['#94a3b8'] * 3
f_ticket_hist = go.Figure(go.Bar(x=LABELS, y=hist_tk.values, marker_color=CORES_TK,
                                 text=hist_tk.values, textposition='outside'))
f_ticket_hist.add_vline(x=3.5, line_dash='dash', line_color=R.GOLD)
f_ticket_hist.add_annotation(x=3.5, y=max(hist_tk.values) * 0.92, text='custo fixo mínimo<br>~R$ 400 mil/ano',
                             showarrow=False, font=dict(size=10.5, color=R.GOLD), xanchor='left', xshift=6)
style(f_ticket_hist, h=430, xtitle='ticket anual combinado (fomento anualizado + proxy RLP), por produtora',
      ytitle='nº de produtoras', showlegend=False)
abaixo_400k = int((tk.comb < 400e3).sum())
cards_ticket = stat_grid([
    stat(f'R$ {br(tk.fom.sum()/ANOS_TK/1e6,0)} <small>mi/ano</small>', 'fomento anualizado (investimento total do período ÷ 10 anos)', 'inv'),
    stat(f'R$ {br(tk.rlp_anual.sum()/1e6,0)} <small>mi/ano</small>', 'proxy da RLP anualizada (15% da receita estimada ÷ 10 anos)', 'inv'),
    stat(f'R$ {br(tk.comb.median()/1e3,0)} <small>mil/ano</small>', 'ticket anual combinado MEDIANO por produtora', 'res'),
    stat(f'{br(100*abaixo_400k/len(tk),0)}%', f'das {len(tk)} produtoras ficam abaixo do custo fixo mínimo (~R$ 400 mil/ano)', 'res'),
])

# ── Pergunta 7 · capacidade de carga: o que cada orçamento compra ─────────────
# As duas identidades da pergunta 6, desenhadas: orçamento ÷ ticket = filmes/ano,
# e filmes/ano ÷ ritmo = empresas sustentadas. Os rótulos escrevem os números que
# o texto cita, para que a âncora tenha veredito 'forte' na verificação.
_TICKETS = [IND['ticket_fsa_mediano_mi'], 3.2, 5.0, 7.0]
_ORC = [(500, R.MUT, 'R$ 500 mi (PAI do PRODECINE)'), (750, R.CYAN, 'R$ 750 mi (proposto)')]
f_carga = go.Figure()
for _o, _cor, _lab in _ORC:
    _n = [_o / t for t in _TICKETS]
    f_carga.add_bar(x=[f'R$ {br(t, 2)} mi' for t in _TICKETS], y=_n, name=_lab,
                    marker_color=_cor, text=[br(v, 0) for v in _n], textposition='outside')
f_carga.add_hline(y=IND['filmes_br_ano'], line=dict(color=R.CORAL, dash='dot'),
                  annotation_text=f"teto de mercado — {br(IND['filmes_br_ano'], 0)} "
                                  f"filmes brasileiros lançados por ano",
                  annotation_position='top right',
                  annotation_font=dict(color=R.CORAL, size=11))
f_carga.update_layout(barmode='group')
style(f_carga, h=420, xtitle='ticket por filme (parcela do FSA)',
      ytitle='filmes financiados por ano')

# a mesma conta traduzida em empresas: filmes/ano ÷ ritmo de 1 filme a cada 2 anos
f_carga_emp = go.Figure()
for _o, _cor, _lab in _ORC:
    _e = [(_o / t) * 2 for t in _TICKETS]
    f_carga_emp.add_bar(x=[f'R$ {br(t, 2)} mi' for t in _TICKETS], y=_e, name=_lab,
                        marker_color=_cor, text=[br(v, 0) for v in _e],
                        textposition='outside')
f_carga_emp.add_hline(y=IND['empresas_ritmo5'], line=dict(color=R.GOLD, dash='dot'),
                      annotation_text=f"hoje: {br(IND['empresas_ritmo5'], 0)} empresas "
                                      f"nesse ritmo",
                      annotation_position='top right',
                      annotation_font=dict(color=R.GOLD, size=11))
f_carga_emp.update_layout(barmode='group')
style(f_carga_emp, h=420, xtitle='ticket por filme (parcela do FSA)',
      ytitle='empresas sustentadas a 1 filme a cada 2 anos')

# renovação: entra muita gente, quase ninguém chega ao segundo filme
f_renov = go.Figure(go.Bar(
    x=['empresas com obra<br>no período', 'estrearam<br>no período',
       'voltaram a produzir'],
    y=[IND['empresas_periodo'], IND['entrantes_periodo'], IND['entrantes_repetiram']],
    marker_color=[R.MUT, R.CYAN, R.GREEN],
    text=[br(IND['empresas_periodo'], 0), br(IND['entrantes_periodo'], 0),
          br(IND['entrantes_repetiram'], 0)], textposition='auto'))
style(f_renov, h=360, ytitle='empresas', showlegend=False)

# os dois pisos por obra: onde o aporte deixa de comprar sala e passa a comprar público
_FX = [('ate1mi', '< R$ 1 mi'), ('1a2mi', 'R$ 1–2 mi'), ('2a3mi', 'R$ 2–3 mi'),
       ('3a5mi', 'R$ 3–5 mi'), ('mais5mi', '> R$ 5 mi')]
_fx = [(lab, IND[f'piso_{k}_estreia'], IND[f'piso_{k}_publico_med'])
       for k, lab in _FX if f'piso_{k}_estreia' in IND]
f_piso = go.Figure()
f_piso.add_bar(x=[l for l, _, _ in _fx], y=[e for _, e, _ in _fx], name='% que estreia em sala',
               marker_color=R.CYAN, text=[br(e, 1) + '%' for _, e, _ in _fx],
               textposition='auto')
f_piso.add_scatter(x=[l for l, _, _ in _fx], y=[p for _, _, p in _fx], name='público mediano',
                   mode='lines+markers+text', yaxis='y2', line=dict(color=R.GOLD, width=2),
                   text=[br(p, 0) for _, _, p in _fx], textposition='top center',
                   textfont=dict(color=R.GOLD, size=11))
f_piso.update_layout(yaxis2=dict(overlaying='y', side='right', type='log',
                                 title='público mediano (log)', showgrid=False))
style(f_piso, h=400, xtitle='faixa de aporte do FSA por obra', ytitle='% que estreia em sala')

# ════════════ COMPONENTES INTERATIVOS (estilo do painel curado: busca/filtro/ordenação) ════════════
_it_n = [0]


def _jesc(o):
    """JSON p/ <script type=application/json> (protege </script>)."""
    return json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _r(v, d=2):
    return None if pd.isna(v) else round(float(v), d)


PAL_CHIP = [R.ACCENT, R.CYAN, R.GOLD, R.GREEN, R.PURPLE, R.CORAL, '#f97316', '#22d3ee',
            '#c084fc', '#eab308', '#fb7185', '#94a3b8']


def chip_pal(values, fixed=None):
    """Paleta estável de chips: cores fixas onde importa, resto por ordem alfabética."""
    pal = dict(fixed or {})
    i = 0
    for v in sorted({str(x) for x in values if x not in (None, '')}):
        if v in pal:
            continue
        pal[v] = PAL_CHIP[i % len(PAL_CHIP)]
        i += 1
    return pal


def itable(cols, rows, search=(), filters=(), sort0=None, note='', maxh=560,
           pills=None, chips=None, sorts=(), rank=False, _doc=''):
    """Tabela-ranking interativa — o desenho das tabelas do painel curado.
    cols: [(key, rótulo, tipo)]
      tipo: 's' texto · 'y' ano · 'i' inteiro · 'nD' número · 'rD' R$ · 'pD' % · 'xD' multiplicador
            'g'  → CHIP colorido (cor por valor, via `chips`)
            'B'+tipo (ex.: 'Bx2', 'Br1') → número COM MINI-BARRA proporcional ao máximo da coluna
    rank=True         → primeira coluna "#" com a posição na ordenação corrente
    pills=(key, rót.) → filtro em PILLS com contagem por valor (em vez de <select>)
    chips={key: {valor: cor}} → paleta dos chips
    sorts=[(key, rótulo)]     → seletor de ordenação explícito (além do clique no cabeçalho)
    rows: [dict] (strings já escapadas); search: [keys]; filters: [(key, rótulo)]; sort0: (key, 'desc'|'asc')."""
    _it_n[0] += 1
    tid = f'it{_it_n[0]}'
    cfg = {'cols': [{'k': k, 'l': l, 't': t} for k, l, t in cols],
           'search': list(search), 'filters': [{'k': k, 'l': l} for k, l in filters],
           'pills': {'k': pills[0], 'l': pills[1]} if pills else None,
           'chips': chips or {}, 'rank': bool(rank),
           'sorts': [{'k': k, 'l': l} for k, l in sorts],
           'sort': {'k': sort0[0], 'd': sort0[1]} if sort0 else None}
    return (f'<div class="itab js-itab" id="{tid}" data-maxh="{maxh}"></div>'
            + (f'<div class="cap">{note}</div>' if note else '')
            + f'<script type="application/json" id="{tid}-c">{_jesc(cfg)}</script>'
              f'<script type="application/json" id="{tid}-d">{_jesc(rows)}</script>')


def metric_rank(items, metrics, label_key='l', top=None, note=''):
    """Ranking com troca de métrica por botão (barras HTML — desenho 'Ranking por Categoria' do painel curado).
    items: [dict rótulo+métricas]; metrics: [(key, rótulo, dec, prefixo, sufixo)]."""
    _it_n[0] += 1
    rid = f'mr{_it_n[0]}'
    cfg = {'metrics': [{'k': k, 'l': l, 'dec': d, 'pre': p, 'suf': s} for k, l, d, p, s in metrics],
           'label': label_key, 'default': metrics[0][0], 'top': top}
    return (f'<div class="mrank js-mrank" id="{rid}"></div>'
            + (f'<div class="cap">{note}</div>' if note else '')
            + f'<script type="application/json" id="{rid}-c">{_jesc(cfg)}</script>'
              f'<script type="application/json" id="{rid}-d">{_jesc(items)}</script>')


def xy_scatter(points, axes=None, combos=None, groups=None, height=520,
               quadrant=False, roi_lines=None, search=True, note='', names=None,
               labels=False, zones=None):
    """Dispersão configurável (desenho das dispersões do painel curado): eixos por select (axes) OU
    combinações fixas por botão (combos) + Lin/Log + busca com destaque dos pontos.
    points: [dict: l rótulo · g grupo · ms tamanho · métricas]; axes: [(key, rótulo)];
    combos: [(xkey, ykey, rótulo, xlog, ylog)]; groups: {grupo: cor}; roi_lines: {ykey: valor}."""
    _it_n[0] += 1
    sid = f'xs{_it_n[0]}'
    cfg = {'axes': [{'k': k, 'l': l} for k, l in axes] if axes else None,
           'combos': [{'x': x, 'y': y, 'l': l, 'lx': lx, 'ly': ly} for x, y, l, lx, ly in combos] if combos else None,
           'groups': groups, 'h': height, 'quad': quadrant, 'roi': roi_lines or {}, 'search': bool(search),
           'names': names, 'labels': bool(labels), 'zones': zones}
    return (f'<div class="xys js-xys" id="{sid}" style="min-height:{height + 78}px"></div>'
            + (f'<div class="cap">{note}</div>' if note else '')
            + f'<script type="application/json" id="{sid}-c">{_jesc(cfg)}</script>'
              f'<script type="application/json" id="{sid}-d">{_jesc(points)}</script>')


def country_bars(rows, sources, note=''):
    """Barras por país com fontes ligáveis/desligáveis (desenho do mapa interativo do painel curado).
    rows: [{'nome': país, <key-fonte>: valor}]; sources: [(key, rótulo, cor, ligada)]."""
    _it_n[0] += 1
    cid_ = f'cb{_it_n[0]}'
    cfg = {'sources': [{'k': k, 'l': l, 'c': c, 'on': on} for k, l, c, on in sources]}
    return (f'<div class="cbar js-cbar" id="{cid_}"></div>'
            + (f'<div class="cap">{note}</div>' if note else '')
            + f'<script type="application/json" id="{cid_}-c">{_jesc(cfg)}</script>'
              f'<script type="application/json" id="{cid_}-d">{_jesc(rows)}</script>')


INTERACT_JS = r"""
(function(){
  function J(id){ return JSON.parse(document.getElementById(id).textContent); }
  function nbr(v, dec){
    if (v === null || v === undefined || isNaN(v)) return '—';
    return (+v).toLocaleString('pt-BR', {minimumFractionDigits: dec, maximumFractionDigits: dec});
  }
  function fmt(v, t){
    if (t === 's') return (v === null || v === undefined || v === '') ? '—' : v;
    if (v === null || v === undefined || isNaN(v)) return '—';
    if (t === 'y') return String(v);
    if (t === 'i') return nbr(v, 0);
    var dec = +t.slice(1) || 0;
    if (t[0] === 'n') return nbr(v, dec);
    if (t[0] === 'r') return 'R$ ' + nbr(v, dec);
    if (t[0] === 'p') return nbr(v, dec) + '%';
    if (t[0] === 'x') return nbr(v, dec) + 'x';
    return v;
  }

  /* ── tabela-ranking: busca + pills + filtros + ordenação + chips + mini-barras ── */
  function initTab(host){
    var cfg = J(host.id + '-c'), data = J(host.id + '-d');
    var st = {q: '', f: {}, p: '', k: cfg.sort ? cfg.sort.k : null, d: (cfg.sort && cfg.sort.d === 'asc') ? 1 : -1};
    /* máximo por coluna de barra — a barra é proporcional ao topo da coluna */
    var maxes = {};
    cfg.cols.forEach(function(c){
      if (c.t[0] !== 'B') return;
      var m = 0;
      data.forEach(function(r){ var v = r[c.k]; if (v !== null && v !== undefined && !isNaN(v)) m = Math.max(m, Math.abs(+v)); });
      maxes[c.k] = m || 1;
    });
    function chipCor(k, v){
      var pal = cfg.chips[k];
      return (pal && pal[v]) ? pal[v] : '#7b849a';
    }
    function cell(r, c, i){
      if (c.t === '#') return '<span class="it-rk">' + (i + 1) + '</span>';
      var v = r[c.k];
      if (c.t === 'g'){
        if (v === null || v === undefined || v === '') return '—';
        var cor = chipCor(c.k, v);
        return '<span class="it-chip" style="color:' + cor + ';border-color:' + cor + '55;background:' + cor + '1a">' + v + '</span>';
      }
      if (c.t[0] === 'B'){
        var t2 = c.t.slice(1);
        if (v === null || v === undefined || isNaN(v)) return '<span class="it-bv">—</span>';
        var w = Math.max(2, 100 * Math.abs(+v) / maxes[c.k]);
        return '<span class="it-bwrap"><span class="it-bar2" style="width:' + w + '%"></span></span>' +
               '<span class="it-bv">' + fmt(v, t2) + '</span>';
      }
      return fmt(v, c.t);
    }
    var bar = '<div class="it-bar">';
    if (cfg.search.length) bar += '<input class="it-q" type="text" placeholder="Buscar…">';
    cfg.filters.forEach(function(f){
      var vals = {};
      data.forEach(function(r){ var v = r[f.k]; if (v !== null && v !== undefined && v !== '') vals[v] = 1; });
      bar += '<select class="it-f" data-k="' + f.k + '"><option value="">' + f.l + ': todos</option>' +
        Object.keys(vals).sort().map(function(v){ return '<option>' + v + '</option>'; }).join('') + '</select>';
    });
    if (cfg.sorts && cfg.sorts.length){
      bar += '<select class="it-so">' + cfg.sorts.map(function(s){
        return '<option value="' + s.k + '"' + (s.k === st.k ? ' selected' : '') + '>' + s.l + ' ↓</option>';
      }).join('') + '</select>';
    }
    bar += '<span class="it-n"></span></div>';
    /* pills com contagem — o filtro por categoria do painel curado */
    if (cfg.pills){
      var cnts = {};
      data.forEach(function(r){ var v = r[cfg.pills.k]; if (v !== null && v !== undefined && v !== '') cnts[v] = (cnts[v] || 0) + 1; });
      var keys = Object.keys(cnts).sort(function(a, b){ return cnts[b] - cnts[a]; });
      bar += '<div class="it-pills"><button class="it-pill on" data-v="">Todos<b>' + data.length + '</b></button>' +
        keys.map(function(v){
          var cor = chipCor(cfg.pills.k, v);
          return '<button class="it-pill" data-v="' + v + '" style="--pc:' + cor + '">' + v + '<b>' + cnts[v] + '</b></button>';
        }).join('') + '</div>';
    }
    var th = (cfg.rank ? '<th class="it-hrk">#</th>' : '') + cfg.cols.map(function(c, ci){
      return '<th' + (ci === 0 ? ' class="it-c0"' : '') + ' data-k="' + c.k + '" data-t="' + c.t +
             '" title="clique para ordenar">' + c.l + '<span class="it-s"></span></th>';
    }).join('');
    host.innerHTML = bar + '<div class="it-wrap" style="max-height:' + (host.dataset.maxh || 560) +
      'px"><table class="dtable it-t"><thead><tr>' + th + '</tr></thead><tbody></tbody></table></div>';
    var tb = host.querySelector('tbody'), cnt = host.querySelector('.it-n');
    function render(){
      var rows = data.filter(function(r){
        for (var k in st.f){ if (st.f[k] && String(r[k]) !== st.f[k]) return false; }
        if (cfg.pills && st.p && String(r[cfg.pills.k]) !== st.p) return false;
        if (st.q){
          var ok = false;
          for (var i = 0; i < cfg.search.length; i++){
            var v = r[cfg.search[i]];
            if (v && String(v).toLowerCase().indexOf(st.q) >= 0){ ok = true; break; }
          }
          if (!ok) return false;
        }
        return true;
      });
      if (st.k){
        var t = 'n';
        cfg.cols.forEach(function(c){ if (c.k === st.k) t = c.t[0] === 'B' ? c.t.slice(1) : c.t; });
        rows.sort(function(a, b){
          var x = a[st.k], y = b[st.k];
          if (t === 's'){
            x = (x === null || x === undefined) ? '' : String(x);
            y = (y === null || y === undefined) ? '' : String(y);
            return st.d * x.localeCompare(y, 'pt-BR');
          }
          x = (x === null || x === undefined || isNaN(x)) ? -Infinity : +x;
          y = (y === null || y === undefined || isNaN(y)) ? -Infinity : +y;
          return st.d * (x - y);
        });
      }
      var cap = 500;
      tb.innerHTML = rows.slice(0, cap).map(function(r, i){
        return '<tr>' + (cfg.rank ? '<td class="it-trk">' + (i + 1) + '</td>' : '') + cfg.cols.map(function(c, ci){
          var num = (c.t !== 's' && c.t !== 'g');
          var kl = [];
          if (c.t[0] === 'B') kl.push('it-bcell');
          if (ci === 0) kl.push('it-c0');                       /* 1ª coluna: congelada */
          else if (c.t === 's') kl.push('it-ss');               /* demais textos: 1 linha + reticências */
          var cls = kl.length ? ' class="' + kl.join(' ') + '"' : '';
          var ttl = (c.t === 's' && r[c.k]) ? ' title="' + String(r[c.k]).replace(/"/g, '&quot;') + '"' : '';
          return '<td' + cls + ttl + (num ? ' style="text-align:right;white-space:nowrap"' : '') + '>' + cell(r, c, i) + '</td>';
        }).join('') + '</tr>';
      }).join('');
      cnt.textContent = rows.length > cap
        ? ('mostrando ' + cap + ' de ' + nbr(rows.length, 0) + ' — refine a busca')
        : (nbr(rows.length, 0) + ' linhas');
      [].slice.call(host.querySelectorAll('th[data-k]')).forEach(function(h){
        h.querySelector('.it-s').textContent = h.dataset.k === st.k ? (st.d > 0 ? ' ↑' : ' ↓') : '';
        h.classList.toggle('on', h.dataset.k === st.k);
      });
      var so2 = host.querySelector('.it-so');
      if (so2 && so2.value !== st.k) so2.value = st.k;
    }
    var q = host.querySelector('.it-q');
    if (q) q.addEventListener('input', function(){ st.q = q.value.trim().toLowerCase(); render(); });
    [].slice.call(host.querySelectorAll('.it-f')).forEach(function(s){
      s.addEventListener('change', function(){ st.f[s.dataset.k] = s.value; render(); });
    });
    var so = host.querySelector('.it-so');
    if (so) so.addEventListener('change', function(){ st.k = so.value; st.d = -1; render(); });
    [].slice.call(host.querySelectorAll('.it-pill')).forEach(function(p){
      p.addEventListener('click', function(){
        st.p = p.dataset.v;
        [].slice.call(host.querySelectorAll('.it-pill')).forEach(function(x){ x.classList.toggle('on', x === p); });
        render();
      });
    });
    [].slice.call(host.querySelectorAll('th[data-k]')).forEach(function(h){
      h.addEventListener('click', function(){
        if (st.k === h.dataset.k) st.d = -st.d; else { st.k = h.dataset.k; st.d = -1; }
        render();
      });
    });
    render();
  }

  /* ── ranking com troca de métrica (barras HTML) ── */
  function initRank(host){
    var cfg = J(host.id + '-c'), data = J(host.id + '-d'), cur = cfg.default;
    host.innerHTML = '<div class="ctrl-bar">' + cfg.metrics.map(function(m){
      return '<button class="ctrl' + (m.k === cur ? ' on' : '') + '" data-k="' + m.k + '">' + m.l + '</button>';
    }).join('') + '</div><div class="mr-rows"></div>';
    var box = host.querySelector('.mr-rows');
    function render(){
      var m = cfg.metrics.filter(function(x){ return x.k === cur; })[0];
      var rows = data.slice().sort(function(a, b){ return (b[m.k] || 0) - (a[m.k] || 0); });
      if (cfg.top) rows = rows.slice(0, cfg.top);
      var max = Math.max.apply(null, rows.map(function(r){ return Math.abs(r[m.k] || 0); })) || 1;
      box.innerHTML = rows.map(function(r, i){
        var v = r[m.k] || 0;
        return '<div class="mr-row"><div class="mr-l" title="' + r[cfg.label] + '">' + (i + 1) + '. ' + r[cfg.label] +
          '</div><div class="mr-bwrap"><div class="mr-b" style="width:' + Math.max(1.5, 100 * Math.abs(v) / max) +
          '%"></div></div><div class="mr-v">' + (m.pre || '') + nbr(v, m.dec) + (m.suf || '') + '</div></div>';
      }).join('');
    }
    [].slice.call(host.querySelectorAll('.ctrl')).forEach(function(b){
      b.addEventListener('click', function(){
        cur = b.dataset.k;
        [].slice.call(host.querySelectorAll('.ctrl')).forEach(function(x){ x.classList.toggle('on', x === b); });
        render();
      });
    });
    render();
  }

  /* ── barras por país com fontes por checkbox ── */
  function initCbar(host){
    var cfg = J(host.id + '-c'), data = J(host.id + '-d');
    host.innerHTML = '<div class="cb-bar">' + cfg.sources.map(function(s){
      return '<label class="cb-l"><input type="checkbox" data-k="' + s.k + '"' + (s.on ? ' checked' : '') +
        '><span class="cb-dot" style="background:' + s.c + '"></span>' + s.l + '</label>';
    }).join('') + '<span class="it-n"></span></div><div class="cb-rows"></div>';
    var box = host.querySelector('.cb-rows'), cnt = host.querySelector('.it-n');
    function render(){
      var on = [].slice.call(host.querySelectorAll('input')).filter(function(i){ return i.checked; })
        .map(function(i){ return i.dataset.k; });
      var rows = data.map(function(r){
        var tot = 0; on.forEach(function(k){ tot += r[k] || 0; });
        return {r: r, tot: tot};
      }).filter(function(x){ return x.tot > 0; }).sort(function(a, b){ return b.tot - a.tot; });
      var max = rows.length ? rows[0].tot : 1;
      box.innerHTML = rows.map(function(x){
        var segs = cfg.sources.filter(function(s){ return on.indexOf(s.k) >= 0 && (x.r[s.k] || 0) > 0; })
          .map(function(s){
            return '<div class="cb-seg" style="width:' + (100 * (x.r[s.k] || 0) / max) + '%;background:' + s.c +
              '" title="' + s.l + ': ' + nbr(x.r[s.k], 0) + '"></div>';
          }).join('');
        return '<div class="mr-row"><div class="mr-l">' + x.r.nome + '</div><div class="mr-bwrap">' + segs +
          '</div><div class="mr-v">' + nbr(x.tot, 0) + '</div></div>';
      }).join('');
      cnt.textContent = rows.length + ' países';
    }
    [].slice.call(host.querySelectorAll('input')).forEach(function(i){ i.addEventListener('change', render); });
    render();
  }

  /* ── dispersão configurável (Plotly; inicializa quando a aba fica visível) ── */
  window._xysInit = function(host){
    if (host.dataset.done || typeof Plotly === 'undefined') return;
    host.dataset.done = '1';
    var cfg = J(host.id + '-c'), data = J(host.id + '-d');
    var st = {q: '', log: true};
    if (cfg.combos){ st.xk = cfg.combos[0].x; st.yk = cfg.combos[0].y; st.lx = cfg.combos[0].lx; st.ly = cfg.combos[0].ly; }
    else { st.xk = cfg.axes[0].k; st.yk = cfg.axes[1].k; st.lx = true; st.ly = true; }
    var bar = '<div class="it-bar">';
    if (cfg.combos){
      bar += cfg.combos.map(function(c, i){
        return '<button class="ctrl' + (i === 0 ? ' on' : '') + '" data-i="' + i + '">' + c.l + '</button>';
      }).join('');
    } else {
      function sel(cls, cur){
        return '<select class="it-f ' + cls + '">' + cfg.axes.map(function(a){
          return '<option value="' + a.k + '"' + (a.k === cur ? ' selected' : '') + '>' + a.l + '</option>';
        }).join('') + '</select>';
      }
      bar += '<span class="xys-lab">X</span>' + sel('xys-x', st.xk) + '<span class="xys-lab">Y</span>' + sel('xys-y', st.yk) +
        '<button class="ctrl xys-lin">Lin</button><button class="ctrl on xys-log">Log</button>';
    }
    if (cfg.search) bar += '<input class="it-q" type="text" placeholder="Destacar…">';
    bar += '<span class="it-n"></span></div>';
    var gd = document.createElement('div');
    host.innerHTML = bar;
    host.appendChild(gd);
    var cnt = host.querySelector('.it-n');
    function axl(k){
      if (cfg.names && cfg.names[k]) return cfg.names[k];
      var l = k;
      (cfg.axes || []).forEach(function(a){ if (a.k === k) l = a.l; });
      return l;
    }
    function draw(){
      var groups = cfg.groups ? Object.keys(cfg.groups) : [null];
      var traces = groups.map(function(g){
        var pts = data.filter(function(p){ return g === null || p.g === g; });
        var op = pts.map(function(p){
          if (!st.q) return 0.7;
          return (p.l && p.l.toLowerCase().indexOf(st.q) >= 0) ? 0.95 : 0.05;
        });
        var cor = g ? cfg.groups[g] : '#6c7bf7';
        /* rotulado = desenho do quadrante curado: bolha OCA (contorno grosso) + rótulo fixo embaixo */
        var tr = {
          type: cfg.labels ? 'scatter' : 'scattergl',
          mode: cfg.labels ? 'markers+text' : 'markers', name: g || '',
          x: pts.map(function(p){ return p[st.xk]; }), y: pts.map(function(p){ return p[st.yk]; }),
          text: pts.map(function(p){ return p.l; }),
          marker: {size: pts.map(function(p){ return p.ms || 7; }),
                   color: cfg.labels ? pts.map(function(p){ return (p.c || cor) + '33'; }) : cor,
                   opacity: op,
                   line: cfg.labels ? {width: 2, color: pts.map(function(p){ return p.c || cor; })} : {width: 0}},
          hovertemplate: '%{text}<br>' + axl(st.xk) + ': %{x:,.3~f}<br>' + axl(st.yk) + ': %{y:,.3~f}<extra>' + (g || '') + '</extra>'
        };
        if (cfg.labels){
          tr.textposition = 'bottom center';
          tr.textfont = {size: 10, family: 'Inter', color: pts.map(function(p){ return p.c || cor; })};
          tr.cliponaxis = false;
        }
        return tr;
      });
      if (st.q){
        var n = data.filter(function(p){ return p.l && p.l.toLowerCase().indexOf(st.q) >= 0; }).length;
        cnt.textContent = n + ' destacado(s)';
      } else cnt.textContent = data.length + ' pontos';
      var shapes = [];
      function med(k){
        var v = data.map(function(p){ return p[k]; }).filter(function(x){ return x !== null && !isNaN(x); }).sort(function(a, b){ return a - b; });
        return v.length ? v[Math.floor(v.length / 2)] : null;
      }
      var annots = [];
      if (cfg.quad){
        var mx = med(st.xk), my = med(st.yk);
        if (mx !== null) shapes.push({type: 'line', x0: mx, x1: mx, yref: 'paper', y0: 0, y1: 1, line: {color: '#2a3050', dash: 'dash', width: 1}});
        if (my !== null) shapes.push({type: 'line', y0: my, y1: my, xref: 'paper', x0: 0, x1: 1, line: {color: '#2a3050', dash: 'dash', width: 1}});
        /* nomes das quatro zonas ao fundo (desenho do painel curado) */
        if (cfg.zones){
          var ZP = {tl: [0.13, 0.86], tr: [0.87, 0.86], bl: [0.13, 0.13], br: [0.87, 0.13]};
          Object.keys(cfg.zones).forEach(function(q){
            if (!ZP[q]) return;
            annots.push({xref: 'paper', yref: 'paper', x: ZP[q][0], y: ZP[q][1], text: cfg.zones[q],
                         showarrow: false, font: {size: 11.5, color: '#39405c'}, align: 'center'});
          });
        }
      }
      if (cfg.roi && cfg.roi[st.yk] !== undefined){
        shapes.push({type: 'line', y0: cfg.roi[st.yk], y1: cfg.roi[st.yk], xref: 'paper', x0: 0, x1: 1, line: {color: '#f87171', dash: 'dot', width: 1}});
      }
      var xlog = cfg.combos ? st.lx : st.log, ylog = cfg.combos ? st.ly : st.log;
      Plotly.react(gd, traces, {
        paper_bgcolor: '#14171f', plot_bgcolor: '#14171f',
        font: {family: 'Inter,system-ui,sans-serif', color: '#e2e8f0', size: 12},
        margin: {l: 64, r: 24, t: 14, b: 52}, height: cfg.h, shapes: shapes, annotations: annots,
        legend: {bgcolor: 'rgba(0,0,0,0)', font: {size: 10.5}, orientation: 'h', y: -0.16, x: 0},
        showlegend: !!cfg.groups,
        xaxis: {title: {text: axl(st.xk), font: {size: 12}}, type: xlog ? 'log' : 'linear',
                gridcolor: '#282d42', zerolinecolor: '#282d42', tickfont: {size: 11}},
        yaxis: {title: {text: axl(st.yk), font: {size: 12}}, type: ylog ? 'log' : 'linear',
                gridcolor: '#282d42', zerolinecolor: '#282d42', tickfont: {size: 11}},
        hoverlabel: {font: {size: 12, family: 'Inter'}}
      }, {displayModeBar: false, responsive: true});
    }
    if (cfg.combos){
      [].slice.call(host.querySelectorAll('.ctrl')).forEach(function(b){
        b.addEventListener('click', function(){
          var c = cfg.combos[+b.dataset.i];
          st.xk = c.x; st.yk = c.y; st.lx = c.lx; st.ly = c.ly;
          [].slice.call(host.querySelectorAll('.ctrl')).forEach(function(x){ x.classList.toggle('on', x === b); });
          draw();
        });
      });
    } else {
      host.querySelector('.xys-x').addEventListener('change', function(e){ st.xk = e.target.value; draw(); });
      host.querySelector('.xys-y').addEventListener('change', function(e){ st.yk = e.target.value; draw(); });
      host.querySelector('.xys-lin').addEventListener('click', function(){
        st.log = false;
        host.querySelector('.xys-lin').classList.add('on'); host.querySelector('.xys-log').classList.remove('on');
        draw();
      });
      host.querySelector('.xys-log').addEventListener('click', function(){
        st.log = true;
        host.querySelector('.xys-log').classList.add('on'); host.querySelector('.xys-lin').classList.remove('on');
        draw();
      });
    }
    var q = host.querySelector('.it-q');
    if (q) q.addEventListener('input', function(){ st.q = q.value.trim().toLowerCase(); draw(); });
    draw();
  };

  function boot(){
    [].slice.call(document.querySelectorAll('.js-itab')).forEach(initTab);
    [].slice.call(document.querySelectorAll('.js-mrank')).forEach(initRank);
    [].slice.call(document.querySelectorAll('.js-cbar')).forEach(initCbar);
  }
  if (document.readyState !== 'loading') boot();
  else document.addEventListener('DOMContentLoaded', boot);
})();
"""

# ════════════ DADOS + INSTÂNCIAS DOS COMPONENTES INTERATIVOS ════════════
LEG = os.path.normpath(os.path.join(BASE, '..', 'fomento-audiovisual'))
DSETS = os.path.join(BASE, 'data', 'legado', 'painel_datasets')

for _c in ['pontuacao_festivais', 'vod_n_paises', 'critica_indice_1_5', 'cita_n_papers',
           'cita_soma_cit', 'critica_n_fontes', 'ano']:
    bg[_c] = pd.to_numeric(bg[_c], errors='coerce')

# nomes de produtora: fomento_fsa (FSA) + base_nivel_produtora (cobre renúncia pura)
BNP = pd.read_csv(os.path.join(DSETS, 'base_nivel_produtora.csv'), sep=';')
# CNPJ aqui vem como float sem zeros à esquerda (regra do CLAUDE.md): int → str → zfill
BNP['cnpj_n'] = BNP.CNPJ_produtora.apply(lambda x: str(int(x)).zfill(14) if pd.notna(x) else '')
_nome_bnp = (BNP.dropna(subset=['razao_social']).set_index('cnpj_n')['razao_social']
             .str.title().str.slice(0, 34).to_dict())
NOME_ALL = {**_nome_bnp, **NOME}


def _cat_label(c):
    c = str(c)
    return 'TV/VOD (fora do recorte cinema)' if c.startswith('_') else c[:34]


# ── Obras detalhadas (aba "Obras Detalhadas" do painel curado): TODAS as obras do fomento ──
OB_ROWS = []
for r_ in bg.itertuples():
    _inv = r_.investimento_total_deflac
    _rec = r_.receita_total_deflac if pd.notna(r_.receita_total_deflac) else None
    OB_ROWS.append({
        't': esc(str(r_.titulo).title()[:44]),
        'p': esc(NOME_ALL.get(r_.cnpj_n, '—')),
        'a': int(r_.ano) if pd.notna(r_.ano) else None,
        'c': esc(_cat_label(r_.categoria)),
        'g': r_.grupo,
        'i': _r(_inv / 1e6),
        'f': _r(r_.investimento_fsa_deflac / 1e6) if pd.notna(r_.investimento_fsa_deflac) else 0.0,
        'b': _r(r_.bilheteria_deflac / 1e6) if pd.notna(r_.bilheteria_deflac) else None,
        'r': _r(_rec / _inv) if (_rec and _inv) else None,
        'x': _r(r_.roi_internacional_0_100, 1),
        'e': int(r_.adm_eu_lumiere) if pd.notna(r_.adm_eu_lumiere) and r_.adm_eu_lumiere > 0 else None,
        'ft': int(r_.pontuacao_festivais) if pd.notna(r_.pontuacao_festivais) and r_.pontuacao_festivais > 0 else None,
        'v': int(r_.vod_n_paises) if pd.notna(r_.vod_n_paises) and r_.vod_n_paises > 0 else None,
        'q': _r(r_.critica_indice_1_5, 1),
        # camada extra da tabela-ranking: o que mais existe por obra na base canônica
        'ch': esc(str(r_.chamada)[:46]) if pd.notna(r_.chamada) else '—',
        'uf': esc(str(r_.uf)) if pd.notna(r_.uf) else '—',
        'rn': _r((r_.investimento_renuncia_total_deflac or 0) / 1e6) if pd.notna(r_.investimento_renuncia_total_deflac) else 0.0,
        'rc': _r(_rec / 1e6) if _rec else None,
        'j': _r((r_.janelas_crt or 0) / 1e6) if pd.notna(r_.janelas_crt) else None,
        'pu': int(r_.publico_domestico) if pd.notna(r_.publico_domestico) and r_.publico_domestico > 0 else None,
        'ss': int(r_.sessoes_total) if pd.notna(r_.sessoes_total) and r_.sessoes_total > 0 else None,
        'nm': int(r_.n_municipios) if pd.notna(r_.n_municipios) and r_.n_municipios > 0 else None,
        'rf': _r(_rec / r_.investimento_fsa_deflac) if (_rec and pd.notna(r_.investimento_fsa_deflac)
                                                        and r_.investimento_fsa_deflac > 0) else None,
        'vp': int(r_.vod_n_plataformas) if pd.notna(r_.vod_n_plataformas) and r_.vod_n_plataformas > 0 else None,
        'pa': int(r_.total_paises_alcancados) if pd.notna(r_.total_paises_alcancados) and r_.total_paises_alcancados > 0 else None,
        'np': int(r_.cita_n_papers) if pd.notna(r_.cita_n_papers) and r_.cita_n_papers > 0 else None,
        'nc': int(r_.cita_soma_cit) if pd.notna(r_.cita_soma_cit) and r_.cita_soma_cit > 0 else None,
        'cf': esc(str(r_.critica_confianca)) if pd.notna(r_.critica_confianca) else '—',
        'nf': int(r_.critica_n_fontes) if pd.notna(r_.critica_n_fontes) and r_.critica_n_fontes > 0 else None,
    })
CAT_PAL = chip_pal([r['c'] for r in OB_ROWS])
GRP_PAL = chip_pal([r['g'] for r in OB_ROWS],
                   fixed={'FSA puro': R.ACCENT, 'Renúncia pura': R.GOLD,
                          'FSA+Ren · FSA maj.': R.CYAN, 'FSA+Ren · Ren. maj.': R.PURPLE})
it_obras = itable(
    cols=[('t', 'Obra', 's'), ('a', 'Ano', 'y'), ('uf', 'UF', 's'), ('p', 'Produtora', 's'),
          ('g', 'Grupo', 'g'), ('c', 'Categoria', 'g'), ('ch', 'Chamada', 's'),
          ('f', 'FSA (mi)', 'Br2'), ('rn', 'Renúncia (mi)', 'r2'), ('i', 'Inv. total (mi)', 'Br2'),
          ('b', 'Bilheteria (mi)', 'Br2'), ('j', 'Janelas CRT (mi)', 'r2'), ('rc', 'Receita ref. (mi)', 'Br2'),
          ('pu', 'Público', 'i'), ('ss', 'Sessões', 'i'), ('nm', 'Municípios', 'i'),
          ('r', 'ROI dom.', 'Bx2'), ('rf', 'ROI s/ FSA', 'x2'),
          ('x', 'Intl 0–100', 'Bn1'), ('ft', 'Fest. (pts)', 'i'), ('e', 'Adm. EU', 'i'),
          ('v', 'Países VOD', 'i'), ('vp', 'Plat. VOD', 'i'), ('pa', 'Países alcanç.', 'i'),
          ('q', 'Crítica', 'n1'), ('nf', 'Fontes', 'i'), ('cf', 'Confiança', 's'),
          ('np', 'Papers', 'i'), ('nc', 'Citações', 'i')],
    rows=OB_ROWS, search=('t', 'p', 'ch'), filters=[('c', 'Categoria'), ('a', 'Ano'), ('uf', 'UF')],
    pills=('g', 'Grupo'), chips={'c': CAT_PAL, 'g': GRP_PAL}, rank=True,
    sorts=[('b', 'Bilheteria'), ('pu', 'Público'), ('rc', 'Receita de referência'), ('r', 'ROI dom.'), ('rf', 'ROI sobre FSA'),
           ('x', 'Intl 0–100'), ('i', 'Investimento total'), ('f', 'FSA'), ('rn', 'Renúncia'),
           ('e', 'Admissões EU'), ('ft', 'Festivais'), ('pa', 'Países alcançados'),
           ('q', 'Crítica'), ('np', 'Papers'), ('nc', 'Citações')],
    sort0=('b', 'desc'), maxh=680, note='', _doc='<b>29 colunas por obra</b> — tudo o que a base canônica guarda de cada filme: as duas pontas do '
         'dinheiro (FSA e renúncia), as três da receita (bilheteria, janelas CRT e a de referência), os dois '
         'ROIs, o índice internacional aberto em festivais/Europa/VOD/países, e a camada simbólica '
         '(crítica com nº de fontes e confiança declarada, papers e citações). Nome e posição ficam '
         'congelados ao rolar. Valores em R$ mi de 2024; "—" = sem dado observado.')

# ── Chamadas detalhadas (interativa, base_nivel_chamada completa) ──
BNC = pd.read_csv(os.path.join(DSETS, 'base_nivel_chamada.csv'), sep=';')
CH_ROWS = []
for r_ in BNC.itertuples():
    CH_ROWS.append({
        'ch': esc(str(r_.chamada)[:58]), 'c': esc(str(r_.categoria)[:34]),
        'n': int(r_.n_obras), 'nb': int(r_.n_obras_com_bilheteria),
        'f': _r(r_.investimento_fsa_deflac / 1e6, 1), 'i': _r(r_.investimento_total_deflac / 1e6, 1),
        'ra': _r(r_.roi_dom_total_agregado), 'rm': _r(r_.roi_dom_total_medio_obra),
        'im': _r(r_.roi_intl_medio, 1), 'ix': _r(r_.roi_intl_max, 1),
        'pf': _r(r_.pct_com_festival, 0), 'pl': _r(r_.pct_com_lumiere, 0),
        'e': int(r_.adm_eu_total) if pd.notna(r_.adm_eu_total) else None,
        'cr': _r(r_.critica_media, 1), 'np': int(r_.n_produtoras_distintas)})
CHCAT_PAL = chip_pal([r['c'] for r in CH_ROWS])
it_chamadas = itable(
    cols=[('ch', 'Chamada', 's'), ('c', 'Categoria', 'g'), ('n', 'Obras', 'i'), ('nb', 'C/ bilh.', 'i'),
          ('f', 'FSA (mi)', 'Br1'), ('i', 'Inv. total (mi)', 'r1'), ('ra', 'ROI agreg.', 'Bx2'),
          ('rm', 'ROI médio', 'x2'), ('im', 'Intl méd.', 'Bn1'), ('ix', 'Intl máx.', 'n1'),
          ('pf', '% festival', 'p0'), ('pl', '% Lumière', 'p0'), ('e', 'Adm. EU', 'i'),
          ('cr', 'Crítica', 'n1'), ('np', 'Produtoras', 'i')],
    rows=CH_ROWS, search=('ch',), pills=('c', 'Categoria'), chips={'c': CHCAT_PAL}, rank=True,
    sorts=[('f', 'FSA investido'), ('ra', 'ROI agregado'), ('rm', 'ROI médio por obra'),
           ('im', 'Intl médio'), ('n', 'Nº de obras'), ('pf', '% com festival'), ('e', 'Admissões EU')],
    sort0=('f', 'desc'), maxh=680, note='', _doc='Todas as chamadas da base consolidada, uma linha por chamada — o desenho da aba '
         '"Chamadas Detalhadas" do painel curado, recalculado nesta base: pílulas de categoria com contagem, '
         'chip colorido por mecanismo e barra proporcional nas colunas de volume e retorno.')

# ── Ranking por categoria com troca de métrica (desenho setRankSort do painel curado) ──
MR_ITEMS = [{'l': esc(str(r_.cat)), 'pub': _r(r_.publico_por_mi_fsa, 0), 'roi': _r(r_.roi_dom_fsa_crt),
             'pci': _r(r_.pct_com_intl, 1), 'dsi': _r(r_.desemp_intl_medio, 2), 'fsa': _r(r_.fsa_mi, 0),
             'n': int(r_.n), 'cri': _r(r_.critica_media), 'pap': _r(r_.papers_por_obra),
             'pw': _r(r_.pct_presenca_intl, 1)} for r_ in M.itertuples()]
mr_cat = metric_rank(
    MR_ITEMS,
    metrics=[('pub', 'Espect./R$ mi', 0, '', ''), ('roi', 'ROI dom. (CRT)', 2, '', 'x'),
             ('pci', '% c/ sinal intl', 1, '', '%'), ('dsi', 'Desemp. intl', 2, '', ''),
             ('fsa', 'FSA investido', 0, 'R$ ', ' mi'), ('n', 'Nº obras', 0, '', ''),
             ('cri', 'Crítica (1–5)', 2, '', ''), ('pap', 'Papers/obra', 2, '', ''),
             ('pw', '% presença Wikipedia', 1, '', '%')],
    note='Ranking de mecanismos com a métrica escolhida no botão — as nove réguas do trabalho '
         'na mesma vitrine (desenho do painel curado). Nenhum mecanismo lidera em tudo.')

# ── Quadrante de mecanismos com troca de eixos (desenho setQuadAxis do painel curado) ──
MEC_PAL = chip_pal([str(r_.cat) for r_ in M.itertuples()])
QP_PTS = [{'l': esc(str(r_.cat)), 'ms': (max(r_.fsa_mi, 5) ** 0.5) * 2.0 + 6,
           'c': MEC_PAL.get(str(r_.cat), R.ACCENT),
           'pub': _r(r_.publico_por_mi_fsa, 0), 'pci': _r(r_.pct_com_intl, 1),
           'fsa': _r(r_.fsa_mi, 0), 'roi': _r(r_.roi_dom_fsa_crt), 'dsi': _r(r_.desemp_intl_medio, 2)}
          for r_ in M.itertuples()]
xys_quad_cat = xy_scatter(
    QP_PTS,
    combos=[('roi', 'dsi', 'ROI dom. × Intl', True, False),
            ('pub', 'pci', 'Conversão dom. × % intl', True, False),
            ('fsa', 'roi', 'FSA total × ROI dom.', True, False),
            ('fsa', 'dsi', 'FSA total × Desemp. intl', True, False)],
    names={'pub': 'espectadores por R$ mi de FSA', 'pci': '% de obras com sinal internacional',
           'fsa': 'FSA investido (R$ mi)', 'roi': 'ROI doméstico (c/ CRT)', 'dsi': 'desempenho internacional (0–100)'},
    height=520, quadrant=True, search=False, labels=True,
    zones={'tl': 'Vocação<br>internacional', 'tr': 'Duplo<br>impacto',
           'bl': 'Baixo retorno<br>detectado', 'br': 'Vocação<br>comercial'},
    note='<b>Vocação comercial × alcance internacional por mecanismo</b> — o quadrante do painel curado, com '
         'os quatro botões de eixo. Tracejado = medianas, que dividem as quatro zonas; bolha = FSA investido; '
         'cor = mecanismo. Nenhum mecanismo ocupa o duplo impacto com folga.')

# ── Cards "Categorias de Fomento — Critérios e Resultados" (desenho do painel curado) ──
_cg = (BNC.groupby('categoria')
       .agg(nch=('chamada', 'nunique'), n=('n_obras', 'sum'),
            fsa=('investimento_fsa_deflac', 'sum'), inv=('investimento_total_deflac', 'sum'),
            rec=('receita_total_deflac', 'sum'), pf=('pct_com_festival', 'mean'),
            npr=('n_produtoras_distintas', 'sum'))
       .sort_values('fsa', ascending=False))
_pal_cat = [R.GOLD, R.CYAN, R.ACCENT, R.PURPLE, R.GREEN, '#f97316', R.CORAL, '#94a3b8', '#eab308', R.MUT]
cards_criterios = '<div class="clcards">' + ''.join(
    f'<div class="clc" style="border-top-color:{_pal_cat[i % len(_pal_cat)]}">'
    f'<div class="clc-h"><span>{esc(str(g)[:30])}</span><b>{int(r_.nch)}</b></div>'
    f'<div class="clc-d">{int(r_.nch)} chamada(s) · {int(r_.n)} obras · {int(r_.npr)} produtoras</div>'
    f'<div class="clc-m"><span>FSA</span><b>R$ {br(r_.fsa/1e6,0)} mi</b></div>'
    f'<div class="clc-m"><span>ROI dom. agregado</span><b>{br(r_.rec/r_.inv,2) if r_.inv else "—"}</b></div>'
    f'<div class="clc-m"><span>% c/ festival</span><b>{br(r_.pf,0)}%</b></div></div>'
    for i, (g, r_) in enumerate(_cg.iterrows())) + '</div>'

# ── Síntese "qual mecanismo é melhor para cada métrica" (aba Síntese do painel curado) ──
_METR_SINT = [('publico_por_mi_fsa', 'Conversão doméstica (espect./R$ mi)'),
              ('roi_dom_fsa_crt', 'ROI doméstico (c/ CRT)'),
              ('pct_com_intl', '% de obras com sinal internacional'),
              ('desemp_intl_medio', 'Desempenho internacional (0–100)'),
              ('critica_media', 'Crítica (1–5)'),
              ('papers_por_obra', 'Repercussão acadêmica (papers/obra)'),
              ('pct_presenca_intl', 'Presença Wikipedia internacional')]
_sint_rows = []
for k_, lab_ in _METR_SINT:
    tt_ = M.sort_values(k_, ascending=False).head(3)
    _sint_rows.append([lab_] + [f'{esc(str(x["cat"]))} <b style="color:#e8ecf4">({br(x[k_], 1)})</b>'
                                for _, x in tt_.iterrows()])
tab_sintese_metrica = tabela(['Métrica', '1º', '2º', '3º'], _sint_rows)

# ── Dispersão de GRUPOS por obra com toggle dom/intl (desenho togSwitch da Visão Geral curada) ──
XG_PTS = []
for r_ in dispg.itertuples():
    XG_PTS.append({'l': esc(str(r_.titulo).title()[:40]), 'g': r_.grupo, 'ms': 7,
                   'inv': _r(r_.investimento_total_deflac / 1e6),
                   'roi': _r(max(r_.roi_dom, 0.001)),
                   'intl': _r(max(r_.roi_internacional_0_100, 0.01), 2) if pd.notna(r_.roi_internacional_0_100) else 0.01})
xys_grupos = xy_scatter(
    XG_PTS,
    combos=[('inv', 'roi', 'Investimento × ROI doméstico', True, True),
            ('inv', 'intl', 'Investimento × Desemp. internacional', True, False)],
    names={'inv': 'investimento total por obra (R$ mi)', 'roi': 'ROI doméstico da obra',
           'intl': 'desempenho internacional (0–100)'},
    groups=COR_G, height=500, roi_lines={'roi': 1.0},
    note='Obra a obra, com o toggle doméstico/internacional do painel curado. Pontilhado vermelho = '
         'recuperação do investimento. Use a busca para achar um filme.')

# ── Dispersão de PRODUTORAS com eixos configuráveis + busca (desenho "Por Cluster" curado) ──
XP_PTS = []
for r_ in bq.itertuples():
    XP_PTS.append({'l': esc(str(r_.nome)), 'g': r_.tipo if r_.tipo in CORES_TIPO else 'Sem classificação',
                   'ms': min(float(r_.n), 30.0) * 1.4 + 5,
                   'fsa': _r(max(r_.fsa / 1e6, 0.01)), 'bilh': _r(max(r_.bilheteria / 1e6, 0.01)),
                   'roi': _r(max(r_.roi_dom, 0.001), 3),
                   'dsi': _r(max(r_.desemp, 0.01), 2) if pd.notna(r_.desemp) else 0.01,
                   'eu': _r(max(r_.admeu / 1e3, 0.01), 1), 'n': int(r_.n)})
_grupos_prod = {**CORES_TIPO}
if any(p['g'] == 'Sem classificação' for p in XP_PTS):
    _grupos_prod['Sem classificação'] = R.MUT
xys_prod = xy_scatter(
    XP_PTS,
    axes=[('fsa', 'FSA captado (R$ mi)'), ('roi', 'ROI doméstico'), ('bilh', 'Bilheteria (R$ mi)'),
          ('dsi', 'Desemp. internacional (0–100)'), ('eu', 'Admissões Europa (mil)'), ('n', 'Nº de obras')],
    groups=_grupos_prod, height=540, roi_lines={'roi': 1.0},
    note='A dispersão de produtoras do painel curado: escolha os eixos, alterne Lin/Log e busque uma '
         'produtora pelo nome (os demais pontos esmaecem). Bolha = nº de obras; cor = perfil.')

# ── Ranking de produtoras (tabela interativa, base_nivel_produtora + tipologia nova) ──
_tipo_map = PERFIL_POR_CNPJ
PRD_ROWS = []
for r_ in BNP.itertuples():
    _inv = r_.investimento_total_deflac if pd.notna(r_.investimento_total_deflac) else 0
    _rec = r_.receita_total_deflac if pd.notna(r_.receita_total_deflac) else None
    if pd.isna(r_.razao_social) or not str(r_.razao_social).strip():
        continue                      # sem razão social no cadastro: não vira linha de ranking
    PRD_ROWS.append({
        'p': esc(str(r_.razao_social).title()[:38]), 'uf': esc(str(r_.UF)) if pd.notna(r_.UF) else '—',
        'tp': esc(_tipo_map.get(r_.cnpj_n, 'Sem classificação')),
        'n': int(r_.n_obras),
        'f': _r((r_.investimento_fsa_deflac or 0) / 1e6, 1) if pd.notna(r_.investimento_fsa_deflac) else 0.0,
        'i': _r(_inv / 1e6, 1),
        'rc': _r(_rec / 1e6, 1) if _rec else None,
        'r': _r(r_.roi_dom_total_deflac) if pd.notna(r_.roi_dom_total_deflac) else None,
        'x': _r(r_.roi_intl_medio, 1) if pd.notna(r_.roi_intl_medio) else None,
        'e': int(r_.adm_eu_total) if pd.notna(r_.adm_eu_total) and r_.adm_eu_total > 0 else None,
        'ni': int(r_.n_obras_com_presenca_intl) if pd.notna(r_.n_obras_com_presenca_intl) else 0,
        'cr': _r(r_.critica_media, 1) if pd.notna(r_.critica_media) else None,
        # camada extra da tabela-ranking por empresa
        'cg': esc(str(r_.classificacao_agente)[:26]) if pd.notna(r_.classificacao_agente) else '—',
        'nfs': int(r_.n_obras_fsa) if pd.notna(r_.n_obras_fsa) else 0,
        'nrn': int(r_.n_obras_renuncia) if pd.notna(r_.n_obras_renuncia) else 0,
        'bl': _r((r_.bilheteria_deflac or 0) / 1e6, 1) if pd.notna(r_.bilheteria_deflac) else None,
        'rff': _r(r_.roi_dom_fsa_deflac) if pd.notna(r_.roi_dom_fsa_deflac) else None,
        'xm': _r(r_.roi_intl_max, 1) if pd.notna(r_.roi_intl_max) else None,
        'nfe': int(r_.n_obras_com_festival) if pd.notna(r_.n_obras_com_festival) else 0,
        'nlu': int(r_.n_obras_com_lumiere) if pd.notna(r_.n_obras_com_lumiere) else 0,
        'nvo': int(r_.n_obras_com_vod) if pd.notna(r_.n_obras_com_vod) else 0,
        'pm': int(r_.total_paises_max) if pd.notna(r_.total_paises_max) and r_.total_paises_max > 0 else None,
        'pf': _r(r_.pct_obras_genero_feminino * 100, 0) if pd.notna(r_.pct_obras_genero_feminino) else None,
        'ps': _r(r_.pct_receita_sintetica * 100, 0) if pd.notna(r_.pct_receita_sintetica) else None})
it_prod = itable(
    cols=[('p', 'Produtora', 's'), ('uf', 'UF', 's'), ('tp', 'Perfil', 'g'), ('cg', 'Classificação', 's'),
          ('n', 'Obras', 'i'), ('nfs', 'C/ FSA', 'i'), ('nrn', 'C/ renúncia', 'i'),
          ('f', 'FSA (mi)', 'Br1'), ('i', 'Inv. total (mi)', 'Br1'),
          ('bl', 'Bilheteria (mi)', 'Br1'), ('rc', 'Receita (mi)', 'Br1'), ('ps', '% est.', 'p0'),
          ('r', 'ROI dom.', 'Bx2'), ('rff', 'ROI s/ FSA', 'x2'),
          ('x', 'Intl méd.', 'Bn1'), ('xm', 'Intl máx.', 'n1'), ('ni', 'Obras intl', 'i'),
          ('nfe', 'C/ festival', 'i'), ('nlu', 'C/ Lumière', 'i'), ('nvo', 'C/ VOD', 'i'),
          ('e', 'Adm. EU', 'i'), ('pm', 'Países (máx.)', 'i'),
          ('cr', 'Crítica', 'n1'), ('pf', '% dir. mulher', 'p0')],
    rows=PRD_ROWS, search=('p',), filters=[('uf', 'UF'), ('cg', 'Classificação')],
    pills=('tp', 'Perfil'),
    chips={'tp': chip_pal([r['tp'] for r in PRD_ROWS],
                          fixed={**CORES_TIPO, 'Sem classificação': R.MUT})}, rank=True,
    sorts=[('f', 'FSA captado'), ('i', 'Investimento total'), ('bl', 'Bilheteria'), ('rc', 'Receita gerada'),
           ('r', 'ROI dom.'), ('rff', 'ROI sobre FSA'), ('x', 'Intl médio'), ('xm', 'Intl máximo'),
           ('e', 'Admissões EU'), ('n', 'Nº de obras'), ('ni', 'Obras com sinal intl'),
           ('nfe', 'Obras em festival'), ('cr', 'Crítica')],
    sort0=('f', 'desc'), maxh=680, note='', _doc='<b>24 colunas por empresa</b>: a carteira aberta (obras com FSA × com renúncia), o dinheiro pelas '
         'duas pontas, a receita com o % que é estimativa declarada, os dois ROIs, o internacional em média e '
         'máximo com a contagem de obras por canal (festival · Lumière · VOD), e a camada simbólica. '
         'Perfil = classificação do estudo anterior, por grupo econômico; a pílula <i>Sem classificação</i> é '
         'a cobertura que falta — CNPJ que não entrou em nenhum grupo da tipologia.')

# ── Boxplots por perfil (desenho pr_cl_box / pr_cl_box_intl do painel curado) ──
f_box_roi = go.Figure()
for tipo_, cor_ in CORES_TIPO.items():
    _sub = bq[(bq.tipo == tipo_) & (bq.roi_dom > 0)]
    if len(_sub):
        f_box_roi.add_trace(go.Box(y=_sub.roi_dom, name=tipo_[:22], marker_color=cor_, boxpoints='outliers',
                                   marker=dict(size=3, opacity=0.5), line=dict(width=1.5)))
f_box_roi.add_hline(y=1.0, line_dash='dot', line_color=R.CORAL)
f_box_roi.update_yaxes(type='log')
style(f_box_roi, h=440, ytitle='ROI doméstico por produtora (log)', showlegend=False)
f_box_intl = go.Figure()
for tipo_, cor_ in CORES_TIPO.items():
    _sub = bq[bq.tipo == tipo_]
    if len(_sub):
        f_box_intl.add_trace(go.Box(y=_sub.desemp.fillna(0), name=tipo_[:22], marker_color=cor_,
                                    boxpoints='outliers', marker=dict(size=3, opacity=0.5), line=dict(width=1.5)))
style(f_box_intl, h=420, ytitle='desempenho internacional médio (0–100)', showlegend=False)

# ── Viabilidade: ticket anual × nº de obras (desenho viability_scatter/scatter_tick do painel curado) ──
_nob = bg.groupby('cnpj_n')['CPB'].count().rename('n')
tkv = tk.merge(_nob, on='cnpj_n', how='left')
tkv['n'] = tkv.n.fillna(1)
tkv = tkv[tkv.comb > 0].nlargest(400, 'fom')
f_viab = go.Figure()
for lab_, mask_, cor_ in [('abaixo do custo fixo (~R$ 400 mil/ano)', tkv.comb < 400e3, R.CORAL),
                          ('acima do custo fixo', tkv.comb >= 400e3, R.GREEN)]:
    _sub = tkv[mask_]
    f_viab.add_trace(go.Scatter(
        x=_sub.comb / 1e3, y=_sub.n, mode='markers', name=lab_,
        marker=dict(size=(_sub.fom / 1e6).clip(lower=0.5) ** 0.5 * 2.4 + 4, color=cor_, opacity=0.6, line=dict(width=0)),
        customdata=[NOME.get(c, '—') for c in _sub.cnpj_n],
        hovertemplate='%{customdata}<br>ticket anual R$ %{x:,.0f} mil · %{y} obras<extra></extra>'))
f_viab.add_vline(x=400, line_dash='dash', line_color=R.GOLD)
f_viab.update_xaxes(type='log')
style(f_viab, h=470, xtitle='ticket anual combinado por produtora (R$ mil/ano, log) — tracejado = custo fixo mínimo',
      ytitle='nº de obras no período · bolha = fomento total (top 400 produtoras)')

# ── Proliferação: entradas × saídas de produtoras por ano (desenho conc-prod_growth/delta curado) ──
_anos_prod = b_fsa[(b_fsa.ano >= 2014) & (b_fsa.ano <= 2023)].groupby('cnpj_n')['ano'].agg(['min', 'max'])
_ativ = {a: int(((_anos_prod['min'] <= a) & (_anos_prod['max'] >= a)).sum()) for a in range(2014, 2024)}
_novas = _anos_prod['min'].value_counts().reindex(range(2014, 2024), fill_value=0)
_ultimas = _anos_prod['max'].value_counts().reindex(range(2014, 2024), fill_value=0)
f_pdelta = go.Figure()
f_pdelta.add_bar(x=list(_novas.index), y=_novas.values, name='estreiam no FSA (1ª obra)', marker_color=R.GREEN)
f_pdelta.add_bar(x=list(_ultimas.index), y=[-v for v in _ultimas.values], name='última obra no recorte', marker_color=R.CORAL)
f_pdelta.add_scatter(x=list(_ativ.keys()), y=list(_ativ.values()), name='produtoras com obra ativa',
                     mode='lines+markers', line=dict(color=R.CYAN, width=3))
f_pdelta.update_layout(barmode='relative')
style(f_pdelta, h=430, xtitle='ano de início de produção (recorte FSA-cinema)',
      ytitle='produtoras: entradas (verde) × últimas obras (vermelho)')

# ── Barras por país com fontes por checkbox (desenho do mapa fest/VOD curado) ──
FEST_PAIS = {'Cannes': 'França', 'Annecy': 'França', 'Berlim': 'Alemanha', 'Veneza': 'Itália',
             'Oscar': 'Estados Unidos', 'Sundance': 'Estados Unidos', 'NYFF': 'Estados Unidos',
             'Globo de Ouro': 'Estados Unidos', 'Locarno': 'Suíça', 'TIFF': 'Canadá',
             'San Seb.': 'Espanha', 'Rotterdam': 'Países Baixos', 'BFI London': 'Reino Unido',
             'BAFTA': 'Reino Unido', 'Havana': 'Cuba'}
FC = pd.read_csv(os.path.join(BASE, 'data', 'legado', 'festivais_consolidado.csv'))
_fest_pais = {}
for _col, _pais in FEST_PAIS.items():
    if _col in FC.columns:
        _fest_pais[_pais] = _fest_pais.get(_pais, 0) + int((pd.to_numeric(FC[_col], errors='coerce').fillna(0) > 0).sum())
_cb_paises = {}
for _iso, _n in vod_pais.items():
    _cb_paises.setdefault(ISO2[_iso][1], {})['vod'] = int(_n)
for _pais, _n in _fest_pais.items():
    _cb_paises.setdefault(_pais, {})['fest'] = _n
cb_paises = country_bars(
    [{'nome': p, 'vod': v.get('vod', 0), 'fest': v.get('fest', 0)} for p, v in _cb_paises.items()],
    sources=[('vod', 'Títulos brasileiros em VOD (Lumière)', R.ACCENT, True),
             ('fest', 'Obras em festivais (país-sede)', R.GOLD, True)],
    note='País a país, com as fontes ligáveis do painel curado: VOD (catálogos europeus, Lumière) e '
         'festivais (obras com participação, pelo país-sede do festival — universo amplo do consolidado, '
         'inclui obras fora do recorte 2014–2023).')

# ── Soft power: tabelas interativas de crítica e citação acadêmica ──
_bc = bg[bg.critica_indice_1_5.notna()]
CRIT_ROWS = [{'t': esc(str(r_.titulo).title()[:44]), 'a': int(r_.ano) if pd.notna(r_.ano) else None,
              'c': esc(_cat_label(r_.categoria)), 'q': _r(r_.critica_indice_1_5, 2),
              'nf': int(r_.critica_n_fontes) if pd.notna(r_.critica_n_fontes) else None,
              'cf': esc(str(r_.critica_confianca)) if pd.notna(r_.critica_confianca) else '—',
              'ft': int(r_.pontuacao_festivais) if pd.notna(r_.pontuacao_festivais) and r_.pontuacao_festivais > 0 else None}
             for r_ in _bc.itertuples()]
it_critica = itable(
    cols=[('t', 'Obra', 's'), ('a', 'Ano', 'y'), ('c', 'Categoria', 's'), ('q', 'Índice (1–5)', 'n2'),
          ('nf', 'Nº críticas', 'i'), ('cf', 'Confiança', 's'), ('ft', 'Fest. (pts)', 'i')],
    rows=CRIT_ROWS, search=('t',), filters=[('c', 'Categoria'), ('cf', 'Confiança')], sort0=('q', 'desc'),
    note='Índice de crítica agregado (1–5) — o desenho da aba Crítica do painel curado, na base atual.')
_bp2 = bg[bg.cita_n_papers.fillna(0) > 0]
PAP_ROWS = [{'t': esc(str(r_.titulo).title()[:44]), 'a': int(r_.ano) if pd.notna(r_.ano) else None,
             'c': esc(_cat_label(r_.categoria)), 'np': int(r_.cita_n_papers),
             'nc': int(r_.cita_soma_cit) if pd.notna(r_.cita_soma_cit) else None,
             'q': _r(r_.critica_indice_1_5, 1)} for r_ in _bp2.itertuples()]
it_papers = itable(
    cols=[('t', 'Obra', 's'), ('a', 'Ano', 'y'), ('c', 'Categoria', 's'), ('np', 'Papers', 'i'),
          ('nc', 'Citações', 'i'), ('q', 'Crítica', 'n1')],
    rows=PAP_ROWS, search=('t',), filters=[('c', 'Categoria')], sort0=('np', 'desc'),
    note='Repercussão acadêmica por obra (OpenAlex) — a aba Citação do painel curado, na base atual.')

print('figuras prontas; montando abas…')


# ── chrome de painel: barra de KPIs no topo de cada aba ───────────────────────
def kpi(v, l, kind='inv'):
    """Ladrilho de KPI. kind: inv (azul) · res (verde) · warn (ouro) · int (roxo)."""
    return f'<div class="kpi {kind}"><div class="v">{v}</div><div class="l">{l}</div></div>'


def kpibar(cards):
    return ('<div class="kpibar">' + ''.join(cards) + '</div>') if cards else ''

# ════════════════════════ SÍNTESE (aba Visão geral) ════════════════════════
EVID_CHAVE = {
    'c1': f'{br(IND["obras_retorno"],0)} obras ligadas por CPB · público {br(IND["cobertura_publico"],0)}% observado · 2 universos + 2 indicadores',
    'c2': f'bilheteria dom {br(IND["cat_dist_ret_dom"],2)}/{br(IND["cat_prod_ret_dom"],2)} × festivais {br(IND["cat_fest_ret_dom"],2)} · intl inverte ({br(IND["cat_fest_ret_intl"],1)} × {br(IND["cat_dist_ret_intl"],1)}) · distribuidora 1,5× mais aporte',
    'c3': f'renúncia retorno {br(IND["inst_renuncia_pura_ret_dom"],2)} mas {br(IND["inst_renuncia_pura_pct_intl"],0)}% intl · FSA puro {br(IND["inst_fsa_puro_ret_dom"],2)} e {br(IND["inst_fsa_puro_pct_intl"],0)}% intl',
    'c4': f'6 perfis · {br(IND["grupos_carteira"],0)} empresas na carteira · mediana R$ {br(IND["produtoras_mediana_inv_anual"]/1000,0)} mil/ano vs piso R$ 400 mil',
    'c5': f'décimo superior {br(IND["decil_sup_share"],1)}% × metade de baixo {br(IND["metade_baixo_share"],1)}% · Gini fomento {br(IND["gini_fsa_produtora"],2)} × bilheteria {br(IND["gini_bilheteria_obra"],2)}',
    'c6': f'ritmo mediano 1 obra/década · só {br(IND["empresas_ritmo5"],0)} empresas em ritmo · {br(IND["entrantes_periodo"],0)} entrantes e {br(IND["entrantes_repetiram"],0)} que repetiram',
    'c7': f'curta em festival {br(CU["curtas_com_curta_pct"],1)}% × {br(CU["curtas_base_geral_pct"],1)}% do universo ({br(CU["curtas_mult"],1)}×) · piso de visibilidade entre R$ 3 e 5 mi',
}
_rows_sint = []
for pid, ptitulo, pdesc in S.PARTES:
    _rows_sint.append([f'<b style="color:#6c7bf7">{ptitulo}</b>', '', '', ''])
    for cid, parte, rotulo, tese, tldr, status, kind, peso in S.CLAIMS:
        if parte != pid:
            continue
        _rows_sint.append([f'<a href="#{cid}" style="color:#6c7bf7;text-decoration:none;font-weight:700">{cid[1:]}</a>',
                           tese, EVID_CHAVE[cid]])
tab_sint = tabela(['#', 'Pergunta', 'O que o dado mostra'], _rows_sint)

aba_visao = (
    '<div class="pnl-hd"><div class="hd-l"><div class="kicker">Painel de evidências</div>'
    '<h2>Oito perguntas sobre o fomento, e o dado de cada uma</h2></div></div>'
    + kpibar([kpi(f'{br(IND["obras_retorno"],0)}', 'obras no universo de retorno'),
              kpi(f'{len(PTO)}', 'grupos econômicos na carteira'),
              kpi(f'R$ {br(IND["inv_total_retorno_mi"]/1000,2)} <small>bi</small>', 'dinheiro público medido (R$ 2024)'),
              kpi(f'{br(IND["retorno_dom"],2)}', 'retorno doméstico de referência', 'res'),
              kpi(f'{br(IND["pct_sinal_intl"],0)}%', 'com sinal internacional', 'int'),
              kpi('8', 'perguntas, cada uma com a sua aba', 'res')])
    + f'<p class="lead">O gêmeo de dados do <a href="{ENS}">argumento</a>. O bloco <b>Dados gerais</b> traz o '
    'painel por unidade de análise — instrumento, ranking, chamada, produtora, concentração; o bloco <b>As '
    'perguntas</b> traz os indicadores de cada uma das oito. Como cada número é calculado, com os limites do '
    'dado e a consulta que refaz a conta, fica na aba <b>Metodologia</b>, no fim do menu. A tabela abaixo é a '
    'sinopse; clique no número para abrir.</p>'
    '<a class="xtab" href="#g_visao">◫ Abrir os dados gerais →</a>'
    + tab_sint +

    '<h2 style="margin-top:44px">O todo: que setor é este, e onde o FSA cabe nele</h2>'
    + stat_grid([
        stat(f'~R$ {br(gnm["pib_total_2019_corr_bi"],1)} <small>bi</small>', 'valor adicionado do setor audiovisual (2019)', 'inv'),
        stat(f'{br(gnm["prod_pct_total_2019"],1)}%', 'é a cadeia do cinema (produção+distribuição+exibição)', 'inv'),
        stat(f'{br(gnm["emprego_total_2019"]/1000,0)} <small>mil</small>', 'empregos formais no setor (2019)', 'res'),
        stat(f'R$ {br(gnm["fsa_2019_mi"],0)} <small>mi</small>', 'FSA comprometido em 2019 (real)', 'res')])
    + f'<div class="chart">{DL(f_macro)}</div><div class="cap">FSA real (azul) e VA da cadeia do cinema (ouro): '
    'sobreposição de 6 anos — contexto, nunca causa.</div>'
    + f'<div class="chart">{DL(f_exp)}</div><div class="cap">Comércio exterior de serviços audiovisuais: '
    'exportação sobe, saldo segue negativo.</div>')


def _figs_html(figs, cols=2):
    """Grade de cards de painel (não mais figura + legenda empilhadas em coluna de artigo).
    cols=1 força largura cheia (figuras largas: séries longas, mapas, dispersões)."""
    if not figs:
        return ''
    h = [f'<div class="figgrid{"" if cols == 2 else " one"}">']
    for frag, cap in figs:
        # figura alta (≥470px) = densa (rankings horizontais, dispersões, mapas): ocupa a linha inteira
        _m = re.search(r'min-height:(\d+)px', frag)
        _span = ' span2' if (_m and int(_m.group(1)) >= 470) else ''
        h.append(f'<div class="card{_span}"><div>{frag}</div>'
                 + (f'<div class="card-c">{cap}</div>' if cap else '') + '</div>')
    h.append('</div>')
    return ''.join(h)


# ── REMAPEAMENTO 14 → 8 ALEGAÇÕES (decisão 2026-07-26) ────────────────────────
# As abas continuam sendo construídas com os ids legados c1..c14; este mapa diz
# em qual alegação NOVA cada uma entra. Quando o segundo item não é None, a aba
# é uma CONTINUAÇÃO (entra na mesma aba, sob um subtítulo) em vez de alegação
# própria. c13/c14 viram anexos.
LEGACY = {
    'c1': ('c1', None),
    'c2': ('c2', None),
    'c3': ('c2', 'Distribuidoras como proponentes selecionam obras de melhor desempenho que as produtoras?'),
    'c4': ('c3', None),
    'c5': ('c2', 'As políticas afirmativas por cota reduzem a desigualdade entre os selecionados?'),
    'c6': ('c4', None),
    'c7': ('c6', None),
    'c8': ('c5', None),
    'c9': ('c6', 'Onde a produtora fica na cadeia que reparte a renda da obra?'),
    'c14': ('c7', None),
}
# Abas legadas que saíram do documento (governança, fonte única, benchmark, soft
# power, negativas e proposições) não são mais montadas — o HTML só carrega o que
# existe no DOCX. O conteúdo segue no histórico do repositório.
FORA = {'c10', 'c11', 'c12', 'c13'}


METODO_POR_PERGUNTA = []


def secao_claim(cid, como_testei, figs, veredito, ressalvas, derrubaria, repro_html, extra='', curado=(),
                subabas=(), kpis=()):
    """Conteúdo de uma aba de alegação. Com `subabas` [(sid, rótulo, html), …], a abertura
    (teste → figuras → veredito → ressalvas) vira a primeira sub-aba ("O teste") e as demais
    abrem em segunda camada de menu — o modelo de duas camadas do painel curado."""
    # a aba saiu do documento (governança, fonte única, benchmark) → não monta
    if cid in FORA:
        return ''
    _novo, _sub = LEGACY.get(cid, (cid, None))
    _anexo = _novo.startswith('anx_')
    if _anexo:
        parte, rotulo, tese, status, kind, peso = 'p4', 'Anexo', _sub, 'CONTEXTO', 'warn', 'compl'
        num = ''
    else:
        _, parte, rotulo, tese, _, status, kind, peso = S.CLAIM_BY_ID[_novo]
        num = _novo[1:]
    anc = ''
    romano = {'p1': 'I', 'p2': 'II', 'p3': 'III', 'p4': 'IV'}[parte]
    # Decisão do Cainan (2026-08-10): o painel mostra DADO. Veredito, status tipado e
    # ressalvas saem de todas as abas; "como testei" e "reproduza esta conta" não são
    # jogados fora — migram para a aba METODOLOGIA, que passa a explicar pergunta a
    # pergunta (ver METODO_POR_PERGUNTA, montado aqui e consumido na aba do fim).
    METODO_POR_PERGUNTA.append({
        'num': num, 'romano': romano, 'rotulo': rotulo, 'tese': tese, 'sub': _sub,
        'anexo': _anexo, 'como': como_testei, 'ressalvas': ressalvas, 'repro': repro_html or ''})
    teste = [kpibar(list(kpis)), extra, _figs_html(figs)]
    if curado:
        teste.append('<div class="curado-hd"><span>▦ Do painel curado</span> desenho do estudo anterior, '
                     'números recalculados nesta base</div>')
        teste.append(_figs_html(curado))
    teste_html = ''.join(teste)
    if _anexo:
        head = ('<div class="pnl-hd"><div class="hd-l"><div class="kicker">Anexo · material de contexto</div>'
                f'<h2>{tese}</h2></div></div>')
    elif _sub:
        # continuação: entra na mesma aba, sob subtítulo, sem repetir o cabeçalho
        head = (f'<div class="contsep"></div><div class="pnl-hd" style="margin-top:34px"><div class="hd-l">'
                f'<div class="kicker">Continuação da alegação {num}</div><h3>{_sub}</h3></div></div>')
    else:
        head = ('<div class="pnl-hd"><div class="hd-l">'
                f'<div class="kicker">Parte {romano} · Pergunta {num} · {rotulo}</div><h2>{tese}</h2></div></div>')
    if subabas:
        panels = [('teste', 'Panorama', teste_html)] + list(subabas)
        btns = ''.join(
            f'<button class="stab{" on" if i == 0 else ""}" data-target="sp-{cid}-{sid}">{lab}</button>'
            for i, (sid, lab, _) in enumerate(panels))
        panes = ''.join(
            f'<div class="spanel" id="sp-{cid}-{sid}" style="display:{"block" if i == 0 else "none"}">{h_}</div>'
            for i, (sid, lab, h_) in enumerate(panels))
        corpo = f'<div class="swrap"><div class="stabs">{btns}</div>{panes}</div>'
    else:
        corpo = teste_html
    _lnk = '' if _sub and not _anexo else (
        f'<a class="plink" href="{ENS}#{_novo}">← ler esta pergunta no argumento</a>'
        f'<a class="xtab" href="#metodologia">◇ como esta conta é feita →</a>')
    return head + corpo + _lnk


# ════════════════════════ ABAS C1–C14 ════════════════════════
# 2026-08-17: as abas de PERGUNTA e os anexos foram removidos daqui.
# O painel passa a ser só a camada de dados gerais; a camada das perguntas
# será recriada do zero. Histórico no git.

# ════════════════════════ ABAS ANEXAS ════════════════════════
fmt_pct = lambda num, den: (br(100 * num / den, 1) + '%') if den else '—'
tab_sp_cat = tabela(['Categoria', 'Obras', 'Crítica', 'Papers/obra', 'Presença intl', 'IMDb mediano'],
                    [[r.cat, br(r.n, 0), br(r.critica_media, 2), br(r.papers_soma / r.n, 2),
                      fmt_pct(r.n_presenca_intl, r.n), br(r.imdb_votes_mediana, 0)]
                     for r in sc.sort_values('papers_obra', ascending=False).itertuples()])
aba_dados = (
    '<div class="kicker">Reprodutibilidade</div><h2>Os dados abertos por trás de tudo</h2>'
    f'<p class="lead">Este trabalho é uma demonstração do <a href="{S.RIDAB_PORTAL}">RIDAB</a> — Repositório '
    f'Independente do Audiovisual Brasileiro: dezenas de bases oficiais (ANCINE, CNC, BFI, INCAA, ACAU, Lumière, '
    f'IBGE) em Parquet aberto, com catálogo, esquema e licença CC-BY-4.0.</p>'
    f'<p>Cada aba traz seu bloco <i>reproduza esta conta</i>. O padrão: os <b>microdados</b> vêm do RIDAB '
    f'(consultáveis por DuckDB direto da nuvem); a <b>consolidação obra-a-obra</b> vive nos scripts versionados '
    f'deste repositório; o que vem do estudo anterior ou de fontes públicas entra marcado como <b>documental</b>.</p>'
    f'<pre class="rsql">import duckdb\ncon = duckdb.connect()\ncon.sql("INSTALL httpfs; LOAD httpfs;")\n'
    f'con.sql("""\n  SELECT ano_edital, COUNT(*) AS contratos\n  FROM \'{HFP}/fomento_fsa.parquet\'\n'
    f'  GROUP BY 1 ORDER BY 1\n""").show()</pre>'
    f'<p style="font-size:13.5px;color:#7b849a">Explore no navegador: <a href="{S.RIDAB_PORTAL}/explorar">RIDAB › '
    f'Explorar</a> · catálogo: <a href="{S.RIDAB_PORTAL}/datasets/">datasets</a> · espelho: '
    f'<a href="{S.RIDAB_HF}">Hugging Face</a>.</p>')

# ── insumos que as abas de dados gerais usam (vinham do bloco removido) ──
TTi = TT.set_index('k')
tab_tipos = tabela(
    ['Perfil', 'Grupos', '% do dinheiro público', 'Retorno dom.', 'Espect./R$ mi',
     '% recorrente', '% anteriores a 2006'],
    [[r.k, f'{int(r.n_produtoras)}', f'{br(r.pct_fsa,1)}%', f'{br(r.roi_fsa_crt,2)}',
      f'{br(r.pub_por_mi_fsa,0)}', f'{br(r.pct_recorrente,0)}%', f'{br(r.pct_pre2006,0)}%']
     for r in TT.itertuples()])
_TOPO = TT[TT.k.isin(['Duplo Retorno', 'Retorno Doméstico'])]
_BASE = TT[TT.k.str.startswith(('Fomento Baixo', 'Pequeno Porte'))]
_rec_tot = TT.receita_crt_mi.sum()

# ════════════════ BLOCO 1 · DADOS GERAIS — as 4 abas do painel curado ════════════════
# Decisão do Cainan (2026-08-10): o painel abre pelos DADOS GERAIS, nas mesmas quatro abas
# do painel do estudo anterior (Visão geral · Chamadas · Produtoras · Concentração), cada
# uma com as suas sub-abas e a sua base completa dentro — como no original. Só DEPOIS vêm
# as perguntas, na ordem do ensaio. As figuras são compartilhadas com as abas de alegação
# sem duplicar payload (ver `DL()` em site_base: N divs, 1 spec).
def _sub(cid, panels):
    """Sub-abas no mesmo desenho de `secao_claim` (o router liga por .swrap/.stab/.spanel)."""
    btns = ''.join(f'<button class="stab{" on" if i == 0 else ""}" data-target="sp-{cid}-{sid}">{lab}</button>'
                   for i, (sid, lab, _) in enumerate(panels))
    panes = ''.join(f'<div class="spanel" id="sp-{cid}-{sid}" style="display:{"block" if i == 0 else "none"}">{h_}</div>'
                    for i, (sid, _, h_) in enumerate(panels))
    return f'<div class="swrap"><div class="stabs">{btns}</div>{panes}</div>'


# ── ABA 1 · VISÃO GERAL — o dinheiro por instrumento de financiamento ──────────
g_visao = (
    kpibar([kpi(f'{br(IND["obras_aplicacao"],0)}', 'obras no universo de aplicação'),
            kpi(f'{br(IND["obras_retorno"],0)}', 'no universo de retorno (com as duas pontas)'),
            kpi(f'R$ {br(IND["inv_total_retorno_mi"]/1000,2)} <small>bi</small>', 'dinheiro público medido (R$ 2024)'),
            kpi(f'{br(IND["retorno_dom"],2)}', 'retorno doméstico de referência', 'res'),
            kpi(f'{br(IND["publico_mi"],1)} <small>mi</small>', 'espectadores observados', 'res'),
            kpi(f'{br(IND["pct_sinal_intl"],0)}%', 'com sinal internacional', 'int')])
    + '<p class="lead">A aba de abertura do painel curado: os quatro grupos de financiamento — renúncia pura, '
    'FSA puro e os dois mistos — lado a lado nas duas réguas. É o retrato de quem põe o dinheiro e do que sai '
    'de cada arranjo.</p>'
    + _sub('gv', [
        ('resumo', 'Visão geral', tab_grupos
         + _figs_html([(DL(f_disp_grupo), 'Investimento × retorno por obra e grupo de financiamento (escala log): '
                                          'a nuvem inteira, com a mediana de cada arranjo.')], cols=1)
         + '<h3 style="font-size:16px;margin:22px 0 4px;color:#e8ecf4">A mesma população, eixos à sua escolha</h3>'
         + '<div class="chart">' + xys_grupos + '</div>'),
        ('dom', 'Retorno doméstico',
         _figs_html([(DL(f_ren1), 'Público e retorno doméstico por composição do financiamento: a renúncia tem o '
                                  'maior ROI; o misto, o maior público.'),
                     (DL(f_grup), 'ROI doméstico por origem do dinheiro (média ponderada): a renúncia pura é o '
                                  'único grupo que recupera em sala.'),
                     (DL(f_c1), 'ROI doméstico por mecanismo: quase nenhum recupera caixa em sala — por desenho.'),
                     (DL(f_jan), 'O retorno doméstico separando o observado (bilheteria) do estimado (janelas CRT).'),
                     (DL(f_topdom), 'As 15 maiores bilheterias entre as obras com FSA (R$ 2024).')])),
        ('intl', 'Retorno internacional',
         cards_intl
         + _figs_html([(DL(f_ren2), 'O perfil internacional por composição de financiamento: FSA majoritário lidera.'),
                       (DL(f_ren3), 'Internacional por instrumento: o misto concentra as admissões europeias.'),
                       (DL(f_mapa_eu), 'Títulos brasileiros em catálogos VOD por país (Lumière).'),
                       (DL(f_topvod), 'Top países por nº de títulos brasileiros em VOD.'),
                       (DL(f_itop), 'As 12 obras de maior índice internacional (0–100). A cauda cai rápido.')])
         + '<h3 style="font-size:16px;margin:22px 0 4px;color:#e8ecf4">País a país — ligue e desligue as fontes</h3>'
         + cb_paises),
        ('setor', 'O setor em volta',
         _figs_html([(DL(f_macro), 'FSA real e valor adicionado da cadeia do cinema: contexto, nunca causa.'),
                     (DL(f_exp), 'Comércio exterior de serviços audiovisuais: exportação sobe, saldo negativo.'),
                     (DL(f_parque), 'O parque exibidor: salas em operação e complexos.'),
                     (DL(f_preco), 'Preço médio do ingresso ao longo da série.')])),
    ]))

# ── ABA 2 · RANKINGS — obras → produtoras → chamadas, as três bases completas ─
# Decisão do Cainan (2026-08-10): logo depois da visão geral vem uma aba SÓ de ranking,
# nesta ordem. As três tabelas densas moram aqui (não são duplicadas nas abas temáticas,
# que trazem os resumos e apontam para cá com o chip ▦).
g_rankings = (
    kpibar([kpi(f'{len(OB_ROWS)}', 'obras no ranking'),
            kpi(f'{len(PRD_ROWS)}', 'produtoras'),
            kpi(f'{len(CH_ROWS)}', 'chamadas'),
            kpi('29 · 24 · 16', 'colunas por linha em cada tabela', 'int'),
            kpi(f'R$ {br(bg.bilheteria_deflac.max()/1e6,0)} <small>mi</small>', 'maior bilheteria individual', 'res'),
            kpi(f'R$ {br(bp.fsa.max()/1e6,0)} <small>mi</small>', 'maior captação individual de FSA')])

    + _sub('gr', [
        ('obras', 'Obras', it_obras),
        ('produtoras', 'Produtoras', it_prod),
        ('chamadas', 'Chamadas', it_chamadas),
    ]))

# ── ABA 3 · CHAMADAS — o mecanismo como unidade de análise ────────────────────
g_chamadas = (
    kpibar([kpi(f'{len(CH_ROWS)}', 'chamadas na base consolidada'),
            kpi(f'{len(MR_ITEMS)}', 'mecanismos distintos'),
            kpi(f'{br(gn2["p2_bilh_pub"],0)}', 'espect./R$ mi — critério bilheteria', 'res'),
            kpi(f'{br(gn2["p2_fest_pub"],0)}', 'espect./R$ mi — critério festival', 'warn'),
            kpi(f'{br(gn2["p2_fest_intlpct"],0)}%', 'com sinal intl — critério festival', 'int'),
            kpi(f'{br(gn2["p2_bilh_intlpct"],0)}%', 'com sinal intl — critério bilheteria', 'int')])
    + '<p class="lead">A aba "Categorias das Chamadas" do painel curado: o quadrante que posiciona cada '
    'mecanismo nas duas vocações, o ranking que troca de régua no botão, os cards de critério e as duas bases '
    'completas — chamada a chamada e obra a obra.</p>'
    + _sub('gc', [
        ('quadrante', 'Comparação',
         '<div class="chart">' + xys_quad_cat + '</div>' + mr_cat
         + _figs_html([(DL(f_rk_cat), 'Bilheteria acumulada, nº de obras e FSA investido por categoria (sem TV).'),
                       (DL(f_rk_cat_int), 'O par internacional: admissões acumuladas na Europa por categoria.'),
                       (DL(f_roi_dom_cat), 'Retorno doméstico agregado por categoria de chamada.'),
                       (DL(f_roi_int_cat), 'Retorno internacional médio (0–100) por categoria de chamada.'),
                       (DL(f_ipen), 'A penetração internacional por mecanismo completo.'),
                       (DL(f_tl), 'Valor investido por ano e categoria — o cardápio se reconfigura ano a ano.')])
         + '<a class="xtab" href="#g_rankings">▦ Ranking de mecanismos por métrica →</a>'),
        ('criterios', 'Critérios & resultados',
         '<p class="lead">Os cards "Categorias de Fomento — Critérios e Resultados" do painel curado: cada '
         'mecanismo com seu volume, alcance e retorno agregado.</p>' + cards_criterios
         + '<h3 style="font-size:16px;margin:22px 0 4px;color:#e8ecf4">Qual mecanismo lidera cada métrica</h3>'
         + tab_sintese_metrica),
        ('chamadas', 'Chamadas detalhadas',
         '<p class="lead">As 25 chamadas com mais obras. A base inteira, com as 16 colunas, pílulas de '
         'categoria e ordenação por qualquer régua, fica na aba Rankings.</p>'
         + '<a class="xtab" href="#g_rankings">▦ Todas as chamadas, uma a uma →</a>' + tab_chamadas),
        ('obras', 'Obras por mecanismo',
         '<p class="lead">Como as obras se distribuem entre os mecanismos. A base obra a obra, com as 26 '
         'colunas, fica na aba Rankings.</p>'
         + '<a class="xtab" href="#g_rankings">▦ Todas as obras, uma a uma →</a>'
         + _figs_html([(DL(f_disp_chamada), 'Cada ponto é uma chamada: retorno doméstico × desempenho '
                                            'internacional; tamanho pelo dinheiro aplicado.')], cols=1)),
    ]))

# ── ABA 3 · PRODUTORAS — a empresa como unidade de análise ────────────────────
g_produtoras = (
    kpibar([kpi(f'{len(PTO)}', 'grupos econômicos na carteira'),
            kpi(f'{len(PRD_ROWS)}', 'produtoras na base'),
            kpi(f'R$ {br(bp.fsa.max()/1e6,0)} <small>mi</small>', 'maior captação individual de FSA'),
            kpi(f'{int(_TOPO.n_produtoras.sum())}', 'grupos devolvem em alguma régua', 'res'),
            kpi(f'{br(_TOPO.pct_fsa.sum(),0)}%', 'do dinheiro foi para eles'),
            kpi(f'{br(gn3["pct_tira_unica"],0)}%', 'aparecem uma única vez', 'warn')])
    + '<p class="lead">A aba "Produtoras" do painel curado: os perfis de retorno, a matriz de portfólio, o '
    'ranking interativo da carteira inteira e a trajetória das empresas.</p>'
    + _sub('gp', [
        ('clusters', 'Por cluster',
         cards_tipos + tab_tipos
         + _figs_html([(DL(f_tipo), 'Os seis perfis: % do dinheiro absorvido × retorno doméstico; bolha = nº de grupos.'),
                       (DL(f_perfil_br), 'Quanto cada perfil recebeu e quanto devolveu.'),
                       (DL(f_box_roi), 'ROI doméstico por perfil (boxplot): a mediana de cada tipo, não só a média.'),
                       (DL(f_box_intl), 'Desempenho internacional por perfil.')])),
        ('portfolio', 'Matriz de portfólio',
         '<p class="lead">A dispersão de produtoras do painel curado — a leitura fixa e, abaixo, a versão com '
         'os controles do original: eixos configuráveis, escala Lin/Log e busca por produtora.</p>'
         + _figs_html([(DL(f_disp_prod), 'Cada ponto é uma produtora: FSA captado (x, log) × ROI doméstico '
                                         '(y, log); bolha = nº de obras; cor = perfil.'),
                       (DL(f_quadp), 'A mesma população nas duas dimensões: ROI doméstico × desempenho internacional.')])
         + '<div class="chart">' + xys_prod + '</div>'),
        ('ranking', 'Quem lidera',
         '<p class="lead">Os topos por régua. A carteira inteira, com as 24 colunas e as pílulas de perfil, '
         'fica na aba Rankings.</p>'
         + '<a class="xtab" href="#g_rankings">▦ Todas as produtoras, uma a uma →</a>'
         + _figs_html([(DL(f_rk_fsa), 'As 15 produtoras que mais captaram FSA (R$ 2024).'),
                       (DL(f_rk_bil), 'As 15 produtoras de maior bilheteria acumulada.'),
                       (DL(f_rk_eu), 'As 10 produtoras com mais admissões na Europa (Lumière).')])
         + '<h3 style="font-size:16px;margin:22px 0 4px;color:#e8ecf4">Top 20 por bilheteria — em detalhe</h3>'
         + tab_top_prod),
        ('trajetoria', 'Trajetória & recorrência',
         _figs_html([(DL(f_rec), 'Recorrentes concentram a maior parte do FSA.'),
                     (DL(f_tick), 'O acerto na primeira obra eleva o ticket das seguintes.'),
                     (DL(f_pre06), f'Quem já produzia antes do FSA ter escala domina o topo ({GL["fonte_pre2006"]}).'),
                     (DL(f_addon), 'Quem recebe apoio à ponta já vendia.')])),
    ]))

# ── ABA 4 · CONCENTRAÇÃO — pulverização, desigualdade e o custo de existir ────
g_concentracao = (
    kpibar([kpi(f'{br(IND["gini_fsa_produtora"],2)}', 'Gini do FSA por produtora', 'warn'),
            kpi(f'{br(IND["gini_bilheteria_obra"],2)}', 'Gini da bilheteria por obra', 'warn'),
            kpi(f'{br(gn3["share_top10_fsa"],0)}%', 'do FSA nas dez maiores'),
            kpi(f'{br(IND["rj_sp_share"],0)}%', 'do investimento em RJ+SP', 'warn'),
            kpi(f'R$ {br(IND["produtoras_mediana_inv_anual"]/1000,0)} <small>mil</small>', 'ticket anual mediano', 'warn'),
            kpi(f'{br(100*abaixo_400k/len(tk),0)}%', 'operam abaixo do custo fixo mínimo', 'warn')])
    + '<p class="lead">A aba "Concentração" do painel curado: quantas empresas o fundo criou, como o dinheiro '
    'se distribui entre elas e se o aporte cobre o custo de manter uma produtora de pé.</p>'
    + _sub('gk', [
        ('prolif', 'Proliferação',
         _figs_html([(DL(f_prolif), 'Produtoras ativas por ano e universo acumulado (base atual, 2014+).'),
                     (DL(f_pdelta), 'Entradas × saídas: produtoras estreando no FSA (verde), última obra do '
                                    'recorte (vermelho) e o estoque ativo (linha). As bordas 2014/2023 inflam ambas.')])),
        ('desigual', 'Desigualdade',
         _figs_html([(DL(f_lz), 'Curva de Lorenz — FSA por produtora: a distância até a diagonal é a desigualdade.'),
                     (DL(f_gini), 'Gini anual do fundo (azul) × acumulado (ouro) × concentração do mercado (vermelho).'),
                     (DL(f_shareN), 'Share acumulado do FSA por nº de produtoras.'),
                     (DL(f_uf), 'Público de filmes brasileiros por UF.')])),
        ('ticket', 'Ticket & viabilidade',
         cards_ticket
         + _figs_html([(DL(f_ticket_hist), 'Distribuição do ticket anual combinado (fomento + proxy RLP), com o '
                                           'tracejado no custo fixo mínimo. A massa está à esquerda da linha.'),
                       (DL(f_c6fig), 'Conversão (barras) e chegada à sala (linha) sobem com o tamanho do aporte.')])),
        ('cadeia', 'A cadeia que reparte',
         _figs_html([(DL(f_dist), 'Concentração da distribuição: público por distribuidora (vermelho = major).'),
                     (DL(f_exib), 'Concentração da exibição: público por operador de salas.'),
                     (DL(f_elo), 'A posição relativa de cada elo da cadeia (Produtora = 100).')])),
    ]))

# ════════════════════════ MONTAGEM: SIDEBAR + ABAS + ROUTER ════════════════════════
# fusão 14 → 8: as abas legadas são concatenadas na alegação nova a que pertencem
# 2026-08-17 (Cainan): só Rankings e Chamadas ficam liberados. Visão geral,
# Produtoras e Concentração seguem visíveis na barra lateral como botão
# DESLIGADO — o conteúdo delas não é gerado, então não há como alcançá-lo nem
# pela URL. Basta devolver o par à lista abaixo para religar.
ABAS = [('g_rankings', g_rankings),
        ('g_chamadas', g_chamadas),
        ('dados', aba_dados)]
DESLIGADAS = [('g_visao', '1', 'Visão geral'),
              ('g_produtoras', '4', 'Produtoras'),
              ('g_concentracao', '5', 'Concentração')]

nav_parts = ['<div class="pn-label">Painel</div>',
             '<div class="pn-grp">Dados gerais</div>']
_ORDEM = [('g_visao', '1', 'Visão geral'), ('g_rankings', '2', 'Rankings'),
          ('g_chamadas', '3', 'Chamadas'), ('g_produtoras', '4', 'Produtoras'),
          ('g_concentracao', '5', 'Concentração')]
_LIBERADAS = {aid for aid, _ in ABAS}
for _aid, _num, _lab in _ORDEM:
    if _aid in _LIBERADAS:
        _on = ' on' if _aid == ABAS[0][0] else ''
        nav_parts.append(f'<a class="pn-item{_on}" data-aba="{_aid}" href="#{_aid}">'
                         f'<span class="pn-num pn-g">{_num}</span>{_lab}</a>')
    else:
        nav_parts.append(f'<span class="pn-item pn-off" aria-disabled="true" '
                         f'title="em preparação">'
                         f'<span class="pn-num">{_num}</span>{_lab}'
                         f'<span class="pn-tag">em breve</span></span>')
nav_parts.append('<div class="pn-sep">Fonte</div>')
nav_parts.append('<a class="pn-item" data-aba="dados" href="#dados">'
                 '<span class="pn-num">▹</span>Dados abertos</a>')
sidebar = '<nav class="pn" id="pn">' + ''.join(nav_parts) + '</nav>'

abas_html = ''.join(
    f'<div class="aba" id="aba-{aid}" style="display:{"block" if aid == ABAS[0][0] else "none"}">{conteudo}</div>'
    for aid, conteudo in ABAS)

CSS_PANEL = """
.pl{display:flex;align-items:flex-start}
.pn{position:sticky;top:49px;flex:0 0 248px;max-height:calc(100vh - 49px);overflow-y:auto;
    padding:18px 10px 40px 18px;border-right:1px solid #1c2030;scrollbar-width:thin}
.pn-label{font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:#7b849a;font-weight:800;margin:0 0 8px 10px}
.pn-grp{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:#5b647c;font-weight:800;margin:16px 0 4px 10px;line-height:1.4}
.pn-sep{font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:#7b849a;font-weight:800;
        margin:22px 0 6px;padding:10px 10px 0;border-top:1px solid #1c2030}
.pn-num.pn-g{background:#1a2338;border-color:#2a3a5e;color:#38bdf8}
/* ── aba de metodologia: um bloco dobrável por pergunta ── */
.msec{font-size:12px;text-transform:uppercase;letter-spacing:.13em;color:#6c7bf7;font-weight:800;
      margin:34px 0 8px;padding-top:16px;border-top:1px solid #232838}
.mq{background:#12151e;border:1px solid #232838;border-radius:10px;margin-bottom:8px;overflow:hidden}
.mq>summary{list-style:none;cursor:pointer;padding:12px 16px;display:flex;flex-direction:column;gap:3px;transition:.12s}
.mq>summary::-webkit-details-marker{display:none}
.mq>summary:hover{background:#161a25}
.mq-k{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:#6c7bf7;font-weight:800}
.mq-t{font-size:14px;font-weight:700;color:#e8ecf4;line-height:1.35}
.mq[open]>summary{border-bottom:1px solid #232838;background:#161a25}
.mq[open] .mq-t::before{content:"▾  ";color:#6c7bf7}
.mq:not([open]) .mq-t::before{content:"▸  ";color:#5b647c}
.mq-b{padding:14px 18px 16px}
.mq-b p{font-size:13.5px;color:#a8b0c0;margin-bottom:12px}
.mq-lab{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:#7b849a;font-weight:800;margin-bottom:5px}
.pn-item{display:flex;align-items:center;gap:9px;padding:7px 10px;border-radius:9px;font-size:13px;font-weight:600;
         color:#a8b0c0;text-decoration:none;transition:.12s;line-height:1.3}
.pn-item:hover{background:#14171f;color:#e2e8f0}
.pn-item.on{background:#1a1f2e;color:#e8ecf4;border:1px solid #282d42}
.pn-item.pn-off{color:#4a5164;cursor:not-allowed;user-select:none}
.pn-item.pn-off:hover{background:none;color:#4a5164}
.pn-item.pn-off .pn-num{background:#0f1218;border-color:#1a1f2c;color:#39405260}
.pn-tag{margin-left:auto;font-size:9.5px;font-weight:700;letter-spacing:.07em;
        text-transform:uppercase;color:#3d4457}
.pn-num{flex:none;width:22px;height:22px;border-radius:7px;background:#14171f;border:1px solid #232838;
        display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:#6c7bf7}
.pn-item.on .pn-num{background:#232a44}
.pn-anc{margin-left:auto;color:#6c7bf7;font-size:8px}
.pc{flex:1;min-width:0;padding:22px 30px 80px;max-width:1620px}
.aba h2{font-size:23px;margin-bottom:10px}
/* ── chrome de PAINEL (não de artigo): cabeçalho compacto, KPIs, grade de cards ── */
.pnl-hd{display:flex;align-items:flex-start;gap:18px;flex-wrap:wrap;padding:0 0 14px;margin-bottom:16px;
        border-bottom:1px solid #232838}
.pnl-hd .hd-l{flex:1;min-width:260px}
.pnl-hd .kicker{margin-bottom:6px}
.pnl-hd h2{margin-bottom:0;max-width:900px}
.pnl-hd h3{font-size:18px;font-weight:800;color:#e8ecf4;margin:0}
.pnl-st{flex:none;align-self:center}
.kpibar{display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:10px;margin:0 0 16px}
.kpi{background:#12151e;border:1px solid #232838;border-top:2px solid #6c7bf7;border-radius:10px;padding:11px 13px 10px}
.kpi.res{border-top-color:#34d399}.kpi.warn{border-top-color:#fbbf24}.kpi.int{border-top-color:#a78bfa}
.kpi .v{font-size:22px;font-weight:800;color:#e8ecf4;line-height:1.05;letter-spacing:-.5px}
.kpi .v small{font-size:12.5px;font-weight:700;color:#7b849a}
.kpi .l{font-size:10.5px;color:#7b849a;margin-top:5px;line-height:1.35}
.howto{background:#101320;border:1px solid #232838;border-left:3px solid #38bdf8;border-radius:10px;
       padding:12px 15px;margin:0 0 16px;font-size:13px;color:#9aa3b5;line-height:1.55}
.howto b{color:#cbd5e1}
.howto .ht{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:#38bdf8;
           font-weight:800;margin-bottom:5px}
.figgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(410px,1fr));gap:12px;margin:14px 0}
.figgrid.one{grid-template-columns:1fr}
.card.span2{grid-column:1/-1}
.card{background:#12151e;border:1px solid #232838;border-radius:12px;padding:12px 12px 4px;
      display:flex;flex-direction:column;min-width:0}
.card>div:first-child{min-width:0}
.card-c{font-size:12px;color:#7b849a;line-height:1.5;padding:8px 4px 10px;margin-top:auto;border-top:1px solid #1a1f2e}
.card-c b{color:#a8b0c0}
.xtab{display:inline-flex;align-items:center;gap:8px;margin:14px 8px 4px 0;font-size:12.5px;font-weight:700;
      color:#38bdf8;text-decoration:none;background:#101728;border:1px solid #24304e;border-radius:20px;padding:8px 15px}
.xtab:hover{border-color:#38bdf8}
.aba .lead{font-size:14px;max-width:960px}
.aba p{font-size:14px}
@media(max-width:900px){.figgrid{grid-template-columns:1fr}.pc{padding:18px 16px 70px}}
.curado-hd{margin:34px 0 6px;padding:12px 16px;background:#101728;border:1px solid #24304e;border-left:3px solid #38bdf8;
           border-radius:10px;font-size:13px;color:#8f98ab}
.curado-hd span{display:block;font-size:13.5px;font-weight:800;color:#38bdf8;margin-bottom:2px}
.swrap{margin-top:18px}
.stabs{display:flex;flex-wrap:wrap;gap:2px;border-bottom:1px solid #232838;margin-bottom:20px}
.stab{appearance:none;background:none;border:0;border-bottom:2px solid transparent;color:#8f98ab;font:700 12px 'Inter',sans-serif;
      letter-spacing:.06em;text-transform:uppercase;padding:10px 14px;cursor:pointer;transition:.12s}
.stab:hover{color:#e2e8f0}
.stab.on{color:#e8ecf4;border-bottom-color:#6c7bf7}
.clcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:12px;margin:18px 0}
.clc{background:#12151e;border:1px solid #232838;border-top:3px solid #6c7bf7;border-radius:12px;padding:14px 15px}
.clc-h{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:4px}
.clc-h span{font-size:12.5px;font-weight:800;color:#e8ecf4}
.clc-h b{font-size:20px;font-weight:800;color:#e8ecf4}
.clc-d{font-size:11.5px;color:#7b849a;line-height:1.45;margin-bottom:9px;min-height:32px}
.clc-m{display:flex;justify-content:space-between;font-size:12px;color:#8f98ab;padding:3px 0;border-top:1px solid #1a1f2e}
.clc-m b{color:#cbd5e1;font-weight:700}
.gloss{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-top:16px}
.g{background:#12151e;border:1px solid #232838;border-radius:10px;padding:13px 15px}
.g dt{font-size:13px;font-weight:800;color:#e8ecf4;margin-bottom:5px}
.g dd{font-size:12.5px;color:#8f98ab;line-height:1.55;margin:0}
@media(max-width:900px){
  .pl{flex-direction:column}
  .pn{position:static;flex:none;width:100%;max-height:none;display:flex;flex-wrap:wrap;gap:4px;
      border-right:0;border-bottom:1px solid #1c2030;padding:12px 14px}
  .pn-label,.pn-grp{display:none}
  .pn-item{padding:5px 10px;font-size:12px}
  .pc{padding:22px 16px 70px}
}
/* ── componentes interativos (estilo do painel curado) ── */
.it-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:14px 0 10px}
.it-q{background:#101320;border:1px solid #282d42;border-radius:8px;color:#e2e8f0;font:500 13px 'Inter',sans-serif;
      padding:7px 12px;min-width:190px;outline:none}
.it-q:focus{border-color:#6c7bf7}
.it-f{background:#101320;border:1px solid #282d42;border-radius:8px;color:#a8b0c0;font:600 12px 'Inter',sans-serif;
      padding:7px 8px;outline:none;max-width:230px}
.it-n{margin-left:auto;font-size:11.5px;color:#7b849a;white-space:nowrap}
.it-wrap{overflow:auto;border:1px solid #282d42;border-radius:10px}
.it-t thead th{position:sticky;top:0;z-index:2;cursor:pointer;user-select:none}
.it-t thead th:hover{color:#e2e8f0}
.it-t thead th.on{color:#8b97f9}
.it-s{color:#6c7bf7}
/* ── desenho das tabelas-ranking do painel curado: pills, chips, mini-barras, posição ── */
.it-pills{display:flex;flex-wrap:wrap;gap:6px;width:100%;margin-top:4px}
.it-pill{appearance:none;display:inline-flex;align-items:center;gap:7px;background:#101320;border:1px solid #282d42;
         border-radius:16px;color:#8f98ab;font:700 11.5px 'Inter',sans-serif;padding:5px 11px;cursor:pointer;transition:.12s}
.it-pill:hover{color:#e2e8f0;border-color:#3a4160}
.it-pill b{font-size:10px;font-weight:800;color:#7b849a;background:#1a1f2e;border-radius:9px;padding:1px 6px}
.it-pill.on{color:#e8ecf4;background:#232a44;border-color:#6c7bf7}
.it-pill.on b{color:#c7cef5;background:#2f3760}
.it-pill[style*="--pc"].on{border-color:var(--pc);background:color-mix(in srgb,var(--pc) 16%,#101320)}
.it-chip{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.02em;padding:2px 9px;border-radius:11px;
         border:1px solid;white-space:nowrap;max-width:250px;overflow:hidden;text-overflow:ellipsis;vertical-align:middle}
.it-hrk,.it-trk{width:34px;text-align:right;color:#5b647c;font-weight:800;font-size:11.5px;padding-right:4px!important}
/* colunas congeladas: com 16 colunas o scroll horizontal não pode levar embora QUEM é a linha */
.it-t td.it-trk,.it-t th.it-hrk{position:sticky;left:0;z-index:3;background:#101320}
.it-t th.it-hrk{z-index:5}
.it-t td.it-c0,.it-t th.it-c0{position:sticky;left:34px;z-index:3;background:#101320;
  max-width:250px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  box-shadow:1px 0 0 #232838;font-weight:600;color:#e8ecf4}
.it-t th.it-c0{z-index:5}
.it-t tr:hover td.it-c0,.it-t tr:hover td.it-trk{background:#151a28}
.it-t td.it-ss{max-width:210px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.it-bcell{min-width:120px}
.it-bwrap{display:inline-block;vertical-align:middle;width:52px;height:6px;background:#1a1f2e;border-radius:3px;
          overflow:hidden;margin-right:8px}
.it-bar2{display:block;height:100%;background:linear-gradient(90deg,#6c7bf7,#38bdf8);border-radius:3px}
.it-bv{display:inline-block;min-width:52px;text-align:right;font-weight:700;color:#e8ecf4}
.ctrl-bar{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 12px}
.ctrl{appearance:none;background:#101320;border:1px solid #282d42;border-radius:16px;color:#8f98ab;
      font:700 11px 'Inter',sans-serif;padding:6px 12px;cursor:pointer;transition:.12s;letter-spacing:.02em}
.ctrl:hover{color:#e2e8f0;border-color:#3a4160}
.ctrl.on{color:#e8ecf4;background:#232a44;border-color:#6c7bf7}
.mr-rows{margin-top:6px}
.mr-row{display:flex;align-items:center;gap:10px;padding:4px 0;border-bottom:1px solid #14171f}
.mr-l{flex:0 0 250px;font-size:12.5px;font-weight:600;color:#cbd5e1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mr-bwrap{flex:1;display:flex;height:16px;background:#101320;border-radius:4px;overflow:hidden}
.mr-b{height:100%;background:linear-gradient(90deg,#6c7bf7,#38bdf8);border-radius:4px}
.cb-seg{height:100%}
.mr-v{flex:0 0 120px;text-align:right;font-size:12px;font-weight:700;color:#e8ecf4;white-space:nowrap}
.cb-bar{display:flex;flex-wrap:wrap;align-items:center;gap:16px;margin:14px 0 10px}
.cb-l{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;font-weight:600;color:#a8b0c0;cursor:pointer}
.cb-l input{accent-color:#6c7bf7}
.cb-dot{width:10px;height:10px;border-radius:3px;display:inline-block}
.xys-lab{font-size:11px;font-weight:800;color:#7b849a}
@media(max-width:720px){.mr-l{flex-basis:130px}.mr-v{flex-basis:84px}}
"""

ROUTER_JS = """
(function(){
  var VALID = %s;
  function draw(el){
    if (el.dataset.done) return;
    el.dataset.done = '1';
    try{
      var spec = JSON.parse(document.getElementById(el.dataset.plot).textContent);
      Plotly.newPlot(el, spec.data, spec.layout, {displayModeBar:false, responsive:true});
    }catch(e){ el.innerHTML = '<div style="color:#7b849a;font-size:13px;padding:30px">gr\\u00e1fico indispon\\u00edvel</div>'; }
  }
  function drawVisible(root){
    var pend = [].slice.call(root.querySelectorAll('.js-plot')).filter(function(el){
      return !el.dataset.done && el.offsetParent !== null;
    });
    pend.forEach(function(el, i){ setTimeout(function(){ draw(el); }, 30 * i); });
    [].slice.call(root.querySelectorAll('.js-xys')).forEach(function(el){
      if (!el.dataset.done && el.offsetParent !== null && window._xysInit) window._xysInit(el);
    });
  }
  function drawAba(id){
    var host = document.getElementById('aba-' + id);
    if (host) drawVisible(host);
  }
  [].slice.call(document.querySelectorAll('.stab')).forEach(function(b){
    b.addEventListener('click', function(){
      var wrap = b.closest('.swrap');
      [].slice.call(wrap.querySelectorAll('.stab')).forEach(function(x){ x.classList.toggle('on', x === b); });
      [].slice.call(wrap.children).forEach(function(p){
        if (p.classList && p.classList.contains('spanel')) p.style.display = 'none';
      });
      var alvo = document.getElementById(b.getAttribute('data-target'));
      if (alvo) {
        alvo.style.display = 'block';
        if (typeof Plotly === 'undefined') { setTimeout(function(){ drawVisible(alvo); }, 300); }
        else { drawVisible(alvo); }
      }
    });
  });
  function show(id){
    if (VALID.indexOf(id) < 0) id = VALID[0];
    [].slice.call(document.querySelectorAll('.aba')).forEach(function(a){ a.style.display = 'none'; });
    var el = document.getElementById('aba-' + id);
    if (el) el.style.display = 'block';
    [].slice.call(document.querySelectorAll('.pn-item')).forEach(function(t){
      t.classList.toggle('on', t.getAttribute('data-aba') === id);
    });
    if (history.replaceState) history.replaceState(null, '', '#' + id);
    window.scrollTo(0, 0);
    function go(){ drawAba(id); }
    if (typeof Plotly === 'undefined') { setTimeout(go, 300); } else { go(); }
  }
  [].slice.call(document.querySelectorAll('.pn-item')).forEach(function(t){
    if (t.classList.contains('pn-off')) return;      // botão desligado: não navega
    t.addEventListener('click', function(ev){ ev.preventDefault(); show(t.getAttribute('data-aba')); });
  });
  window.addEventListener('hashchange', function(){ show(location.hash.replace('#', '') || VALID[0]); });
  function boot(){ show(location.hash.replace('#', '') || VALID[0]); }
  if (document.readyState === 'complete') boot();
  else window.addEventListener('load', boot);
})();
""" % json.dumps([aid for aid, _ in ABAS])

S.ensure_site()
html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Painel de dados | Fomento Audiovisual · FSA 2014–2023</title>
<meta name="description" content="Os agregados do fomento ao cinema brasileiro, obra a obra e chamada a chamada: rankings ordenáveis, dispersões e reprodução via dados abertos do RIDAB.">
<meta property="og:title" content="Painel de dados — Fomento Audiovisual">
<meta property="og:description" content="Rankings de obras, produtoras e chamadas do FSA, com reprodução via dados abertos (RIDAB).">
<meta property="og:type" content="article">
<link rel="icon" href="{S.FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="assets/plotly.min.js" defer></script>
<style>{S.CSS_BASE}{CSS_PANEL}</style></head><body>
{S.sitenav('evidencias')}
<div class="pl">
{sidebar}
<main class="pc">
{abas_html}
<footer class="site">Painel gerado por <code>scripts/22_site_evidencias.py</code>; gráficos desenham ao abrir cada
aba (Plotly local, carregado uma vez). Nenhum número é digitado à mão: tudo sai de script versionado.
<a href="{ENS}">✦ Análise</a> · <a href="index.html">Início</a></footer>
</main>
</div>
<script>{INTERACT_JS}</script>
<script>{ROUTER_JS}</script>
</body></html>"""

out = os.path.join(S.SITE, 'evidencias.html')
with open(out, 'w', encoding='utf-8') as fh:
    fh.write(html)
n_figs = S._plot_n[0]
# ── PNGs das 8 figuras do ensaio (uma por pergunta) ───────────────────────────
# O ensaio e o DOCX levam a mesma figura, renderizada uma vez aqui.
_FIGDIR = os.path.join(BASE, 'site', 'assets', 'figs')
os.makedirs(_FIGDIR, exist_ok=True)
_n_png = 0
for _cid, (_attr, _leg) in S.FIG_PERGUNTA.items():
    if _attr.startswith('__'):
        continue
    _f = globals().get(_attr)
    if _f is None:
        print('  ! figura do ensaio ausente:', _attr)
        continue
    try:
        _f.write_image(os.path.join(_FIGDIR, _attr + '.png'),
                       width=1000, height=int(getattr(_f.layout, 'height', None) or 460), scale=2)
        _n_png += 1
    except Exception as _e:
        print('  ! falha ao exportar', _attr, '::', str(_e)[:90])
print(f'  {_n_png} figuras do ensaio exportadas para site/assets/figs')

# ── specs das figuras dos POPUPS do ensaio (hover num número → o gráfico dele) ─
# O ensaio não recalcula nada: consome estes specs, gerados aqui, uma vez.
_POP = {}
for _k, _fmt, _attr, _leg in S.NUM_FIG:
    if _attr in _POP:
        continue
    _f = globals().get(_attr)
    if _f is None:
        print('  ! figura de popup ausente:', _attr)
        continue
    _POP[_attr] = json.loads(S.fig_spec(_f))
_popout = os.path.join(BASE, 'outputs', 'bases', 'popfigs.json')
with open(_popout, 'w', encoding='utf-8') as _fh:
    json.dump(_POP, _fh, ensure_ascii=False, separators=(',', ':'))
print(f'  {len(_POP)} specs de popup → outputs/bases/popfigs.json '
      f'({os.path.getsize(_popout)/1024:.0f} KB) — rode scripts/21 depois deste')

print(f'OK → site/evidencias.html ({os.path.getsize(out)/1024:.0f} KB) | {n_figs} figuras | '
      f'{_it_n[0]} componentes interativos (tabelas/rankings/dispersões/países) | '
      f'{len(ABAS)} abas (5 dados gerais + fontes) | sidebar + router por hash')
