# -*- coding: utf-8 -*-
"""
analise_renuncia_art3.py — das obras de renúncia que CHEGARAM EM SALAS, quanto
veio do Art. 3º e quanto veio do Art. 3º-A da Lei do Audiovisual (8.685/93).

Pergunta do Cainan (2026-08-10), sequência da análise de renda de exibição.

DE ONDE SAI O DADO (e por que não é a tabela óbvia)
  · `renuncia_fiscal.parquet` do RIDAB TEM as colunas `captado_art3` e
    `captado_art3a` — mas elas estão **100% nulas** nas 4.215 linhas. A tabela
    limpa carrega o esquema sem os valores. (Tarefa para o RIDAB.)
  · O dado com valor por artigo está em `captacao_por_projeto_investidor`,
    na fonte "valores-captados-por-projeto-incentivado-em-reais-r-2002-a-julho
    -de-2020.csv" (`tipo_fluxo='captado'`, um registro por projeto/ano/mecanismo).
    A outra fonte do mesmo parquet (xlsx 2007–2019, por projeto E investidor)
    NÃO entra: somaria duas vezes o mesmo dinheiro.
  · Ligação com a obra: `obras_fomento_indireto` (nº SALIC ↔ CPB). Os três
    cadastros gravam o SALIC em formatos diferentes ('00-0040', '000040',
    '23795'); a chave é o número **só com dígitos**.

RÉGUA
  · "Chegou em salas" = obra do master 1995–2024 no escopo cinema com
    bilheteria > 0 (mesma regra de `analise_renda_exibicao.py`).
  · Deflator IPCA base R$ dez/2024 — a série do RIDAB **começa em 2008**, então
    o real é reportado para 2008–2020 e o período 2002–2007 sai em nominal,
    declarado à parte. Nunca extrapolo deflator.
Rodar: .\\.venv\\Scripts\\python.exe scripts\\analise_renuncia_art3.py
"""
import os
import re
import sys
import csv
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RID = os.path.join(BASE, 'data', 'ridab_cleaned')

nc = lambda s: re.sub(r'[^0-9A-Z]', '', str(s).upper())
sal = lambda s: re.sub(r'\D', '', str(s)).lstrip('0')          # SALIC comparável
br = lambda v, d=1: f'{v:,.{d}f}'.replace(',', '§').replace('.', ',').replace('§', '.')

FONTE_PROJ = 'valores-captados-por-projeto-incentivado-em-reais'
MEC = {'art_3_lei_8_685_93': 'Art. 3º', 'art_3_a_lei_8_685_93': 'Art. 3º-A'}

# ── 1 · captação por projeto, separada por artigo ─────────────────────────────
C = pd.read_parquet(os.path.join(RID, 'captacao_por_projeto_investidor.parquet'))
C = C[(C.tipo_fluxo == 'captado')
      & (C.mecanismo.isin(MEC))
      & (C.fonte_arquivo.str.contains(FONTE_PROJ, na=False))].copy()
C['valor'] = pd.to_numeric(C.valor_brl_nominal, errors='coerce').fillna(0)
C['ano'] = pd.to_numeric(C.ano, errors='coerce')
C['k'] = C.salic.map(sal)
C = C[C.valor > 0]
# parte do CSV da ANCINE traz salic='-' (registro sem número de projeto): esse
# dinheiro existe, mas não tem como ser ligado a uma obra. Sai da conta, declarado.
_sem = C[C.k == '']
print(f'sem nº SALIC no cadastro (não ligável a obra): R$ {br(_sem.valor.sum() / 1e6)} mi '
      f'de R$ {br(C.valor.sum() / 1e6)} mi ({br(100 * _sem.valor.sum() / C.valor.sum(), 1)}%) '
      f'— concentrado em 2002–2012, quase todo Art. 3º')
C = C[C.k != '']

DEF = pd.read_parquet(os.path.join(RID, 'deflator_ipca.parquet'))[['ano', 'fator_real_2024']]
C = C.merge(DEF, on='ano', how='left')
C['real'] = C.valor * C.fator_real_2024          # NaN antes de 2008, de propósito
print(f'captação por artigo: {len(C)} registros · {C.k.nunique()} projetos · '
      f'{int(C.ano.min())}–{int(C.ano.max())}')

# ── 2 · SALIC → CPB → obras que chegaram em salas ─────────────────────────────
OFI = pd.read_parquet(os.path.join(RID, 'obras_fomento_indireto.parquet'))
OFI['k'] = OFI.numero_salic.map(sal)
OFI['cpbn'] = OFI.cpb.map(nc)
OFI = OFI[(OFI.k != '') & (OFI.cpbn.str.len() > 4)].drop_duplicates(['k', 'cpbn'])

M = pd.read_excel(os.path.join(BASE, 'data', 'legado', 'tabela_consolidada_obras.xlsx'))
M['cpbn'] = M.CPB.map(nc)
M['ano_obra'] = pd.to_numeric(M.Ano, errors='coerce')
M['bilheteria'] = pd.to_numeric(M['Bilheteria Deflac. (R$)'], errors='coerce').fillna(0)
PMI = float(pd.read_parquet(os.path.join(RID, 'preco_ingresso.parquet')).pmi_real_2024.median())
_n = lambda s: pd.to_numeric(str(s).strip().replace('.', '').replace(',', '.'), errors='coerce')
_o = []
with open(os.path.join(BASE, 'data', 'ridab_raw', 'filmes_lancados_captacao_1995_2022.csv'),
          encoding='utf-8-sig', errors='replace') as fh:
    for i, row in enumerate(csv.reader(fh, delimiter=';')):
        if i >= 2 and len(row) >= 13:
            _o.append({'cpbn': nc(row[1]), 'pub': _n(row[11])})
O = pd.DataFrame(_o)
O = O[(O.pub > 0) & (O.cpbn.str.len() > 4)].groupby('cpbn', as_index=False).pub.max()
M = M.merge(O, on='cpbn', how='left')
_rec = (M.bilheteria <= 0) & (M.pub > 0)
M.loc[_rec, 'bilheteria'] = M.loc[_rec, 'pub'] * PMI
R = pd.read_parquet(os.path.join(RID, 'obras.parquet'))
R['cpbn'] = R.cpb.map(nc)
M = M.merge(R.drop_duplicates('cpbn')[['cpbn', 'segmento_destinacao_inicial']], on='cpbn', how='left')
M = M[((M.segmento_destinacao_inicial == 'SALAS DE EXIBIÇÃO') | (M.bilheteria > 0))
      & (~M.Categoria.astype(str).str.contains('_tv_excluir', na=False))]
SALAS = set(M.loc[M.bilheteria > 0, 'cpbn'])
print(f'obras no escopo cinema: {len(M)} · com bilheteria (chegaram em salas): {len(SALAS)}')

C = C.merge(OFI[['k', 'cpbn']], on='k', how='left')
C['em_sala'] = C.cpbn.isin(SALAS)
_lig = C.cpbn.notna()
print(f'ligação SALIC→CPB: {br(100 * C.loc[_lig, "valor"].sum() / C.valor.sum(), 1)}% do dinheiro '
      f'({C.loc[_lig, "k"].nunique()} de {C.k.nunique()} projetos)\n')


def bloco(df, titulo):
    print(f'{"═" * 74}\n{titulo}\n{"═" * 74}')
    tot_n = df.valor.sum()
    d08 = df[df.ano >= 2008]
    print(f'{"artigo":<12}{"projetos":>10}{"obras":>8}{"nominal (mi)":>15}{"real 2024 (mi)":>17}')
    for mk, ml in MEC.items():
        s = df[df.mecanismo == mk]
        s8 = d08[d08.mecanismo == mk]
        print(f'{ml:<12}{s.k.nunique():>10}{s.cpbn.nunique():>8}{br(s.valor.sum() / 1e6):>15}'
              f'{br(s8.real.sum() / 1e6):>17}')
    print(f'{"TOTAL":<12}{df.k.nunique():>10}{df.cpbn.nunique():>8}{br(tot_n / 1e6):>15}'
          f'{br(d08.real.sum() / 1e6):>17}')
    a3, a3a = [df[df.mecanismo == m].valor.sum() for m in MEC]
    if a3 + a3a:
        print(f'\nproporção (nominal, série inteira): Art. 3º {br(100 * a3 / (a3 + a3a), 1)}% · '
              f'Art. 3º-A {br(100 * a3a / (a3 + a3a), 1)}%')
    pre = df[df.ano < 2008].valor.sum()
    print(f'fora do deflator (2002–2007, só nominal): R$ {br(pre / 1e6)} mi '
          f'({br(100 * pre / tot_n, 1)}% do nominal)\n')


bloco(C[C.em_sala], 'OBRAS QUE CHEGARAM EM SALAS — captação por artigo')
bloco(C, 'TODOS OS PROJETOS COM ART. 3º/3º-A (com e sem sala, e sem ligação a CPB)')

# ── 2b · a curva de cada artigo no tempo (por que o real inverte a proporção) ─
print('═' * 74)
print('CAPTAÇÃO NOMINAL POR PERÍODO — R$ mi (projetos com SALIC)')
print('═' * 74)
C['per'] = pd.cut(C.ano, [2001, 2007, 2012, 2016, 2020],
                  labels=['2002–07', '2008–12', '2013–16', '2017–20'])
_p = C.pivot_table(index='per', columns='mecanismo', values='valor', aggfunc='sum', observed=False).fillna(0) / 1e6
_p = _p.rename(columns=MEC)[[MEC['art_3_lei_8_685_93'], MEC['art_3_a_lei_8_685_93']]]
print(_p.round(1).to_string())
print('\nO Art. 3º é o mecanismo antigo (existe desde a Lei 8.685/93) e domina o começo\n'
      'da série; o Art. 3º-A, criado pela MP 2.228-1/01, só ganha escala a partir de 2013\n'
      'e é o que responde pela maior parte do dinheiro recente. É por isso que a proporção\n'
      'muda entre nominal e real: o Art. 3º tem mais dinheiro em anos que deflacionam mais.\n')

# ── 3 · o que o Art. 3º-A tem de diferente: concentração por obra ─────────────
print(f'{"═" * 74}\nEM SALAS · as 12 obras que mais captaram pelos dois artigos (nominal)\n{"═" * 74}')
top = (C[C.em_sala].pivot_table(index='cpbn', columns='mecanismo', values='valor', aggfunc='sum')
       .fillna(0).rename(columns=MEC))
top['total'] = top.sum(axis=1)
_M = M.drop_duplicates('cpbn').set_index('cpbn')
tit, bilh = _M.Projeto, _M.bilheteria
for cpb, r in top.nlargest(12, 'total').iterrows():
    nome = str(tit.loc[cpb])[:38].title() if cpb in tit.index else '(sem título no master)'
    b_ = bilh.loc[cpb] / 1e6 if cpb in bilh.index else 0
    print(f'  {nome:<40} Art.3º {br(r["Art. 3º"] / 1e6, 2):>6} · '
          f'3º-A {br(r["Art. 3º-A"] / 1e6, 2):>6} mi  |  bilheteria R$ {br(b_)} mi')

# ── 4 · sanidade: quanto o Art.3º/3º-A representa da renúncia TOTAL em salas ──
M['ren_total_nom'] = (pd.to_numeric(M['Renúncia Art.3/3-A/39 (R$)'], errors='coerce').fillna(0)
                      + pd.to_numeric(M['Renúncia Outros Mec. (R$)'], errors='coerce').fillna(0))
_em = M[M.bilheteria > 0]
art_nom = C[C.em_sala].valor.sum()
print('\n' + '═' * 74)
print('SANIDADE — o Art. 3º/3º-A dentro da renúncia total (obras em salas)')
print('═' * 74)
print(f'renúncia total declarada no master (nominal) .... R$ {br(_em.ren_total_nom.sum() / 1e6)} mi')
print(f'captado por Art. 3º + 3º-A (nominal, esta conta) . R$ {br(art_nom / 1e6)} mi'
      f'  = {br(100 * art_nom / _em.ren_total_nom.sum(), 1)}%')
print('o resto é Art. 1º/1º-A, Art. 39, Funcines, Rouanet e leis estaduais/municipais —')
print('mecanismos que esta tabela também traz, mas que não foram objeto da pergunta.')
