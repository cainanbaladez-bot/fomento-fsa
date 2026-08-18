# O fomento ao cinema brasileiro, em alegações verificáveis · FSA 2014–2023

Site estático, autocontido, pronto para publicar. Três páginas:

| Página | O quê |
|---|---|
| `index.html` | Porta de entrada — o projeto, o método, as **8 alegações** em cards, trilhas de leitura, conexão RIDAB |
| `ensaio.html` | O ensaio autoral (voz em 1ª pessoa): abertura + 8 alegações + contra-alegações + 13 proposições + coda. **Passar o mouse num número-âncora abre o gráfico daquele número** (popup Plotly interativo) |
| `evidencias.html` | **O painel de dados**, em três blocos: **Dados gerais** (5 abas — Visão geral · **Rankings** (obras → produtoras → chamadas, as três bases completas com 29/24/16 colunas) · Chamadas · Produtoras · Concentração), **As perguntas** (as 8 na ordem do ensaio: KPIs + figuras, sem juízo) e **Anexos**, fechando na **Metodologia** — um bloco dobrável por pergunta com a conta, os limites do dado e o “reproduza esta conta” (RIDAB + DuckDB) |

`assets/plotly.min.js` é o único asset (carregado apenas pelas evidências; gráficos em lazy-load).

## Publicar no GitHub Pages

```bash
cd site
git init && git add -A && git commit -m "Fomento em alegações — FSA 2014-2023"
git branch -M main
git remote add origin https://github.com/<usuario>/<repo>.git
git push -u origin main
# GitHub → Settings → Pages → Source: main / (root)
```

Não precisa de build no servidor — é HTML puro (o `.nojekyll` evita processamento Jekyll).

## Regenerar (repositório-mãe: `analise-empirica-fsa-2014-2023/`)

O texto do ensaio é editável em **`site_src/ensaio.md`** (Markdown com marcação mínima).
Depois de editar:

**A ordem importa** — o `22` gera os gráficos que o `21` usa nos popups do ensaio:

```powershell
.\.venv\Scripts\python.exe scripts\20_site_index.py      # index.html
.\.venv\Scripts\python.exe scripts\22_site_evidencias.py # evidencias.html + popfigs.json (~1 min)
.\.venv\Scripts\python.exe scripts\21_site_ensaio.py     # ensaio.html (consome popfigs.json)
```

Infra compartilhada (tema, registro das 8 alegações, bloco RIDAB, `NUM_FIG`): `scripts/site_base.py`.
O *chrome* de painel (KPI bar, grade de cards, sidebar, sub-abas), as 4 abas de dados gerais
e as tabelas-ranking vivem em `scripts/22_site_evidencias.py` — `CSS_PANEL`, `kpi()/kpibar()`,
`_figs_html()`, `itable()`, `xy_scatter()`, `g_visao`/`g_chamadas`/`g_produtoras`/`g_concentracao`.
Os popups do ensaio: `S.NUM_FIG` + `NUMFIG_JS` em `scripts/21_site_ensaio.py`.
Conferência independente dos números-âncora: `scripts/42_auditoria.py`.

## Dados

- Microdados: [RIDAB — Repositório Independente do Audiovisual Brasileiro](https://riabr-dados.github.io/riab)
  · espelho [Hugging Face](https://huggingface.co/datasets/riabr-dados/riab) (CC-BY-4.0)
- Estudo legado citado como documental: [politica.html](https://cainanbaladez-bot.github.io/fomento-audiovisual/politica.html)
- Nenhum número é digitado à mão: tudo sai de script versionado no repositório-mãe.
