# -*- coding: utf-8 -*-
"""
analise_renda_exibicao.py — quanto as SALAS de cinema arrecadaram com filmes de
fomento público, separando FSA e renúncia fiscal.

Pergunta do Cainan (2026-08-10): "no modelo mais amplo da base, quanto as salas
obtiveram de renda bruta (50% da renda total) exclusivamente com filmes
financiados pelo fomento público, separando FSA e renúncia fiscal".

RÉGUA
  · Universo AMPLO = a carteira histórica 1995–2024 (o mesmo master de
    `scripts/12`, com a recuperação da bilheteria anterior a 2010 pela listagem
    da OCA: público × PMI real 2024). O recorte 2014–2023 sai junto, para
    comparação.
  · "Renda das salas" = 50% da RENDA DE BILHETERIA da obra. Os 50% são a praxe
    de mercado do elo de exibição (a mesma usada no argumento, alegação 6) —
    é PARÂMETRO, não medição: a divisão real varia por contrato e por semana.
  · Só bilheteria. Janelas CRT, TV e VOD não passam por sala e ficam fora.
  · Deflação IPCA, base R$ dez/2024, como em todo o projeto.

SEPARAR FSA × RENÚNCIA — duas leituras, porque a obra costuma ter as duas fontes
  (A) RATEIO PROPORCIONAL (principal): a bilheteria de cada obra é dividida
      entre as fontes na proporção do dinheiro que cada uma pôs naquela obra.
      É o tratamento que o painel legado usava ("receita proporcional ao FSA").
  (B) REGIME EXCLUSIVO: só as obras financiadas por uma única fonte entram na
      conta dela; as mistas ficam num balde próprio, sem rateio.
Rodar: .\\.venv\\Scripts\\python.exe scripts\\analise_renda_exibicao.py
"""
import os
import re
import sys
import csv
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SHARE_EXIBICAO = 0.50          # parâmetro declarado, não medição
nc = lambda s: re.sub(r'[^0-9A-Z]', '', str(s).upper())
br = lambda v, d=0: f'{v:,.{d}f}'.replace(',', '§').replace('.', ',').replace('§', '.')


# ── 1 · master de obras 1995–2024 (mesma leitura de scripts/12) ───────────────
M = pd.read_excel(os.path.join(BASE, 'data', 'legado', 'tabela_consolidada_obras.xlsx'))
M['cpbn'] = M.CPB.map(nc)
M['ano'] = pd.to_numeric(M.Ano, errors='coerce')
for col, novo in [('Valor FSA Deflac. (R$2024)', 'inv_fsa'),
                  ('Renúncia Total Deflac. (R$2024)', 'inv_renuncia'),
                  ('Investimento Total Deflac. (R$2024)', 'inv_total'),
                  ('Bilheteria Deflac. (R$)', 'bilheteria')]:
    M[novo] = pd.to_numeric(M[col], errors='coerce').fillna(0)

# recuperação da bilheteria anterior a 2010 (público OCA × PMI real 2024)
PMI = float(pd.read_parquet(os.path.join(BASE, 'data', 'ridab_cleaned',
                                         'preco_ingresso.parquet')).pmi_real_2024.median())
_num_br = lambda s: pd.to_numeric(str(s).strip().replace('.', '').replace(',', '.'), errors='coerce')
_oca = []
with open(os.path.join(BASE, 'data', 'ridab_raw', 'filmes_lancados_captacao_1995_2022.csv'),
          encoding='utf-8-sig', errors='replace') as fh:
    for i, row in enumerate(csv.reader(fh, delimiter=';')):
        if i < 2 or len(row) < 13:
            continue
        _oca.append({'cpbn': nc(row[1]), 'publico_oca': _num_br(row[11])})
OCA = pd.DataFrame(_oca)
OCA = OCA[(OCA.publico_oca > 0) & (OCA.cpbn.str.len() > 4)].groupby('cpbn', as_index=False).publico_oca.max()
M = M.merge(OCA, on='cpbn', how='left')
_rec = (M.bilheteria <= 0) & (M.publico_oca > 0)
M['estimada'] = _rec
M.loc[_rec, 'bilheteria'] = M.loc[_rec, 'publico_oca'] * PMI

# escopo cinema (mesma regra do projeto): cadastro de salas OU bilheteria observada
R = pd.read_parquet(os.path.join(BASE, 'data', 'ridab_cleaned', 'obras.parquet'))
R['cpbn'] = R.cpb.map(nc)
R = R.drop_duplicates('cpbn')[['cpbn', 'segmento_destinacao_inicial']]
M = M.merge(R, on='cpbn', how='left')
M = M[(M.segmento_destinacao_inicial == 'SALAS DE EXIBIÇÃO') | (M.bilheteria > 0)]
M = M[~M.Categoria.astype(str).str.contains('_tv_excluir', na=False)]

# só obra COM fomento público e COM bilheteria (é o que gera renda de sala)
M['fomento'] = M.inv_fsa + M.inv_renuncia
F = M[(M.fomento > 0) & (M.bilheteria > 0)].copy()


def conta(df, rotulo):
    bil = df.bilheteria.sum()
    exib = bil * SHARE_EXIBICAO
    # (A) rateio proporcional ao dinheiro de cada fonte na obra
    sh_fsa = (df.inv_fsa / df.fomento).clip(0, 1)
    bil_fsa = (df.bilheteria * sh_fsa).sum()
    bil_ren = bil - bil_fsa
    # (B) regime exclusivo
    so_fsa = df[(df.inv_fsa > 0) & (df.inv_renuncia <= 0)]
    so_ren = df[(df.inv_renuncia > 0) & (df.inv_fsa <= 0)]
    misto = df[(df.inv_fsa > 0) & (df.inv_renuncia > 0)]
    est = df[df.estimada].bilheteria.sum()

    print(f'\n{"═" * 78}\n{rotulo}\n{"═" * 78}')
    print(f'obras com fomento e bilheteria .......... {len(df):>6}')
    print(f'dinheiro público nessas obras ........... R$ {br(df.fomento.sum() / 1e6)} mi'
          f'  (FSA {br(df.inv_fsa.sum() / 1e6)} · renúncia {br(df.inv_renuncia.sum() / 1e6)})')
    print(f'RENDA DE BILHETERIA (bruta, 100%) ....... R$ {br(bil / 1e6)} mi'
          f'   [{br(100 * est / bil, 1)}% estimada via público × PMI]')
    print(f'► RENDA DAS SALAS (50% da bilheteria) ... R$ {br(exib / 1e6)} mi'
          f'   = R$ {br(exib / 1e9, 2)} bi')
    print('\n(A) RATEIO PROPORCIONAL ao investimento de cada fonte na obra')
    print(f'    FSA ......... bilheteria R$ {br(bil_fsa / 1e6):>9} mi'
          f'  →  salas R$ {br(bil_fsa * SHARE_EXIBICAO / 1e6):>9} mi ({br(100 * bil_fsa / bil, 1)}%)')
    print(f'    Renúncia .... bilheteria R$ {br(bil_ren / 1e6):>9} mi'
          f'  →  salas R$ {br(bil_ren * SHARE_EXIBICAO / 1e6):>9} mi ({br(100 * bil_ren / bil, 1)}%)')
    print('\n(B) REGIME EXCLUSIVO (a obra conta inteira, e só se tiver uma única fonte)')
    for nome, sub in [('só FSA', so_fsa), ('só renúncia', so_ren), ('as duas (misto)', misto)]:
        b = sub.bilheteria.sum()
        print(f'    {nome:<16} {len(sub):>5} obras · bilheteria R$ {br(b / 1e6):>9} mi'
              f'  →  salas R$ {br(b * SHARE_EXIBICAO / 1e6):>9} mi ({br(100 * b / bil, 1)}%)')
    return exib


print(f'PMI real 2024 usado na recuperação pré-2010: R$ {PMI:.2f}')
print(f'master no escopo cinema: {len(M)} obras · com fomento e bilheteria: {len(F)}')
conta(F, 'UNIVERSO AMPLO — carteira histórica 1995–2024')
conta(F[(F.ano >= 2014) & (F.ano <= 2023)], 'RECORTE DO TRABALHO — 2014–2023')

# ── quebra por período: um total de 30 anos esconde o ritmo ──────────────────
print(f'\n{"═" * 78}\nPOR PERÍODO — renda das salas (50% da bilheteria), R$ mi de 2024\n{"═" * 78}')
print(f'{"período":<12}{"obras":>7}{"salas total":>14}{"via FSA":>12}{"via renúncia":>15}{"% estimada":>13}')
for ini, fim in [(1995, 1999), (2000, 2004), (2005, 2009), (2010, 2013), (2014, 2018), (2019, 2024)]:
    sub = F[(F.ano >= ini) & (F.ano <= fim)]
    if not len(sub):
        continue
    b = sub.bilheteria.sum()
    bf = (sub.bilheteria * (sub.inv_fsa / sub.fomento).clip(0, 1)).sum()
    est = sub[sub.estimada].bilheteria.sum()
    print(f'{ini}–{str(fim)[2:]:<7}{len(sub):>7}{br(b * SHARE_EXIBICAO / 1e6):>14}'
          f'{br(bf * SHARE_EXIBICAO / 1e6):>12}{br((b - bf) * SHARE_EXIBICAO / 1e6):>15}'
          f'{br(100 * est / b, 0) + "%":>13}')

# quanto do mercado de sala isso representa, quando o dado permite comparar
try:
    bd = pd.read_parquet(os.path.join(BASE, 'data', 'ridab_cleaned',
                                      'bilheteria_por_filme_ano.parquet'))
    print(f'\n{"─" * 78}\nnota: tabelas de mercado disponíveis para contextualizar '
          f'({len(bd)} linhas em bilheteria_por_filme_ano)')
except Exception as e:
    print('\n(sem tabela de mercado para contexto:', str(e)[:60], ')')
