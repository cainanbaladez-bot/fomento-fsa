# -*- coding: utf-8 -*-
"""
12_base_produtoras.py — BASE AGREGADA POR GRUPO ECONÔMICO (recorte AMPLO).

REGRA DA PARTE III (decisão Cainan 2026-08-08/09) — a unidade muda, e a régua
muda junto, de propósito:

  · As Partes I e II perguntam sobre a DECISÃO DO EDITAL, e por isso vivem no
    recorte 2014–2023: só ali existe variedade de chamadas suficiente para
    comparar regra com regra (antes de 2009 há 2 a 5 chamadas ativas e o FSA
    quase não contratou — comparar critério de seleção ali seria anedota com
    casas decimais).
  · A Parte III pergunta sobre a EMPRESA, e empresa não respeita janela. A tese
    central da parte — o fundo financiou a entrada e não a trajetória — é
    imensurável em dez anos. Por isso a produtora é medida na CARTEIRA INTEIRA,
    1995–2024, a partir do master de obras do estudo anterior.

  A Parte III, portanto, NÃO fecha com as Partes I e II. É proposital e está
  declarado no texto. Para quem quiser reconciliar, cada grupo traz também as
  colunas `*_recorte`, medidas na mesma janela das outras partes.

TITULARIDADE (decisão Cainan 2026-08-09): uma obra tem UM titular e o dinheiro
e o retorno são contados nele, uma vez só. Titular = proponente do contrato
(84% das obras do master); onde não há contrato, requerente do CPB no RIDAB
(100% de cobertura). Onde os dois existem e divergem (4%), vale o proponente.
NÃO há camada de coprodução: a obra conta uma vez, para o titular. Quem ficou de
fora de uma obra que coproduziu, ficou.

Entradas: data/legado/tabela_consolidada_obras.xlsx (master 1995–2024)
          outputs/bases/base_obras.parquet (recorte, p/ as colunas de ponte)
          outputs/tabelas/base_financiamento_obra.parquet (proponente por CPB)
          data/ridab_cleaned/obras.parquet · grupos_economicos.parquet
Saídas:   outputs/bases/base_produtoras.parquet + .csv
          outputs/bases/grupo_economico_map.csv
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

cn = lambda x: re.sub(r'\D', '', str(x)).zfill(14)
nc = lambda s: re.sub(r'[^0-9A-Z]', '', str(s).upper())
vazio = lambda c: (not isinstance(c, str)) or c.strip('0') == ''

# ── 1 · master de obras, 1995–2024 ────────────────────────────────────────────
M = pd.read_excel(os.path.join(BASE, 'data', 'legado',
                               'tabela_consolidada_obras.xlsx'))
M['cpbn'] = M.CPB.map(nc)
M['ano'] = pd.to_numeric(M.Ano, errors='coerce')
for col, novo in [('Valor FSA Deflac. (R$2024)', 'inv_fsa'),
                  ('Renúncia Total Deflac. (R$2024)', 'inv_renuncia'),
                  ('Investimento Total Deflac. (R$2024)', 'inv_total'),
                  ('Bilheteria Deflac. (R$)', 'bilheteria_obs'),
                  ('Outras Janelas Deflac. (R$2024)', 'janelas_crt'),
                  ('ROI Internacional (0-100)', 'intl'),
                  ('Pontuação Festivais', 'fest'),
                  ('Adm. EU — Lumière', 'adm_eu'),
                  ('VOD Intl — N Plataformas', 'vod')]:
    M[novo] = pd.to_numeric(M[col], errors='coerce').fillna(0)
M['receita_ref'] = M.bilheteria_obs + M.janelas_crt

# ── 1b · RECUPERAÇÃO DA BILHETERIA ANTERIOR A 2010 (2026-08-09) ───────────────
# O master só tem bilheteria de 2010 em diante (0% nos anos 90, 5% em 2000–04,
# 10% em 2005–09, 87% de 2010). Sem isso a carteira histórica classifica errado:
# a Diler & Associados, com os sete filmes da Xuxa, aparecia devolvendo 0,07
# porque a bilheteria deles estava zerada na fonte.
# A fonte que resolve JÁ ESTÁ NO RIDAB, em bruto: a listagem da OCA "Filmes
# Brasileiros Lançados Comercialmente em Salas de Exibição — 1995 a 2022", com
# CPB, público e renda por obra. (Deveria virar tabela limpa do RIDAB; hoje é
# lida do raw, como já se faz com a renúncia.)
# A renda de lá é NOMINAL e o deflator do RIDAB só começa em 2008, então NÃO
# uso a renda: uso o PÚBLICO, que não precisa de deflator, valorado ao preço
# médio do ingresso REAL de 2024 (mediana da série `preco_ingresso`, R$ 20,94 —
# a série é notavelmente estável, entre R$ 19,88 e R$ 21,99). É a mesma receita
# de `src/base_obra.py`: público × PMI. Fica declarado como ESTIMATIVA a preço
# real constante, não como renda observada.
import csv

PMI = float(pd.read_parquet(os.path.join(BASE, 'data', 'ridab_cleaned',
                                         'preco_ingresso.parquet')).pmi_real_2024.median())
_num_br = lambda s: pd.to_numeric(
    str(s).strip().replace('.', '').replace(',', '.'), errors='coerce')

_oca = []
with open(os.path.join(BASE, 'data', 'ridab_raw',
                       'filmes_lancados_captacao_1995_2022.csv'),
          encoding='utf-8-sig', errors='replace') as fh:
    for i, row in enumerate(csv.reader(fh, delimiter=';')):
        if i < 2 or len(row) < 13:
            continue
        _oca.append({'cpbn': nc(row[1]), 'titulo': row[2], 'ano_oca': _num_br(row[0]),
                     'publico_oca': _num_br(row[11])})
OCA = pd.DataFrame(_oca)
OCA = OCA[(OCA.publico_oca > 0) & (OCA.cpbn.str.len() > 4)]
OCA = OCA.groupby('cpbn', as_index=False).publico_oca.max()
M = M.merge(OCA, on='cpbn', how='left')
_rec = (M.bilheteria_obs <= 0) & (M.publico_oca > 0)
M['receita_estimada_pmi'] = _rec
M.loc[_rec, 'bilheteria_obs'] = M.loc[_rec, 'publico_oca'] * PMI
M['receita_ref'] = M.bilheteria_obs + M.janelas_crt
print(f'  [bilheteria histórica OCA] {int(_rec.sum())} obras recuperadas '
      f'(público × R$ {PMI:.2f}) → R$ {M.loc[_rec, "bilheteria_obs"].sum()/1e6:,.0f} mi '
      f'a preço real de 2024')

# escopo cinema, mesma regra da obra: cadastro de salas OU bilheteria observada
R = pd.read_parquet(os.path.join(BASE, 'data', 'ridab_cleaned', 'obras.parquet'))
R['cpbn'] = R.cpb.map(nc)
R['req'] = R.cnpj_requerente.map(cn)
R = R.drop_duplicates('cpbn')[['cpbn', 'req', 'segmento_destinacao_inicial',
                               'uf_requerente']]
M = M.merge(R, on='cpbn', how='left')
n0 = len(M)
M = M[(M.segmento_destinacao_inicial == 'SALAS DE EXIBIÇÃO')
      | (M.bilheteria_obs > 0)]
M = M[~M.Categoria.astype(str).str.contains('_tv_excluir', na=False)]
print(f'master: {n0} obras 1995–2024 → {len(M)} no escopo cinema')

# ── 2 · titularidade: proponente do contrato, requerente como reserva ─────────
fin = pd.read_parquet(os.path.join(BASE, 'outputs', 'tabelas',
                                   'base_financiamento_obra.parquet'))
fin['cpbn'] = fin.cpb.map(nc)
fin['c'] = fin.cnpj_proponente.map(cn)
_val = 'valor_r2024'
fin = fin[(fin.cpbn.str.len() > 4) & (~fin.c.map(vazio))]
prop = (fin.sort_values(_val, ascending=False).drop_duplicates('cpbn')
        .set_index('cpbn').c)
M['titular'] = M.cpbn.map(prop).astype('object')
_falta = M.titular.map(vazio)
M.loc[_falta, 'titular'] = M.loc[_falta, 'req']
M['titular'] = M.titular.astype('object')
M = M[(~M.titular.map(vazio)) & (M.inv_total > 0)].copy()
print(f'  titular: {int((~_falta).sum())} por proponente do contrato · '
      f'{int(_falta.sum())} por requerente do CPB → {len(M)} obras com titular')

# ── 3 · grupo econômico: grafo da Ancine ∪ razão social normalizada ───────────
AG = pd.read_parquet(os.path.join(BASE, 'data', 'ridab_cleaned',
                                  'agentes_economicos.parquet'))
AG['c'] = AG.cnpj.map(cn)
NOME = AG.drop_duplicates('c').set_index('c').razao_social.to_dict()
UF = AG.drop_duplicates('c').set_index('c').uf.to_dict()
NOME.update(fin.dropna(subset=['razao_proponente'])
            .drop_duplicates('c').set_index('c').razao_proponente.to_dict())

SUF = r'\b(LTDA|S/?A|SA|EIRELI|EIRELLI|ME|EPP|MEI)\b'


def norm_razao(s):
    s = (unicodedata.normalize('NFKD', str(s))
         .encode('ascii', 'ignore').decode().upper())
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    return re.sub(r'\s+', ' ', re.sub(SUF, ' ', s)).strip()


_par = {}


def _find(x):
    _par.setdefault(x, x)
    while _par[x] != x:
        _par[x] = _par[_par[x]]
        x = _par[x]
    return x


def _uni(x, y):
    rx, ry = _find(x), _find(y)
    if rx != ry:
        _par[rx] = ry


alvo = set(M.titular)
GE = pd.read_parquet(os.path.join(BASE, 'data', 'ridab_cleaned',
                                  'grupos_economicos.parquet'))
n_grafo = 0
for a_, b_ in zip(GE.cnpj.map(cn), GE.cnpj_associado.map(cn)):
    if a_ in alvo or b_ in alvo:
        _uni(a_, b_)
        n_grafo += 1
por_nome, n_nome = {}, 0
for c in alvo:
    rn = norm_razao(NOME.get(c, ''))
    if rn:
        if rn in por_nome:
            _uni(por_nome[rn], c)
            n_nome += 1
        else:
            por_nome[rn] = c
M['grupo'] = M.titular.map(_find)

# ── 4 · agregação por grupo (carteira inteira) ────────────────────────────────
CORTE = (2014, 2023)


def agrega(g):
    rec_ = g[g.receita_ref > 0]
    j = g[(g.ano >= CORTE[0]) & (g.ano <= CORTE[1])]
    return pd.Series({
        'n_obras': len(g), 'n_estreadas': int((g.bilheteria_obs > 0).sum()),
        'taxa_estreia': (g.bilheteria_obs > 0).mean(),
        'publico': g.publico_oca.fillna(0).sum(),
        'n_receita_estimada': int(g.receita_estimada_pmi.sum()),
        'ano_primeira': g.ano.min(), 'ano_ultima': g.ano.max(),
        'inv_fsa': g.inv_fsa.sum(), 'inv_renuncia': g.inv_renuncia.sum(),
        'inv_total': g.inv_total.sum(),
        'receita_ref': g.receita_ref.sum(), 'bilheteria_obs': g.bilheteria_obs.sum(),
        'retorno_dom_carteira': g.receita_ref.sum() / g.inv_total.sum(),
        'melhor_intl': g.intl.max(), 'retorno_intl_medio': g.intl.mean(),
        'n_sinal_intl': int(((g.fest > 0) | (g.adm_eu > 0) | (g.vod > 0)).sum()),
        'adm_eu': g.adm_eu.sum(),
        'so_fsa': bool((g.inv_renuncia <= 0).all()),
        'so_renuncia': bool((g.inv_fsa <= 0).all()),
        # ponte com as Partes I e II — a mesma empresa, medida na janela
        'n_obras_recorte': len(j), 'inv_recorte': j.inv_total.sum(),
        'receita_recorte': j.receita_ref.sum(),
        'retorno_recorte': (j.receita_ref.sum() / j.inv_total.sum()
                            if j.inv_total.sum() > 0 else np.nan),
        'melhor_intl_recorte': (j.intl.max() if len(j) else 0.0),
    })


p = M.groupby('grupo').apply(agrega, include_groups=False).reset_index()
_maior = M.loc[M.groupby('grupo').inv_total.idxmax()][['grupo', 'titular']]
p = p.merge(_maior, on='grupo')
p['razao_social'] = p.titular.map(NOME)
p['uf'] = p.titular.map(UF)
p['n_cnpj'] = p.grupo.map(M.groupby('grupo').titular.nunique())
p['pre_2006'] = p.ano_primeira < 2006

# ── 5 · perfis — metodologia ORIGINAL do estudo anterior ──────────────────────
# Limiares idênticos aos de fomento-audiovisual/scripts/02::_classificar_cluster
# (R$ 2024). NÃO ajustar para acomodar nomes: a tipologia só é defensável porque
# os cortes foram escritos antes de se olhar quem cai onde. Único acréscimo
# (Cainan, 2026-08-08): o residual `Pequeno Porte` juntava quem devolveu alguma
# coisa com quem nunca estreou nada e foi quebrado em dois — sem parâmetro novo.
REC_DUPLO, REC_ESCALA, ROI_DOM_MIN, INV_ALTO = 2.5e6, 10e6, 0.6, 5e6


def perfil(r):
    intl_qualificado = r.melhor_intl >= 13
    if r.receita_ref >= REC_DUPLO and intl_qualificado:
        return 'Duplo Retorno'
    escala = r.receita_ref >= REC_ESCALA
    eficiencia = r.retorno_dom_carteira > ROI_DOM_MIN and r.receita_ref >= REC_DUPLO
    if (escala or eficiencia) and not intl_qualificado:
        return 'Retorno Doméstico'
    if intl_qualificado:
        return 'Retorno Internacional'
    if r.inv_total > INV_ALTO:
        return 'Fomento Baixo Retorno'
    if r.receita_ref > 0 or r.n_sinal_intl > 0:
        return 'Pequeno Porte com algum retorno'
    return 'Pequeno Porte sem retorno'


p['perfil'] = p.apply(perfil, axis=1)
p = p.sort_values('inv_total', ascending=False)
(M[['titular', 'grupo']].drop_duplicates()
 .merge(p[['grupo', 'razao_social', 'perfil']], on='grupo', how='left')
 .rename(columns={'titular': 'cnpj_produtora'})
 .to_csv(os.path.join(OUT, 'grupo_economico_map.csv'), sep=';', index=False,
         encoding='utf-8-sig'))
p.to_parquet(
    os.path.join(OUT, 'base_produtoras.parquet'), index=False)
p.to_csv(
    os.path.join(OUT, 'base_produtoras.csv'), sep=';', index=False,
    encoding='utf-8-sig')

# ── 6 · sumário + cobertura por década (a fonte de festivais é rala no passado)
ORDEM = ['Duplo Retorno', 'Retorno Doméstico', 'Retorno Internacional',
         'Fomento Baixo Retorno', 'Pequeno Porte com algum retorno',
         'Pequeno Porte sem retorno']
print('=' * 78)
print(f'BASE_PRODUTORAS (carteira 1995–2024): {M.titular.nunique()} CNPJs → '
      f'{len(p)} grupos (grafo {n_grafo} arestas · razão social {n_nome} fusões)')
print(f'  {int(p.n_obras.sum())} obras · R$ {p.inv_total.sum()/1e9:.2f} bi · '
      f'receita R$ {p.receita_ref.sum()/1e9:.2f} bi · '
      f'retorno agregado {p.receita_ref.sum()/p.inv_total.sum():.2f}')
print(f'  no recorte 2014–2023: {int(p.n_obras_recorte.sum())} obras · '
      f'R$ {p.inv_recorte.sum()/1e9:.2f} bi (ponte com as Partes I e II)')
print(f'  anteriores a 2006: {int(p.pre_2006.sum())} grupos')
print(p.groupby('perfil').apply(lambda s: pd.Series({
    'grupos': len(s), 'obras': int(s.n_obras.sum()),
    'inv_mi': round(s.inv_total.sum() / 1e6),
    'receita_mi': round(s.receita_ref.sum() / 1e6),
    'retorno': round(s.receita_ref.sum() / s.inv_total.sum(), 2),
    'ticket_anual_mediano': round(s.inv_total.median() / 10),
    'pct_pre2006': round(100 * s.pre_2006.mean()),
}), include_groups=False).reindex(ORDEM).to_string())

M['dec'] = (M.ano // 5) * 5
print('\nCobertura das fontes por época (declarar no texto — o passado é mais ralo):')
print(M.groupby('dec').apply(lambda g: pd.Series({
    'obras': len(g),
    'pct_com_bilheteria': round(100 * (g.bilheteria_obs > 0).mean()),
    'pct_com_festival': round(100 * (g.fest > 0).mean()),
    'pct_com_intl': round(100 * (g.intl > 0).mean()),
}), include_groups=False).to_string())

print('\nTop 12 por investimento:')
print(p.head(12)[['razao_social', 'uf', 'n_cnpj', 'n_obras', 'ano_primeira',
                  'inv_total', 'retorno_dom_carteira', 'melhor_intl', 'perfil']]
      .round(2).to_string(index=False))
