# -*- coding: utf-8 -*-
"""
70_base_obras.py — BASE CANÔNICA POR OBRA (dois universos, denominador total).

Regra metodológica (decisão Cainan 2026-07-25):
  · UNIVERSO DE APLICAÇÃO  = toda obra de CINEMA com fomento público (FSA direto
    e/ou indireto/renúncia), estreada ou não. Serve para taxa de estreia,
    pulverização, capacidade de carga (c7/c8). N ≈ 1.848.
  · UNIVERSO DE RETORNO    = subconjunto com BILHETERIA informada (as duas pontas
    confirmadas: fomento E renda). Serve para retorno doméstico, internacional,
    rankings, comparação por instrumento. Sem renda → o financiamento também sai
    da conta. N ≈ 930 (917 observadas + 13 recuperadas por público×PMI).
  · RETORNO DOMÉSTICO      = receita de referência ÷ INVESTIMENTO PÚBLICO TOTAL
    (FSA + renúncia da obra), nunca só FSA. Ex.: 0,5 FSA + 0,5 renúncia com
    receita 1,0 → retorno 1,0.
  · INTERNACIONAL          = verificado apenas no universo de retorno (obra
    primeiro existe em sala no Brasil; depois mede-se a circulação externa).

Cascata de matching auditada em 2026-07-25 (ver outputs/bases/auditoria_matching.csv):
  CPB é chave sólida — 0 recuperações por título entre obras brasileiras; as obras
  sem renda estão ausentes da própria fonte (lancamentos_distribuidoras).
  Única recuperação legítima: público sem renda → renda estimada por público×PMI
  mediano do ano (flag `renda_pmi_estimada`).

Entradas: data/legado/painel_datasets/base_nivel_obra.csv (legado auditado)
          outputs/tabelas/abt_obra_fsa.parquet (público/sessões por CPB, RIDAB)
          outputs/tabelas/base_bilheteria_obra.parquet (RIDAB, p/ PMI)
          outputs/tabelas/obra_chamadas_fsa.csv (categoria revisada s43)
Saída:    outputs/bases/base_obras.parquet + .csv
"""
import os
import re
import sys
import unicodedata
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'outputs', 'bases')
os.makedirs(OUT, exist_ok=True)

norm_cpb = lambda s: re.sub(r'[^0-9A-Z]', '', str(s).upper())


def norm_cnpj(x):
    if pd.isna(x):
        return ''
    d = re.sub(r'\D', '', str(x))
    if str(x).endswith('.0') and len(d) == 15:
        d = d[:-1]
    return d.zfill(14) if d else ''


# ── 1 · legado auditado (escopo cinema + valores deflacionados) ────────────────
o = pd.read_csv(os.path.join(BASE, 'data', 'legado', 'painel_datasets',
                             'base_nivel_obra.csv'), sep=';')
NUM = ['investimento_fsa_deflac', 'investimento_renuncia_total_deflac',
       'investimento_total_deflac', 'bilheteria_deflac', 'outras_janelas_deflac',
       'roi_internacional_0_100', 'pontuacao_festivais', 'adm_eu_lumiere',
       'vod_n_plataformas', 'vod_n_paises', 'critica_indice_1_5', 'cita_n_papers',
       'ano']
for c in NUM:
    o[c] = pd.to_numeric(o[c], errors='coerce').fillna(0)
DROP = ['_tv_excluir', 'sem_categoria', 'FSA Apenas roteiro']
b = o[~o.categoria.isin(DROP)].copy()
b['cpb'] = b.CPB.map(norm_cpb)
b['cnpj_produtora'] = b.CNPJ_produtora.map(norm_cnpj)

# ── 1a-bis · REPARO do casamento de festivais (2026-08-08) ────────────────────
# `data/legado/festivais_consolidado.csv` tem 106 das 360 linhas sem CPB, e o
# casamento por título do legado falhava quando o título começa por artigo
# ("O Marinheiro das Montanhas" na consolidação × "MARINHEIRO DAS MONTANHAS" na
# base). Refaço o join com o artigo inicial removido e RECOMPUTO o composto pela
# fórmula original do legado (fomento-audiovisual/scripts/01, roi_internacional):
#   70·min(pts/350, 1) + 20·log1p(adm)/log1p(2,5 mi) + 10·min(paises, 5)/5
FEST_MAX, LUM_MAX = 350.0, np.log1p(2_500_000)


def norm_titulo(s):
    s = (unicodedata.normalize('NFKD', str(s))
         .encode('ascii', 'ignore').decode().upper())
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    s = re.sub(r'^(O|A|OS|AS)\s+', '', s.strip())
    return re.sub(r'\s+', ' ', s).strip()


def composto_intl(pts, adm, paises):
    return round(min(pts / FEST_MAX, 1.0) * 70
                 + (np.log1p(adm) / LUM_MAX if adm > 0 else 0) * 20
                 + min(paises, 5) / 5 * 10, 2)


_fc = pd.read_csv(os.path.join(BASE, 'data', 'legado',
                               'festivais_consolidado.csv'), sep=',')
_fc['tn'] = _fc.titulo.map(norm_titulo)
_pts = (_fc[_fc.pontuacao_total > 0].groupby('tn').pontuacao_total.max())
b['_tn'] = b.titulo.map(norm_titulo)
_falta = (b.pontuacao_festivais <= 0) & b._tn.isin(_pts.index)
if _falta.any():
    b.loc[_falta, 'pontuacao_festivais'] = b.loc[_falta, '_tn'].map(_pts)
    b.loc[_falta, 'roi_internacional_0_100'] = [
        composto_intl(r.pontuacao_festivais, r.adm_eu_lumiere, r.vod_n_paises)
        for r in b.loc[_falta].itertuples()]
    print(f'  [reparo festivais] {int(_falta.sum())} obra(s) recuperada(s) por '
          f'título sem artigo: '
          f'{", ".join(b.loc[_falta, "_tn"].head(5).tolist())}')
b = b.drop(columns=['_tn'])

# ── 1b · FILTRO DURO DE ESCOPO: só obras destinadas a SALAS DE EXIBIÇÃO ────────
# O `_tv_excluir` do legado só tirava PRODAV/FSA-TV; a renúncia para TV (séries
# como "Um Contra Todos", "Irmão do Jorel", "Impuros") passava batido e entrava
# como se fosse cinema. `obras.parquet` do RIDAB é a fonte autoritativa do
# segmento de destinação — e traz também a UF do requerente, ausente no legado.
obras = pd.read_parquet(os.path.join(BASE, 'data', 'ridab_cleaned', 'obras.parquet'))
obras['cpb'] = obras.cpb.map(norm_cpb)
obras = obras.drop_duplicates('cpb')[
    ['cpb', 'segmento_destinacao_inicial', 'tipo_obra', 'subtipo_obra',
     'uf_requerente', 'organizacao_temporal', 'quantidade_episodios']]
b = b.merge(obras, on='cpb', how='left')
n0 = len(b)
seg = b.segmento_destinacao_inicial.fillna('')
e_seriada = b.organizacao_temporal.fillna('').str.upper().str.contains('SERIA') | \
            (pd.to_numeric(b.quantidade_episodios, errors='coerce').fillna(0) > 1)
# Regra: é cinema se (a) o cadastro diz SALAS, ou (b) a obra VENDEU INGRESSO em
# sala — a bilheteria é prova de destinação teatral e vale mais que um cadastro
# "INDEFINIDO" (O Candidato Honesto, Praia do Futuro, Nise…), ou (c) não tem
# cadastro e não é seriada. Fora: TV/VOD/outros mercados sem passagem por sala.
teatral = pd.to_numeric(b.bilheteria_deflac, errors='coerce').fillna(0) > 0
manter = (seg == 'SALAS DE EXIBIÇÃO') | teatral | ((seg == '') & ~e_seriada)
removidas = b[~manter]
b = b[manter].copy()
print(f'Filtro de escopo (cinema = cadastro SALAS ou bilheteria observada): '
      f'{n0} -> {len(b)} obras · {len(removidas)} removidas '
      f'(TV/VOD/outros mercados sem passagem por sala, '
      f'R$ {removidas.investimento_total_deflac.sum()/1e6:,.0f} mi)')
removidas[['cpb', 'titulo', 'ano', 'categoria', 'segmento_destinacao_inicial',
           'investimento_total_deflac']].to_csv(
    os.path.join(OUT, 'auditoria_escopo_removidas.csv'), sep=';', index=False,
    encoding='utf-8-sig')

# ── 2 · categoria revisada (s43: add-on vira flag) p/ obras FSA ────────────────
oc = pd.read_csv(os.path.join(BASE, 'outputs', 'tabelas', 'obra_chamadas_fsa.csv'),
                 sep=';')
oc['cpb'] = oc.CPB.map(norm_cpb)
b = b.merge(oc[['cpb', 'cat_nova', 'tem_complementacao', 'tem_comercializacao']],
            on='cpb', how='left')

# ── 3 · público/sessões/municípios reais (ABT · RIDAB, por CPB) ────────────────
abt = pd.read_parquet(os.path.join(BASE, 'outputs', 'tabelas', 'abt_obra_fsa.parquet'))
abt['cpb'] = abt.cpb.map(norm_cpb)
ABT_COLS = ['publico_domestico', 'sessoes_total', 'n_municipios']
for c in ABT_COLS:
    abt[c] = pd.to_numeric(abt[c], errors='coerce')
b = b.merge(abt.drop_duplicates('cpb')[['cpb'] + ABT_COLS], on='cpb', how='left')

# ── 4 · recuperação público×PMI (obras com público e sem renda na fonte) ───────
bil = pd.read_parquet(os.path.join(BASE, 'outputs', 'tabelas',
                                   'base_bilheteria_obra.parquet'))
bil['renda_total'] = pd.to_numeric(bil.renda_total, errors='coerce').fillna(0)
bil['publico_total'] = pd.to_numeric(bil.publico_total, errors='coerce').fillna(0)
bil = bil[bil.e_brasileira & bil.cpb.astype(str).str.startswith('B')].copy()
bil['cpb'] = bil.cpb.map(norm_cpb)

# PMI deflacionado mediano por ano (das obras do escopo com renda e público)
pmi_base = b[b.bilheteria_deflac > 0].merge(
    bil[bil.publico_total > 0][['cpb', 'publico_total']], on='cpb', how='inner')
pmi_base['pmi'] = pmi_base.bilheteria_deflac / pmi_base.publico_total
PMI_ANO = pmi_base.groupby('ano')['pmi'].median()
PMI_GERAL = pmi_base['pmi'].median()

so_publico = bil[(bil.publico_total > 0) & (bil.renda_total <= 0)]
so_publico = so_publico.set_index('cpb')['publico_total']
b['publico_pmi'] = b.cpb.map(so_publico)
mask_pmi = (b.bilheteria_deflac <= 0) & b.publico_pmi.notna()
b['renda_pmi_estimada'] = 0.0
b.loc[mask_pmi, 'renda_pmi_estimada'] = b.loc[mask_pmi].apply(
    lambda r: r.publico_pmi * PMI_ANO.get(r.ano, PMI_GERAL), axis=1)
print(f'Recuperação público×PMI: {int(mask_pmi.sum())} obras · '
      f'R$ {b.renda_pmi_estimada.sum()/1e3:,.0f} mil (deflac.)')

# ── 5 · colunas canônicas ──────────────────────────────────────────────────────
b['inv_fsa'] = b.investimento_fsa_deflac
b['inv_renuncia'] = b.investimento_renuncia_total_deflac
b['inv_total'] = b.investimento_total_deflac
b['bilheteria_obs'] = b.bilheteria_deflac
b['janelas_crt'] = b.outras_janelas_deflac
b['receita_ref'] = b.bilheteria_obs + b.renda_pmi_estimada + b.janelas_crt


def instrumento(r):
    a, n = r.inv_fsa > 0, r.inv_renuncia > 0
    return 'Misto FSA+Renúncia' if a and n else \
           'FSA puro' if a else 'Renúncia pura' if n else 'sem inv.'


b['instrumento'] = b.apply(instrumento, axis=1)

# universos — fomento EFETIVO exigido (obra com captação deflacionada zero não
# tem dinheiro público mensurável e sai dos dois universos; são ~62 obras de
# renúncia aprovada sem captação no período)
b['universo_aplicacao'] = b.inv_total > 0
b['universo_retorno'] = b.universo_aplicacao & (
    (b.bilheteria_obs > 0) | (b.renda_pmi_estimada > 0))

# indicadores (definidos APENAS no universo de retorno)
b['retorno_dom'] = np.where(b.universo_retorno & (b.inv_total > 0),
                            b.receita_ref / b.inv_total, np.nan)
b['retorno_intl'] = np.where(b.universo_retorno, b.roi_internacional_0_100, np.nan)
b['tem_intl'] = b.universo_retorno & (
    (b.pontuacao_festivais > 0) | (b.adm_eu_lumiere > 0) | (b.vod_n_plataformas > 0))

b['uf'] = b.uf_requerente.fillna('')
FINAL = ['cpb', 'titulo', 'ano', 'categoria', 'cat_nova', 'chamada',
         'tem_complementacao', 'tem_comercializacao', 'cnpj_produtora',
         'uf', 'tipo_obra', 'segmento_destinacao_inicial', 'instrumento',
         'inv_fsa', 'inv_renuncia', 'inv_total',
         'bilheteria_obs', 'renda_pmi_estimada', 'janelas_crt', 'receita_ref',
         'publico_domestico', 'sessoes_total', 'n_municipios',
         'roi_internacional_0_100', 'pontuacao_festivais', 'adm_eu_lumiere',
         'vod_n_plataformas', 'vod_n_paises', 'total_paises_alcancados',
         'critica_indice_1_5', 'critica_n_fontes', 'critica_confianca',
         'cita_n_papers', 'cita_soma_cit', 'cita_max_cit',
         'universo_aplicacao', 'universo_retorno', 'retorno_dom', 'retorno_intl',
         'tem_intl']
out = b[FINAL].copy()
out.to_parquet(os.path.join(OUT, 'base_obras.parquet'), index=False)
out.to_csv(os.path.join(OUT, 'base_obras.csv'), sep=';', index=False,
           encoding='utf-8-sig')

# ── 6 · sumário / auditoria ────────────────────────────────────────────────────
ret = out[out.universo_retorno]
apl_n = int(out.universo_aplicacao.sum())
print('=' * 74)
print(f'BASE_OBRAS: {len(out)} obras de cinema no escopo · '
      f'universo de aplicação (fomento efetivo): {apl_n}')
print(f'  universo de retorno: {len(ret)} '
      f'({int((ret.bilheteria_obs > 0).sum())} bilheteria observada '
      f'+ {int(((ret.renda_pmi_estimada > 0) & (ret.bilheteria_obs <= 0)).sum())} via público×PMI)')
print(f'  por instrumento (retorno): {ret.instrumento.value_counts().to_dict()}')
inv_t, rec_t = ret.inv_total.sum(), ret.receita_ref.sum()
print(f'  investimento público total (retorno): R$ {inv_t/1e6:,.0f} mi · '
      f'receita ref.: R$ {rec_t/1e6:,.0f} mi')
print(f'  RETORNO DOMÉSTICO AGREGADO = {rec_t/inv_t:.2f}  '
      f'(só observado: {ret.bilheteria_obs.sum()/inv_t:.2f})')
for g, gg in ret.groupby('instrumento'):
    print(f'    {g:<22} n={len(gg):>3} · retorno={gg.receita_ref.sum()/gg.inv_total.sum():.2f}')
apl = out[~out.universo_retorno]
print(f'  fora do retorno (aplicação sem renda): {len(apl)} obras · '
      f'R$ {apl.inv_total.sum()/1e6:,.0f} mi aplicados')
print(f'  sinal internacional (dentro do retorno): {int(ret.tem_intl.sum())} '
      f'({100*ret.tem_intl.mean():.0f}%)')
