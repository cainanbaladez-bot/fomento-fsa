# -*- coding: utf-8 -*-
"""
26_metricas_hf.py — captura diária das métricas públicas do RIDAB no Hugging Face.

Por que existe: a API do HF só devolve a **janela corrente** (downloads dos últimos
30 dias) e o acumulado de sempre. Ela NÃO guarda histórico — se ninguém capturar
todo dia, a série simplesmente não existe depois. Este script grava um ponto por
dia em `outputs/metricas/hf_ridab.csv` (append idempotente: rodar duas vezes no
mesmo dia sobrescreve a linha do dia, não duplica).

O que dá para saber:  downloads (30 dias), downloads acumulados, likes.
O que NÃO dá:         quem baixou, de onde, e qual parquet — o HF não expõe
                      nada disso ao dono do dataset. Só sairia proxyando os
                      arquivos, que é mudança de arquitetura (decisão adiada).

Rodar:   .\\.venv\\Scripts\\python.exe scripts\\26_metricas_hf.py
Agendar: tarefa diária do Windows (ver README/PLANO).
"""
import os
import sys
import csv
import json
import datetime as dt
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'outputs', 'metricas')
CSV_P = os.path.join(OUT, 'hf_ridab.csv')

ALVOS = [('dataset', 'riabr-dados/riab')]
CAMPOS = ['data', 'tipo', 'repo', 'downloads_30d', 'downloads_total', 'likes',
          'ultima_modificacao', 'coletado_em']
API = 'https://huggingface.co/api/{tipo}s/{repo}?expand[]=downloads&expand[]=downloadsAllTime&expand[]=likes&expand[]=lastModified'


def busca(tipo, repo):
    url = API.format(tipo=tipo, repo=repo)
    req = urllib.request.Request(url, headers={'User-Agent': 'ridab-metricas/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    os.makedirs(OUT, exist_ok=True)
    hoje = dt.date.today().isoformat()
    agora = dt.datetime.now().isoformat(timespec='seconds')

    linhas = []
    if os.path.exists(CSV_P):
        with open(CSV_P, encoding='utf-8-sig', newline='') as fh:
            linhas = [r for r in csv.DictReader(fh)]

    novas, erros = [], []
    for tipo, repo in ALVOS:
        try:
            d = busca(tipo, repo)
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            erros.append(f'{repo}: {e}')
            continue
        novas.append({
            'data': hoje, 'tipo': tipo, 'repo': repo,
            'downloads_30d': d.get('downloads', ''),
            'downloads_total': d.get('downloadsAllTime', ''),
            'likes': d.get('likes', ''),
            'ultima_modificacao': (d.get('lastModified') or '')[:10],
            'coletado_em': agora})

    if not novas:
        print('! nada coletado' + (' — ' + '; '.join(erros) if erros else ''))
        return 1

    # idempotente: a linha do dia é substituída, não duplicada
    chave = {(n['data'], n['repo']) for n in novas}
    linhas = [r for r in linhas if (r.get('data'), r.get('repo')) not in chave] + novas
    linhas.sort(key=lambda r: (r['data'], r['repo']))
    with open(CSV_P, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(linhas)

    for n in novas:
        # variação desde o ponto anterior do mesmo repo, quando existe
        ant = [r for r in linhas if r['repo'] == n['repo'] and r['data'] < n['data']]
        delta = ''
        if ant and str(ant[-1].get('downloads_total', '')).isdigit():
            d0 = int(ant[-1]['downloads_total'])
            d1 = int(n['downloads_total']) if str(n['downloads_total']).isdigit() else d0
            delta = f'  (+{d1 - d0} desde {ant[-1]["data"]})'
        print(f'  {n["repo"]}: {n["downloads_30d"]} downloads em 30 dias · '
              f'{n["downloads_total"]} acumulados · {n["likes"]} likes{delta}')
    if erros:
        print('  ! ' + '; '.join(erros))
    print(f'OK → outputs/metricas/hf_ridab.csv ({len(linhas)} pontos)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
