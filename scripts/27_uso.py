# -*- coding: utf-8 -*-
"""
27_uso.py — PAINEL DE USO (privado): quem leu o quê, e o que baixaram do RIDAB.

Não vai para o site. Escreve `outputs/uso/uso.html`, que é um arquivo local para o
Cainan abrir no navegador — `outputs/uso/` está no .gitignore, então não é publicado
nem versionado. O painel público (site/evidencias.html) continua sendo sobre o
fomento; este aqui é sobre o próprio trabalho.

Duas fontes:
  1. GoatCounter (fsa-fomento) — visitas e, principalmente, os EVENTOS que o site
     dispara: `trecho/<id>` quando alguém abre o gráfico de uma passagem e
     `aba/<id>` quando abre uma aba do painel. O painel do GoatCounter mostra isso
     como `/trecho/h_sequencias`, que não diz nada; aqui o id é traduzido para o
     título do gráfico, que é o que interessa ler.
  2. `outputs/metricas/hf_ridab.csv` — a série de downloads do dataset no Hugging
     Face, capturada todo dia pelo scripts/26.

O token da API fica em `.env.analytics` na raiz (gitignored), assim:
    GOATCOUNTER_SITE=fsa-fomento
    GOATCOUNTER_TOKEN=<token criado em Settings → API>
Sem token o script roda igual e monta a parte do Hugging Face, avisando o que falta.

Rodar:  .\\.venv\\Scripts\\python.exe scripts\\27_uso.py
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

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import site_base as S  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASES = os.path.join(BASE, 'outputs', 'bases')
MET = os.path.join(BASE, 'outputs', 'metricas')
OUT = os.path.join(BASE, 'outputs', 'uso')
DIAS = 90


def brn(x, d=0):
    return f'{x:,.{d}f}'.replace(',', '§').replace('.', ',').replace('§', '.')


# ── credenciais ───────────────────────────────────────────────────────────────
def env():
    p = os.path.join(BASE, '.env.analytics')
    cfg = {}
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8'):
            if '=' in ln and not ln.strip().startswith('#'):
                k, _, v = ln.partition('=')
                cfg[k.strip()] = v.strip().strip('"\'')
    return cfg


CFG = env()
SITE_GC = CFG.get('GOATCOUNTER_SITE', 'fsa-fomento')
TOKEN = CFG.get('GOATCOUNTER_TOKEN', '')


def gc(endpoint, **params):
    """GET na API do GoatCounter. Devolve None quando não há token ou a chamada falha."""
    if not TOKEN:
        return None
    url = f'https://{SITE_GC}.goatcounter.com/api/v0/{endpoint}'
    if params:
        url += '?' + '&'.join(f'{k}={v}' for k, v in params.items() if v not in (None, ''))
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f'  ! GoatCounter {endpoint}: {e}')
        return None


# ── de id técnico para nome humano ────────────────────────────────────────────
TITULOS, SECAO = {}, {}
for nome in ('hoverfigs.json', 'hoverfigs2.json', 'painelfigs.json'):
    p = os.path.join(BASES, nome)
    if os.path.exists(p):
        for k, v in json.load(open(p, encoding='utf-8')).items():
            TITULOS[k] = v['titulo']
            SECAO[k] = v.get('secao', 'c1')
PERGUNTA = {c[0]: c[2] for c in S.CLAIMS}
PAGINA = {'/ensaio.html': 'Análise (o texto)', '/evidencias.html': 'Painel de dados',
          '/index.html': 'Início', '/': 'Início'}


def humano(path):
    """`/trecho/h_criterio` → o título do gráfico; `/aba/q_c2` → o nome da pergunta."""
    p = path if path.startswith('/') else '/' + path
    m = re.match(r'^/trecho/(.+)$', p)
    if m:
        gid = m.group(1)
        sec = SECAO.get(gid, '')
        pref = f'P{sec[1:]} · ' if sec.startswith('c') else ''
        return 'trecho', pref + TITULOS.get(gid, gid), gid
    m = re.match(r'^/aba/(?:q_)?(.+)$', p)
    if m:
        aid = m.group(1)
        if aid in PERGUNTA:
            return 'aba', f'Pergunta {aid[1:]} · {PERGUNTA[aid]}', aid
        return 'aba', {'g_rankings': 'Rankings', 'g_chamadas': 'Chamadas',
                       'dados': 'Dados abertos'}.get(aid, aid), aid
    return 'pagina', PAGINA.get(p, p), p


# ── coleta ────────────────────────────────────────────────────────────────────
hoje = dt.date.today()
ini = (hoje - dt.timedelta(days=DIAS)).isoformat() + 'T00:00:00Z'
fim = hoje.isoformat() + 'T23:00:00Z'

hits = gc('stats/hits', start=ini, end=fim, limit=200, group='day')
total = gc('stats/total', start=ini, end=fim)

linhas, serie_dia = [], {}
if hits and hits.get('hits'):
    for h in hits['hits']:
        tipo, nome, ident = humano(h.get('path', ''))
        linhas.append({'tipo': tipo, 'nome': nome, 'id': ident,
                       'views': (h.get('count') or 0), 'visitantes': (h.get('count_unique') or 0)})
        for d in (h.get('stats') or []):
            serie_dia[d['day']] = serie_dia.get(d['day'], 0) + sum(
                x.get('total', 0) for x in (d.get('hourly_unique') or [])) if False else \
                serie_dia.get(d['day'], 0) + (d.get('daily') or 0)

# Hugging Face (série capturada pelo scripts/26)
hf = []
hf_p = os.path.join(MET, 'hf_ridab.csv')
if os.path.exists(hf_p):
    hf = [r for r in csv.DictReader(open(hf_p, encoding='utf-8-sig'))]

# guarda o retrato do dia, para ter história mesmo se o GoatCounter mudar de plano
os.makedirs(MET, exist_ok=True)
snap = os.path.join(MET, 'goatcounter_paths.csv')
if linhas:
    ja = []
    if os.path.exists(snap):
        ja = [r for r in csv.DictReader(open(snap, encoding='utf-8-sig'))]
        ja = [r for r in ja if r.get('coletado_em', '')[:10] != hoje.isoformat()]
    novo = [{'coletado_em': hoje.isoformat(), 'janela_dias': DIAS, 'tipo': r['tipo'],
             'id': r['id'], 'nome': r['nome'], 'views': r['views'],
             'visitantes': r['visitantes']} for r in linhas]
    with open(snap, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['coletado_em', 'janela_dias', 'tipo', 'id',
                                           'nome', 'views', 'visitantes'])
        w.writeheader()
        w.writerows(ja + novo)


# ── figuras ───────────────────────────────────────────────────────────────────
def base_fig(fig, h=300, legend=False, ytitle=None):
    fig.update_layout(paper_bgcolor='#12151e', plot_bgcolor='#12151e',
                      font=dict(family='Inter,system-ui,sans-serif', color=S.TXT, size=11.5),
                      margin=dict(l=52, r=16, t=12, b=38), height=h, showlegend=legend,
                      hoverlabel=dict(font_size=11.5, font_family='Inter'))
    fig.update_xaxes(gridcolor=S.GRID, zerolinecolor=S.GRID, linecolor=S.GRID, tickfont_size=10.5)
    fig.update_yaxes(gridcolor=S.GRID, zerolinecolor=S.GRID, linecolor=S.GRID, title=ytitle,
                     title_font_size=11, tickfont_size=10.5)
    return fig


def fig_json(fig, pid):
    spec = fig.to_json()
    return (f'<div class="js-plot" data-plot="{pid}" style="min-height:{fig.layout.height}px"></div>'
            f'<script type="application/json" id="{pid}">{spec}</script>')


def rank_html(itens, cor, vazio):
    if not itens:
        return f'<div class="vazio">{vazio}</div>'
    mx = max(i['views'] for i in itens) or 1
    linhas_ = []
    for i in itens:
        pct = 100 * i['views'] / mx
        linhas_.append(
            f'<div class="rk"><div class="rk-l"><span class="rk-n">{i["nome"]}</span>'
            f'<span class="rk-v">{brn(i["views"])}</span></div>'
            f'<div class="rk-b"><i style="width:{pct:.1f}%;background:{cor}"></i></div></div>')
    return ''.join(linhas_)


trechos = sorted([r for r in linhas if r['tipo'] == 'trecho'], key=lambda r: -r['views'])[:20]
abas = sorted([r for r in linhas if r['tipo'] == 'aba'], key=lambda r: -r['views'])[:12]
paginas = sorted([r for r in linhas if r['tipo'] == 'pagina'], key=lambda r: -r['views'])[:12]

figs = []
if serie_dia:
    dias = sorted(serie_dia)
    f = go.Figure(go.Bar(x=dias, y=[serie_dia[d] for d in dias], marker_color=S.CYAN,
                         hovertemplate='%{x}: %{y} visitas<extra></extra>'))
    base_fig(f, 260, ytitle='visitas por dia')
    figs.append(('Visitas por dia', fig_json(f, 'pl-visitas')))

if hf:
    d = [r['data'] for r in hf]
    tot = [int(r['downloads_total'] or 0) for r in hf]
    m30 = [int(r['downloads_30d'] or 0) for r in hf]
    f = make_subplots(specs=[[{'secondary_y': True}]])
    f.add_scatter(x=d, y=tot, name='acumulado', mode='lines+markers',
                  line=dict(color=S.GOLD, width=2.4), marker=dict(size=6),
                  hovertemplate='%{x}: %{y} downloads acumulados<extra></extra>')
    f.add_bar(x=d, y=m30, name='últimos 30 dias', marker_color='#3a4560',
              secondary_y=True, hovertemplate='%{x}: %{y} nos últimos 30 dias<extra></extra>')
    base_fig(f, 260, legend=True, ytitle='downloads acumulados')
    f.update_yaxes(title='janela de 30 dias', secondary_y=True, showgrid=False,
                   title_font_size=11, tickfont_size=10.5)
    f.update_layout(legend=dict(orientation='h', y=1.16, x=0, font_size=10.5,
                                bgcolor='rgba(0,0,0,0)'))
    figs.append(('Downloads do RIDAB no Hugging Face', fig_json(f, 'pl-hf')))

# ── KPIs ──────────────────────────────────────────────────────────────────────
tot_views = (total or {}).get('total', 0)
tot_uniq = (total or {}).get('total_unique', 0)
n_trechos = sum(r['views'] for r in linhas if r['tipo'] == 'trecho')
hf_ult = hf[-1] if hf else None

kpis = [
    (brn(tot_views), f'visitas em {DIAS} dias', S.CYAN),
    (brn(tot_uniq), 'visitantes distintos', S.ACCENT),
    (brn(n_trechos), 'gráficos de trecho abertos', S.PURPLE),
    (brn(int(hf_ult['downloads_total'])) if hf_ult else '—', 'downloads do RIDAB (acumulado)', S.GOLD),
]

aviso = ''
if not TOKEN:
    aviso = ('<div class="aviso"><b>Falta o token da API.</b> A parte do GoatCounter está vazia '
             'porque este painel ainda não tem credencial. Crie em '
             '<a href="https://fsa-fomento.goatcounter.com/user/api">fsa-fomento.goatcounter.com '
             '→ API</a>, com permissão de <i>leitura de estatísticas</i>, e escreva na raiz do '
             'projeto um arquivo <code>.env.analytics</code> com duas linhas:<br>'
             '<code>GOATCOUNTER_SITE=fsa-fomento</code><br><code>GOATCOUNTER_TOKEN=&lt;o token&gt;</code>'
             '<br>Depois é só rodar este script de novo. O arquivo é ignorado pelo git.</div>')
elif not linhas:
    aviso = ('<div class="aviso"><b>Nenhum acesso ainda.</b> O token funciona, mas o GoatCounter '
             'não recebeu dado nenhum no período — o esperado enquanto ninguém abriu o site '
             'publicado (localhost não conta).</div>')

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0d14;color:#e2e8f0;font-family:Inter,system-ui,sans-serif;padding:26px 30px 70px}
h1{font-size:25px;font-weight:800;letter-spacing:-.4px;margin-bottom:6px}
.sub{color:#8f9ab3;font-size:13.5px;margin-bottom:22px;max-width:900px;line-height:1.6}
.priv{display:inline-block;font-size:10px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;
      color:#fbbf24;border:1px solid #5b4413;background:#241b0c;border-radius:20px;padding:3px 10px;margin-bottom:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px}
.kpi{background:#12151e;border:1px solid #232838;border-top:2px solid var(--c);border-radius:10px;padding:13px 15px}
.kpi .v{font-size:27px;font-weight:800;letter-spacing:-.6px;line-height:1}
.kpi .l{font-size:11px;color:#7b849a;margin-top:6px;line-height:1.4}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:14px}
.card{background:#12151e;border:1px solid #232838;border-radius:12px;padding:15px 16px 13px}
.card h2{font-size:14.5px;font-weight:700;margin-bottom:4px}
.card .h{font-size:11.5px;color:#7b849a;margin-bottom:13px;line-height:1.5}
.full{grid-column:1/-1}
.rk{margin-bottom:9px}
.rk-l{display:flex;gap:10px;align-items:baseline;font-size:12.5px;margin-bottom:3px}
.rk-n{flex:1;color:#cbd5e1;line-height:1.4}
.rk-v{font-weight:800;font-variant-numeric:tabular-nums;color:#e8ecf4}
.rk-b{height:5px;background:#1a1f2c;border-radius:3px;overflow:hidden}
.rk-b i{display:block;height:100%;border-radius:3px}
.vazio{color:#5b647c;font-size:12.5px;font-style:italic;padding:14px 0}
.aviso{background:#241b0c;border:1px solid #5b4413;border-left:3px solid #fbbf24;border-radius:10px;
       padding:13px 16px;margin-bottom:22px;font-size:13px;color:#f3d9a0;line-height:1.65}
.aviso b{color:#fbbf24}.aviso a{color:#fbbf24}
.aviso code{background:#0f1218;border:1px solid #3a2f14;border-radius:5px;padding:1px 6px;font-size:12px}
footer{margin-top:30px;color:#5b647c;font-size:11.5px;line-height:1.7;border-top:1px solid #1c2030;padding-top:14px}
"""

LAZY = """
(function(){
  function draw(el){
    try{ var s=JSON.parse(document.getElementById(el.dataset.plot).textContent);
      Plotly.newPlot(el, s.data, s.layout, {displayModeBar:false, responsive:true});
    }catch(e){}
  }
  function go(){ document.querySelectorAll('.js-plot').forEach(draw); }
  if(document.readyState==='complete') go(); else window.addEventListener('load', go);
})();
"""

os.makedirs(OUT, exist_ok=True)
shutil.copyfile(os.path.join(BASE, 'site', 'assets', 'plotly.min.js'),
                os.path.join(OUT, 'plotly.min.js'))

kpi_html = ''.join(f'<div class="kpi" style="--c:{c}"><div class="v">{v}</div>'
                   f'<div class="l">{l}</div></div>' for v, l, c in kpis)
figs_html = ''.join(f'<div class="card full"><h2>{t}</h2>{h}</div>' for t, h in figs)

html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Uso · FSA 2014–2023 (privado)</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="plotly.min.js" defer></script>
<style>{CSS}</style></head><body>
<div class="priv">arquivo privado · não publicado</div>
<h1>Quem leu o quê</h1>
<p class="sub">Uso do trabalho nos últimos {DIAS} dias: visitas ao texto e ao painel, quais passagens
do argumento as pessoas abriram, e o que foi baixado do RIDAB. Gerado por
<code>scripts/27_uso.py</code> a partir do GoatCounter e da API do Hugging Face.
Atualizado em {dt.datetime.now().strftime('%d/%m/%Y %H:%M')}.</p>
{aviso}
<div class="kpis">{kpi_html}</div>
<div class="grid">
{figs_html}
<div class="card full"><h2>Passagens mais abertas</h2>
  <div class="h">Cada linha é um gráfico de trecho que alguém abriu no texto — é o que a pessoa
  quis conferir por conta própria. Vale mais que o número de visitas.</div>
  {rank_html(trechos, S.PURPLE, 'Nenhum trecho aberto ainda.')}</div>
<div class="card"><h2>Abas do painel</h2>
  <div class="h">Qual pergunta puxou gente para os dados.</div>
  {rank_html(abas, S.CYAN, 'Nenhuma aba visitada ainda.')}</div>
<div class="card"><h2>Páginas</h2>
  <div class="h">O tráfego bruto, para contexto.</div>
  {rank_html(paginas, S.ACCENT, 'Nenhuma visita ainda.')}</div>
</div>
<footer>
Este arquivo fica em <code>outputs/uso/</code>, que está no .gitignore — não é versionado nem
publicado. O site não expõe nada disso.<br>
Fontes: GoatCounter (<code>{SITE_GC}</code>, sem cookie, IPs próprios filtrados) ·
Hugging Face API (<code>riabr-dados/riab</code>, {len(hf)} ponto(s) capturado(s) pelo scripts/26).<br>
Ressalva de sempre: bloqueador de anúncio derruba parte da medição, então trate estes números
como piso, não como censo.
</footer>
<script>{LAZY}</script>
</body></html>"""

p_out = os.path.join(OUT, 'uso.html')
with open(p_out, 'w', encoding='utf-8') as fh:
    fh.write(html)
print(f'  visitas: {brn(tot_views)} · trechos abertos: {brn(n_trechos)} · '
      f'caminhos distintos: {len(linhas)}')
print(f'  Hugging Face: {len(hf)} ponto(s) na série')
if not TOKEN:
    print('  ! sem GOATCOUNTER_TOKEN em .env.analytics — a parte de acessos sai vazia')
print(f'OK → outputs/uso/uso.html ({os.path.getsize(p_out) / 1024:.0f} KB)')
