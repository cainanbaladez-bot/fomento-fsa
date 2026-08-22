# -*- coding: utf-8 -*-
"""
27_uso.py — PAINEL DE USO (privado): quem leu o quê, e o que baixaram do RIDAB.

Não vai para o site. `outputs/uso/` e `.env.analytics` estão no .gitignore — nada
disso é versionado nem publicado. O painel público (site/evidencias.html) é sobre o
fomento; este é sobre o próprio trabalho.

DOIS MODOS
  · `python scripts/27_uso.py`            escreve outputs/uso/uso.html e sai
  · `python scripts/27_uso.py --servir`   sobe http://localhost:8790 e fica de pé;
                                          a página tem botão "atualizar", que refaz a
                                          coleta na hora. É o modo de deixar fixo no
                                          navegador (a tarefa RIDAB-PainelUso sobe
                                          isso sozinha no logon).

O QUE ELE MOSTRA
  Tudo o que o GoatCounter tem — visitas por dia, referências, países, navegadores,
  sistemas, telas, campanhas — mais o que ele NÃO sabe mostrar: os eventos do site
  traduzidos. Onde o painel dele diz `/trecho/h_sequencias`, aqui aparece o título do
  gráfico, ordenado por quantas vezes foi aberto. Junta ainda a série de downloads do
  RIDAB no Hugging Face, capturada pelo scripts/26.

CREDENCIAL  — `.env.analytics` na raiz do projeto (gitignored):
    GOATCOUNTER_SITE=fsa-fomento
    GOATCOUNTER_TOKEN=<token de Settings → API, permissão de ler estatísticas>
Sem token o painel monta a parte do Hugging Face e avisa o que falta.
"""
import os
import re
import sys
import csv
import json
import shutil
import datetime as dt
import urllib.request
import urllib.error

import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import site_base as S  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASES = os.path.join(BASE, 'outputs', 'bases')
MET = os.path.join(BASE, 'outputs', 'metricas')
OUT = os.path.join(BASE, 'outputs', 'uso')
DIAS = 90
PORTA = 8790

# blocos de contexto do GoatCounter. O nome do endpoint não está documentado na
# referência pública, então cada um é tentado e o que não responder é ignorado.
BLOCOS = [('toprefs', 'De onde vieram', S.CYAN),
          ('locations', 'Países', S.GREEN),
          ('browsers', 'Navegadores', S.ACCENT),
          ('systems', 'Sistemas', S.PURPLE),
          ('sizes', 'Tamanho de tela', S.GOLD),
          ('campaigns', 'Campanhas', S.CORAL),
          ('languages', 'Idiomas', '#7b849a')]


# Sob `pythonw` (é assim que o atalho sobe o servidor, para não abrir janela de
# console) `sys.stdout` é None e qualquer print derruba o processo em silêncio —
# foi o que aconteceu na primeira versão do .bat. Aqui a saída vai para um log.
if sys.stdout is None or sys.stderr is None:
    os.makedirs(OUT, exist_ok=True)
    _log = open(os.path.join(OUT, 'servidor.log'), 'a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = _log
    print(f'== {dt.datetime.now():%d/%m/%Y %H:%M:%S} · painel de uso iniciado sem console')
else:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass


def brn(x, d=0):
    try:
        return f'{float(x):,.{d}f}'.replace(',', '§').replace('.', ',').replace('§', '.')
    except (TypeError, ValueError):
        return '—'


def env():
    p = os.path.join(BASE, '.env.analytics')
    cfg = {}
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8'):
            if '=' in ln and not ln.strip().startswith('#'):
                k, _, v = ln.partition('=')
                cfg[k.strip()] = v.strip().strip('"\'')
    return cfg


def gc(endpoint, token, site, **params):
    if not token:
        return None
    url = f'https://{site}.goatcounter.com/api/v0/{endpoint}'
    if params:
        url += '?' + '&'.join(f'{k}={v}' for k, v in params.items() if v not in (None, ''))
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code not in (400, 404):        # 400/404 = bloco que não existe: silêncio
            print(f'  ! GoatCounter {endpoint}: HTTP {e.code}')
        return None
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f'  ! GoatCounter {endpoint}: {e}')
        return None


# ── de id técnico para nome humano ────────────────────────────────────────────
def carrega_titulos():
    titulos, secao = {}, {}
    for nome in ('hoverfigs.json', 'hoverfigs2.json', 'painelfigs.json'):
        p = os.path.join(BASES, nome)
        if os.path.exists(p):
            for k, v in json.load(open(p, encoding='utf-8')).items():
                titulos[k] = v['titulo']
                secao[k] = v.get('secao', 'c1')
    return titulos, secao


TITULOS, SECAO = carrega_titulos()
PERGUNTA = {c[0]: c[2] for c in S.CLAIMS}

# ── OS TRÊS PRODUTOS ──────────────────────────────────────────────────────────
# Os três sites dividem o mesmo GoatCounter e se distinguem pelo caminho da página.
# Cada um vira uma ripa no painel, com os seus próprios números.
PRODUTOS = [
    {'id': 'fsa', 'nome': 'Análise do fomento · FSA 2014–2023', 'cor': S.CYAN,
     'prefixo': '/fomento-fsa', 'url': 'https://cainanbaladez-bot.github.io/fomento-fsa/',
     'o_que': 'o ensaio e o painel de dados',
     'paginas': {'/ensaio.html': 'Análise (o texto)', '/evidencias.html': 'Painel de dados',
                 '/index.html': 'Início', '/': 'Início'}},
    {'id': 'ridab', 'nome': 'RIDAB · repositório de dados', 'cor': S.GREEN,
     'prefixo': '/riab', 'url': 'https://riabr-dados.github.io/riab/',
     'o_que': 'o portal dos dados abertos',
     'paginas': {'/': 'Início do portal', '/datasets/': 'Datasets', '/explorar/': 'Explorar',
                 '/transformar/': 'Transformar (cruzar bases)', '/conexoes/': 'Conexões',
                 '/consulta/': 'Consulta', '/mural/': 'Mural', '/sobre/': 'Sobre',
                 '/brasil-no-mundo/': 'Brasil no mundo'}},
    {'id': 'mostra', 'nome': 'Planejador da 49ª Mostra', 'cor': S.GOLD,
     'prefixo': '/planejador-mostrasp', 'url': 'https://cainanbaladez-bot.github.io/planejador-mostrasp/',
     'o_que': 'a agenda pessoal do festival',
     'paginas': {'/': 'Planejador', '/index.html': 'Planejador'}},
]
ABA_NOME = {'g_rankings': 'Rankings', 'g_chamadas': 'Chamadas', 'dados': 'Dados abertos'}


def humano(path):
    """Classifica o caminho: evento do ensaio, ou página de um dos três produtos."""
    p = path if path.startswith('/') else '/' + path
    m = re.match(r'^/trecho/(.+)$', p)
    if m:
        gid = m.group(1)
        sec = SECAO.get(gid, '')
        pref = f'P{sec[1:]} · ' if sec.startswith('c') else ''
        return 'trecho', pref + TITULOS.get(gid, gid), gid, 'fsa'
    m = re.match(r'^/aba/(?:q_)?(.+)$', p)
    if m:
        aid = m.group(1)
        nome = (f'Pergunta {aid[1:]} · {PERGUNTA[aid]}' if aid in PERGUNTA
                else ABA_NOME.get(aid, aid))
        return 'aba', nome, aid, 'fsa'
    for pr in PRODUTOS:
        if p == pr['prefixo'] or p.startswith(pr['prefixo'] + '/'):
            resto = p[len(pr['prefixo']):] or '/'
            return 'pagina', pr['paginas'].get(resto, resto), p, pr['id']
    return 'pagina', p, p, '?'


# ── coleta ────────────────────────────────────────────────────────────────────
def coleta():
    cfg = env()
    site = cfg.get('GOATCOUNTER_SITE', 'fsa-fomento')
    token = cfg.get('GOATCOUNTER_TOKEN', '')
    hoje = dt.date.today()
    ini = (hoje - dt.timedelta(days=DIAS)).isoformat() + 'T00:00:00Z'
    fim = hoje.isoformat() + 'T23:00:00Z'

    total = gc('stats/total', token, site, start=ini, end=fim)
    hits = gc('stats/hits', token, site, start=ini, end=fim, limit=200, group='day')

    linhas, serie = [], {}
    for h in ((hits or {}).get('hits') or []):
        tipo, nome, ident, prod = humano(h.get('path', ''))
        dia = {x['day']: (x.get('daily') or 0) for x in (h.get('stats') or [])}
        linhas.append({'tipo': tipo, 'nome': nome, 'id': ident, 'produto': prod,
                       'views': h.get('count') or 0, 'dia': dia})
    # a série diária sai do /stats/total, que já vem dia a dia e não some quando
    # ainda não há caminho nenhum registrado (o /stats/hits vem vazio nesse caso)
    for d in ((total or {}).get('stats') or []):
        serie[d['day']] = d.get('daily') or 0

    contexto = []
    for page, rotulo, cor in BLOCOS:
        r = gc(f'stats/{page}', token, site, start=ini, end=fim, limit=10)
        itens = (r or {}).get('stats') or []
        itens = [{'nome': (i.get('name') or '(desconhecido)'), 'views': i.get('count') or 0}
                 for i in itens if (i.get('count') or 0) > 0]
        if itens:
            contexto.append((rotulo, cor, itens[:8]))

    hf = []
    hf_p = os.path.join(MET, 'hf_ridab.csv')
    if os.path.exists(hf_p):
        hf = list(csv.DictReader(open(hf_p, encoding='utf-8-sig')))

    if linhas:                       # retrato do dia, para a série sobreviver ao GoatCounter
        os.makedirs(MET, exist_ok=True)
        snap = os.path.join(MET, 'goatcounter_paths.csv')
        ja = []
        if os.path.exists(snap):
            ja = [r for r in csv.DictReader(open(snap, encoding='utf-8-sig'))
                  if r.get('coletado_em', '')[:10] != hoje.isoformat()]
        cols = ['coletado_em', 'janela_dias', 'produto', 'tipo', 'id', 'nome', 'views']
        with open(snap, 'w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(ja + [{'coletado_em': hoje.isoformat(), 'janela_dias': DIAS,
                               'produto': r.get('produto', ''), 'tipo': r['tipo'],
                               'id': r['id'], 'nome': r['nome'], 'views': r['views']}
                              for r in linhas])
    return {'site': site, 'token': bool(token), 'linhas': linhas, 'serie': serie,
            'total': total or {}, 'contexto': contexto, 'hf': hf}


# ── figuras ───────────────────────────────────────────────────────────────────
def base_fig(fig, h=300, legend=False, ytitle=None):
    fig.update_layout(paper_bgcolor='#12151e', plot_bgcolor='#12151e',
                      font=dict(family='Inter,system-ui,sans-serif', color=S.TXT, size=11.5),
                      margin=dict(l=54, r=16, t=12, b=38), height=h, showlegend=legend,
                      hoverlabel=dict(font_size=11.5, font_family='Inter'))
    fig.update_xaxes(gridcolor=S.GRID, zerolinecolor=S.GRID, linecolor=S.GRID, tickfont_size=10.5)
    fig.update_yaxes(gridcolor=S.GRID, zerolinecolor=S.GRID, linecolor=S.GRID, title=ytitle,
                     title_font_size=11, tickfont_size=10.5)
    return fig


def fig_html(fig, pid):
    return (f'<div class="js-plot" data-plot="{pid}" style="min-height:{fig.layout.height}px"></div>'
            f'<script type="application/json" id="{pid}">{fig.to_json()}</script>')


def rank_html(itens, cor, vazio, mostrar_pct=False):
    if not itens:
        return f'<div class="vazio">{vazio}</div>'
    mx = max(i['views'] for i in itens) or 1
    tot = sum(i['views'] for i in itens) or 1
    out = []
    for i in itens:
        larg = 100 * i['views'] / mx
        val = f'{brn(i["views"])}' + (f' <small>{100 * i["views"] / tot:.0f}%</small>'
                                      if mostrar_pct else '')
        out.append(f'<div class="rk"><div class="rk-l"><span class="rk-n">{i["nome"]}</span>'
                   f'<span class="rk-v">{val}</span></div>'
                   f'<div class="rk-b"><i style="width:{larg:.1f}%;background:{cor}"></i></div></div>')
    return ''.join(out)


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0d14;color:#e2e8f0;font-family:Inter,system-ui,sans-serif;padding:0 0 70px}
.top{position:sticky;top:0;z-index:20;background:rgba(11,13,20,.94);backdrop-filter:blur(10px);
     border-bottom:1px solid #1c2030;padding:13px 30px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.top h1{font-size:18px;font-weight:800;letter-spacing:-.3px}
.priv{font-size:9.5px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#fbbf24;
      border:1px solid #5b4413;background:#241b0c;border-radius:20px;padding:3px 9px}
.quando{font-size:11.5px;color:#7b849a;margin-left:auto}
.btn{background:#1a2338;border:1px solid #2a3a5e;color:#7dd3fc;border-radius:20px;padding:6px 15px;
     font-size:12.5px;font-weight:700;text-decoration:none;cursor:pointer;transition:.14s;white-space:nowrap}
.btn:hover{background:#22304d;color:#bae6fd;border-color:#38bdf8}
.btn.load{opacity:.55;pointer-events:none}
main{padding:22px 30px 0}
.sub{color:#8f9ab3;font-size:13px;margin-bottom:20px;max-width:940px;line-height:1.65}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:12px;margin-bottom:22px}
.kpi{background:#12151e;border:1px solid #232838;border-top:2px solid var(--c);border-radius:10px;padding:13px 15px}
.kpi .v{font-size:26px;font-weight:800;letter-spacing:-.6px;line-height:1}
.kpi .l{font-size:11px;color:#7b849a;margin-top:6px;line-height:1.4}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:14px}
.ripa{background:#12151e;border:1px solid #232838;border-left:4px solid var(--c);border-radius:12px;
      padding:16px 18px 14px;margin-bottom:16px}
.ripa-hd{display:flex;align-items:flex-start;gap:20px;flex-wrap:wrap;padding-bottom:13px;
         margin-bottom:14px;border-bottom:1px solid #1c2030}
.ripa-hd h2{font-size:17px;font-weight:800;letter-spacing:-.2px;color:#eef1f6;margin:0}
.ripa-sub{font-size:11.5px;color:#7b849a;margin-top:4px}
.ripa-sub a{color:var(--c);text-decoration:none;font-weight:600}
.ripa-kpi{display:flex;gap:26px;margin-left:auto}
.ripa-kpi div{text-align:right}
.ripa-kpi b{display:block;font-size:23px;font-weight:800;letter-spacing:-.5px;color:#e8ecf4;line-height:1}
.ripa-kpi span{display:block;font-size:10.5px;color:#7b849a;margin-top:4px}
.ripa-corpo{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px}
.col h3{font-size:12px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;
        color:#8f9ab3;margin-bottom:5px}
.col.serie{min-width:230px}
.mini{font-size:13px;color:#cbd5e1;line-height:1.7;background:#0f1218;border:1px solid #1c2030;
      border-radius:9px;padding:10px 12px}
.mini b{color:#e8ecf4;font-size:15px}
.dim{color:#6d7689;font-size:11px}
.card{background:#12151e;border:1px solid #232838;border-radius:12px;padding:15px 16px 13px;min-width:0}
.card h2{font-size:14.5px;font-weight:700;margin-bottom:4px}
.card .h{font-size:11.5px;color:#7b849a;margin-bottom:13px;line-height:1.5}
.full{grid-column:1/-1}
.sec{grid-column:1/-1;font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:#6c7bf7;
     font-weight:800;margin:22px 0 -2px;padding-top:14px;border-top:1px solid #1c2030}
.rk{margin-bottom:9px}
.rk-l{display:flex;gap:10px;align-items:baseline;font-size:12.5px;margin-bottom:3px}
.rk-n{flex:1;color:#cbd5e1;line-height:1.4;word-break:break-word}
.rk-v{font-weight:800;font-variant-numeric:tabular-nums;color:#e8ecf4;white-space:nowrap}
.rk-v small{font-weight:600;color:#7b849a;font-size:10.5px;margin-left:3px}
.rk-b{height:5px;background:#1a1f2c;border-radius:3px;overflow:hidden}
.rk-b i{display:block;height:100%;border-radius:3px}
.vazio{color:#5b647c;font-size:12.5px;font-style:italic;padding:12px 0}
.aviso{background:#241b0c;border:1px solid #5b4413;border-left:3px solid #fbbf24;border-radius:10px;
       padding:13px 16px;margin-bottom:20px;font-size:13px;color:#f3d9a0;line-height:1.65}
.aviso b{color:#fbbf24}.aviso a{color:#fbbf24}
.aviso code{background:#0f1218;border:1px solid #3a2f14;border-radius:5px;padding:1px 6px;font-size:12px}
footer{margin:28px 30px 0;color:#5b647c;font-size:11.5px;line-height:1.7;border-top:1px solid #1c2030;padding-top:14px}
"""

JS = """
(function(){
  function draw(el){
    try{ var s=JSON.parse(document.getElementById(el.dataset.plot).textContent);
      Plotly.newPlot(el, s.data, s.layout, {displayModeBar:false, responsive:true});
    }catch(e){}
  }
  function go(){ document.querySelectorAll('.js-plot').forEach(draw); }
  if(document.readyState==='complete') go(); else window.addEventListener('load', go);
  var b=document.getElementById('btn-atualizar');
  if(b) b.addEventListener('click', function(){ b.classList.add('load'); b.textContent='coletando…'; });
})();
"""


def spark(dias, valores, cor, pid, h=110):
    """Fita fina de visitas por dia, para ir dentro da ripa do produto."""
    f = go.Figure(go.Bar(x=dias, y=valores, marker_color=cor,
                         hovertemplate='%{x}: %{y} visita(s)<extra></extra>'))
    f.update_layout(paper_bgcolor='#12151e', plot_bgcolor='#12151e', height=h,
                    margin=dict(l=34, r=8, t=6, b=22), showlegend=False,
                    font=dict(family='Inter,system-ui,sans-serif', color=S.TXT, size=10),
                    hoverlabel=dict(font_size=11, font_family='Inter'))
    f.update_xaxes(showgrid=False, linecolor=S.GRID, tickfont_size=9)
    f.update_yaxes(gridcolor='#1a1f2c', zerolinecolor=S.GRID, tickfont_size=9,
                   rangemode='tozero', nticks=3)
    return fig_html(f, pid)


def monta_html(d, servidor=False):
    linhas, serie, total, hf = d['linhas'], d['serie'], d['total'], d['hf']
    dias = sorted(serie) if serie else []

    # ── as três ripas ─────────────────────────────────────────────────────────
    ripas = []
    for pr in PRODUTOS:
        do_prod = [r for r in linhas if r.get('produto') == pr['id']]
        pags = sorted([r for r in do_prod if r['tipo'] == 'pagina'], key=lambda r: -r['views'])
        visitas = sum(r['views'] for r in pags)
        por_dia = [sum(r['dia'].get(dia, 0) for r in pags) for dia in dias]
        ativos = sum(1 for v in por_dia if v)

        # o que cada produto tem de próprio, além das páginas
        extra = ''
        if pr['id'] == 'fsa':
            trechos = sorted([r for r in do_prod if r['tipo'] == 'trecho'],
                             key=lambda r: -r['views'])[:12]
            abas = sorted([r for r in do_prod if r['tipo'] == 'aba'],
                          key=lambda r: -r['views'])[:8]
            extra = (f'<div class="col"><h3>Passagens abertas no texto</h3>'
                     f'<div class="h">O gráfico que a pessoa quis conferir por conta própria.</div>'
                     f'{rank_html(trechos, S.PURPLE, "Ninguém abriu um trecho ainda.")}</div>'
                     f'<div class="col"><h3>Abas do painel</h3>'
                     f'<div class="h">Qual pergunta puxou gente para os dados.</div>'
                     f'{rank_html(abas, S.CYAN, "Nenhuma aba visitada ainda.")}</div>')
        elif pr['id'] == 'ridab' and hf:
            u = hf[-1]
            extra = (f'<div class="col"><h3>Downloads no Hugging Face</h3>'
                     f'<div class="h">Ressalva: o portal lê os parquets direto de lá, então '
                     f'visita ao portal também vira download — e o DuckDB lê por faixas, então '
                     f'uma visita pode gerar mais de uma requisição.</div>'
                     f'<div class="mini"><b>{brn(u["downloads_total"])}</b> acumulados · '
                     f'<b>{brn(u["downloads_30d"])}</b> nos últimos 30 dias · '
                     f'{brn(u["likes"])} likes<br><span class="dim">série de {len(hf)} '
                     f'ponto(s), capturada todo dia pelo scripts/26</span></div></div>')
        elif pr['id'] == 'mostra':
            extra = ('<div class="col"><h3>Nota do app</h3>'
                     '<div class="h">O Planejador é um PWA: quem instalou abre do cache e pode '
                     'usar sem internet, e nesse caso a visita não chega ao contador. O número '
                     'aqui é piso, mais ainda que nos outros dois.</div></div>')

        ripas.append(f"""
<section class="ripa" style="--c:{pr['cor']}">
  <div class="ripa-hd">
    <div>
      <h2>{pr['nome']}</h2>
      <div class="ripa-sub">{pr['o_que']} · <a href="{pr['url']}" target="_blank">{pr['prefixo']}/</a></div>
    </div>
    <div class="ripa-kpi">
      <div><b>{brn(visitas)}</b><span>visitas</span></div>
      <div><b>{brn(len(pags))}</b><span>páginas vistas</span></div>
      <div><b>{brn(ativos)}</b><span>dias com acesso</span></div>
    </div>
  </div>
  <div class="ripa-corpo">
    <div class="col serie">
      <h3>Visitas por dia</h3>
      {spark(dias, por_dia, pr['cor'], 'sp-' + pr['id']) if dias else '<div class="vazio">sem série ainda</div>'}
    </div>
    <div class="col"><h3>Páginas</h3>
      {rank_html(pags[:10], pr['cor'], 'Nenhuma visita ainda.')}</div>
    {extra}
  </div>
</section>""")

    # ── contexto, comum aos três ──────────────────────────────────────────────
    ctx = ''.join(f'<div class="card"><h2>{rot}</h2>{rank_html(it, cor, "—", True)}</div>'
                  for rot, cor, it in d['contexto'])

    tot_geral = total.get('total', 0)
    tot_ev = total.get('total_events', 0)
    sem_prod = [r for r in linhas if r.get('produto') == '?']

    aviso = ''
    if not d['token']:
        aviso = ('<div class="aviso"><b>Falta o token da API.</b> Crie em '
                 f'<a href="https://{d["site"]}.goatcounter.com/user/api">'
                 f'{d["site"]}.goatcounter.com → API</a> e escreva em <code>.env.analytics</code>: '
                 f'<code>GOATCOUNTER_SITE={d["site"]}</code> e <code>GOATCOUNTER_TOKEN=…</code></div>')
    elif not tot_geral:
        aviso = ('<div class="aviso"><b>Nenhum acesso no período.</b> O token funciona; o '
                 'GoatCounter só não recebeu dado. Lembre que localhost não conta e que os '
                 'seus IPs e navegadores marcados são ignorados de propósito.</div>')
    if sem_prod:
        aviso += ('<div class="aviso"><b>Caminhos fora dos três produtos:</b> '
                  + ', '.join(f'<code>{r["id"]}</code>' for r in sem_prod[:6])
                  + '. Se for site novo, me diga para eu acrescentar a ripa dele.</div>')

    botao = ('<a class="btn" id="btn-atualizar" href="/atualizar">↻ atualizar agora</a>'
             if servidor else '')

    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Uso · três produtos</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="plotly.min.js" defer></script>
<style>{CSS}</style></head><body>
<div class="top"><h1>Quem leu o quê</h1><span class="priv">privado</span>
  <span class="quando">{brn(tot_geral)} visitas e {brn(tot_ev)} eventos em {DIAS} dias ·
  coletado em {dt.datetime.now().strftime('%d/%m/%Y às %H:%M')}</span>
  {botao}</div>
<main>
{aviso}
{''.join(ripas)}
<div class="sec">De onde vem e em que abrem — os três somados</div>
<div class="grid">{ctx or '<div class="card"><div class="vazio">Sem dado de contexto ainda.</div></div>'}</div>
</main>
<footer>
Arquivo privado em <code>outputs/uso/</code> (no .gitignore, com <code>noindex</code>).
Os três sites dividem o mesmo GoatCounter e se separam pelo caminho da página.<br>
GoatCounter sem cookie, com os seus IPs filtrados e os navegadores marcados por
<code>#toggle-goatcounter</code> · Hugging Face <code>riabr-dados/riab</code>.<br>
Bloqueador de anúncio derruba parte da medição, e o Planejador funciona offline:
trate tudo como piso, não como censo.
</footer>
<script>{JS}</script>
</body></html>"""


def escreve(html):
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, 'plotly.min.js')
    if not os.path.exists(dst):
        shutil.copyfile(os.path.join(BASE, 'site', 'assets', 'plotly.min.js'), dst)
    p = os.path.join(OUT, 'uso.html')
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(html)
    return p


def resumo(d):
    print(f'  visitas: {brn(d["total"].get("total", 0))} · '
          f'trechos abertos: {brn(sum(r["views"] for r in d["linhas"] if r["tipo"] == "trecho"))} · '
          f'caminhos: {len(d["linhas"])} · blocos de contexto: {len(d["contexto"])}')
    print(f'  Hugging Face: {len(d["hf"])} ponto(s) na série')
    if not d['token']:
        print('  ! sem GOATCOUNTER_TOKEN em .env.analytics — os blocos de acesso saem vazios')


def servir():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    estado = {'html': '', 'quando': None}

    def atualiza():
        d = coleta()
        estado['html'] = monta_html(d, servidor=True)
        estado['quando'] = dt.datetime.now()
        escreve(estado['html'])
        resumo(d)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _envia(self, corpo, tipo='text/html; charset=utf-8', code=200):
            b = corpo if isinstance(corpo, bytes) else corpo.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', tipo)
            self.send_header('Content-Length', str(len(b)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            caminho = self.path.split('?')[0]
            if caminho == '/atualizar':
                print(f'[{dt.datetime.now():%H:%M:%S}] atualizando…')
                atualiza()
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                return
            if caminho.endswith('plotly.min.js'):
                with open(os.path.join(OUT, 'plotly.min.js'), 'rb') as fh:
                    self._envia(fh.read(), 'application/javascript')
                return
            if caminho in ('/', '/uso.html'):
                # recoleta sozinho se o retrato tiver mais de 10 minutos
                if not estado['quando'] or \
                        (dt.datetime.now() - estado['quando']).total_seconds() > 600:
                    atualiza()
                self._envia(estado['html'])
                return
            self._envia('não encontrado', 'text/plain; charset=utf-8', 404)

    atualiza()
    srv = ThreadingHTTPServer(('127.0.0.1', PORTA), H)
    print(f'\nPainel de uso em http://localhost:{PORTA}  (Ctrl+C para parar)')
    print('  a página recoleta sozinha a cada 10 min, ou na hora pelo botão "atualizar agora"')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nencerrado')


if __name__ == '__main__':
    if '--servir' in sys.argv:
        servir()
    else:
        dados = coleta()
        caminho = escreve(monta_html(dados, servidor=False))
        resumo(dados)
        print(f'OK → outputs/uso/uso.html ({os.path.getsize(caminho) / 1024:.0f} KB)')
        print('   para deixar fixo no navegador: scripts\\27_uso.py --servir  → http://localhost:8790')
