# -*- coding: utf-8 -*-
"""
23_hover_trechos.py — as 8 VISUALIZAÇÕES DE TRECHO do ensaio (hover).

Origem: comentários do Cainan no `textos-docx/FSA-argumento-e-verificacao_EDITADO8.docx`
(19/08/2026). Cada comentário marca um TRECHO do texto e pede um gráfico; aqui cada
pedido vira uma figura Plotly + a âncora (trecho inicial → trecho final) que o
`scripts/21` usa para sublinhar a passagem e abrir o gráfico no hover.

Saída: `outputs/bases/hoverfigs.json`  { id: {inicio, fim, titulo, legenda, fonte, spec} }

Os oito pedidos (verbatim do DOCX):
  g0  série histórica do retorno doméstico com valor investido e renda gerada
      (decomposta entre bilheteria e estimativa de cauda longa)
  g1  a mesma série, só que do RETORNO DO FSA, na fonte dos relatórios de gestão da Ancine
  g2  série histórica só com os grandes exibidores e a renda de cada um com filmes brasileiros
  g3  mapa dos países citados com nº de filmes brasileiros selecionados por país (festivais)
  g4  ranking dos filmes brasileiros na Europa (bilheteria Lumière)
  g5  mapa dos países com presença de VOD, com nº de filmes por país
  g6  série histórica que abarque a maior parte das informações do recorte
  g7  ranking das produtoras por retorno doméstico e retorno internacional

Rodar:  .\.venv\Scripts\python.exe scripts\23_hover_trechos.py   (antes do scripts/21)
"""
import os
import re
import sys
import json
import unicodedata

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import site_base as S  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RID = os.path.join(BASE, 'data', 'ridab_cleaned')
BASES = os.path.join(BASE, 'outputs', 'bases')
REF = os.path.join(BASE, 'referencia')

rid = lambda t: pd.read_parquet(os.path.join(RID, t + '.parquet'))
nc = lambda s: re.sub(r'[^0-9A-Z]', '', str(s).upper())
FIGS = {}


def mojibake(s):
    """Alguns cadastros do RIDAB vêm com UTF-8 lido como latin-1 (CINEMATOGRÃFICA)."""
    try:
        return str(s).encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return str(s)


def reg(gid, inicio, fim, titulo, legenda, fonte, fig):
    FIGS[gid] = {'inicio': inicio, 'fim': fim, 'titulo': titulo,
                 'legenda': legenda, 'fonte': fonte,
                 'spec': json.loads(fig.to_json())}
    print(f'  ✓ {gid}  {titulo}')


def base(fig, h=380, legend=True, ytitle=None, y2title=None, xtitle=None):
    fig.update_layout(
        paper_bgcolor='#12151e', plot_bgcolor='#12151e',
        font=dict(family='Inter,system-ui,sans-serif', color=S.TXT, size=11.5),
        margin=dict(l=58, r=58 if y2title else 16, t=10, b=42), height=h,
        showlegend=legend,
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=10.5), orientation='h',
                    y=1.14, x=0, yanchor='top'),
        hoverlabel=dict(font_size=11.5, font_family='Inter'), hovermode='x unified')
    fig.update_xaxes(gridcolor=S.GRID, zerolinecolor=S.GRID, linecolor=S.GRID,
                     title=xtitle, title_font_size=11, tickfont_size=10.5)
    fig.update_yaxes(gridcolor=S.GRID, zerolinecolor=S.GRID, linecolor=S.GRID,
                     title=ytitle, title_font_size=11, tickfont_size=10.5)
    if y2title:
        fig.update_yaxes(title=y2title, secondary_y=True, showgrid=False)
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# g0 · retorno doméstico ano a ano — investido × renda (bilheteria + cauda longa)
# ══════════════════════════════════════════════════════════════════════════════
B = pd.read_parquet(os.path.join(BASES, 'base_obras.parquet'))
R = B[B.universo_retorno == True].copy()                                    # noqa: E712
a = (R.groupby('ano')
      .agg(inv=('inv_total', 'sum'), bil=('bilheteria_obs', 'sum'),
           crt=('janelas_crt', 'sum'), n=('cpb', 'size')).reset_index())
a['rec'] = a.bil + a.crt
a['ret'] = a.rec / a.inv

f = make_subplots(specs=[[{'secondary_y': True}]])
f.add_bar(x=a.ano, y=-a.inv / 1e6, name='investimento público (FSA + renúncia)',
          marker_color='#5a6478', hovertemplate='R$ %{customdata:.1f} mi<extra></extra>',
          customdata=a.inv / 1e6)
f.add_bar(x=a.ano, y=a.bil / 1e6, name='renda de bilheteria (observada)',
          marker_color=S.CYAN, hovertemplate='R$ %{y:.1f} mi<extra></extra>')
f.add_bar(x=a.ano, y=a.crt / 1e6, name='demais janelas (estimativa por CRT)',
          marker_color=S.PURPLE, marker_pattern_shape='/',
          hovertemplate='R$ %{y:.1f} mi<extra></extra>')
f.add_scatter(x=a.ano, y=a.ret, name='retorno doméstico do ano (renda ÷ investimento)',
              mode='lines+markers', line=dict(color=S.GOLD, width=2.4),
              marker=dict(size=6), secondary_y=True,
              hovertemplate='%{y:.2f}×<extra></extra>')
f.add_hline(y=1, line_dash='dot', line_color='#4b5468', secondary_y=True)
f.update_layout(barmode='relative', bargap=0.28)
base(f, h=390, ytitle='R$ milhões (dez/2024)', y2title='retorno (×)')
f.update_xaxes(dtick=1)
reg('g0',
    'O primeiro indicador é o **retorno doméstico**',
    'incluindo a combinação com fomento indireto.',
    'Retorno doméstico ano a ano — o que entrou de dinheiro público e o que voltou de renda',
    'Barras para baixo: o investimento público da safra (FSA + renúncia captada). Para cima: a receita '
    'de referência das mesmas obras, separando a bilheteria observada da estimativa das demais janelas '
    '(CRT). A linha é o retorno do ano; a pontilhada marca 1,00× (renda = investimento). '
    f'{len(R)} obras do universo de retorno, R$ dez/2024.',
    'RIDAB · outputs/bases/base_obras.parquet (scripts/10 e 13)', f)


# ══════════════════════════════════════════════════════════════════════════════
# g1 · retorno do FSA como o próprio FSA mede — relatórios de gestão da Ancine
# ══════════════════════════════════════════════════════════════════════════════
G = pd.read_csv(os.path.join(REF, 'fsa_retorno_relatorios_gestao.csv'))
DEF = rid('deflator_ipca').set_index('ano').fator_real_2024.to_dict()
G['fator'] = G.ano.map(DEF)
G['desemb'] = G.desembolso_nominal * G.fator
G['ret'] = G.retorno_nominal * G.fator
G['pct'] = 100 * G.retorno_nominal / G.desembolso_nominal
g = G.dropna(subset=['retorno_nominal'])

f = make_subplots(specs=[[{'secondary_y': True}]])
f.add_bar(x=g.ano, y=g.desemb / 1e6, name='desembolso do FSA no ano',
          marker_color='#5a6478', hovertemplate='R$ %{y:.1f} mi<extra></extra>')
f.add_bar(x=g.ano, y=g.ret / 1e6, name='retorno financeiro recolhido no ano',
          marker_color=S.CORAL, hovertemplate='R$ %{y:.1f} mi<extra></extra>')
f.add_scatter(x=g.ano, y=g.pct, name='retorno ÷ desembolso do ano (%)', mode='lines+markers',
              line=dict(color=S.GOLD, width=2.4), marker=dict(size=6), secondary_y=True,
              hovertemplate='%{y:.1f}%<extra></extra>')
f.update_layout(barmode='group', bargap=0.3)
base(f, h=390, ytitle='R$ milhões (dez/2024)', y2title='% do desembolso')
f.update_xaxes(dtick=1)
f.update_yaxes(range=[0, max(6, g.pct.max() * 1.6)], secondary_y=True)
reg('g1',
    'Aqui cabe uma observação. O retorno do FSA',
    'recai sobre e **renda líquida do produtor**.',
    'O retorno do FSA como o próprio FSA mede — recolhido ano a ano (2015–2023)',
    'O que o fundo recolhe de volta é a participação sobre a receita líquida do produtor, o último elo '
    'da cadeia. Comparado ao desembolso do mesmo ano, o recolhimento fica entre 1% e 4%. Não é a mesma '
    'conta do retorno doméstico: aqui é caixa que volta ao Tesouro, ali é renda que a obra gera no '
    'mercado. 2017 e 2018 saem arredondados porque é assim que os relatórios divulgam.',
    'Relatórios Anuais de Gestão do FSA / Ancine (2015–2023) — desembolso da Tabela 12 do RG 2023; '
    'planilha em referencia/fsa_retorno_relatorios_gestao.csv', f)


# ══════════════════════════════════════════════════════════════════════════════
# g2 · a renda dos grandes exibidores com os filmes de fomento
# ══════════════════════════════════════════════════════════════════════════════
M = pd.read_excel(os.path.join(BASE, 'data', 'legado', 'tabela_consolidada_obras.xlsx'))
M['cpbn'] = M.CPB.map(nc)
M['fomento'] = (pd.to_numeric(M['Valor FSA Deflac. (R$2024)'], errors='coerce').fillna(0)
                + pd.to_numeric(M['Renúncia Total Deflac. (R$2024)'], errors='coerce').fillna(0))
CPB_FOM = set(M.loc[M.fomento > 0, 'cpbn'])

EX = rid('bilheteria_diaria_exibidora_filme_ano')
EX['cpbn'] = EX.cpb_roe.map(nc)

# a abertura por exibidor não cobre o período todo: 2014–2015 não existem e 2016 vem
# pela metade. Mede-se a cobertura contra o público total do ano (bilheteria_por_filme_ano)
# e só entram os anos com ≥ 90% — o resto viraria queda que é do dado, não do mercado.
_tot = rid('bilheteria_por_filme_ano').groupby('ano').publico.sum()
_cob = (EX.groupby('ano').publico_total.sum() / _tot).dropna()
ANOS_EX = sorted(a for a in _cob[_cob >= 0.90].index if 2014 <= a <= 2023)
print(f'    g2 · cobertura da abertura por exibidor: anos usados {ANOS_EX[0]}–{ANOS_EX[-1]} '
      f'(descartados: {[int(a) for a in range(2014, 2024) if a not in ANOS_EX]})')
EX = EX[(EX.ano.isin(ANOS_EX)) & (EX.cpbn.isin(CPB_FOM))].copy()
PMI = rid('preco_ingresso').set_index('ano').pmi_real_2024.to_dict()
EX['renda'] = EX.publico_total * EX.ano.map(PMI)
EX['nome'] = EX.exibidora.map(mojibake)

# O dado aberto identifica a EMPRESA que informou a sessão, não o grupo econômico do
# exibidor (a tabela grupos_economicos do RIDAB só cobre produção). Por isso só se
# reúnem aqui as redes nacionais que dá para reconhecer pela razão social sem chutar;
# o resto fica num balde declarado.
GRUPO = [('Cinemark', r'CINEMARK'),
         ('Cinépolis', r'CINEPOLIS|CINÉPOLIS'),
         ('Grupo Severiano Ribeiro (Kinoplex)',
          r'SEVERIANO RIBEIRO|SÃO LUIZ|SAO LUIZ|KINOPLEX|SR RIO|SR SÃO|SR SAO'),
         ('UCI', r'UNITED CINEMAS|\bUCI\b'),
         ('Playarte', r'PLAYARTE')]


def grupo_de(nome):
    up = unicodedata.normalize('NFKD', nome.upper())
    for g_, rx in GRUPO:
        if re.search(rx, nome.upper()) or re.search(rx, up):
            return g_
    return 'demais exibidores (redes regionais e independentes)'


EX['grupo'] = EX.nome.map(grupo_de)
piv = (EX.assign(sala=EX.renda * 0.50)
         .pivot_table(index='ano', columns='grupo', values='sala', aggfunc='sum')
         .fillna(0) / 1e6)
ordem = [g_ for g_, _ in GRUPO] + ['demais exibidores (redes regionais e independentes)']
ordem = [c for c in ordem if c in piv.columns]
CORES = [S.CYAN, S.ACCENT, S.PURPLE, S.GOLD, S.GREEN, S.CORAL, '#5a6478']

f = go.Figure()
for i, c in enumerate(ordem):
    f.add_bar(x=piv.index, y=piv[c], name=c, marker_color=CORES[i % len(CORES)],
              hovertemplate='R$ %{y:.1f} mi<extra></extra>')
f.update_layout(barmode='stack', bargap=0.28)
base(f, h=390, ytitle='renda das salas, R$ mi (dez/2024)')
f.update_xaxes(dtick=1)
reg('g2',
    'Em 29 anos (1996–2024), **as salas de cinema brasileiras faturaram',
    'apenas dos filmes para salas de cinema.',
    'A parte da cadeia que fica com o exibidor — renda de sala com filmes de fomento, por grupo',
    'Metade da renda de bilheteria (a praxe de mercado do elo de exibição, parâmetro declarado, não '
    'medição) das obras com dinheiro público, atribuída ao grupo exibidor que informou a sessão. '
    f'A série vai de {ANOS_EX[0]} a {ANOS_EX[-1]}: é o intervalo em que a bilheteria aberta por '
    'exibidor cobre o mercado (em 2014 e 2015 essa abertura não existe no dado aberto e 2016 vem pela '
    'metade). Renda = público × PMI real do ano; os grupos são reunidos por nome de razão social.',
    'RIDAB · bilheteria_diaria_exibidora_filme_ano + preco_ingresso; carteira de fomento 1995–2024', f)


# ══════════════════════════════════════════════════════════════════════════════
# g3 · mapa dos países dos festivais
# ══════════════════════════════════════════════════════════════════════════════
PAIS_ISO = {
    'Brasil': 'BRA', 'Estados Unidos': 'USA', 'França': 'FRA', 'Portugal': 'PRT',
    'Espanha': 'ESP', 'Alemanha': 'DEU', 'Itália': 'ITA', 'Argentina': 'ARG',
    'Uruguai': 'URY', 'Chile': 'CHL', 'Cuba': 'CUB', 'México': 'MEX',
    'Colômbia': 'COL', 'Canadá': 'CAN', 'Reino Unido': 'GBR', 'Holanda': 'NLD',
    'Bélgica': 'BEL', 'Suíça': 'CHE', 'Áustria': 'AUT', 'Suécia': 'SWE',
    'Dinamarca': 'DNK', 'Noruega': 'NOR', 'Finlândia': 'FIN', 'Polônia': 'POL',
    'Rússia': 'RUS', 'Ucrânia': 'UKR', 'Grécia': 'GRC', 'Turquia': 'TUR',
    'Sérvia': 'SRB', 'Bósnia e Herzegovina': 'BIH', 'Romênia': 'ROU',
    'República Tcheca': 'CZE', 'Estônia': 'EST', 'Irlanda': 'IRL',
    'Índia': 'IND', 'China': 'CHN', 'Coreia do Sul': 'KOR', 'Japão': 'JPN',
    'Taiwan': 'TWN', 'Austrália': 'AUS', 'Nova Zelândia': 'NZL',
    'África do Sul': 'ZAF', 'Marrocos': 'MAR', 'Egito': 'EGY', 'Israel': 'ISR',
    'Peru': 'PER', 'Bolívia': 'BOL', 'Equador': 'ECU', 'Venezuela': 'VEN',
    'Costa Rica': 'CRI', 'Panamá': 'PAN', 'República Dominicana': 'DOM',
}

# evento (ou cidade/sigla no nome do evento) → país. Cobre os 861 registros das atas.
EVENTO_PAIS = [
    (r'havana|cuba', 'Cuba'),
    (r'rio de janeiro|festival do rio|gramado|bras[ií]lia|tiradentes|paulínia|paulinia|mostra .*s[ãa]o paulo|'
     r'coisa de cinema|janela internacional|cine cear[áa]|cine pe|recife|guarnic[êe]|forumdoc|mostra do filme livre|'
     r'olhar de cinema|curitiba|semana dos realizadores|é tudo verdade|e tudo verdade|mixbrasil|recine|cinesul|'
     r'grande pr[êe]mio do cinema brasileiro|academia brasileira|cine esquema novo|porto alegre|femina|fica|'
     r'ambiental|minas gerais|\(brasil\)', 'Brasil'),
    (r'toulouse|cannes|nantes|trois continents|3 continents|biarritz|marselha|amiens|annecy|belfort|'
     r'femmes|film de femmes|paris|fran[çc]a|nouveau cin[ée]ma de|c[ée]sar', 'França'),
    (r'lisboa|porto|fantasporto|festin|santa maria da feira|cinanima|doclisboa|indielisboa|queer lisboa|portugal', 'Portugal'),
    (r'san sebasti|donostia|huelva|gijon|gij[óo]n|valladolid|seminci|sitges|m[áa]laga|espanha|catalu', 'Espanha'),
    (r'berlim|berlin|munique|m[üu]nchen|mannheim|heidelberg|leipzig|lucas|hof|oberhausen|alemanha|lakino', 'Alemanha'),
    (r'veneza|roma|turim|torino|giffoni|it[áa]lia|pesaro|locarno film', 'Itália'),
    (r'toronto|montreal|montr[ée]al|vancouver|hot docs|nouveau cin[ée]ma|canad[áa]', 'Canadá'),
    (r'sundance|miami|chicago|nova york|new york|nyff|tribeca|los angeles|afi|palm springs|austin|sxsw|'
     r'south by southwest|seattle|denver|nashville|newport|san francisco|frameline|riverrun|telluride|'
     r'cine las americas|laliff|newfest|sarasota|art of the real|new directors|eua|\(estados unidos\)', 'Estados Unidos'),
    (r'mar del plata|bafici|buenos aires|argentina|nueva mirada|cine pol[íi]tico', 'Argentina'),
    (r'punta del este|uruguai|llamale h|cinemateca uruguaya', 'Uruguai'),
    (r'vi[ñn]a del mar|valdivia|femcine|santiago|chile', 'Chile'),
    (r'guadalajara|morelia|ficunam|cidade do m[ée]xico|m[ée]xico|docs df', 'México'),
    (r'cartagena|bogot[áa]|col[ôo]mbia|ficci', 'Colômbia'),
    (r'roterd|rotterdam|amsterd|idfa|holanda|pa[íi]ses baixos', 'Holanda'),
    (r'londres|london|bfi|sheffield|inglaterra|reino unido', 'Reino Unido'),
    (r'estocolmo|stockholm|g[öo]teborg|su[ée]cia', 'Suécia'),
    (r'copenhagen|copenhague|cph:|dinamarca', 'Dinamarca'),
    (r'oslo|noruega', 'Noruega'),
    (r'helsinki|finl[âa]ndia|tampere', 'Finlândia'),
    (r'z[uü]rich|zurique|locarno|nyon|visions du r[ée]el|gen[èe]bra|su[íi][çc]a|sui[çc]a', 'Suíça'),
    (r'viena|vienna|viennale|[áa]ustria', 'Áustria'),
    (r'bruxelas|brussels|gante|ghent|b[ée]lgica|biff+', 'Bélgica'),
    (r'karlovy vary|praga|tcheca|tcheco', 'República Tcheca'),
    (r'vars[óo]via|warsaw|pol[ôo]nia|krak', 'Polônia'),
    (r'tallin|tallinn|black nights|poff|est[ôo]nia', 'Estônia'),
    (r'moscou|moscow|r[úu]ssia', 'Rússia'),
    (r'kiev|kyiv|molodist|ucr[âa]nia', 'Ucrânia'),
    (r'sarajevo|b[óo]snia', 'Bósnia e Herzegovina'),
    (r'transilvania|transilv[âa]nia|tiff cluj|rom[êe]nia', 'Romênia'),
    (r'atenas|athens|thessaloniki|salonica|gr[ée]cia', 'Grécia'),
    (r'istambul|istanbul|iksv|antalya|turquia', 'Turquia'),
    (r'cork|dublin|irlanda', 'Irlanda'),
    (r'kerala|iffk|idsffk|mumbai|calcut[áa]|kolkata|kiff|goa|iffi|[ií]ndia', 'Índia'),
    (r'hong kong|shanghai|xangai|beijing|pequim|china', 'China'),
    (r'busan|pusan|jeonju|jiff|seul|coreia', 'Coreia do Sul'),
    (r't[óo]quio|tokyo|jap[ãa]o', 'Japão'),
    (r'taipei|cavalo de ouro|golden horse|taiwan', 'Taiwan'),
    (r'sydney|melbourne|miff|brisbane|austr[áa]lia', 'Austrália'),
    (r'durban|joanesburgo|[áa]frica do sul', 'África do Sul'),
    (r'marrakech|marraquexe|marrocos', 'Marrocos'),
    (r'cairo|egito', 'Egito'),
    (r'jerusal[ée]m|tel aviv|israel', 'Israel'),
    (r'lima|peru', 'Peru'),
]
FE = rid('fsa_atas_festivais')
FE['ev'] = (FE.evento.fillna('').astype(str) + ' | ' + FE.pais_evento_extraido.fillna('').astype(str)).str.lower()


def pais_do_evento(ev):
    for rx, pais in EVENTO_PAIS:
        if re.search(rx, ev):
            return pais
    return None


FE['pais'] = FE.ev.map(pais_do_evento)
FE['obra'] = FE.cpb.fillna(FE.chave_titulo).astype(str)
cob = FE.pais.notna().mean()
mp = (FE.dropna(subset=['pais']).groupby('pais')
        .agg(obras=('obra', 'nunique'), selecoes=('obra', 'size')).reset_index())
mp['iso'] = mp.pais.map(PAIS_ISO)
mp = mp.dropna(subset=['iso']).sort_values('obras', ascending=False)

f = go.Figure(go.Choropleth(
    locations=mp.iso, z=mp.obras, text=mp.pais, customdata=mp.selecoes,
    colorscale=[[0, '#16233a'], [0.25, '#1c4a72'], [0.6, '#2f86c4'], [1, '#7dd3fc']],
    marker_line_color='#0b0d14', marker_line_width=0.4,
    colorbar=dict(title=dict(text='obras', font=dict(size=10)), thickness=9, len=0.72,
                  tickfont=dict(size=9.5), outlinewidth=0),
    hovertemplate='<b>%{text}</b><br>%{z} obras · %{customdata} seleções<extra></extra>'))
f.update_layout(
    geo=dict(bgcolor='#12151e', landcolor='#1b1f2b', lakecolor='#12151e',
             showocean=True, oceancolor='#12151e', showcountries=True,
             countrycolor='#2a3040', showframe=False, coastlinecolor='#2a3040',
             projection_type='natural earth'),
    paper_bgcolor='#12151e', margin=dict(l=0, r=0, t=0, b=0), height=380,
    font=dict(family='Inter,system-ui,sans-serif', color=S.TXT, size=11.5), showlegend=False)
reg('g3',
    'O primeiro componente é o próprio desempenho em festivais internacionais',
    '`fsa_atas_festivais` do RIDAB.',
    'Onde as obras do FSA foram selecionadas — países dos festivais nas atas',
    f'{int(mp.obras.sum())} pares obra–país e {int(mp.selecoes.sum())} seleções, de '
    f'{len(FE)} registros das atas. O país sai do nome do evento (as atas não trazem campo de país); '
    f'{cob * 100:.0f}% dos registros foram identificados, o resto não tinha no nome nada que permitisse '
    'localizar o festival. A cor é o número de obras distintas, não de seleções.',
    'RIDAB · fsa_atas_festivais (atas das chamadas de desempenho artístico)', f)


# ══════════════════════════════════════════════════════════════════════════════
# g4 · ranking dos filmes brasileiros na Europa (Lumière)
# ══════════════════════════════════════════════════════════════════════════════
LU = rid('bilheteria_europa')
LU = LU[LU.tem_brasil == True].sort_values('total_eu27_gb_desde_1996', ascending=False)  # noqa: E712
top = LU.head(20).iloc[::-1]
rot = [f'{t}' for t in top.titulo_original]
f = go.Figure(go.Bar(
    x=top.total_eu27_gb_desde_1996 / 1e3, y=rot, orientation='h',
    marker_color=[S.CYAN if i >= len(top) - 3 else S.ACCENT for i in range(len(top))],
    customdata=list(zip(top.ano_producao, top.paises_producao)),
    hovertemplate='<b>%{y}</b> (%{customdata[0]}) · %{customdata[1]}'
                  '<br>%{x:.1f} mil espectadores<extra></extra>'))
base(f, h=430, legend=False, xtitle='espectadores na Europa (mil), acumulado desde 1996')
f.update_layout(margin=dict(l=190, r=16, t=10, b=42), hovermode='closest')
f.update_yaxes(tickfont_size=10)
reg('g4',
    'O segundo são as admissões em salas no exterior',
    'do Observatório Europeu do Audiovisual.',
    'Os 20 filmes brasileiros mais vistos nas salas da Europa (Lumière)',
    f'Admissões acumuladas desde 1996 nos 27 países da UE mais o Reino Unido, para as '
    f'{len(LU)} obras com participação brasileira que o Lumière registra. É bilheteria de sala: '
    'o que o filme brasileiro vende no cinema europeu, não streaming nem TV. Os dois primeiros '
    'colocados são de 1998 e 2002 — a régua de comparação do que veio depois.',
    'RIDAB · bilheteria_europa (Lumière / Observatório Europeu do Audiovisual)', f)


# ══════════════════════════════════════════════════════════════════════════════
# g5 · mapa da presença em catálogos de VOD
# ══════════════════════════════════════════════════════════════════════════════
ISO2_3 = {'AT': 'AUT', 'BE': 'BEL', 'BG': 'BGR', 'CH': 'CHE', 'CY': 'CYP', 'CZ': 'CZE',
          'DE': 'DEU', 'DK': 'DNK', 'EE': 'EST', 'ES': 'ESP', 'FI': 'FIN', 'FR': 'FRA',
          'GB': 'GBR', 'GR': 'GRC', 'HR': 'HRV', 'HU': 'HUN', 'IE': 'IRL', 'IS': 'ISL',
          'IT': 'ITA', 'LT': 'LTU', 'LU': 'LUX', 'LV': 'LVA', 'MT': 'MLT', 'NL': 'NLD',
          'NO': 'NOR', 'PL': 'POL', 'PT': 'PRT', 'RO': 'ROU', 'SE': 'SWE', 'SI': 'SVN',
          'SK': 'SVK', 'BR': 'BRA'}
NOME2 = {'AT': 'Áustria', 'BE': 'Bélgica', 'BG': 'Bulgária', 'CH': 'Suíça', 'CY': 'Chipre',
         'CZ': 'Rep. Tcheca', 'DE': 'Alemanha', 'DK': 'Dinamarca', 'EE': 'Estônia',
         'ES': 'Espanha', 'FI': 'Finlândia', 'FR': 'França', 'GB': 'Reino Unido',
         'GR': 'Grécia', 'HR': 'Croácia', 'HU': 'Hungria', 'IE': 'Irlanda', 'IS': 'Islândia',
         'IT': 'Itália', 'LT': 'Lituânia', 'LU': 'Luxemburgo', 'LV': 'Letônia', 'MT': 'Malta',
         'NL': 'Holanda', 'NO': 'Noruega', 'PL': 'Polônia', 'PT': 'Portugal', 'RO': 'Romênia',
         'SE': 'Suécia', 'SI': 'Eslovênia', 'SK': 'Eslováquia', 'BR': 'Brasil'}
VD = rid('vod_europa')
VD = VD[VD.tem_brasil == True]                                              # noqa: E712
vp = (VD.groupby('country')
        .agg(obras=('titulo_original', 'nunique'), catalogos=('catalog', 'nunique')).reset_index())
vp['iso'] = vp.country.map(ISO2_3)
vp['nome'] = vp.country.map(NOME2).fillna(vp.country)
vp = vp.dropna(subset=['iso']).sort_values('obras', ascending=False)

f = go.Figure(go.Choropleth(
    locations=vp.iso, z=vp.obras, text=vp.nome, customdata=vp.catalogos,
    colorscale=[[0, '#221a38'], [0.3, '#432d78'], [0.65, '#7a5cd6'], [1, '#c4b5fd']],
    marker_line_color='#0b0d14', marker_line_width=0.4,
    colorbar=dict(title=dict(text='obras', font=dict(size=10)), thickness=9, len=0.72,
                  tickfont=dict(size=9.5), outlinewidth=0),
    hovertemplate='<b>%{text}</b><br>%{z} obras em %{customdata} catálogos<extra></extra>'))
f.update_layout(
    geo=dict(bgcolor='#12151e', landcolor='#1b1f2b', lakecolor='#12151e', showocean=True,
             oceancolor='#12151e', showcountries=True, countrycolor='#2a3040',
             showframe=False, coastlinecolor='#2a3040', projection_type='natural earth',
             lataxis_range=[33, 71], lonaxis_range=[-25, 33]),
    paper_bgcolor='#12151e', margin=dict(l=0, r=0, t=0, b=0), height=380,
    font=dict(family='Inter,system-ui,sans-serif', color=S.TXT, size=11.5), showlegend=False)
reg('g5',
    'O terceiro é a presença em catálogos de VOD',
    'contada em número de países.',
    'Em quantos países cada obra brasileira aparece no catálogo de VOD',
    f'{VD.titulo_original.nunique()} obras com participação brasileira presentes em catálogos de VOD de '
    f'{len(vp)} países, {VD.catalog.nunique()} catálogos no total. O levantamento é do Observatório '
    'Europeu, então o mapa é europeu: é presença em catálogo, não audiência — diz que a obra está '
    'disponível, não que foi vista.',
    'RIDAB · vod_europa (Observatório Europeu do Audiovisual)', f)


# ══════════════════════════════════════════════════════════════════════════════
# g6 · a série histórica do FSA que sustenta o recorte 2014–2023
# ══════════════════════════════════════════════════════════════════════════════
M['ano'] = pd.to_numeric(M.Ano, errors='coerce')
M['fsa'] = pd.to_numeric(M['Valor FSA Deflac. (R$2024)'], errors='coerce').fillna(0)
M['bil'] = pd.to_numeric(M['Bilheteria Deflac. (R$)'], errors='coerce').fillna(0)
FS = M[(M.fsa > 0) & (M.ano.between(2008, 2024))].copy()
FS['n_cham'] = FS['Todas Chamadas FSA'].fillna(FS.Chamada).astype(str)
h = (FS.groupby('ano')
       .agg(obras=('CPB', 'size'), com_bil=('bil', lambda s: (s > 0).sum()),
            dinheiro=('fsa', 'sum'), chamadas=('Chamada', 'nunique')).reset_index())
h['pct'] = 100 * h.com_bil / h.obras

f = make_subplots(specs=[[{'secondary_y': True}]])
f.add_bar(x=h.ano, y=h.obras, name='obras com dinheiro do FSA',
          marker_color=['#2f3a52' if a < 2014 or a > 2023 else S.ACCENT for a in h.ano],
          hovertemplate='%{y} obras<extra></extra>')
f.add_scatter(x=h.ano, y=h.chamadas, name='chamadas distintas no ano', mode='lines+markers',
              line=dict(color=S.GREEN, width=2.2), marker=dict(size=5.5), secondary_y=True,
              hovertemplate='%{y} chamadas<extra></extra>')
f.add_scatter(x=h.ano, y=h.pct, name='% das obras com bilheteria informada', mode='lines',
              line=dict(color=S.GOLD, width=2, dash='dot'), yaxis='y3',
              hovertemplate='%{y:.0f}% com bilheteria<extra></extra>')
f.update_layout(
    bargap=0.25,
    yaxis3=dict(overlaying='y', side='right', range=[0, 105], showgrid=False,
                position=1.0, tickfont=dict(size=9.5, color=S.GOLD), showticklabels=False))
base(f, h=390, ytitle='obras financiadas', y2title='chamadas')
f.update_xaxes(dtick=2)
f.add_vrect(x0=2013.5, x1=2023.5, fillcolor=S.ACCENT, opacity=0.07, line_width=0)
reg('g6',
    'Entre 2014 e 2018 o salto é de outra ordem',
    'está medindo a limitação do dado.',
    'Por que o recorte é 2014–2023 — a escala do FSA ano a ano',
    'Barras: obras que receberam dinheiro do FSA em cada ano da carteira (a faixa clara é o recorte '
    'da Parte II). Linha verde: quantas chamadas distintas estavam ativas — é a variedade de regras '
    'competindo no mesmo ano. Linha pontilhada: a fatia das obras daquele ano que tem bilheteria '
    'informada, que é a condição para entrar no universo de retorno.',
    'RIDAB + carteira consolidada 1995–2024 (data/legado/tabela_consolidada_obras.xlsx)', f)


# ══════════════════════════════════════════════════════════════════════════════
# g7 · ranking das produtoras — retorno doméstico e retorno internacional
# ══════════════════════════════════════════════════════════════════════════════
P = pd.read_parquet(os.path.join(BASES, 'base_produtoras.parquet'))
Q = P[(P.n_obras >= 3) & (P.inv_total >= 3e6) & (P.receita_ref > 0)].copy()
d1 = Q.sort_values('retorno_dom_carteira', ascending=False).head(12).iloc[::-1]
d2 = Q.sort_values('melhor_intl', ascending=False).head(12).iloc[::-1]
curto = lambda s: (s[:26] + '…') if len(s) > 27 else s

f = make_subplots(rows=1, cols=2, horizontal_spacing=0.34,
                  subplot_titles=('por retorno doméstico (renda ÷ investimento)',
                                  'por retorno internacional (0–100, melhor obra)'))
f.add_bar(x=d1.retorno_dom_carteira, y=[curto(t) for t in d1.grupo], orientation='h',
          marker_color=S.CYAN, row=1, col=1, name='doméstico',
          customdata=list(zip(d1.n_obras, d1.inv_total / 1e6)),
          hovertemplate='<b>%{y}</b><br>%{x:.2f}× · %{customdata[0]} obras · '
                        'R$ %{customdata[1]:.1f} mi investidos<extra></extra>')
f.add_bar(x=d2.melhor_intl, y=[curto(t) for t in d2.grupo], orientation='h',
          marker_color=S.PURPLE, row=1, col=2, name='internacional',
          customdata=list(zip(d2.n_obras, d2.retorno_dom_carteira)),
          hovertemplate='<b>%{y}</b><br>%{x:.0f}/100 · %{customdata[0]} obras · '
                        'retorno doméstico %{customdata[1]:.2f}×<extra></extra>')
base(f, h=430, legend=False)
f.update_layout(margin=dict(l=170, r=16, t=34, b=36), hovermode='closest')
f.update_yaxes(tickfont_size=9.5)
f.update_xaxes(tickfont_size=9.5)
for an in f.layout.annotations:
    an.font.size = 10.5
    an.font.color = S.MUT
reg('g7',
    'Já a Parte III, que tem como foco o impacto nas empresas',
    'ajudam a entender melhor o cenário todo.',
    'Ranking das produtoras — as duas réguas lado a lado',
    f'Grupos econômicos da carteira 1996–2024 com pelo menos 3 obras e R$ 3 milhões de investimento '
    f'({len(Q)} de {len(P)} grupos passam no corte, para não premiar quem tem uma obra só). '
    'À esquerda, quanto de renda doméstica a carteira do grupo gerou por real investido. À direita, '
    'a melhor pontuação internacional de uma obra do grupo. São listas quase disjuntas — é esse o ponto.',
    'RIDAB · outputs/bases/base_produtoras.parquet (scripts/12)', f)


# ── saída ─────────────────────────────────────────────────────────────────────
out = os.path.join(BASES, 'hoverfigs.json')
with open(out, 'w', encoding='utf-8') as fh:
    json.dump(FIGS, fh, ensure_ascii=False, separators=(',', ':'))
print(f'\nOK → outputs/bases/hoverfigs.json ({os.path.getsize(out) / 1024:.0f} KB) · '
      f'{len(FIGS)} visualizações de trecho')
