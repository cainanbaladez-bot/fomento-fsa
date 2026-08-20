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

sys.stdout.reconfigure(encoding='utf-8')
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
PAGINA = {'/ensaio.html': 'Análise (o texto)', '/evidencias.html': 'Painel de dados',
          '/index.html': 'Início', '/': 'Início'}
ABA_NOME = {'g_rankings': 'Rankings', 'g_chamadas': 'Chamadas', 'dados': 'Dados abertos'}


def humano(path):
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
        return 'aba', ABA_NOME.get(aid, aid), aid
    return 'pagina', PAGINA.get(p, p), p


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
        tipo, nome, ident = humano(h.get('path', ''))
        linhas.append({'tipo': tipo, 'nome': nome, 'id': ident,
                       'views': h.get('count') or 0, 'visitantes': h.get('count_unique') or 0})
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
        cols = ['coletado_em', 'janela_dias', 'tipo', 'id', 'nome', 'views', 'visitantes']
        with open(snap, 'w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(ja + [{'coletado_em': hoje.isoformat(), 'janela_dias': DIAS,
                               'tipo': r['tipo'], 'id': r['id'], 'nome': r['nome'],
                               'views': r['views'], 'visitantes': r['visitantes']}
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
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:14px}
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


def monta_html(d, servidor=False):
    linhas, serie, total, hf = d['linhas'], d['serie'], d['total'], d['hf']
    trechos = sorted([r for r in linhas if r['tipo'] == 'trecho'], key=lambda r: -r['views'])[:25]
    abas = sorted([r for r in linhas if r['tipo'] == 'aba'], key=lambda r: -r['views'])[:12]
    paginas = sorted([r for r in linhas if r['tipo'] == 'pagina'], key=lambda r: -r['views'])[:12]

    figs = []
    if serie:
        dias = sorted(serie)
        f = go.Figure(go.Bar(x=dias, y=[serie[x] for x in dias], marker_color=S.CYAN,
                             hovertemplate='%{x}: %{y} visitas<extra></extra>'))
        base_fig(f, 250, ytitle='visitas por dia')
        figs.append(('Visitas por dia', fig_html(f, 'pl-visitas')))
    if hf:
        x = [r['data'] for r in hf]
        f = make_subplots(specs=[[{'secondary_y': True}]])
        f.add_scatter(x=x, y=[int(r['downloads_total'] or 0) for r in hf], name='acumulado',
                      mode='lines+markers', line=dict(color=S.GOLD, width=2.4), marker=dict(size=6),
                      hovertemplate='%{x}: %{y} acumulados<extra></extra>')
        f.add_bar(x=x, y=[int(r['downloads_30d'] or 0) for r in hf], name='últimos 30 dias',
                  marker_color='#3a4560', secondary_y=True,
                  hovertemplate='%{x}: %{y} na janela de 30 dias<extra></extra>')
        base_fig(f, 250, legend=True, ytitle='downloads acumulados')
        f.update_yaxes(title='janela de 30 dias', secondary_y=True, showgrid=False,
                       title_font_size=11, tickfont_size=10.5)
        f.update_layout(legend=dict(orientation='h', y=1.18, x=0, font_size=10.5,
                                    bgcolor='rgba(0,0,0,0)'))
        figs.append(('Downloads do RIDAB no Hugging Face', fig_html(f, 'pl-hf')))

    hf_ult = hf[-1] if hf else None
    kpis = [(brn(total.get('total', 0)), f'visitas em {DIAS} dias', S.CYAN),
            (brn(total.get('total_unique', 0)), 'visitantes distintos', S.ACCENT),
            (brn(sum(r['views'] for r in linhas if r['tipo'] == 'trecho')),
             'gráficos de trecho abertos', S.PURPLE),
            (brn(hf_ult['downloads_total']) if hf_ult else '—',
             'downloads do RIDAB (acumulado)', S.GOLD)]

    aviso = ''
    if not d['token']:
        aviso = ('<div class="aviso"><b>Falta o token da API.</b> Os blocos de acesso estão '
                 'vazios porque este painel ainda não tem credencial. Crie em '
                 f'<a href="https://{d["site"]}.goatcounter.com/user/api">'
                 f'{d["site"]}.goatcounter.com → API</a> (permissão de <i>ler estatísticas</i>) e '
                 'escreva na raiz do projeto um <code>.env.analytics</code> com:<br>'
                 f'<code>GOATCOUNTER_SITE={d["site"]}</code><br>'
                 '<code>GOATCOUNTER_TOKEN=&lt;o token&gt;</code><br>'
                 'Depois é só apertar atualizar aqui em cima. O arquivo é ignorado pelo git.</div>')
    elif not linhas:
        aviso = ('<div class="aviso"><b>Nenhum acesso ainda.</b> O token funciona, mas o '
                 'GoatCounter não recebeu dado no período — esperado enquanto ninguém abriu o '
                 'site publicado (localhost não conta).</div>')

    ctx = ''.join(f'<div class="card"><h2>{rot}</h2>{rank_html(it, cor, "—", True)}</div>'
                  for rot, cor, it in d['contexto'])
    botao = ('<a class="btn" id="btn-atualizar" href="/atualizar">↻ atualizar agora</a>'
             if servidor else '')
    figs_html = ''.join(f'<div class="card full"><h2>{t}</h2>{h}</div>' for t, h in figs)

    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Uso · FSA 2014–2023</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="plotly.min.js" defer></script>
<style>{CSS}</style></head><body>
<div class="top"><h1>Quem leu o quê</h1><span class="priv">privado</span>
  <span class="quando">coletado em {dt.datetime.now().strftime('%d/%m/%Y às %H:%M')}</span>
  {botao}</div>
<main>
<p class="sub">Uso do trabalho nos últimos {DIAS} dias: o tráfego, de onde veio, e — o que
importa mais — <b>quais passagens do argumento as pessoas abriram</b>. Some a isso a série de
downloads do RIDAB no Hugging Face. Fontes: GoatCounter (<code>{d['site']}</code>) e API do
Hugging Face.</p>
{aviso}
<div class="kpis">{''.join(f'<div class="kpi" style="--c:{c}"><div class="v">{v}</div><div class="l">{l}</div></div>' for v, l, c in kpis)}</div>
<div class="grid">
{figs_html}
<div class="card full"><h2>Passagens mais abertas</h2>
  <div class="h">Cada linha é um gráfico de trecho que alguém abriu dentro do texto — o que a
  pessoa quis conferir por conta própria. Lê melhor que contagem de visita.</div>
  {rank_html(trechos, S.PURPLE, 'Nenhum trecho aberto ainda.')}</div>
<div class="card"><h2>Abas do painel</h2>
  <div class="h">Qual pergunta puxou gente para os dados.</div>
  {rank_html(abas, S.CYAN, 'Nenhuma aba visitada ainda.')}</div>
<div class="card"><h2>Páginas</h2>
  <div class="h">O tráfego bruto, para contexto.</div>
  {rank_html(paginas, S.ACCENT, 'Nenhuma visita ainda.')}</div>
<div class="sec">De onde vem e em que abrem</div>
{ctx or '<div class="card full"><div class="vazio">Sem dado de contexto ainda.</div></div>'}
</div>
</main>
<footer>
Arquivo privado: mora em <code>outputs/uso/</code>, que está no .gitignore — não é versionado
nem publicado, e a página leva <code>noindex</code>.<br>
GoatCounter sem cookie, com os seus IPs filtrados · Hugging Face <code>riabr-dados/riab</code>,
{len(hf)} ponto(s) na série (scripts/26, diário).<br>
Bloqueador de anúncio derruba parte da medição: trate como piso, não como censo.
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
