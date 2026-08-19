# -*- coding: utf-8 -*-
"""
24_hover_trechos2.py — visualizações de TRECHO das Partes II, III e IV.

Continuação do `scripts/23_hover_trechos.py`, que fez a Parte I a partir dos oito
comentários do Cainan no DOCX (o benchmark). Aqui as passagens são escolhidas na
mesma lógica: passagem que faz uma afirmação empírica → um gráfico que abre a
informação inteira daquela afirmação (série histórica decomposta, ranking, mapa,
dispersão), sempre com dado real e a ressalva na própria legenda.

Diferença de infra: a âncora aqui é por **parágrafo** (`secao` + `par`, a mesma
numeração de blocos que o `scripts/21` usa ao renderizar), e não por casamento de
texto. Editar a frase não quebra o vínculo; mover o parágrafo de lugar, sim.

Saída: `outputs/bases/hoverfigs2.json`
Rodar:  .\.venv\Scripts\python.exe scripts\24_hover_trechos2.py   (antes do scripts/21)
"""
import os
import re
import sys
import json
import unicodedata

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
FIGS = {}

CINZA, CINZA2 = '#5a6478', '#39405280'


def reg(gid, secao, par, titulo, legenda, fonte, fig):
    FIGS[gid] = {'secao': secao, 'par': par, 'titulo': titulo, 'legenda': legenda,
                 'fonte': fonte, 'spec': json.loads(fig.to_json())}
    print(f'  ✓ {gid:<18} [{secao} p{par}]  {titulo[:62]}')


def base(fig, h=390, legend=True, ytitle=None, y2title=None, xtitle=None, hover='x unified'):
    fig.update_layout(
        paper_bgcolor='#12151e', plot_bgcolor='#12151e',
        font=dict(family='Inter,system-ui,sans-serif', color=S.TXT, size=11.5),
        margin=dict(l=58, r=58 if y2title else 16, t=10, b=42), height=h,
        showlegend=legend,
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=10.5), orientation='h',
                    y=1.14, x=0, yanchor='top'),
        hoverlabel=dict(font_size=11.5, font_family='Inter'), hovermode=hover)
    fig.update_xaxes(gridcolor=S.GRID, zerolinecolor=S.GRID, linecolor=S.GRID,
                     title=xtitle, title_font_size=11, tickfont_size=10.5)
    fig.update_yaxes(gridcolor=S.GRID, zerolinecolor=S.GRID, linecolor=S.GRID,
                     title=ytitle, title_font_size=11, tickfont_size=10.5)
    if y2title:
        fig.update_yaxes(title=y2title, secondary_y=True, showgrid=False)
    return fig


def subtit(fig, size=10.5):
    for an in fig.layout.annotations:
        an.font.size = size
        an.font.color = S.MUT
    return fig


def brn(x, d=1):
    """Número no padrão BR para as legendas (1.234,5)."""
    return f'{x:,.{d}f}'.replace(',', '§').replace('.', ',').replace('§', '.')


def curto(s, n=26):
    s = str(s)
    return s if len(s) <= n + 1 else s[:n] + '…'


# ══════════════════════════════════════════════════════════════════════════════
# bases
# ══════════════════════════════════════════════════════════════════════════════
B = pd.read_parquet(os.path.join(BASES, 'base_obras.parquet'))
R = B[B.universo_retorno == True].copy()                                    # noqa: E712
P = pd.read_parquet(os.path.join(BASES, 'base_produtoras.parquet'))
IND = json.load(open(os.path.join(BASES, 'indicadores.json'), encoding='utf-8'))
CUR = json.load(open(os.path.join(BASES, 'curtas_indicadores.json'), encoding='utf-8'))

CAT_FSA = ['Bilheteria · Distribuidora', 'Bilheteria · Produtora', 'Festivais · Pontuação',
           'Automático Bilheteria', 'Automático Festivais', 'Coprodução Intl',
           'Arranjos Regionais', 'Add-on FSA (Compl./Comerc.)']
COR_CAT = {'Bilheteria · Distribuidora': S.CYAN, 'Bilheteria · Produtora': '#2f86c4',
           'Festivais · Pontuação': S.PURPLE, 'Automático Bilheteria': S.GOLD,
           'Automático Festivais': '#d9a441', 'Coprodução Intl': S.GREEN,
           'Arranjos Regionais': CINZA, 'Add-on FSA (Compl./Comerc.)': S.CORAL}


def agg(d):
    inv = d.inv_total.sum()
    return dict(n=len(d), inv=inv, rec=d.receita_ref.sum(), ret=d.receita_ref.sum() / inv,
                intl=d.roi_internacional_0_100.sum() / (inv / 1e6),
                pct=100 * (d.roi_internacional_0_100 > 0).mean(),
                ticket=d.inv_total.mean(), pub=d.publico_domestico.sum() / inv * 1e6,
                estreia=100 * (d.bilheteria_obs > 0).mean())


# ══════════════════════════════════════════════════════════════════════════════
# c2 p3 · o retorno por categoria de chamada — as duas réguas lado a lado
# ══════════════════════════════════════════════════════════════════════════════
cat = pd.DataFrame({c: agg(d) for c, d in R.groupby('cat_nova') if c in CAT_FSA}).T
cat = cat.reindex([c for c in CAT_FSA if c in cat.index])
o = cat.iloc[::-1]
f = make_subplots(rows=1, cols=2, horizontal_spacing=0.30,
                  subplot_titles=('retorno doméstico (renda ÷ investimento)',
                                  'retorno internacional (índice por R$ milhão)'))
f.add_bar(x=o.ret, y=[curto(i, 24) for i in o.index], orientation='h', row=1, col=1,
          marker_color=[COR_CAT[i] for i in o.index],
          customdata=np.stack([o.n, o.inv / 1e6, o.ticket / 1e6], -1),
          hovertemplate='<b>%{y}</b><br>%{x:.2f}× · %{customdata[0]:.0f} obras · '
                        'R$ %{customdata[1]:.0f} mi (ticket R$ %{customdata[2]:.2f} mi)<extra></extra>')
f.add_bar(x=o.intl, y=[curto(i, 24) for i in o.index], orientation='h', row=1, col=2,
          marker_color=[COR_CAT[i] for i in o.index],
          customdata=np.stack([o.pct, o.n], -1),
          hovertemplate='<b>%{y}</b><br>%{x:.2f} por R$ mi · %{customdata[0]:.1f}%% das '
                        '%{customdata[1]:.0f} obras com algum sinal<extra></extra>')
base(f, h=400, legend=False, hover='closest')
f.update_layout(margin=dict(l=150, r=16, t=34, b=36))
f.update_yaxes(tickfont_size=9.5)
subtit(f)
reg('h_criterio', 'c2', 3,
    'O que cada critério de seleção devolveu — as oito categorias do FSA',
    'Cada barra é uma categoria de chamada, com as 855 obras do universo de retorno '
    'repartidas entre elas. À esquerda, quanto de renda doméstica saiu por real investido; '
    'à direita, o índice internacional acumulado por R$ milhão. Bilheteria e festivais não '
    'competem pela mesma régua: cada critério entrega o que ele seleciona.',
    'RIDAB · outputs/bases/base_obras.parquet (scripts/10 e 13)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c2 p5 · a distribuição do ticket nos dois blocos
# ══════════════════════════════════════════════════════════════════════════════
blocos = [('Bilheteria · Distribuidora', S.CYAN), ('Bilheteria · Produtora', '#2f86c4'),
          ('Festivais · Pontuação', S.PURPLE)]
f = go.Figure()
for cnome, cor in blocos:
    d = R[R.cat_nova == cnome]
    f.add_box(x=d.inv_total / 1e6, name=curto(cnome, 24), marker_color=cor, boxpoints='all',
              jitter=0.45, pointpos=0, marker=dict(size=4, opacity=0.55), line_width=1.4,
              text=d.titulo, hovertemplate='%{text}<br>R$ %{x:.2f} mi<extra></extra>')
f.add_vline(x=4, line_dash='dot', line_color='#6b7690',
            annotation_text='R$ 4 mi', annotation_font_size=10,
            annotation_font_color='#8f9ab3', annotation_position='top')
base(f, h=390, legend=False, xtitle='investimento público na obra, R$ milhões (dez/2024)',
     hover='closest')
f.update_layout(margin=dict(l=150, r=16, t=14, b=42))
f.update_yaxes(tickfont_size=9.5)
reg('h_ticket', 'c2', 5,
    'O porte das obras de cada critério — obra a obra',
    'Cada ponto é uma obra, na posição do dinheiro público que recebeu; a caixa marca a '
    'mediana e os quartis. O bloco de festivais quase não passa dos R$ 4 milhões, o de '
    'bilheteria com distribuidora se espalha muito acima. É por isso que a comparação de '
    'retorno entre eles precisa ser refeita dentro da mesma faixa de porte.',
    'RIDAB · base_obras (universo de retorno, 2014–2023)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c2 p6 · quem de fato vendeu ingresso fora — ranking Lumière por critério
# ══════════════════════════════════════════════════════════════════════════════
lu = R[R.adm_eu_lumiere > 0].nlargest(18, 'adm_eu_lumiere').iloc[::-1]
f = go.Figure(go.Bar(
    x=lu.adm_eu_lumiere / 1e3, y=[curto(t, 30) for t in lu.titulo], orientation='h',
    marker_color=[COR_CAT.get(c, CINZA) for c in lu.cat_nova],
    customdata=np.stack([lu.cat_nova, lu.ano, lu.inv_total / 1e6], -1),
    hovertemplate='<b>%{y}</b> (%{customdata[1]})<br>%{x:.1f} mil espectadores na Europa'
                  '<br>%{customdata[0]} · R$ %{customdata[2]:.1f} mi<extra></extra>'))
base(f, h=430, legend=False, xtitle='espectadores em salas na Europa (mil)', hover='closest')
f.update_layout(margin=dict(l=180, r=16, t=10, b=42))
f.update_yaxes(tickfont_size=9.5)
reg('h_intl_publico', 'c2', 6,
    'As audiências internacionais do recorte, e de qual edital cada uma saiu',
    'As 18 obras de 2014–2023 com mais espectadores em salas europeias, coloridas pela '
    'categoria da chamada que as financiou. O critério de festivais leva mais filmes para '
    'fora; o público lá fora, quando aparece, sai em poucos títulos das linhas de '
    'bilheteria com distribuidora. Público de sala não é o mesmo que circulação.',
    'RIDAB · base_obras × Lumière (Observatório Europeu do Audiovisual)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c2 p9 · para onde o dinheiro foi, ano a ano
# ══════════════════════════════════════════════════════════════════════════════
fsa = R[R.cat_nova.isin(CAT_FSA)]
piv = (fsa.pivot_table(index='ano', columns='cat_nova', values='inv_total', aggfunc='sum')
          .reindex(columns=[c for c in CAT_FSA]).fillna(0) / 1e6)
f = go.Figure()
for c in piv.columns:
    f.add_bar(x=piv.index, y=piv[c], name=curto(c, 26), marker_color=COR_CAT[c],
              hovertemplate='R$ %{y:.1f} mi<extra></extra>')
f.update_layout(barmode='stack', bargap=0.26)
base(f, h=400, ytitle='investimento público, R$ mi (dez/2024)')
f.update_xaxes(dtick=1)
reg('h_dinheiro', 'c2', 9,
    'Para onde o dinheiro foi, ano a ano, por critério de seleção',
    'O investimento público das obras do universo de retorno, empilhado por categoria de '
    'chamada e distribuído pelo ano da obra. O bloco de bilheteria (dois tons de azul) '
    'domina a série inteira; o de festivais (roxo) nunca chega perto. A escolha de quanto '
    'cada critério recebe é anterior a qualquer resultado que se meça depois.',
    'RIDAB · base_obras (universo de retorno)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c2 p13 · a anatomia do sistema — dispersão categoria a categoria
# ══════════════════════════════════════════════════════════════════════════════
f = go.Figure()
for c in cat.index:
    r = cat.loc[c]
    f.add_scatter(x=[r.ret], y=[r.intl], mode='markers+text', name=curto(c, 26),
                  text=[curto(c, 22)], textposition='top center',
                  textfont=dict(size=9.5, color='#9aa3b6'),
                  marker=dict(size=max(12, min(52, (r.inv / 1e6) ** 0.5 * 2.1)),
                              color=COR_CAT[c], opacity=0.82,
                              line=dict(color='#0b0d14', width=1)),
                  customdata=[[r.n, r.inv / 1e6, r.pct]],
                  hovertemplate='<b>' + c + '</b><br>retorno doméstico %{x:.2f}× · '
                                'internacional %{y:.2f}/R$ mi<br>%{customdata[0]:.0f} obras · '
                                'R$ %{customdata[1]:.0f} mi · %{customdata[2]:.1f}%% com sinal'
                                '<extra></extra>')
base(f, h=400, legend=False, xtitle='retorno doméstico (×)',
     ytitle='retorno internacional por R$ milhão', hover='closest')
f.update_layout(margin=dict(l=58, r=24, t=18, b=44))
reg('h_anatomia', 'c2', 13,
    'A anatomia do sistema — cada categoria de chamada nas duas dimensões',
    'Cada bolha é uma categoria de chamada; o tamanho é o dinheiro que ela recebeu. '
    'O canto superior direito é a única posição que combina as duas coisas, e só a '
    'bilheteria com roteiro e distribuidora chega perto dele com volume. O eixo vertical '
    'isolado é o território das linhas de festival e de coprodução, com bolhas pequenas.',
    'RIDAB · base_obras agregada por categoria (mesma conta de base_chamadas)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c2 p18 · leitura de roteiro contra decisão automática
# ══════════════════════════════════════════════════════════════════════════════
rot = R[R.cat_nova.isin(['Bilheteria · Distribuidora', 'Bilheteria · Produtora',
                         'Festivais · Pontuação'])]
aut = R[R.cat_nova.isin(['Automático Bilheteria', 'Automático Festivais'])]
ar, aa = agg(rot), agg(aut)
# fragilidade: quanto os 3 maiores respondem no bloco automático
top3 = aut.nlargest(3, 'receita_ref').receita_ref.sum() / aut.receita_ref.sum() * 100
ret_sem3 = ((aut.receita_ref.sum() - aut.nlargest(3, 'receita_ref').receita_ref.sum())
            / (aut.inv_total.sum() - aut.nlargest(3, 'receita_ref').inv_total.sum()))

reguas = [('retorno doméstico (×)', ar['ret'], aa['ret'], '{:.2f}'),
          ('internacional por R$ mi', ar['intl'], aa['intl'], '{:.2f}'),
          ('público por R$ mi (mil)', ar['pub'] / 1e3, aa['pub'] / 1e3, '{:.1f}'),
          ('% que chegou à sala', ar['estreia'], aa['estreia'], '{:.1f}'),
          ('% com sinal internacional', ar['pct'], aa['pct'], '{:.1f}')]
f = make_subplots(rows=1, cols=5, horizontal_spacing=0.045,
                  subplot_titles=[r[0] for r in reguas])
for i, (nome, v1, v2, fmt) in enumerate(reguas, start=1):
    f.add_bar(x=['lê roteiro', 'automático'], y=[v1, v2], row=1, col=i,
              marker_color=[S.CYAN, S.GOLD], showlegend=False,
              text=[fmt.format(v1), fmt.format(v2)], textposition='outside',
              textfont=dict(size=9.5), cliponaxis=False,
              hovertemplate='%{x}: %{y:.2f}<extra></extra>')
base(f, h=380, legend=False, hover='closest')
f.update_layout(margin=dict(l=34, r=12, t=40, b=56))
f.update_xaxes(tickfont_size=9, tickangle=-30)
f.update_yaxes(tickfont_size=8.5, showgrid=True)
subtit(f, 9.5)
reg('h_automatismo', 'c2', 18,
    'Ler o projeto contra confiar no histórico — as cinco réguas',
    f'{ar["n"]:.0f} obras e R$ {ar["inv"] / 1e6:.0f} milhões nas chamadas que leem roteiro, '
    f'{aa["n"]:.0f} obras e R$ {aa["inv"] / 1e6:.0f} milhões nas automáticas, com ticket médio '
    f'praticamente igual (R$ {brn(ar["ticket"] / 1e6, 2)} mi contra R$ {brn(aa["ticket"] / 1e6, 2)} mi) — '
    f'não é o porte do filme que explica a diferença. Ressalva que vale para tudo aqui: o bloco '
    f'automático é frágil, três obras respondem por {top3:.0f}% da sua receita e sem elas o '
    f'retorno doméstico cai para {brn(ret_sem3, 2)}.',
    'RIDAB · base_obras (universo de retorno)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c2 p23 · complementação e comercialização como marcação sobre a obra
# ══════════════════════════════════════════════════════════════════════════════
pares = [('complementação', R.tem_complementacao == True), ('comercialização', R.tem_comercializacao == True)]  # noqa: E712
f = make_subplots(rows=1, cols=2, horizontal_spacing=0.16,
                  subplot_titles=('retorno doméstico (×)', '% das obras com sinal internacional'))
lab, v_ret, v_pct, cor, cst = [], [], [], [], []
for nome, mask in pares:
    a1, a0 = agg(R[mask]), agg(R[~mask])
    lab += [f'com {nome}', f'sem {nome}']
    v_ret += [a1['ret'], a0['ret']]
    v_pct += [a1['pct'], a0['pct']]
    cor += [S.CORAL if nome == 'comercialização' else S.ACCENT, CINZA]
    cst += [[a1['n'], a1['ticket'] / 1e6], [a0['n'], a0['ticket'] / 1e6]]
f.add_bar(x=lab, y=v_ret, marker_color=cor, row=1, col=1, customdata=cst,
          text=[f'{v:.2f}' for v in v_ret], textposition='outside', textfont_size=10,
          cliponaxis=False,
          hovertemplate='<b>%{x}</b><br>%{y:.2f}× · %{customdata[0]:.0f} obras · '
                        'ticket R$ %{customdata[1]:.2f} mi<extra></extra>')
f.add_bar(x=lab, y=v_pct, marker_color=cor, row=1, col=2, customdata=cst,
          text=[f'{v:.1f}%' for v in v_pct], textposition='outside', textfont_size=10,
          cliponaxis=False,
          hovertemplate='<b>%{x}</b><br>%{y:.1f}%% · %{customdata[0]:.0f} obras<extra></extra>')
base(f, h=380, legend=False, hover='closest')
f.update_layout(margin=dict(l=48, r=16, t=36, b=62))
f.update_xaxes(tickfont_size=9.5, tickangle=-18)
subtit(f)
reg('h_addon', 'c2', 24,
    'Complementação e comercialização não são categoria, são marcação sobre a obra',
    'Tratadas como marcação, a extensão é bem maior do que a contagem de categoria sugere. '
    'A complementação quase não distingue. A comercialização distingue no sentido inverso do '
    'esperado: menos retorno doméstico e muito mais sinal internacional — porque no recorte '
    'ela foi majoritariamente para cinema de festival e para Arranjos Regionais, com ticket '
    'menor. É leitura sobre para onde a distribuição pública foi, não sobre o que ela produz.',
    'RIDAB · base_obras (marcações tem_complementacao / tem_comercializacao)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c3 p1 · os três instrumentos de financiamento
# ══════════════════════════════════════════════════════════════════════════════
ORD_I = ['Renúncia pura', 'Misto FSA+Renúncia', 'FSA puro']
COR_I = {'Renúncia pura': S.GOLD, 'Misto FSA+Renúncia': S.ACCENT, 'FSA puro': S.CYAN}
ins = pd.DataFrame({i: agg(d) for i, d in R.groupby('instrumento') if i in ORD_I}).T.reindex(ORD_I)
f = make_subplots(specs=[[{'secondary_y': True}]])
f.add_bar(x=ins.index, y=ins.inv / 1e6, name='investimento público', marker_color=CINZA,
          hovertemplate='R$ %{y:.0f} mi<extra></extra>')
f.add_bar(x=ins.index, y=ins.rec / 1e6, name='receita doméstica de referência',
          marker_color=[COR_I[i] for i in ins.index], showlegend=True,
          hovertemplate='R$ %{y:.0f} mi<extra></extra>')
f.add_scatter(x=ins.index, y=ins.ret, name='retorno doméstico (×)', mode='markers+text',
              marker=dict(size=13, color=S.CORAL, symbol='diamond'),
              text=[f'{v:.2f}×' for v in ins.ret], textposition='top center',
              textfont=dict(size=11.5, color=S.CORAL), secondary_y=True,
              hovertemplate='%{y:.2f}×<extra></extra>')
f.update_layout(barmode='group', bargap=0.34)
base(f, h=390, ytitle='R$ milhões (dez/2024)', y2title='retorno (×)')
f.update_yaxes(range=[0, float(ins.ret.max()) * 1.45], secondary_y=True)
reg('h_instrumento', 'c3', 1,
    'O que cada instrumento de financiamento pôs e o que voltou em renda',
    f'A renúncia pura é o único grupo que devolve mais renda doméstica do que recebeu: '
    f'R$ {ins.loc["Renúncia pura", "rec"] / 1e6:.0f} milhões de receita para '
    f'R$ {ins.loc["Renúncia pura", "inv"] / 1e6:.0f} milhões de dinheiro público, em '
    f'{ins.loc["Renúncia pura", "n"]:.0f} obras. O FSA puro, com o menor ticket dos três '
    f'(R$ {brn(ins.loc["FSA puro", "ticket"] / 1e6, 2)} mi), devolve '
    f'{brn(ins.loc["FSA puro", "ret"], 2)}. Comparar os três é comparar quem decide o '
    'investimento, não só quem paga por ele.',
    'RIDAB · base_obras (universo de retorno, 2014–2023)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c3 p3 · as franquias — onde o FSA entra e de onde ele sai
# ══════════════════════════════════════════════════════════════════════════════
M = pd.read_excel(os.path.join(BASE, 'data', 'legado', 'tabela_consolidada_obras.xlsx'))
M['fsa'] = pd.to_numeric(M['Valor FSA Deflac. (R$2024)'], errors='coerce').fillna(0)
M['ren'] = pd.to_numeric(M['Renúncia Total Deflac. (R$2024)'], errors='coerce').fillna(0)
M['bil'] = pd.to_numeric(M['Bilheteria Deflac. (R$)'], errors='coerce').fillna(0)
M['anoN'] = pd.to_numeric(M.Ano, errors='coerce')
M = M[~M.Projeto.astype(str).str.upper().str.contains('TEMPORADA', na=False)]


def raiz(t):
    t = unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode().upper().strip()
    t = re.sub(r'\s*[-–:]\s*.*$', '', t)
    t = re.sub(r'\b(2|3|4|5|II|III|IV|V)\b\s*$', '', t).strip()
    return re.sub(r'\s+', ' ', t)


M['fr'] = M.Projeto.map(raiz)
fr = (M[M.bil > 0].groupby('fr')
       .agg(n=('Projeto', 'size'), bil=('bil', 'sum'), fsa=('fsa', 'sum'), ren=('ren', 'sum'))
       .query('n >= 2').nlargest(9, 'bil').index)
det = M[M.fr.isin(fr)].sort_values(['fr', 'anoN'])
f = make_subplots(specs=[[{'secondary_y': True}]])
ordem_fr = list(M[M.fr.isin(fr)].groupby('fr').bil.sum().sort_values().index)
for pos, com_fsa in [(0, True), (1, False)]:
    d = det[(det.fsa > 0) == com_fsa]
    f.add_bar(y=[curto(x, 22) for x in d.fr], x=d.bil / 1e6, orientation='h',
              name='filme com dinheiro do FSA' if com_fsa else 'filme sem FSA (renúncia)',
              marker_color=S.CYAN if com_fsa else S.GOLD,
              customdata=np.stack([d.Projeto, d.anoN, d.fsa / 1e6, d.ren / 1e6], -1),
              hovertemplate='<b>%{customdata[0]}</b> (%{customdata[1]:.0f})<br>'
                            'bilheteria R$ %{x:.1f} mi<br>FSA R$ %{customdata[2]:.2f} mi · '
                            'renúncia R$ %{customdata[3]:.2f} mi<extra></extra>')
f.update_layout(barmode='stack', bargap=0.3)
base(f, h=430, xtitle='bilheteria da franquia, R$ mi (dez/2024)', hover='closest')
f.update_layout(margin=dict(l=160, r=16, t=34, b=44))
f.update_yaxes(categoryorder='array', categoryarray=[curto(x, 22) for x in ordem_fr],
               tickfont_size=9.5)
reg('h_sequencias', 'c3', 3,
    'As franquias do período — o filme que o fundo bancou e os que vieram depois sem ele',
    'As nove franquias de maior bilheteria da carteira, com cada filme empilhado na barra da '
    'sua franquia: azul quando teve dinheiro do FSA, dourado quando foi só renúncia. O padrão '
    'que o texto descreve aparece na barra: o fundo banca o primeiro, a descoberta se confirma, '
    'e as continuações — que são as que faturam — saem sem ele. Franquia é reunida por raiz do '
    'título, sem séries de TV.',
    'Carteira consolidada 1995–2024 (data/legado/tabela_consolidada_obras.xlsx) · RIDAB', f)


# ══════════════════════════════════════════════════════════════════════════════
# c3 p9 · quem devolve em sala não é quem exporta
# ══════════════════════════════════════════════════════════════════════════════
f = make_subplots(specs=[[{'secondary_y': True}]])
f.add_bar(x=ins.index, y=ins.pct, name='% das obras com algum sinal internacional',
          marker_color=[COR_I[i] for i in ins.index],
          text=[f'{v:.1f}%' for v in ins.pct], textposition='outside', textfont_size=10.5,
          cliponaxis=False, hovertemplate='%{y:.1f}%%<extra></extra>')
f.add_scatter(x=ins.index, y=ins.ret, name='retorno doméstico (×)', mode='lines+markers',
              line=dict(color=S.CORAL, width=2.4, dash='dot'), marker=dict(size=9),
              secondary_y=True, hovertemplate='%{y:.2f}×<extra></extra>')
base(f, h=380, ytitle='% com sinal internacional', y2title='retorno doméstico (×)')
f.update_yaxes(range=[0, 40])
f.update_yaxes(range=[0, float(ins.ret.max()) * 1.25], secondary_y=True)
f.update_layout(bargap=0.45)
reg('h_intl_instrumento', 'c3', 9,
    'O grupo que devolve mais em sala é o que menos circula fora',
    'As barras são a fatia das obras de cada instrumento que tem algum sinal internacional; '
    'a linha pontilhada é o retorno doméstico do mesmo grupo. As duas curvas andam em '
    'sentidos opostos: a renúncia pura lidera a renda de sala e fica por último na '
    'circulação; o FSA puro faz o contrário. É o mesmo dinheiro público comprando coisas '
    'diferentes, com quem decide o investimento mudando junto.',
    'RIDAB · base_obras (universo de retorno)', f)




# ══════════════════════════════════════════════════════════════════════════════
# PARTE III · as empresas — a dispersão que serve de mapa para os casos citados
# ══════════════════════════════════════════════════════════════════════════════
COR_PERFIL = {'Retorno Doméstico': S.CYAN, 'Retorno Internacional': S.PURPLE,
              'Duplo Retorno': S.GREEN, 'Fomento Baixo Retorno': S.CORAL,
              'Pequeno Porte com algum retorno': '#6b7690', 'Pequeno Porte sem retorno': '#464e63'}
ORD_PERFIL = ['Duplo Retorno', 'Retorno Doméstico', 'Retorno Internacional',
              'Fomento Baixo Retorno', 'Pequeno Porte com algum retorno', 'Pequeno Porte sem retorno']


def nome_curto(rz):
    s = str(rz).title()
    s = re.sub(r'\s+(Ltda|S/?A|Eireli|Me|Epp)\b.*$', '', s, flags=re.I)
    s = re.sub(r'\s*[-–]\s*(Me|Epp)\b.*$', '', s, flags=re.I)
    return curto(s.strip(' .-'), 24)


P = P.copy()
P['nome'] = P.razao_social.map(nome_curto)
P['retx'] = P.retorno_dom_carteira.fillna(0).clip(lower=0.01)
P['size'] = np.clip((P.inv_total / 1e6) ** 0.5 * 1.9, 5, 40)


def disp(destaques=(), rotular=(), h=400):
    """Dispersão retorno doméstico × internacional dos 697 grupos da carteira."""
    fig = go.Figure()
    if destaques:
        fundo = P[~P.perfil.isin(destaques)]
        fig.add_scatter(
            x=fundo.retx, y=fundo.melhor_intl, mode='markers', name='demais grupos',
            marker=dict(size=fundo['size'] * 0.7, color='#39405a', opacity=0.5, line=dict(width=0)),
            customdata=np.stack([fundo.nome, fundo.n_obras, fundo.inv_total / 1e6, fundo.perfil], -1),
            hovertemplate='<b>%{customdata[0]}</b><br>retorno doméstico %{x:.2f}× · '
                          'internacional %{y:.1f}<br>%{customdata[1]:.0f} obras · '
                          'R$ %{customdata[2]:.1f} mi · %{customdata[3]}<extra></extra>')
    alvos = [p for p in ORD_PERFIL if p in destaques] if destaques else ORD_PERFIL
    for pf in alvos:
        d = P[P.perfil == pf]
        fig.add_scatter(
            x=d.retx, y=d.melhor_intl, mode='markers', name=curto(pf, 26),
            marker=dict(size=d['size'], color=COR_PERFIL[pf], opacity=0.85,
                        line=dict(color='#0b0d14', width=0.9)),
            customdata=np.stack([d.nome, d.n_obras, d.inv_total / 1e6, d.receita_ref / 1e6], -1),
            hovertemplate='<b>%{customdata[0]}</b><br>retorno doméstico %{x:.2f}× · '
                          'internacional %{y:.1f}<br>%{customdata[1]:.0f} obras · '
                          'R$ %{customdata[2]:.1f} mi investidos · R$ %{customdata[3]:.1f} mi '
                          'de receita<extra></extra>')
    for chave, dx, dy in rotular:
        d = P[P.razao_social.fillna('').str.upper().str.contains(chave, regex=False)]
        if not len(d):
            print(f'    ! rótulo não encontrado: {chave}')
            continue
        r = d.iloc[0]
        fig.add_annotation(x=np.log10(r.retx), y=r.melhor_intl, text=nome_curto(r.razao_social),
                           showarrow=True, arrowhead=0, arrowsize=1, arrowwidth=1,
                           arrowcolor='#6b7690', ax=dx, ay=dy,
                           font=dict(size=9.5, color='#cbd5e1'),
                           bgcolor='rgba(18,21,30,.82)', borderpad=2)
    base(fig, h=h, xtitle='retorno doméstico da carteira (×, escala log)',
         ytitle='melhor índice internacional (0–100)', hover='closest')
    fig.update_xaxes(type='log', tickvals=[0.01, 0.1, 0.5, 1, 2, 5, 10],
                     ticktext=['0,01', '0,1', '0,5', '1', '2', '5', '10'])
    fig.add_vline(x=1, line_dash='dot', line_color='#4b5468')
    fig.update_layout(margin=dict(l=60, r=20, t=46, b=46))
    return fig


f = disp()
reg('h_perfis', 'c4', 2,
    'Os 697 grupos econômicos da carteira, nas duas réguas',
    'Cada bolha é um grupo econômico financiado entre 1996 e 2024; o tamanho é o dinheiro '
    'público que ele recebeu. O eixo horizontal é quanto a carteira devolveu de renda '
    'doméstica por real (a pontilhada marca 1,00×), o vertical é o melhor resultado '
    'internacional de uma obra dele. Os perfis do texto são os cantos deste gráfico — e o '
    'canto de cima à direita, que combina as duas coisas, é o mais vazio.',
    'RIDAB · outputs/bases/base_produtoras.parquet (scripts/12)', f)

f = disp(destaques=('Retorno Doméstico',),
         rotular=[('MORENA', 40, -30), ('TOTAL ENTERTAINMENT', 46, 28), ('CAMISA LISTRADA', -48, -28),
                  ('MIGDAL', 30, 30), ('DILER', -34, -32)])
_rd = P[P.perfil == 'Retorno Doméstico']
reg('h_dom_casos', 'c4', 3,
    'O perfil de retorno doméstico — e os casos que o texto cita',
    f'As {len(_rd)} empresas do perfil doméstico em destaque, o resto da carteira em cinza. '
    'Todas encostadas no eixo horizontal: entregam renda de sala e índice internacional zero '
    'ou quase. Morena, Total e Camisa Listrada estão à direita da linha de 1,00× — devolveram '
    f'mais renda do que receberam. Somadas, as {len(_rd)} receberam R$ '
    f'{brn(_rd.inv_total.sum() / 1e9, 2)} bilhões e geraram R$ {brn(_rd.receita_ref.sum() / 1e9, 2)} bilhões.',
    'RIDAB · base_produtoras (carteira 1996–2024)', f)

f = disp(destaques=('Retorno Internacional',),
         rotular=[('AVANTE', 48, 26), ('CINCO DA NORTE', -52, -26), ('CINEMA INFLAMAVEL', 48, -28),
                  ('ANAVILHANA', -48, 28), ('CONSPIRAÇÃO', -40, -28)])
_ri = P[P.perfil == 'Retorno Internacional']
_consp = P[P.razao_social.fillna('').str.contains('CONSPIRAÇÃO', na=False)].inv_total.sum()
reg('h_intl_casos', 'c4', 8,
    'O perfil de retorno internacional — a escala é outra',
    f'As {len(_ri)} empresas do perfil internacional em destaque. Ocupam o alto do gráfico com '
    f'as menores bolhas da carteira: R$ {_ri.inv_total.sum() / 1e6:.0f} milhões somadas, contra '
    f'R$ {_consp / 1e6:.0f} milhões da Conspiração sozinha, marcada aqui só para dar a escala. '
    'Avante, Cinco da Norte e Cinema Inflamável têm uma ou duas obras na base — é resultado '
    'alto sobre carteira curta, não trajetória consolidada.',
    'RIDAB · base_produtoras (carteira 1996–2024)', f)

f = disp(destaques=('Duplo Retorno',),
         rotular=[('CINEMASCOPIO', -50, -26), ('VITRINE', -46, 26), ('BIÔNICA', 46, -26),
                  ('FILMES DE PLASTICO', -52, 28), ('O2 CINEMA', 40, 24)])
_dr = P[P.perfil == 'Duplo Retorno']
reg('h_duplo_casos', 'c4', 13,
    'O duplo retorno — 30 grupos no único quadrante que combina as duas coisas',
    f'Os {len(_dr)} grupos de duplo retorno, R$ {brn(_dr.inv_total.sum() / 1e9, 2)} bilhão investido '
    f'para R$ {brn(_dr.receita_ref.sum() / 1e9, 2)} bilhões de receita. Atenção ao que o gráfico '
    'mostra: a posição do GRUPO, não a da obra. Na maior parte deles o duplo vem de obras '
    'separadas, uma que vende e outra que viaja. Cinemascópio e Vitrine chegam ali com a mesma '
    'obra, Bacurau; a Biônica chega com dois negócios dentro da mesma empresa.',
    'RIDAB · base_produtoras (carteira 1996–2024)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c4 p16 · de onde veio o dinheiro de cada perfil
# ══════════════════════════════════════════════════════════════════════════════
op = P.groupby('perfil')[['inv_fsa', 'inv_renuncia']].sum().reindex(ORD_PERFIL)
op['tot'] = op.inv_fsa + op.inv_renuncia
op = op.iloc[::-1]
f = go.Figure()
f.add_bar(y=[curto(i, 26) for i in op.index], x=100 * op.inv_fsa / op.tot, orientation='h',
          name='FSA', marker_color=S.CYAN, customdata=op.inv_fsa / 1e6,
          hovertemplate='FSA: %{x:.1f}%% (R$ %{customdata:.0f} mi)<extra></extra>')
f.add_bar(y=[curto(i, 26) for i in op.index], x=100 * op.inv_renuncia / op.tot, orientation='h',
          name='renúncia fiscal', marker_color=S.GOLD, customdata=op.inv_renuncia / 1e6,
          hovertemplate='renúncia: %{x:.1f}%% (R$ %{customdata:.0f} mi)<extra></extra>')
f.update_layout(barmode='stack', bargap=0.36)
base(f, h=380, xtitle='composição do dinheiro público recebido (%)', hover='y unified')
f.update_layout(margin=dict(l=180, r=16, t=34, b=44))
f.update_yaxes(tickfont_size=9.5)
reg('h_origem', 'c4', 16,
    'De onde veio o dinheiro de cada perfil de empresa',
    'A diferença entre uma empresa que o fundo construiu e uma que ele apenas acompanhou está '
    'na composição do que ela recebeu. O perfil de retorno doméstico é majoritariamente '
    'renúncia — decisão de investimento tomada pela empresa que abate imposto. O perfil '
    'internacional e o pequeno porte são majoritariamente FSA, que é onde o Estado escolheu.',
    'RIDAB · base_produtoras (inv_fsa e inv_renuncia por grupo)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c4 p17 · quem já existia antes do FSA contra quem nasceu dentro dele
# ══════════════════════════════════════════════════════════════════════════════
co = (P.assign(coorte=np.where(P.pre_2006, 'já produzia antes de 2006', 'estreou de 2006 em diante'))
       .pivot_table(index='coorte', columns='perfil', values='grupo', aggfunc='size')
       .reindex(columns=ORD_PERFIL).fillna(0))
copc = 100 * co.div(co.sum(axis=1), axis=0)
f = go.Figure()
for pf in ORD_PERFIL:
    f.add_bar(y=copc.index, x=copc[pf], orientation='h', name=curto(pf, 24),
              marker_color=COR_PERFIL[pf], customdata=co[pf],
              hovertemplate=pf + ': %{x:.1f}%% (%{customdata:.0f} grupos)<extra></extra>')
f.update_layout(barmode='stack', bargap=0.5)
base(f, h=380, xtitle='distribuição dos grupos de cada coorte (%)', hover='y unified')
f.update_layout(margin=dict(l=170, r=16, t=58, b=44))
f.update_yaxes(tickfont_size=10)
_a = 100 * co.loc['já produzia antes de 2006', 'Duplo Retorno'] / co.loc['já produzia antes de 2006'].sum()
_b = 100 * co.loc['estreou de 2006 em diante', 'Duplo Retorno'] / co.loc['estreou de 2006 em diante'].sum()
reg('h_coorte', 'c4', 17,
    'Quem já existia antes do FSA chega ao duplo retorno cinco vezes mais',
    f'{brn(_a)}% dos grupos que já produziam antes de 2006 estão no duplo retorno, contra '
    f'{brn(_b)}% dos que estrearam de 2006 em diante — {brn(_a / _b)} vezes. A leitura não é que a '
    'empresa nova produz pior: é que a trajetória até o duplo retorno leva mais tempo do que o '
    'fundo deu, e o fundo financiou a entrada sem financiar a permanência.',
    'RIDAB · base_produtoras (perfil × coorte pré-2006)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c4 p22 · a concentração numa linha só
# ══════════════════════════════════════════════════════════════════════════════
lz = P.sort_values('inv_total', ascending=False).reset_index(drop=True)
lz['g'] = 100 * (lz.index + 1) / len(lz)
lz['d'] = 100 * lz.inv_total.cumsum() / lz.inv_total.sum()
lz['r'] = 100 * lz.receita_ref.cumsum() / lz.receita_ref.sum()
alto = P[P.perfil.isin(['Duplo Retorno', 'Retorno Doméstico'])]
_g91 = 100 * len(alto) / len(P)
_d91 = 100 * alto.inv_total.sum() / P.inv_total.sum()
_r91 = 100 * alto.receita_ref.sum() / P.receita_ref.sum()
f = go.Figure()
f.add_scatter(x=lz.g, y=lz.d, name='% do dinheiro público acumulado', mode='lines',
              line=dict(color=S.CYAN, width=2.6), hovertemplate='%{y:.1f}%% do dinheiro<extra></extra>')
f.add_scatter(x=lz.g, y=lz.r, name='% da receita acumulada', mode='lines',
              line=dict(color=S.GOLD, width=2.6), hovertemplate='%{y:.1f}%% da receita<extra></extra>')
f.add_scatter(x=[0, 100], y=[0, 100], name='distribuição perfeitamente igual', mode='lines',
              line=dict(color='#4b5468', width=1.4, dash='dot'), hoverinfo='skip')
f.add_vline(x=_g91, line_dash='dash', line_color='#6b7690')
f.add_annotation(x=_g91, y=6, text=f'{len(alto)} grupos de alto retorno ({_g91:.0f}%)',
                 showarrow=False, xanchor='left', xshift=6,
                 font=dict(size=9.5, color='#9aa3b6'), bgcolor='rgba(18,21,30,.85)')
base(f, h=390, xtitle='grupos, do que mais recebeu para o que menos recebeu (%)',
     ytitle='% acumulado')
reg('h_lorenz', 'c4', 22,
    'O desenho numa linha — quem recebeu e quem devolveu',
    f'Os grupos entram no eixo horizontal ordenados do que mais recebeu para o que menos '
    f'recebeu. A linha azul acumula o dinheiro público, a dourada acumula a receita — e sobe '
    f'muito mais rápido. Os {len(alto)} grupos de alto retorno ({_g91:.0f}% do total) ficam com '
    f'{_d91:.0f}% do dinheiro e respondem por {_r91:.0f}% da receita. A diagonal pontilhada é '
    'como seria a distribuição perfeitamente igual; a distância até ela é a concentração.',
    'RIDAB · base_produtoras (carteira 1996–2024)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c5 p2 · a proliferação de empresas
# ══════════════════════════════════════════════════════════════════════════════
# a série do texto conta TODA obra com fomento identificado no cadastro do RIDAB
# (investimento FSA ou fomento indireto), pelo ano de produção inicial, e a empresa
# ativa é a requerente do CPB — uma por obra.
_O = rid('obras')
_O['cpbn'] = _O.cpb.map(nc)
_fom = set(rid('obras_investimento_fsa_pda').cpb.map(nc)) | set(rid('obras_fomento_indireto').cpb.map(nc))
_X = _O[_O.cpbn.isin(_fom)].drop_duplicates('cpbn').copy()
_X['anoN'] = pd.to_numeric(_X.ano_producao_inicial, errors='coerce')
serie = (_X[_X.anoN.between(2006, 2024)].groupby('anoN')
           .agg(obras=('cpbn', 'size'), empresas=('cnpj_requerente', 'nunique')).reset_index())
serie['por_emp'] = serie.obras / serie.empresas
f = make_subplots(specs=[[{'secondary_y': True}]])
f.add_bar(x=serie.anoN, y=serie.obras, name='obras com fomento público no ano',
          marker_color=S.ACCENT, hovertemplate='%{y} obras<extra></extra>')
f.add_scatter(x=serie.anoN, y=serie.empresas, name='empresas distintas produzindo no ano',
              mode='lines+markers', line=dict(color=S.GOLD, width=2.4), marker=dict(size=6),
              hovertemplate='%{y} empresas<extra></extra>')
f.add_scatter(x=serie.anoN, y=serie.por_emp, name='obras por empresa no ano', mode='lines',
              line=dict(color=S.CORAL, width=2, dash='dot'), secondary_y=True,
              hovertemplate='%{y:.2f} obra por empresa<extra></extra>')
base(f, h=395, ytitle='obras e empresas no ano', y2title='obras por empresa')
f.update_yaxes(range=[0, 3], secondary_y=True)
f.update_xaxes(dtick=2)
_i, _ff = serie[serie.anoN == 2010].iloc[0], serie[serie.anoN == 2023].iloc[0]
reg('h_proliferacao', 'c5', 2,
    'A proliferação — cresceram as obras e cresceu, junto, o número de empresas',
    f'De 2010 a 2023 as obras com fomento saltaram de {_i.obras:.0f} para {_ff.obras:.0f} '
    f'({brn(_ff.obras / _i.obras)}×) e as empresas produzindo no ano, de {_i.empresas:.0f} para '
    f'{_ff.empresas:.0f} ({brn(_ff.empresas / _i.empresas)}×) — cresceram juntas. A linha '
    f'pontilhada é o que interessa: obras por empresa saiu de {brn(_i.por_emp, 2)} para '
    f'{brn(_ff.por_emp, 2)}, praticamente não se mexe. O dinheiro novo criou empresas novas em '
    'vez de dar escala às que já existiam. Empresa ativa aqui é a requerente do CPB, uma por obra.',
    'RIDAB · obras × obras_investimento_fsa_pda + obras_fomento_indireto (ano de produção)', f)



# ══════════════════════════════════════════════════════════════════════════════
# c5 p4 · os decis do dinheiro
# ══════════════════════════════════════════════════════════════════════════════
q = P.sort_values('inv_total', ascending=False).reset_index(drop=True)
q['dec'] = pd.qcut(q.index.to_series().rank(method='first'), 10, labels=range(1, 11)).astype(int)
dc = q.groupby('dec').agg(n=('grupo', 'size'), inv=('inv_total', 'sum'), med=('inv_total', 'mean'))
dc['pct'] = 100 * dc.inv / dc.inv.sum()
f = make_subplots(specs=[[{'secondary_y': True}]])
f.add_bar(x=[f'{i}º' for i in dc.index], y=dc.pct, name='% de todo o dinheiro público',
          marker_color=[S.CORAL if i == 1 else S.ACCENT if i == 2 else CINZA for i in dc.index],
          text=[f'{v:.1f}%' for v in dc.pct], textposition='outside', textfont_size=9.5,
          cliponaxis=False, customdata=dc.n,
          hovertemplate='%{y:.1f}%% do dinheiro · %{customdata:.0f} grupos<extra></extra>')
f.add_scatter(x=[f'{i}º' for i in dc.index], y=dc.med / 1e6, name='média por grupo (R$ mi, log)',
              mode='lines+markers', line=dict(color=S.GOLD, width=2.4), marker=dict(size=6),
              secondary_y=True, hovertemplate='R$ %{y:.2f} mi por grupo<extra></extra>')
base(f, h=390, ytitle='% do dinheiro público', y2title='média por grupo (R$ mi)',
     xtitle='decil de grupos, do que mais recebeu ao que menos recebeu')
f.update_yaxes(type='log', secondary_y=True)
reg('h_decis', 'c5', 4,
    'Não existe faixa intermediária — o dinheiro por decil de grupo',
    f'Cada barra é um décimo dos {len(P)} grupos da carteira. O primeiro decil fica com '
    f'{brn(dc.pct.iloc[0])}% de todo o dinheiro público; a metade de baixo divide '
    f'{brn(dc.pct.iloc[5:].sum())}%. A linha dourada, em escala logarítmica, é a média por grupo: '
    'cai de dezenas de milhões para centenas de milhares em dois degraus e depois se achata. '
    'Não é uma distribuição em degraus, são dois blocos.',
    'RIDAB · base_produtoras (carteira 1996–2024)', f)




# ══════════════════════════════════════════════════════════════════════════════
# c6 p3 · o ticket anual de cada empresa contra o piso de existir
# ══════════════════════════════════════════════════════════════════════════════
tk = P[(P.n_obras >= 1) & (P.inv_total > 0)].copy()
tk['anos'] = (tk.ano_ultima - tk.ano_primeira + 1).clip(lower=1)
tk['tanual'] = tk.inv_total / tk.anos
faixas = [(0, .4, 'abaixo de R$ 400 mil'), (.4, 1, 'R$ 400 mil a 1 mi'),
          (1, 3, 'R$ 1 mi a 3 mi'), (3, 6, 'R$ 3 mi a 6 mi'), (6, 1e9, 'acima de R$ 6 mi')]
cont = [((tk.tanual / 1e6 >= a) & (tk.tanual / 1e6 < b)).sum() for a, b, _ in faixas]
cores_fx = [S.CORAL, '#e08a5a', S.GOLD, S.CYAN, S.GREEN]
f = go.Figure(go.Bar(
    x=[r[2] for r in faixas], y=cont, marker_color=cores_fx,
    text=[f'{c} grupos' for c in cont], textposition='outside', textfont_size=10,
    cliponaxis=False,
    customdata=[100 * c / len(tk) for c in cont],
    hovertemplate='<b>%{x}</b><br>%{y} grupos · %{customdata:.1f}%% da carteira<extra></extra>'))
base(f, h=390, legend=False, ytitle='grupos econômicos',
     xtitle='ticket anual do grupo (investimento ÷ anos de atividade na base)', hover='closest')
f.update_layout(margin=dict(l=56, r=16, t=16, b=58))
f.update_xaxes(tickfont_size=9.5)
_ab400 = 100 * (tk.tanual < 4e5).mean()
_ab3 = 100 * (tk.tanual < 3e6).mean()
reg('h_ticket_anual', 'c6', 3,
    'O ticket anual das empresas contra o piso de manter a porta aberta',
    f'O ticket anual é o dinheiro público que o grupo recebeu dividido pelos anos entre a '
    f'primeira e a última obra dele na base. {_ab400:.0f}% dos grupos ficam abaixo dos R$ 400 mil '
    f'que o texto estima como custo anual mínimo de uma produtora com equipe mínima, e '
    f'{_ab3:.0f}% abaixo dos R$ 3 milhões que permitiriam estrutura permanente. Ressalva: o '
    'aporte da obra é orçamento de produção, não custeio da empresa — a comparação dimensiona '
    'a ordem de grandeza, não julga a empresa.',
    'RIDAB · base_produtoras (carteira 1996–2024)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c6 p5 · o ritmo — quantas obras cada grupo lançou em dez anos
# ══════════════════════════════════════════════════════════════════════════════
GM = pd.read_csv(os.path.join(BASES, 'grupo_economico_map.csv'), sep=';', dtype=str)
GM['cnpj'] = GM.cnpj_produtora.astype(str)
RG = R.assign(cnpj=R.cnpj_produtora.astype(str)).merge(
    GM[['cnpj', 'grupo', 'razao_social']], on='cnpj', how='left')
rit = RG.dropna(subset=['grupo']).groupby(['grupo', 'razao_social']).size().reset_index(name='n')
bins = [(1, 1, '1 obra'), (2, 2, '2 obras'), (3, 4, '3 a 4'), (5, 9, '5 a 9'), (10, 99, '10 ou mais')]
cnt = [((rit.n >= a) & (rit.n <= b)).sum() for a, b, _ in bins]
top5 = rit.nlargest(5, 'n')
f = go.Figure(go.Bar(
    x=[b[2] for b in bins], y=cnt, marker_color=[S.CORAL, '#e08a5a', S.GOLD, S.CYAN, S.GREEN],
    text=[f'{c}' for c in cnt], textposition='outside', textfont_size=10.5, cliponaxis=False,
    customdata=[100 * c / len(rit) for c in cnt],
    hovertemplate='<b>%{x}</b><br>%{y} grupos · %{customdata:.1f}%% dos grupos<extra></extra>'))
f.add_annotation(x=4, y=cnt[-1], yshift=34, showarrow=False, align='right',
                 text='<br>'.join(nome_curto(t) for t in top5.razao_social),
                 font=dict(size=9, color='#9aa3b6'), bgcolor='rgba(18,21,30,.86)', borderpad=3)
base(f, h=390, legend=False, ytitle='grupos produtores',
     xtitle='obras lançadas em sala entre 2014 e 2023', hover='closest')
f.update_layout(margin=dict(l=56, r=16, t=30, b=48))
reg('h_ritmo', 'c6', 5,
    'O ritmo de dez anos — a metade do sistema lançou uma vez só',
    f'Os {len(rit)} grupos que lançaram alguma das 855 obras do recorte, distribuídos pelo '
    f'número de obras que cada um lançou em dez anos. {cnt[0]} deles — '
    f'{100 * cnt[0] / len(rit):.0f}% — lançaram uma única vez; {cnt[-1]} mantiveram ritmo de uma '
    'obra por ano ou mais, e estão nomeados no gráfico. É a intermitência, não a falta de '
    'dinheiro numa obra, que impede a empresa de existir de forma contínua.',
    'RIDAB · base_obras × grupo econômico (outputs/bases/grupo_economico_map.csv)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c6 p8 · a capacidade de carga do fundo
# ══════════════════════════════════════════════════════════════════════════════
t_grid = np.arange(2.0, 8.01, 0.1)
f = make_subplots(specs=[[{'secondary_y': True}]])
for orc, cor, nome in [(500, S.CYAN, 'PAI de R$ 500 mi/ano'), (750, S.GOLD, 'PAI de R$ 750 mi/ano')]:
    n = orc / t_grid
    f.add_scatter(x=t_grid, y=n, name=nome, mode='lines', line=dict(color=cor, width=2.6),
                  customdata=n / 0.5,
                  hovertemplate='ticket R$ %{x:.1f} mi → %{y:.0f} filmes/ano '
                                '(%{customdata:.0f} empresas a 1 obra a cada 2 anos)<extra></extra>')
f.add_scatter(x=[3.2], y=[86], mode='markers+text', name='o que o período de fato entregou',
              marker=dict(size=13, color=S.CORAL, symbol='diamond'),
              text=['2014–2023: 86 obras/ano<br>ticket R$ 3,2 mi'], textposition='top right',
              textfont=dict(size=9.5, color='#cbd5e1'),
              hovertemplate='86 obras por ano, ticket médio R$ 3,2 mi<extra></extra>')
f.add_vline(x=5, line_dash='dot', line_color='#6b7690')
f.add_annotation(x=5, y=170, text='R$ 5 mi por obra', showarrow=False, xanchor='left', xshift=6,
                 font=dict(size=9.5, color='#9aa3b6'), bgcolor='rgba(18,21,30,.85)')
base(f, h=390, xtitle='ticket médio por obra (R$ milhões)', ytitle='filmes financiados por ano',
     hover='closest')
f.update_yaxes(range=[0, 260])
reg('h_carga', 'c6', 8,
    'A capacidade de carga — o que o orçamento compra, a cada ticket',
    'Duas equações, três variáveis: orçamento = filmes × ticket, e empresas = filmes ÷ ritmo. '
    'Fixados dois parâmetros, o terceiro sai por consequência. As curvas mostram quantos filmes '
    'por ano cada PAI compra conforme o ticket sobe; o losango é o que o período de fato '
    'entregou. A R$ 5 milhões por obra, os R$ 500 milhões do PAI compram cem filmes por ano — '
    'que sustentam duzentas empresas em ritmo de um filme a cada dois anos.',
    'Aritmética do texto sobre o PAI do PRODECINE + média observada de 2014–2023 (RIDAB)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c6 p14 · a porta de entrada e a de permanência
# ══════════════════════════════════════════════════════════════════════════════
# estreante = grupo cuja PRIMEIRA obra da carteira inteira (1996–2024) caiu no recorte,
# e não apenas cuja primeira obra do recorte está aqui — senão todo grupo seria estreante.
prim = RG.dropna(subset=['grupo']).groupby('grupo').ano.min()
nobras = RG.dropna(subset=['grupo']).groupby('grupo').size()
est = pd.DataFrame({'ano': prim, 'n': nobras}).join(P.set_index('grupo').ano_primeira)
est = est[(est.ano.between(2014, 2023)) & (est.ano_primeira >= 2014)]
ser = est.groupby('ano').agg(novos=('n', 'size'), voltou=('n', lambda s: (s >= 2).sum())).reset_index()
f = go.Figure()
f.add_bar(x=ser.ano, y=ser.novos - ser.voltou, name='estreou no período e não voltou',
          marker_color=CINZA, hovertemplate='%{y} grupos<extra></extra>')
f.add_bar(x=ser.ano, y=ser.voltou, name='estreou e chegou à segunda obra',
          marker_color=S.GREEN, hovertemplate='%{y} grupos<extra></extra>')
f.update_layout(barmode='stack', bargap=0.28)
base(f, h=390, ytitle='grupos que estrearam no ano')
f.update_xaxes(dtick=1)
_tot, _volt = ser.novos.sum(), ser.voltou.sum()
reg('h_renovacao', 'c6', 14,
    'A porta de entrada está escancarada; a de permanência é que está fechada',
    f'Cada barra é a safra de grupos que estreou na carteira naquele ano, partida entre os que '
    f'voltaram a lançar dentro do período (verde) e os que não voltaram (cinza). São {_tot} '
    f'grupos estreantes em dez anos e apenas {_volt} ({brn(100 * _volt / _tot, 0)}%) chegaram à '
    f'segunda obra — a contagem é por grupo econômico, não por CNPJ, então fica abaixo da '
    f'contagem de empresas do texto. As safras mais recentes ainda têm '
    'menos tempo de janela, o que puxa o verde para baixo no fim da série — mas a diferença é '
    'grande demais para ser só isso. O problema não é fazer o primeiro filme, é sobreviver até '
    'o segundo.',
    'RIDAB · base_obras × grupo econômico (2014–2023)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c7 p2 · somar carteiras em vez de esperar que cada empresa cresça
# ══════════════════════════════════════════════════════════════════════════════
r3 = rit[rit.n >= 3]
unidades = int(r3.n.sum() // 10)
hoje = int((rit.n >= 10).sum())
f = go.Figure()
f.add_bar(x=['hoje, empresa a empresa', 'somando as carteiras de quem<br>já lança 3 ou mais por década'],
          y=[hoje, unidades], marker_color=[CINZA, S.GREEN],
          text=[f'{hoje} unidades', f'{unidades} unidades'], textposition='outside',
          textfont_size=11, cliponaxis=False,
          customdata=[[len(rit), rit.n.sum()], [len(r3), r3.n.sum()]],
          hovertemplate='%{y} unidades com ritmo de 1 obra/ano<br>'
                        '(%{customdata[0]} grupos, %{customdata[1]} obras no período)<extra></extra>')
base(f, h=380, legend=False, ytitle='unidades com ritmo de uma obra por ano', hover='closest')
f.update_layout(margin=dict(l=56, r=16, t=16, b=62), bargap=0.55)
f.update_xaxes(tickfont_size=10)
reg('h_fusao', 'c7', 2,
    'Somar carteiras em vez de esperar que cada empresa cresça sozinha',
    f'À esquerda, quantos grupos hoje sustentam sozinhos o ritmo de uma obra por ano: {hoje}. '
    f'À direita, quantas unidades desse mesmo ritmo saem se as carteiras dos {len(r3)} grupos que '
    f'já lançam três ou mais por década forem somadas — {unidades}. É aritmética de carteira, '
    'não previsão: pressupõe que a fusão preserve o ritmo somado, que é justamente o que o '
    'desenho por SPE teria de garantir.',
    'RIDAB · base_obras × grupo econômico (2014–2023)', f)


# ══════════════════════════════════════════════════════════════════════════════
# c7 p11 · o custo da cadeia proposta dentro do PAI
# ══════════════════════════════════════════════════════════════════════════════
etapas = [('desenvolvimento (100 projetos)', 12.5, S.CYAN),
          ('produção (10 primeiros longas)', 30, S.ACCENT),
          ('distribuição (2 a 3 obras)', 10, S.PURPLE),
          ('SUAT Curtas Internacional', 25, S.GOLD)]
tot = sum(e[1] for e in etapas)
f = go.Figure()
for nome, v, cor in etapas:
    f.add_bar(y=['renovação proposta'], x=[v], orientation='h', name=nome, marker_color=cor,
              hovertemplate=nome + ': R$ %{x:.1f} mi<extra></extra>')
f.add_bar(y=['renovação proposta'], x=[500 - tot], orientation='h',
          name='resto do PAI do PRODECINE', marker_color='#2a3040',
          hovertemplate='resto do PAI: R$ %{x:.0f} mi<extra></extra>')
f.update_layout(barmode='stack', bargap=0.72)
base(f, h=330, xtitle='R$ milhões por ano, sobre um PAI de R$ 500 milhões', hover='closest')
f.update_layout(margin=dict(l=130, r=16, t=58, b=44))
reg('h_custo_cadeia', 'c7', 11,
    'O que a proposta de renovação custaria dentro do PAI',
    f'A cadeia desenvolvimento → produção → distribuição sai por cerca de R$ {brn(tot - 25, 0)} '
    f'milhões ao ano, e o SUAT Curtas por mais R$ 25 milhões (os 5% que o texto propõe): '
    f'{brn(100 * tot / 500)}% de um PAI de R$ 500 milhões. A barra mostra a proporção real da '
    'proposta dentro da linha de cinema — é a ordem de grandeza da conta do texto, não uma '
    'peça orçamentária.',
    'Parâmetros declarados no próprio texto sobre o PAI do PRODECINE', f)


# ══════════════════════════════════════════════════════════════════════════════
# c7 p18 · o curta em festival como credencial de entrada
# ══════════════════════════════════════════════════════════════════════════════
ic = CUR['curtas_ic']
f = go.Figure()
f.add_bar(x=['direções com curta em<br>festival de primeira linha', 'todas as direções de longa<br>no cadastro da ANCINE'],
          y=[CUR['curtas_com_curta_pct'], CUR['curtas_base_geral_pct']],
          marker_color=[S.GREEN, CINZA],
          error_y=dict(type='data', symmetric=False,
                       array=[ic[1] - CUR['curtas_com_curta_pct'], 0],
                       arrayminus=[CUR['curtas_com_curta_pct'] - ic[0], 0],
                       color='#9aa3b6', thickness=1.4, width=7),
          text=[f'{CUR["curtas_com_curta_pct"]:.1f}%', f'{CUR["curtas_base_geral_pct"]:.1f}%'],
          textposition='outside', textfont_size=12, cliponaxis=False,
          hovertemplate='%{x}: %{y:.1f}%%<extra></extra>')
base(f, h=370, legend=False, ytitle='% que chega ao mercado europeu com um longa', hover='closest')
f.update_layout(margin=dict(l=58, r=16, t=22, b=62), bargap=0.55)
f.update_xaxes(tickfont_size=10)
f.update_yaxes(range=[0, 66])
reg('h_curtas', 'c7', 18,
    'O curta em festival como marcador antecipado do longa que exporta',
    f'{brn(CUR["curtas_com_curta_pct"])}% das direções que levaram um curta a festival de '
    f'primeira linha e já tiveram tempo de fazer um longa chegaram ao mercado europeu com ele '
    f'(12 de 29). Entre as {brn(CUR["curtas_universo"], 0)} direções de longa do cadastro, '
    f'{brn(CUR["curtas_base_geral_pct"])}% '
    f'(199). São {brn(CUR["curtas_mult"])} vezes a chance, com p < 0,001. A barra de erro é o '
    f'intervalo de confiança de 95% do grupo de curtas ({brn(ic[0])}% a {brn(ic[1])}%), largo '
    'porque a coorte madura tem 29 direções. Ressalva que o texto já faz: o curta em festival de primeira linha '
    'é também sinal de talento e de rede, então parte do efeito é seleção, não causa.',
    'outputs/bases/curtas_indicadores.json (scripts/14) · RIDAB + curadoria de seleções', f)


# ── saída ─────────────────────────────────────────────────────────────────────
out = os.path.join(BASES, 'hoverfigs2.json')
with open(out, 'w', encoding='utf-8') as fh:
    json.dump(FIGS, fh, ensure_ascii=False, separators=(',', ':'))
print(f'\nOK → outputs/bases/hoverfigs2.json ({os.path.getsize(out) / 1024:.0f} KB) · '
      f'{len(FIGS)} visualizações de trecho')
