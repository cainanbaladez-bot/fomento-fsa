# -*- coding: utf-8 -*-
"""
site_base.py — infraestrutura compartilhada do SITE FINAL (site/), a versão única do trabalho.

Três páginas: index.html (porta de entrada) · ensaio.html (voz autoral, 14 alegações)
· evidencias.html (painel de dados completo). Difere do relatorio_base.py (que fica
intocado para os caps antigos) em três pontos:
  1. Plotly NÃO é embutido inline — vai uma vez em site/assets/plotly.min.js e os
     gráficos renderizam por lazy-load (IntersectionObserver), páginas leves.
  2. Registro único das 8 ALEGAÇÕES (ids, títulos, TL;DR, status) usado pelas 3 páginas.
  3. Bloco "Reproduza esta conta" conectando cada evidência ao RIDAB (portal + HF + DuckDB).

Builders: scripts/20_site_index.py · 21_site_ensaio.py · 22_site_evidencias.py.
O CSS daqui (CSS_BASE) é o de ARTIGO — usado por index/ensaio. O evidencias.html soma a
ele o CSS_PANEL do próprio scripts/22 (sidebar, KPI bar, grade de cards): é painel, não texto.
Fonte editável do ensaio: site_src/ensaio.md.
"""
import os
import shutil
import plotly.io as pio

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, 'site')
ASSETS = os.path.join(SITE, 'assets')
SRC = os.path.join(BASE, 'site_src')

# ── RIDAB (conexão canônica) ──────────────────────────────────────────────────
RIDAB_PORTAL = 'https://riabr-dados.github.io/riab'
RIDAB_HF = 'https://huggingface.co/datasets/riabr-dados/riab'
RIDAB_HF_PATH = 'hf://datasets/riabr-dados/riab/cleaned'   # + /<tabela>.parquet
LEGADO_URL = 'https://cainanbaladez-bot.github.io/fomento-audiovisual'

# ── paleta (idêntica à identidade fechada do projeto) ─────────────────────────
BG, SURF, TXT, MUT, GRID = '#0b0d14', '#14171f', '#e2e8f0', '#7b849a', '#282d42'
ACCENT, CYAN, PURPLE, GOLD, GREEN, CORAL = '#6c7bf7', '#38bdf8', '#a78bfa', '#fbbf24', '#34d399', '#f87171'

# ── AS 8 ALEGAÇÕES em 4 PARTES — registro único (usado pelas 3 páginas) ──────
# Hierarquia: 'ancora' = alegações centrais do argumento; 'compl' = complementares.
# Tom: sóbrio, sem frase de efeito — a tese descreve o achado, não o vende.
PARTES = [
    ('p1', 'Parte I · As evidências domésticas e internacionais',
     'A base do trabalho: a vastidão do registro público do audiovisual brasileiro, a metodologia dos dois '
     'universos e os dois indicadores centrais — o retorno doméstico e o retorno internacional.'),
    ('p2', 'Parte II · A decisão de investimento',
     'O núcleo do trabalho. O que o edital usa para decidir — o critério de seleção, o elo que propõe e o '
     'instrumento de financiamento — determina o tipo de cinema que se viabiliza.'),
    ('p3', 'Parte III · O que a política produziu nas empresas',
     'O que o financiamento constrói do lado das empresas: os perfis de retorno, a concentração, a escala '
     'que o fundo comporta e o desenho que os dados recomendam.'),
]
PARTE_BY_ID = {p[0]: p for p in PARTES}

# (id, parte, rótulo curto, título-tese, TL;DR, status, tom, peso)
CLAIMS = [
    # ── Parte I · As evidências ──
    ('c1', 'p1', 'A política é mensurável',
     'O registro público do audiovisual brasileiro é vasto o bastante para basear a política em evidências',
     'Microdados abertos obra a obra — contratos, bilheteria por sessão, atas, registros — cruzáveis por CPB. Poucos países publicam nesse nível de detalhe. Dois universos declarados (aplicação e retorno) e dois indicadores: o retorno doméstico e o retorno internacional.',
     'SUSTENTADA', 'ok', 'ancora'),
    # ── Parte II · A decisão de investimento ──
    ('c2', 'p2', 'O dado de entrada condiciona o resultado',
     'O dado usado na seleção condiciona o resultado — e isso vale também para o critério de cota',
     'Critério de bilheteria: retorno doméstico 0,43 e internacional 0,61 por R$ mi. Critério de festival: 0,06 e 1,61. A inversão é limpa. Com o critério constante, a distribuidora desloca o patamar. E quando o dado de entrada é a cota, negros passam de 22% dos inscritos a 29% dos contratados; mulheres, de 35% a 53%.',
     'SUSTENTADA', 'ok', 'ancora'),
    ('c3', 'p2', 'Quem decide, quem arrisca, quem captura',
     'O principal fator de resultado em sala é a renúncia — recurso público de decisão privada',
     'A renúncia pura tem o maior retorno doméstico (1,92, contra 0,11 do FSA puro) e a menor internacionalização (22% contra 32%). É um suporte automático operado pelas majors. E o fundo banca o teste: o 1º Minha Mãe é uma Peça saiu de edital, o 2º e o 3º foram renúncia pura e renderam R$ 408 mi.',
     'SUSTENTADA', 'ok', 'ancora'),
    # ── Parte III · O que a política produziu nas empresas ──
    ('c4', 'p3', 'O perfil de empresa que o fomento induziu',
     'O fomento induziu poucas empresas capazes de devolver nas duas réguas e uma cauda que não devolve em nenhuma',
     'Das 697 empresas financiadas desde 1995, 30 vendem ingresso e circulam fora, 61 só vendem em casa e 24 só circulam fora. Noventa e oito receberam mais de R$ 5 mi cada e não entregaram nenhuma das duas coisas.',
     'SUSTENTADA · descritiva', 'warn', 'ancora'),
    ('c5', 'p3', 'Concentração e dispersão do fomento',
     'As regras contra a concentração produziram proliferação sem desconcentrar o fomento',
     'Um CNPJ por chamada e tetos de captação: obras por ano cresceram 5,5× e produtoras ativas 5×, mas o décimo superior dos grupos ficou com 60,7% do dinheiro e a metade de baixo dividiu 6,1%. Mais gente entrou, e entrou menor.',
     'SUSTENTADA · descritiva', 'warn', 'ancora'),
    ('c6', 'p3', 'Escala, sustentação e renovação',
     'O fundo sustenta muitas empresas num ritmo que não sustenta nenhuma — e quem entra não chega ao segundo filme',
     'Ritmo mediano de uma obra por década e só 32 empresas em ritmo de um filme a cada dois anos. O ticket mediano fica abaixo do piso de visibilidade, o mercado já lança 219 filmes por ano com 78% abaixo de dez mil espectadores, e das 503 empresas do período 376 estrearam nele — mas só 86 voltaram a produzir.',
     'SUSTENTADA · descritiva', 'warn', 'ancora'),
    ('c7', 'p3', 'O desenho que os dados recomendam',
     'Há uma reorganização que os dados sustentam: carteira em vez de obra, e uma porta de entrada com critério objetivo',
     'Somar carteiras por SPE para dar ritmo às empresas; uma cadeia de desenvolvimento que garanta o primeiro longa; e um suporte automático de curtas, o marcador antecipado mais forte da base — 41,4% das direções com curta em festival de primeira linha chegam ao mercado europeu, contra 4,6% do universo.',
     'PROPOSTA · derivada do diagnóstico', 'warn', 'ancora'),
]

# A figura MAIS SIGNIFICATIVA de cada pergunta. Decisão do Cainan (09/08/2026):
# o ensaio e o DOCX levam UMA figura por pergunta, logo depois da pergunta; o
# painel de verificação segue com todas as 81 e os componentes interativos.
FIG_PERGUNTA = {
    'c1': ('__nuvem__', 'O registro público em uma imagem. Cada ponto representa cerca de 130 '
           'registros abertos reunidos no RIDAB, cerca de 1,3 milhão no total.'),
    'c2': ('f_disp_chamada', 'Cada ponto é uma chamada pública: retorno doméstico no eixo '
           'horizontal, desempenho internacional no vertical, tamanho pelo dinheiro aplicado. '
           'Complementação e comercialização ficam fora porque são aporte sobre filme pronto e '
           'distorcem os dois eixos.'),
    'c3': ('f_grup', 'Retorno doméstico e alcance externo por composição do financiamento: a '
           'renúncia pura devolve mais em sala e viaja menos; o FSA puro faz o inverso.'),
    'c4': ('f_disp_prod', 'Cada bolha é um grupo econômico: investimento acumulado no eixo '
           'horizontal, retorno doméstico no vertical, ambos em escala log, cor pelo perfil. A '
           'linha tracejada é o retorno igual a 1.'),
    'c5': ('f_lz', 'Curva de Lorenz do investimento por grupo econômico: a distância até a '
           'diagonal é a desigualdade da distribuição do fomento.'),
    'c6': ('f_ticket_hist', 'Distribuição das empresas por faixa de operação anual, com o '
           'tracejado no custo fixo mínimo de manter uma produtora de pé. A massa do gráfico '
           'está à esquerda da linha.'),
    'c7': ('f_carga', 'A capacidade de carga do fundo: quantos filmes por ano cada orçamento '
           'compra em função do ticket, e quantas empresas isso sustenta em ritmo de um filme '
           'a cada dois anos.'),
}

CLAIM_BY_ID = {c[0]: c for c in CLAIMS}

# ── as PERGUNTAS (moldura do site — cada item é uma pergunta verificável) ──────
# 1ª versão; Cainan refina caso a caso. Usada no index (scripts/20) e no DOCX (scripts/30).
# O registro CLAIMS acima (teses) fica intacto; a pergunta é só o headline.
PERGUNTAS = {
    'c1': 'Existem evidências disponíveis para avaliar o fomento ao cinema de sala?',
    'c2': 'O dado de entrada que um edital usa para selecionar projetos é determinante no tipo de desempenho verificado pelas obras fomentadas?',
    'c3': 'Qual é o papel da renúncia fiscal na política pública de fomento para salas de cinema?',
    'c4': 'Qual perfil de produtora o fomento público induziu?',
    'c5': 'As regras de distribuição dos recursos evitaram a concentração do fomento?',
    'c6': 'O que sobra para cada empresa é suficiente para ela existir, e por onde entra quem ainda está de fora?',
    'c7': 'Como reorganizar o fomento para que as empresas ganhem ritmo sem que a porta de entrada se feche?',
}


# ── fonte única de texto: seções do ensaio.md compartilhadas entre as páginas ──
# (o index NÃO duplica texto; lê a mesma seção que o ensaio/DOCX usam → nunca divergem)
import re as _re

# ── NÚMEROS-ÂNCORA DO ENSAIO → figura do painel (decisão Cainan 2026-08-10) ───
# No ensaio, passar o mouse sobre um destes números abre um popup com O GRÁFICO que
# mostra aquele número. O texto marcado NÃO é digitado aqui: vem de indicadores.json
# formatado por `fmt` — se o número mudar na base, muda no texto e a marcação segue
# casando. `scripts/22` exporta os specs em outputs/bases/popfigs.json; `scripts/21`
# embute só os usados. Entrada: (chave_do_indicador, formato, figura, legenda).
#   formato: 'n0' 'n1' 'n2' = casas decimais (pt-BR) · 'p0' = inteiro + %
#            'mil' = valor/1000 sem decimal · 'x2' = 2 casas (razão)
NUM_FIG = [
    ('obras_retorno',              'n0',  'f_serie',       'As 855 obras do universo de retorno na série anual da política.'),
    ('obras_aplicacao',            'n0',  'f_serie',       'O universo de aplicação — 985 obras com fomento efetivo entre 2014 e 2023.'),
    ('empresas_aplicacao',         'n0',  'f_lz',          'As produtoras do universo de aplicação, na curva que mostra como o fomento se distribui entre elas.'),
    ('retorno_dom',                'x2',  'f_c1',          'O retorno doméstico de referência, mecanismo a mecanismo.'),
    ('publico_mi',                 'n1',  'f_cob',         'Os espectadores observados, e a conversão de cada mecanismo por R$ mi.'),
    ('taxa_estreia',               'pf0', 'f_cob',         'A taxa de estreia em sala por mecanismo.'),
    ('pct_sinal_intl',             'p0',  'f_cober',       'A cobertura de cada sinal internacional sobre as 855 obras.'),
    ('n_festivais',                'n0',  'f_ipen',        'As obras com participação em festival, por mecanismo.'),
    ('n_lumiere',                  'n0',  'f_lstar',       'As obras com bilheteria na Europa e o alcance em idiomas.'),
    ('inst_renuncia_pura_ret_dom', 'x2',  'f_grup',        'O retorno doméstico por origem do dinheiro: a renúncia pura é a única que recupera em sala.'),
    ('inst_fsa_puro_ret_dom',      'x2',  'f_grup',        'O retorno doméstico por origem do dinheiro: o FSA puro no extremo oposto da renúncia.'),
    ('inst_renuncia_pura_pct_intl', 'p0', 'f_ren2',        'O perfil internacional por composição de financiamento.'),
    ('inst_fsa_puro_pct_intl',     'p0',  'f_ren2',        'O perfil internacional por composição de financiamento: o FSA puro circula mais.'),
    ('cat_dist_ret_dom',           'x2',  'f_roi_dom_cat', 'O retorno doméstico agregado por categoria de chamada.'),
    ('cat_fest_ret_dom',           'x2',  'f_roi_dom_cat', 'O retorno doméstico agregado por categoria: o critério de festival no piso.'),
    ('gini_fsa_produtora',         'x2',  'f_lz',          'A curva de Lorenz do FSA por produtora — a distância até a diagonal é este Gini.'),
    ('gini_bilheteria_obra',       'x2',  'f_gini',        'O Gini do fundo comparado ao do mercado: a bilheteria concentra muito mais.'),
    ('top10_share_fsa',            'p0',  'f_shareN',      'O share acumulado do FSA por número de produtoras.'),
    ('rj_sp_share',                'p0',  'f_uf',          'O público de filmes brasileiros por UF.'),
    ('produtoras_mediana_inv_anual', 'mil', 'f_ticket_hist', 'A distribuição das empresas por faixa de operação anual, com o custo fixo mínimo tracejado.'),
]


def num_texto(valor, fmt):
    """Formata o número-âncora exatamente como ele aparece no texto do ensaio."""
    if fmt == 'mil':
        return br(valor / 1000, 0)
    if fmt == 'p0':
        return br(valor, 0)
    if fmt == 'pf0':
        return br(valor * 100, 0)
    if fmt == 'x2':
        return br(valor, 2)
    return br(valor, int(fmt[1]))


def ensaio_md_secao(sid):
    """Devolve (titulo, blocks) da seção [sid] de site_src/ensaio.md.
    blocks: lista de ('p', txt) | ('li', txt) | ('nuvem', None)."""
    raw = open(os.path.join(SRC, 'ensaio.md'), encoding='utf-8').read()
    cur, lines = None, []
    for ln in raw.splitlines():
        m = _re.match(r'##\s*\[(\w+)\]\s*(.+)$', ln)
        if m:
            if cur == sid:
                break
            cur = m.group(1)
            if cur == sid:
                titulo = m.group(2).strip()
            continue
        if cur == sid:
            lines.append(ln)
    blocks, para = [], []

    def flush():
        if para:
            blocks.append(('p', ' '.join(para))); para.clear()
    for ln in lines:
        s = ln.rstrip()
        if s.strip() == '[NUVEM]':
            flush(); blocks.append(('nuvem', None))
        elif not s.strip():
            flush()
        elif s.lstrip().startswith('- '):
            flush(); blocks.append(('li', s.lstrip()[2:]))
        else:
            para.append(s.strip())
    flush()
    return titulo, blocks


def ensaio_md_titulos():
    """{sid: título} de todas as seções do ensaio.md (títulos dos cN = as perguntas,
    editáveis via DOCX → scripts/31)."""
    raw = open(os.path.join(SRC, 'ensaio.md'), encoding='utf-8').read()
    return {m.group(1): m.group(2).strip()
            for m in _re.finditer(r'^##\s*\[(\w+)\]\s*(.+)$', raw, flags=_re.M)}


def md_inline(t):
    t = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = _re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', t)
    return t


def blocks_to_html(blocks, nuvem_html=''):
    """Renderiza os blocks em HTML (p, ul, e o fragmento da nuvem no marcador)."""
    out, ul = [], []

    def flush_ul():
        if ul:
            out.append('<ul>' + ''.join(f'<li>{md_inline(i)}</li>' for i in ul) + '</ul>'); ul.clear()
    for kind, tx in blocks:
        if kind == 'li':
            ul.append(tx)
        elif kind == 'nuvem':
            flush_ul(); out.append(nuvem_html)
        else:
            flush_ul(); out.append(f'<p>{md_inline(tx)}</p>')
    flush_ul()
    return ''.join(out)


def ensure_site():
    """Garante site/ + assets (plotly.min.js copiado uma única vez do venv)."""
    os.makedirs(ASSETS, exist_ok=True)
    dst = os.path.join(ASSETS, 'plotly.min.js')
    if not os.path.exists(dst):
        src = os.path.join(BASE, '.venv', 'Lib', 'site-packages', 'plotly', 'package_data', 'plotly.min.js')
        shutil.copyfile(src, dst)
    return dst


def br(x, dec=1):
    """Número no padrão BR (1.234,5)."""
    return f"{x:,.{dec}f}".replace(',', '§').replace('.', ',').replace('§', '.')


def style(fig, h=440, title=None, ytitle=None, xtitle=None, showlegend=True):
    fig.update_layout(
        paper_bgcolor=SURF, plot_bgcolor=SURF,
        font=dict(family='Inter,system-ui,sans-serif', color=TXT, size=12),
        margin=dict(l=64, r=28, t=46 if title else 16, b=52), height=h,
        title=dict(text=title, font=dict(size=15, color=TXT), x=0.01) if title else None,
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=10.5), orientation='h', y=-0.18, x=0),
        showlegend=showlegend, hoverlabel=dict(font_size=12, font_family='Inter'))
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, title=xtitle, title_font_size=12, tickfont_size=11)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, title=ytitle, title_font_size=12, tickfont_size=11)
    return fig


_plot_n = [0]

_plot_ids = {}      # id(figura) → pid já emitido (ver DL abaixo)


def DL(fig):
    """Figura → embed LAZY: JSON no HTML + render só quando entra na viewport.
    Mantém a página leve (nada de plotly inline por figura).

    A MESMA figura pode aparecer em várias abas sem duplicar payload: na 2ª vez em
    diante sai só a <div>, apontando para o JSON já emitido (o loader resolve por
    `data-plot` → getElementById, então N divs podem compartilhar um spec)."""
    h = fig.layout.height or 440
    known = _plot_ids.get(id(fig))
    if known:
        return f'<div class="js-plot" data-plot="{known}" style="min-height:{h}px"></div>'
    _plot_n[0] += 1
    pid = f'pl{_plot_n[0]}'
    _plot_ids[id(fig)] = pid
    spec = pio.to_json(fig, validate=False)
    return (f'<div class="js-plot" data-plot="{pid}" style="min-height:{h}px"></div>'
            f'<script type="application/json" id="{pid}">{spec}</script>')


def fig_spec(fig):
    """Spec JSON cru da figura — usado pelo ensaio para os popups do hover."""
    return pio.to_json(fig, validate=False)


def stat(value, label, kind='inv'):
    return f'<div class="stat {kind}"><div class="v">{value}</div><div class="l">{label}</div></div>'


def stat_grid(cards):
    return '<div class="statgrid">' + ''.join(cards) + '</div>'


def epigrafe(quote, autor):
    return f'<blockquote class="epi">{quote}<cite>— {autor}</cite></blockquote>'


def tabela(headers, rows):
    th = ''.join(f'<th>{h}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    return (f'<div class="dtwrap"><table class="dtable"><thead><tr>{th}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def section(sid, kicker, title, intro, figs=(), takeaway=None, disc=None, repro_html=None,
            volta_href=None, volta_label='← voltar à alegação no ensaio'):
    h = [f'<section id="{sid}"><div class="kicker">{kicker}</div><h2>{title}</h2>{intro}']
    for frag, cap in figs:
        h.append(f'<div class="chart">{frag}</div>')
        if cap:
            h.append(f'<div class="cap">{cap}</div>')
    if takeaway:
        h.append(f'<div class="takeaway">{takeaway}</div>')
    if disc:
        h.append(f'<div class="disc">{disc}</div>')
    if repro_html:
        h.append(repro_html)
    if volta_href:
        h.append(f'<a class="plink" href="{volta_href}">{volta_label}</a>')
    h.append('</section>')
    return ''.join(h)


def metodologia(blocks, intro=''):
    inner = (f'<p class="mlead">{intro}</p>' if intro else '')
    for tit, cont in blocks:
        inner += f'<div class="mb"><div class="mbt">{tit}</div>{cont}</div>'
    return ('<details class="metodo" id="metodologia"><summary>'
            '<span class="msum">Metodologia &amp; auditoria</span>'
            '<span class="mhint">como estes números são calculados e onde estão os furos — clique para abrir e conferir</span>'
            f'</summary><div class="mbody">{inner}</div></details>')


def repro(tabelas=(), query=None, scripts=None, documental=None, nota=None):
    """Bloco 'Reproduza esta conta' — a ponte de cada evidência com o RIDAB.
    tabelas: nomes de tabelas RIDAB (chips → catálogo do portal);
    query: SQL DuckDB pronto (roda em qualquer máquina, sem baixar nada);
    scripts: passos consolidados neste repositório; documental: fontes citadas."""
    h = ['<details class="repro"><summary><span class="rsum">⟲ Reproduza esta conta</span>'
         '<span class="rhint">dados abertos (RIDAB) + o caminho exato do número</span></summary><div class="rbody">']
    if tabelas:
        chips = ''.join(f'<a class="rtab" href="{RIDAB_PORTAL}/datasets/" title="catálogo RIDAB">{t}</a>' for t in tabelas)
        h.append(f'<div class="rrow"><span class="rlab">Tabelas RIDAB</span><span>{chips}</span></div>')
    if query:
        h.append('<div class="rrow"><span class="rlab">DuckDB — direto da nuvem, sem baixar nada</span></div>'
                 f'<pre class="rsql">{query.strip()}</pre>')
    if scripts:
        h.append(f'<div class="rrow"><span class="rlab">Consolidação obra-a-obra (este repositório)</span>'
                 f'<span class="rtxt">{scripts}</span></div>')
    if documental:
        h.append(f'<div class="rrow"><span class="rlab">Camada documental</span><span class="rtxt">{documental}</span></div>')
    if nota:
        h.append(f'<div class="rnote">{nota}</div>')
    h.append(f'<div class="rfoot">Portal: <a href="{RIDAB_PORTAL}/explorar">RIDAB · Explorar (SQL no navegador)</a> · '
             f'dados: <a href="{RIDAB_HF}">Hugging Face</a> (CC-BY-4.0) · '
             f'prefixo dos parquets: <code>{RIDAB_HF_PATH}/…</code></div></div></details>')
    return ''.join(h)


FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='7' fill='%230b0d14'/%3E"
           "%3Crect x='6' y='16' width='4' height='9' rx='1' fill='%236c7bf7'/%3E"
           "%3Crect x='14' y='10' width='4' height='15' rx='1' fill='%2338bdf8'/%3E"
           "%3Crect x='22' y='6' width='4' height='19' rx='1' fill='%23a78bfa'/%3E%3C/svg%3E")

CSS_BASE = """
*{box-sizing:border-box;margin:0;padding:0}
:root{color-scheme:dark}
body{background:#0b0d14;color:#e2e8f0;font-family:'Inter',system-ui,sans-serif;line-height:1.6;font-size:15px;-webkit-font-smoothing:antialiased}
a{color:#6c7bf7}
.sitenav{position:sticky;top:0;z-index:50;background:rgba(11,13,20,.88);backdrop-filter:blur(10px);border-bottom:1px solid #1c2030}
.sitenav .in{max-width:1080px;margin:0 auto;padding:10px 24px;display:flex;align-items:center;gap:18px}
.sitenav .brand{font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#7b849a;text-decoration:none;margin-right:auto}
.sitenav .brand b{color:#6c7bf7}
.sitenav a.nv{font-size:13px;font-weight:600;color:#a8b0c0;text-decoration:none;padding:5px 12px;border-radius:16px;transition:.15s}
.sitenav a.nv:hover{color:#e2e8f0;background:#14171f}
.sitenav a.nv.on{color:#e2e8f0;background:#1a1f2e;border:1px solid #282d42}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px 90px}
header.page{padding:52px 0 30px;border-bottom:1px solid #282d42}
.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:#6c7bf7;font-weight:700;margin-bottom:10px}
h1{font-size:35px;font-weight:800;line-height:1.13;letter-spacing:-.6px;margin-bottom:14px}
.sub{font-size:16.5px;color:#9aa3b5;max-width:820px;line-height:1.6}
.toc{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px}
.toc a{font-size:12px;color:#a8b0c0;text-decoration:none;background:#14171f;border:1px solid #282d42;border-radius:20px;padding:5px 13px;transition:.15s}
.toc a:hover{border-color:#6c7bf7;color:#e2e8f0}
section{margin-top:56px}
.kicker{font-size:11px;text-transform:uppercase;letter-spacing:.13em;color:#6c7bf7;font-weight:800;margin-bottom:8px}
h2{font-size:24px;font-weight:800;letter-spacing:-.3px;margin-bottom:14px;line-height:1.22}
h2 em{font-style:italic}
.lead{font-size:16px;color:#cbd5e1;margin-bottom:10px}
p{color:#a8b0c0;margin-bottom:12px}
p strong,.lead strong,li strong{color:#e2e8f0;font-weight:700}
.chart{background:#14171f;border:1px solid #282d42;border-radius:12px;padding:14px 14px 6px;margin:18px 0 10px}
.cap{font-size:12.5px;color:#7b849a;margin:2px 4px 16px;border-left:2px solid #282d42;padding-left:12px}
.cap b{color:#a8b0c0}
.takeaway{background:linear-gradient(135deg,rgba(108,123,247,.10),transparent 70%);border:1px solid #282d42;border-left:3px solid #6c7bf7;border-radius:10px;padding:16px 18px;margin:16px 0;font-size:14.5px;color:#b7bfcf}
.takeaway b{color:#e2e8f0}
.disc{background:rgba(251,191,36,.05);border:1px solid rgba(251,191,36,.22);border-radius:10px;padding:14px 16px;margin:14px 0;font-size:13px;color:#a8b0c0}
.disc b{color:#fbbf24}
.warn{background:rgba(248,113,113,.06);border:1px solid rgba(248,113,113,.25);border-radius:10px;padding:16px 18px;margin-top:30px;font-size:13px;color:#a8b0c0}
.warn b{color:#f87171}
.warn a{color:#7b849a}
.statgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px;margin:20px 0}
.stat{background:#14171f;border:1px solid #282d42;border-radius:12px;padding:16px 16px 14px}
.stat .v{font-size:26px;font-weight:800;color:#e2e8f0;line-height:1.05;letter-spacing:-.5px}
.stat .v small{font-size:14px;font-weight:700;color:#7b849a}
.stat .l{font-size:11.5px;color:#7b849a;margin-top:6px;line-height:1.35}
.stat.inv{border-left:3px solid #6c7bf7}.stat.res{border-left:3px solid #34d399}
.dtwrap{overflow-x:auto;margin:18px 0;border:1px solid #282d42;border-radius:10px}
.dtable{border-collapse:collapse;width:100%;font-size:13px}
.dtable th{text-align:left;padding:9px 13px;color:#7b849a;font-weight:700;border-bottom:1px solid #282d42;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;white-space:nowrap;background:#101320}
.dtable td{padding:8px 13px;border-bottom:1px solid #14171f;color:#cbd5e1}
.dtable tr:last-child td{border-bottom:0}
.dtable tr:hover td{background:#12151e}
.mtag{display:inline-block;font-size:11px;padding:2px 9px;border-radius:10px;margin:3px 5px 3px 0;font-weight:600;white-space:nowrap}
.mtag.ok{background:rgba(52,211,153,.10);color:#34d399;border:1px solid rgba(52,211,153,.3)}
.mtag.warn{background:rgba(251,191,36,.10);color:#fbbf24;border:1px solid rgba(251,191,36,.3)}
.plink,.evchip{display:inline-flex;align-items:center;gap:8px;margin:18px 8px 4px 0;font-size:13px;font-weight:700;color:#6c7bf7;text-decoration:none;background:#12151e;border:1px solid #282d42;border-radius:22px;padding:9px 17px;transition:.15s}
.plink:hover,.evchip:hover{border-color:#6c7bf7;background:rgba(108,123,247,.10)}
.plink span,.evchip span{transition:.15s}
.plink:hover span,.evchip:hover span{transform:translateX(3px)}
.epi{border-left:3px solid #6c7bf7;margin:26px 0 0;padding:4px 0 4px 22px;font-size:18px;font-style:italic;color:#cbd5e1;line-height:1.55;letter-spacing:-.2px}
.epi cite{display:block;margin-top:9px;font-size:13px;font-style:normal;color:#7b849a;letter-spacing:0}
.metodo{background:#0e1118;border:1px solid #282d42;border-radius:12px;margin:28px 0 0;overflow:hidden}
.metodo>summary{list-style:none;cursor:pointer;padding:15px 20px;display:flex;flex-direction:column;gap:3px;background:#12151e;transition:.15s}
.metodo>summary::-webkit-details-marker{display:none}
.metodo>summary:hover{background:#161a25}
.msum{font-size:14px;font-weight:700;color:#e2e8f0}
.metodo[open]>summary .msum::before{content:"▾  "}
.metodo:not([open])>summary .msum::before{content:"▸  "}
.mhint{font-size:12px;color:#7b849a}
.mbody{padding:4px 20px 20px}
.mlead{font-size:13.5px;color:#cbd5e1;margin:14px 0 0}
.mb{margin-top:16px}
.mbt{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#6c7bf7;font-weight:700;margin-bottom:6px}
.mb p{font-size:13.5px;margin-bottom:7px}
.mb ul{margin:4px 0 8px 18px}
.mb li{font-size:13.5px;color:#a8b0c0;margin-bottom:5px}
code,.mb code{background:#1c2030;padding:1px 6px;border-radius:4px;font-size:12.5px;color:#cbd5e1;font-family:ui-monospace,'Cascadia Mono',monospace}
.repro{background:#0d1420;border:1px solid #1f2b45;border-radius:12px;margin:18px 0 6px;overflow:hidden}
.repro>summary{list-style:none;cursor:pointer;padding:13px 18px;display:flex;flex-direction:column;gap:2px;transition:.15s}
.repro>summary::-webkit-details-marker{display:none}
.repro>summary:hover{background:#111a2b}
.rsum{font-size:13.5px;font-weight:700;color:#38bdf8}
.rhint{font-size:12px;color:#7b849a}
.rbody{padding:2px 18px 16px;border-top:1px solid #1f2b45}
.rrow{margin-top:12px;display:flex;flex-direction:column;gap:6px}
.rlab{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:#7b849a;font-weight:700}
.rtab{display:inline-block;font-size:12px;font-family:ui-monospace,monospace;color:#9fd7f5;background:#0f1b2d;border:1px solid #1f2b45;border-radius:6px;padding:2px 9px;margin:2px 6px 2px 0;text-decoration:none}
.rtab:hover{border-color:#38bdf8}
.rtxt{font-size:13px;color:#a8b0c0}
.rsql{background:#0a0f1a;border:1px solid #1f2b45;border-radius:8px;padding:12px 14px;font-size:12px;line-height:1.55;color:#c7d7ee;overflow-x:auto;font-family:ui-monospace,'Cascadia Mono',monospace;white-space:pre}
.rnote{margin-top:12px;font-size:12.5px;color:#7b849a}
.rfoot{margin-top:14px;padding-top:12px;border-top:1px solid #1f2b45;font-size:12px;color:#7b849a}
.rfoot a{color:#38bdf8;text-decoration:none}
footer.site{margin-top:90px;padding-top:26px;border-top:1px solid #282d42;font-size:13.5px;color:#7b849a;line-height:1.65}
footer.site a{color:#6c7bf7;text-decoration:none}
@media(max-width:720px){h1{font-size:27px}h2{font-size:21px}.sitenav .in{padding:10px 16px;gap:8px}.wrap{padding:0 18px 70px}}
"""

LAZY_JS = """
(function(){
  function start(){
    var els = [].slice.call(document.querySelectorAll('.js-plot'));
    var queue = els.slice();
    function draw(el){
      if (el.dataset.done) return;
      el.dataset.done = '1';
      try{
        var spec = JSON.parse(document.getElementById(el.dataset.plot).textContent);
        Plotly.newPlot(el, spec.data, spec.layout, {displayModeBar:false, responsive:true});
      }catch(e){ el.innerHTML = '<div style="color:#7b849a;font-size:13px;padding:30px">gr\\u00e1fico indispon\\u00edvel</div>'; }
    }
    // prioridade: o que entra na viewport desenha na hora
    if ('IntersectionObserver' in window && window.innerHeight > 0){
      var io = new IntersectionObserver(function(es){
        es.forEach(function(e){ if(e.isIntersecting){ io.unobserve(e.target); draw(e.target); } });
      }, {rootMargin:'700px 0px'});
      els.forEach(function(el){ io.observe(el); });
    }
    // garantia: fila progressiva em idle desenha TUDO, mesmo sem scroll/IO
    var idle = window.requestIdleCallback || function(f){ setTimeout(f, 150); };
    function tick(){
      var el = queue.shift();
      while (el && el.dataset.done) el = queue.shift();
      if (!el) return;
      draw(el);
      idle(tick);
    }
    idle(tick);
  }
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start);
})();
"""


def sitenav(active):
    def nv(href, label, key):
        on = ' on' if key == active else ''
        return f'<a class="nv{on}" href="{href}">{label}</a>'
    return ('<nav class="sitenav"><div class="in">'
            '<a class="brand" href="index.html">Fomento <b>Audiovisual</b></a>'
            + nv('index.html', 'Início', 'index')
            + nv('ensaio.html', 'Análise', 'ensaio')
            + nv('evidencias.html', 'Painel', 'evidencias')
            + '</div></nav>')


def html_shell(fname, title, desc, eyebrow, h1, sub, toc_links, body, footer='',
               active='index', plotly=False, serif=False, extra_css=''):
    """Escreve site/<fname>. plotly=True inclui assets/plotly.min.js + lazy loader.
    serif=True carrega a Newsreader (usada no corpo do ensaio)."""
    toc = ''.join(f'<a href="{href}">{label}</a>' for href, label in toc_links)
    fonts = 'family=Inter:wght@400;500;600;700;800'
    if serif:
        fonts += '&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500'
    plotly_head = '<script src="assets/plotly.min.js" defer></script>' if plotly else ''
    lazy = f'<script>{LAZY_JS}</script>' if plotly else ''
    html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="article">
<link rel="icon" href="{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?{fonts}&display=swap" rel="stylesheet">
{plotly_head}
<style>{CSS_BASE}{extra_css}</style></head><body>
{sitenav(active)}
<div class="wrap">
<header class="page">
  <div class="eyebrow">{eyebrow}</div>
  <h1>{h1}</h1>
  <p class="sub">{sub}</p>
  <div class="toc">{toc}</div>
</header>
{body}
{footer}
</div>
{lazy}
</body></html>"""
    ensure_site()
    out = os.path.join(SITE, fname)
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(html)
    return out
