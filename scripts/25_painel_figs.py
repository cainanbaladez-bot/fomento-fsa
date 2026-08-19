# -*- coding: utf-8 -*-
"""
25_painel_figs.py — figuras COMPLEMENTARES do painel (só painel, não vão no ensaio).

O painel de perguntas do `site/evidencias.html` é montado com as 34 visualizações de
trecho do ensaio (scripts/23 e 24). Estas aqui entram junto, como leitura do conjunto:
o que a passagem não pede mas ajuda a entender o todo — cobertura do dado, forma da
distribuição, série do instrumento, geografia, sobrevivência das empresas.

Saída: `outputs/bases/painelfigs.json`  { id: {secao, titulo, legenda, fonte, spec} }
Rodar:  .\.venv\Scripts\python.exe scripts\25_painel_figs.py   (antes do scripts/22)
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import site_base as S  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RID = os.path.join(BASE, 'data', 'ridab_cleaned')
BASES = os.path.join(BASE, 'outputs', 'bases')
rid = lambda t: pd.read_parquet(os.path.join(RID, t + '.parquet'))
nc = lambda s: re.sub(r'[^0-9A-Z]', '', str(s).upper())
CINZA = '#5a6478'
FIGS = {}


def brn(x, d=1):
    return f'{x:,.{d}f}'.replace(',', '§').replace('.', ',').replace('§', '.')


def curto(s, n=26):
    s = str(s)
    return s if len(s) <= n + 1 else s[:n] + '…'


def reg(gid, secao, titulo, legenda, fonte, fig):
    FIGS[gid] = {'secao': secao, 'titulo': titulo, 'legenda': legenda, 'fonte': fonte,
                 'spec': json.loads(fig.to_json())}
    print(f'  ✓ {gid:<20} [{secao}]  {titulo[:60]}')


def base(fig, h=400, legend=True, ytitle=None, y2title=None, xtitle=None, hover='x unified'):
    fig.update_layout(
        paper_bgcolor='#12151e', plot_bgcolor='#12151e',
        font=dict(family='Inter,system-ui,sans-serif', color=S.TXT, size=11.5),
        margin=dict(l=58, r=58 if y2title else 16, t=10, b=44), height=h, showlegend=legend,
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=10.5), orientation='h',
                    y=1.13, x=0, yanchor='top'),
        hoverlabel=dict(font_size=11.5, font_family='Inter'), hovermode=hover)
    fig.update_xaxes(gridcolor=S.GRID, zerolinecolor=S.GRID, linecolor=S.GRID, title=xtitle,
                     title_font_size=11, tickfont_size=10.5)
    fig.update_yaxes(gridcolor=S.GRID, zerolinecolor=S.GRID, linecolor=S.GRID, title=ytitle,
                     title_font_size=11, tickfont_size=10.5)
    if y2title:
        fig.update_yaxes(title=y2title, secondary_y=True, showgrid=False)
    return fig


B = pd.read_parquet(os.path.join(BASES, 'base_obras.parquet'))
R = B[B.universo_retorno == True].copy()                                    # noqa: E712
P = pd.read_parquet(os.path.join(BASES, 'base_produtoras.parquet'))


# ══════════════════════════════════════════════════════════════════════════════
# c1 · as duas pontas: quanto do dinheiro tem resultado mensurável
# ══════════════════════════════════════════════════════════════════════════════
etapas = [
    ('obras com fomento na<br>carteira 2014–2023', len(B), B.inv_total.sum()),
    ('universo de aplicação<br>(escopo cinema)', int(B.universo_aplicacao.sum()),
     B.loc[B.universo_aplicacao == True, 'inv_total'].sum()),                 # noqa: E712
    ('universo de retorno<br>(com renda encontrada)', int(B.universo_retorno.sum()),
     B.loc[B.universo_retorno == True, 'inv_total'].sum()),                   # noqa: E712
]
f = make_subplots(specs=[[{'secondary_y': True}]])
f.add_bar(x=[e[0] for e in etapas], y=[e[1] for e in etapas], name='obras',
          marker_color=[CINZA, S.ACCENT, S.CYAN],
          text=[f'{e[1]} obras' for e in etapas], textposition='outside', textfont_size=10.5,
          cliponaxis=False, hovertemplate='%{y} obras<extra></extra>')
f.add_scatter(x=[e[0] for e in etapas], y=[e[2] / 1e9 for e in etapas],
              name='dinheiro público correspondente (R$ bi)', mode='lines+markers+text',
              line=dict(color=S.GOLD, width=2.4), marker=dict(size=9),
              text=[f'R$ {brn(e[2] / 1e9, 2)} bi' for e in etapas], textposition='bottom center',
              textfont=dict(size=10, color=S.GOLD), secondary_y=True,
              hovertemplate='R$ %{y:.2f} bi<extra></extra>')
base(f, h=400, ytitle='obras', y2title='R$ bilhões (dez/2024)', hover='closest')
f.update_yaxes(range=[0, len(B) * 1.2])
f.update_yaxes(range=[0, B.inv_total.sum() / 1e9 * 1.25], secondary_y=True)
f.update_xaxes(tickfont_size=10)
_perda = 100 * (1 - B.loc[B.universo_retorno == True, 'inv_total'].sum() / B.inv_total.sum())  # noqa: E712
reg('p_universos', 'c1',
    'As duas pontas — quanto da carteira tem financiamento e resultado ao mesmo tempo',
    f'A regra dos dois universos em três degraus. Do primeiro para o segundo sai o que não é '
    f'cinema; do segundo para o terceiro sai a obra sem renda encontrada — e o dinheiro dela '
    f'sai junto do denominador. No fim, {brn(100 - _perda)}% do dinheiro da carteira fica '
    'dentro da conta de retorno. Um indicador que jogasse no denominador dinheiro sem resultado '
    'mensurável estaria medindo a limitação do dado, não o desempenho.',
    'RIDAB · outputs/bases/base_obras.parquet (scripts/10 e 13)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c1 · a forma da distribuição: o agregado não é a obra típica
# ══════════════════════════════════════════════════════════════════════════════
rd = R[R.retorno_dom > 0].retorno_dom
f = go.Figure()
f.add_histogram(x=np.log10(rd), nbinsx=46, marker_color=S.CYAN, opacity=0.85,
                name='obras', hovertemplate='%{y} obras<extra></extra>')
for v, cor, nome in [(rd.median(), S.GOLD, f'mediana {brn(rd.median(), 2)}×'),
                     (R.receita_ref.sum() / R.inv_total.sum(), S.CORAL,
                      f'agregado {brn(R.receita_ref.sum() / R.inv_total.sum(), 2)}×'),
                     (1.0, '#6b7690', 'renda = investimento')]:
    f.add_vline(x=np.log10(v), line_dash='dot', line_color=cor,
                annotation_text=nome, annotation_font_size=9.5, annotation_font_color=cor,
                annotation_position='top')
base(f, h=400, legend=False, ytitle='obras',
     xtitle='retorno doméstico da obra (escala log)', hover='closest')
f.update_xaxes(tickvals=[-3, -2, -1, 0, 1, 2],
               ticktext=['0,001', '0,01', '0,1', '1', '10', '100'])
reg('p_dist_retorno', 'c1',
    'A obra típica não é o agregado — a distribuição do retorno doméstico',
    f'Cada barra é uma faixa de retorno; a escala é logarítmica porque o fenômeno é '
    f'multiplicativo. A obra mediana devolve {brn(rd.median(), 2)}× o que recebeu, o agregado da '
    f'carteira devolve {brn(R.receita_ref.sum() / R.inv_total.sum(), 2)}× — a distância entre as '
    'duas linhas é a concentração do resultado em poucos títulos. Ler a média sem olhar a forma '
    'da distribuição leva a conclusões erradas sobre a obra comum.',
    'RIDAB · base_obras (universo de retorno, 855 obras)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c2 · a matriz critério × resultado
# ══════════════════════════════════════════════════════════════════════════════
CAT_FSA = ['Bilheteria · Distribuidora', 'Bilheteria · Produtora', 'Festivais · Pontuação',
           'Automático Bilheteria', 'Automático Festivais', 'Coprodução Intl',
           'Arranjos Regionais', 'Add-on FSA (Compl./Comerc.)']


def agg(d):
    inv = d.inv_total.sum()
    return dict(ret=d.receita_ref.sum() / inv,
                intl=d.roi_internacional_0_100.sum() / (inv / 1e6),
                pct=100 * (d.roi_internacional_0_100 > 0).mean(),
                pub=d.publico_domestico.sum() / inv * 1e6,
                estreia=100 * (d.bilheteria_obs > 0).mean(),
                ticket=d.inv_total.mean(), n=len(d), inv=inv)


cat = pd.DataFrame({c: agg(d) for c, d in R.groupby('cat_nova') if c in CAT_FSA}).T
cat = cat.reindex([c for c in CAT_FSA if c in cat.index])
metr = [('retorno doméstico', 'ret', '{:.2f}×'), ('internacional por R$ mi', 'intl', '{:.2f}'),
        ('% com sinal intl', 'pct', '{:.0f}%'), ('espectadores por R$ mi', 'pub', '{:,.0f}'),
        ('% que chegou à sala', 'estreia', '{:.0f}%')]
Z = np.array([[cat.loc[c, k] / cat[k].max() for _, k, _ in metr] for c in cat.index])
TXT = [[f.format(cat.loc[c, k]).replace(',', '.') for _, k, f in metr] for c in cat.index]
f = go.Figure(go.Heatmap(
    z=Z[::-1], text=[t for t in TXT[::-1]], texttemplate='%{text}',
    x=[m[0] for m in metr], y=[curto(c, 24) for c in cat.index[::-1]],
    colorscale=[[0, '#141a2a'], [0.35, '#1d3b5e'], [0.7, '#2f86c4'], [1, '#7dd3fc']],
    showscale=False, textfont=dict(size=10.5, color='#e8ecf4'), xgap=2, ygap=2,
    hovertemplate='<b>%{y}</b><br>%{x}: %{text}<extra></extra>'))
base(f, h=400, legend=False, hover='closest')
f.update_layout(margin=dict(l=160, r=16, t=16, b=64))
f.update_xaxes(tickfont_size=9.5, tickangle=-16, showgrid=False)
f.update_yaxes(tickfont_size=9.5, showgrid=False)
reg('p_matriz_criterio', 'c2',
    'A matriz do sistema — cada categoria de chamada em cinco réguas',
    'O mesmo dado das barras, agora tudo de uma vez: cada linha é uma categoria de chamada, '
    'cada coluna uma régua, e a cor é a posição relativa dentro da coluna (o valor absoluto '
    'está escrito na célula). Nenhuma linha fica clara na matriz inteira — não existe categoria '
    'boa em tudo, e é isso que impede tratar a escolha do critério como detalhe administrativo.',
    'RIDAB · base_obras (universo de retorno)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c2 · quantas obras carregam a renda de cada bloco
# ══════════════════════════════════════════════════════════════════════════════
f = go.Figure()
CORB = {'Bilheteria · Distribuidora': S.CYAN, 'Bilheteria · Produtora': '#2f86c4',
        'Festivais · Pontuação': S.PURPLE, 'Automático Bilheteria': S.GOLD,
        'Arranjos Regionais': CINZA}
for cnome, cor in CORB.items():
    d = R[R.cat_nova == cnome].sort_values('receita_ref', ascending=False)
    if not len(d):
        continue
    y = 100 * d.receita_ref.cumsum() / d.receita_ref.sum()
    x = 100 * (np.arange(len(d)) + 1) / len(d)
    f.add_scatter(x=x, y=y, mode='lines', name=curto(cnome, 26),
                  line=dict(color=cor, width=2.4),
                  hovertemplate='%{x:.0f}%% das obras → %{y:.0f}%% da receita<extra></extra>')
f.add_scatter(x=[0, 100], y=[0, 100], mode='lines', name='receita igual entre as obras',
              line=dict(color='#4b5468', width=1.3, dash='dot'), hoverinfo='skip')
f.add_hline(y=80, line_dash='dot', line_color='#6b7690')
base(f, h=400, xtitle='obras da categoria, da que mais fez renda para a que menos fez (%)',
     ytitle='% da receita da categoria', hover='closest')
reg('p_pareto', 'c2',
    'Quantas obras carregam a renda de cada categoria',
    'Cada curva é uma categoria: quanto mais colada no canto superior esquerdo, mais a receita '
    'dela depende de poucos títulos. A linha pontilhada horizontal marca 80% da receita. É o '
    'contexto que qualquer comparação de retorno agregado precisa ter — num sistema em que meia '
    'dúzia de obras carrega o bloco, a média diz menos do que a forma da curva.',
    'RIDAB · base_obras (universo de retorno)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c3 · a série do instrumento — quem financiou o cinema em cada ano
# ══════════════════════════════════════════════════════════════════════════════
ORD_I = ['Renúncia pura', 'Misto FSA+Renúncia', 'FSA puro']
COR_I = {'Renúncia pura': S.GOLD, 'Misto FSA+Renúncia': S.ACCENT, 'FSA puro': S.CYAN}
pv = (R[R.instrumento.isin(ORD_I)]
      .pivot_table(index='ano', columns='instrumento', values='inv_total', aggfunc='sum')
      .reindex(columns=ORD_I).fillna(0))
pvn = (R[R.instrumento.isin(ORD_I)]
       .pivot_table(index='ano', columns='instrumento', values='cpb', aggfunc='size')
       .reindex(columns=ORD_I).fillna(0))
f = make_subplots(specs=[[{'secondary_y': True}]])
for c in ORD_I:
    f.add_bar(x=pv.index, y=pv[c] / 1e6, name=c, marker_color=COR_I[c], customdata=pvn[c],
              hovertemplate='R$ %{y:.1f} mi · %{customdata:.0f} obras<extra></extra>')
f.add_scatter(x=pv.index, y=100 * pv['FSA puro'] / pv.sum(axis=1),
              name='fatia do FSA puro (%)', mode='lines', line=dict(color=S.CORAL, width=2, dash='dot'),
              secondary_y=True, hovertemplate='%{y:.0f}%% do dinheiro do ano<extra></extra>')
f.update_layout(barmode='stack', bargap=0.26)
base(f, h=400, ytitle='investimento público, R$ mi (dez/2024)', y2title='% do ano')
f.update_yaxes(range=[0, 60], secondary_y=True)
f.update_xaxes(dtick=1)
reg('p_instrumento_ano', 'c3',
    'Quem financiou o cinema em cada ano — a série por instrumento',
    'O agregado do período esconde a mudança de composição. A barra mostra quanto dinheiro '
    'entrou por instrumento em cada safra; a linha pontilhada, a fatia que veio só do FSA. '
    'Comparar retorno entre instrumentos sem olhar esta série é comparar carteiras que foram '
    'formadas em conjunturas diferentes, com bilheterias de anos diferentes.',
    'RIDAB · base_obras (universo de retorno, 2014–2023)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c4 · a cauda: como o dinheiro se reparte entre os grupos
# ══════════════════════════════════════════════════════════════════════════════
inv = P[P.inv_total > 0].inv_total
f = go.Figure()
f.add_histogram(x=np.log10(inv), nbinsx=42, marker_color=S.ACCENT, opacity=0.85,
                hovertemplate='%{y} grupos<extra></extra>')
for v, cor, nome in [(inv.median(), S.GOLD, f'mediana R$ {brn(inv.median() / 1e6, 2)} mi'),
                     (5e6, S.CORAL, 'R$ 5 mi'),
                     (inv.quantile(0.9), '#6b7690', f'9º decil R$ {brn(inv.quantile(0.9) / 1e6, 1)} mi')]:
    f.add_vline(x=np.log10(v), line_dash='dot', line_color=cor, annotation_text=nome,
                annotation_font_size=9.5, annotation_font_color=cor, annotation_position='top')
base(f, h=400, legend=False, ytitle='grupos econômicos',
     xtitle='dinheiro público recebido pelo grupo na carteira (escala log)', hover='closest')
f.update_xaxes(tickvals=[4, 5, 6, 7, 8, 9],
               ticktext=['R$ 10 mil', 'R$ 100 mil', 'R$ 1 mi', 'R$ 10 mi', 'R$ 100 mi', 'R$ 1 bi'])
reg('p_cauda', 'c4',
    'Como o dinheiro se reparte entre os 697 grupos',
    f'A distribuição do que cada grupo recebeu em toda a carteira. O grupo mediano ficou com '
    f'R$ {brn(inv.median() / 1e6, 2)} milhões acumulados em anos — abaixo do orçamento de um único '
    'longa. A massa da distribuição está à esquerda do corte de R$ 5 milhões que o texto usa '
    'para separar quem teve escala de quem não teve, e a cauda longa da direita é onde estão '
    'as empresas que respondem pela maior parte da receita.',
    'RIDAB · base_produtoras (carteira 1996–2024)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c5 · a geografia do dinheiro
# ══════════════════════════════════════════════════════════════════════════════
uf = (R.groupby('uf').agg(obras=('cpb', 'size'), inv=('inv_total', 'sum'),
                          rec=('receita_ref', 'sum'),
                          intl=('roi_internacional_0_100', 'mean')).reset_index())
uf = uf[uf.uf.notna() & (uf.uf != '')].sort_values('inv', ascending=False).head(14).iloc[::-1]
f = make_subplots(rows=1, cols=2, horizontal_spacing=0.24,
                  subplot_titles=('dinheiro público recebido (R$ mi)',
                                  'retorno doméstico da UF (×)'))
f.add_bar(x=uf.inv / 1e6, y=uf.uf, orientation='h', row=1, col=1, marker_color=S.ACCENT,
          customdata=uf.obras,
          hovertemplate='<b>%{y}</b><br>R$ %{x:.0f} mi · %{customdata:.0f} obras<extra></extra>')
f.add_bar(x=uf.rec / uf.inv, y=uf.uf, orientation='h', row=1, col=2,
          marker_color=[S.CYAN if v >= 1 else CINZA for v in (uf.rec / uf.inv)],
          customdata=uf.intl,
          hovertemplate='<b>%{y}</b><br>%{x:.2f}× · índice intl médio %{customdata:.1f}<extra></extra>')
base(f, h=420, legend=False, hover='closest')
f.update_layout(margin=dict(l=44, r=16, t=34, b=40))
for an in f.layout.annotations:
    an.font.size = 10.5
    an.font.color = S.MUT
reg('p_uf', 'c5',
    'A geografia do fomento — para onde o dinheiro foi e o que voltou',
    'As 14 UFs que mais receberam dinheiro público no recorte, com o retorno doméstico de cada '
    'uma ao lado. A UF é a da proponente, não a do set de filmagem. As duas colunas juntas '
    'mostram que a concentração geográfica do dinheiro e a do resultado não são a mesma coisa — '
    'e que a regionalização se mede em duas pontas, não numa.',
    'RIDAB · base_obras (UF da produtora proponente)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c6 · a sobrevivência das empresas até a segunda obra
# ══════════════════════════════════════════════════════════════════════════════
GM = pd.read_csv(os.path.join(BASES, 'grupo_economico_map.csv'), sep=';', dtype=str)
RG = (R.assign(cnpj=R.cnpj_produtora.astype(str))
       .merge(GM.assign(cnpj=GM.cnpj_produtora)[['cnpj', 'grupo']], on='cnpj', how='left')
       .dropna(subset=['grupo']))
prim = RG.groupby('grupo').ano.min()
seg = RG.sort_values('ano').groupby('grupo').ano.apply(lambda s: s.iloc[1] if len(s) > 1 else np.nan)
dd = pd.DataFrame({'prim': prim, 'seg': seg}).join(P.set_index('grupo').ano_primeira)
dd = dd[(dd.prim >= 2014) & (dd.ano_primeira >= 2014)]
anos = np.arange(0, 10)
curva, expostos = [], []
for k in anos:
    exp = dd[dd.prim <= 2023 - k]
    expostos.append(len(exp))
    curva.append(100 * ((exp.seg - exp.prim) <= k).sum() / len(exp) if len(exp) else np.nan)
f = go.Figure()
f.add_scatter(x=anos, y=curva, mode='lines+markers', name='chegou à segunda obra',
              line=dict(color=S.GREEN, width=2.6), marker=dict(size=7), customdata=expostos,
              hovertemplate='em até %{x} anos: %{y:.1f}%% dos %{customdata} grupos expostos<extra></extra>')
base(f, h=400, legend=False, ytitle='% dos grupos que chegaram à segunda obra',
     xtitle='anos desde a estreia', hover='closest')
f.update_yaxes(range=[0, 60])
f.update_xaxes(dtick=1)
reg('p_sobrevivencia', 'c6',
    'Quanto tempo leva — e quantos chegam — até a segunda obra',
    'Cada ponto olha só para os grupos que já tiveram aquele tanto de anos de janela desde a '
    'estreia, então a queda no fim da série não é efeito de recorte. A curva sobe devagar e '
    'estaciona: passar da primeira para a segunda obra não é questão de esperar mais tempo, é '
    'uma barreira. Qualquer política de renovação que só abra vaga para o primeiro filme '
    'reencontra esta curva.',
    'RIDAB · base_obras × grupo econômico (2014–2023)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c7 · o que a proposta muda no funil de entrada
# ══════════════════════════════════════════════════════════════════════════════
_estreantes_ano = len(dd) / 10
_seg_ano = dd.seg.notna().sum() / 10
etapas7 = [('desenvolvimento<br>(proposta)', 100, S.CYAN),
           ('produção de<br>primeiros longas', 10, S.ACCENT),
           ('distribuição<br>selecionada', 2.5, S.PURPLE),
           ('hoje: estreantes<br>por ano', _estreantes_ano, CINZA),
           ('hoje: chegam à<br>segunda obra', _seg_ano, S.CORAL)]
f = go.Figure(go.Bar(
    x=[e[0] for e in etapas7], y=[e[1] for e in etapas7],
    marker_color=[e[2] for e in etapas7],
    text=[f'{brn(e[1], 0)}' for e in etapas7], textposition='outside', textfont_size=11,
    cliponaxis=False, hovertemplate='%{x}: %{y:.0f} por ano<extra></extra>'))
base(f, h=400, legend=False, ytitle='projetos ou empresas por ano', hover='closest')
f.update_layout(margin=dict(l=56, r=16, t=16, b=66), bargap=0.42)
f.update_xaxes(tickfont_size=9.5)
reg('p_funil', 'c7',
    'O funil que a proposta desenha, ao lado do que o sistema faz hoje',
    f'As três primeiras barras são a cadeia proposta no texto: 100 projetos em desenvolvimento, '
    f'10 primeiros longas, 2 a 3 lançamentos apoiados. As duas últimas são o sistema atual medido: '
    f'cerca de {brn(_estreantes_ano, 0)} grupos estreiam por ano e {brn(_seg_ano, 0)} chegam à '
    'segunda obra. A comparação é de ordem de grandeza — a proposta não aumenta a entrada, ela '
    'garante que o que entra seja acompanhado até virar segundo filme.',
    'Parâmetros do texto + RIDAB · base_obras × grupo econômico', f)


out = os.path.join(BASES, 'painelfigs.json')
with open(out, 'w', encoding='utf-8') as fh:
    json.dump(FIGS, fh, ensure_ascii=False, separators=(',', ':'))
print(f'\nOK → outputs/bases/painelfigs.json ({os.path.getsize(out) / 1024:.0f} KB) · '
      f'{len(FIGS)} figuras complementares do painel')
