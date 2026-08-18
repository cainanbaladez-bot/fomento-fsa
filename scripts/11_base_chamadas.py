# -*- coding: utf-8 -*-
"""
71_base_chamadas.py — BASE AGREGADA POR CATEGORIA DE CHAMADA (dois universos).

Sobe a régua de 70_base_obras um nível de agregação: para cada categoria de
seleção (cat_nova das obras FSA; instrumento p/ renúncia), mede:
  · lado APLICAÇÃO — tudo que foi contratado (obras, dinheiro, taxa de estreia);
  · lado RETORNO   — só as duas pontas confirmadas (retorno doméstico agregado
    = Σreceita ÷ Σinvestimento TOTAL, retorno internacional médio, sinal intl).

Entrada: outputs/bases/base_obras.parquet
Saída:   outputs/bases/base_chamadas.parquet + .csv
"""
import os
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'outputs', 'bases')

b = pd.read_parquet(os.path.join(OUT, 'base_obras.parquet'))
b = b[b.universo_aplicacao].copy()

# rótulo da linha: categoria revisada (obras FSA) ou o grupo de renúncia;
# fallback da categoria longa normalizado para o mesmo rótulo curto da cat_nova
CURTO = {
    'FSA Pontuação Bilheteria e Roteiro — Distribuidora': 'Bilheteria · Distribuidora',
    'FSA Pontuação Bilheteria e Roteiro — Produtora': 'Bilheteria · Produtora',
    'FSA Pontuação Festivais e Roteiro': 'Festivais · Pontuação',
    'FSA Automático Bilheteria': 'Automático Bilheteria',
    'FSA Automático Festivais': 'Automático Festivais',
    'FSA Complementação': 'Add-on FSA (Compl./Comerc.)',
    'FSA Comercialização / Distribuição': 'Add-on FSA (Compl./Comerc.)',
    'FSA Coprodução Internacional': 'Coprodução Intl',
    'FSA SAV/MINC / Arranjos Regionais': 'Arranjos Regionais',
}
b['grupo'] = b.cat_nova.fillna(b.categoria.map(lambda c: CURTO.get(str(c), str(c))))


def agrega(g):
    ret = g[g.universo_retorno]
    inv_ret = ret.inv_total.sum()
    return pd.Series({
        'n_aplicacao': len(g),
        'inv_fsa_aplicacao': g.inv_fsa.sum(),
        'inv_renuncia_aplicacao': g.inv_renuncia.sum(),
        'inv_total_aplicacao': g.inv_total.sum(),
        'n_retorno': len(ret),
        'taxa_estreia': len(ret) / len(g) if len(g) else np.nan,
        'inv_total_retorno': inv_ret,
        'receita_ref': ret.receita_ref.sum(),
        'bilheteria_obs': ret.bilheteria_obs.sum(),
        'retorno_dom': ret.receita_ref.sum() / inv_ret if inv_ret > 0 else np.nan,
        'retorno_dom_obs': ret.bilheteria_obs.sum() / inv_ret if inv_ret > 0 else np.nan,
        'retorno_intl_medio': ret.retorno_intl.mean(),
        'n_sinal_intl': int(ret.tem_intl.sum()),
        'pct_sinal_intl': ret.tem_intl.mean() * 100 if len(ret) else np.nan,
        'publico': ret.publico_domestico.sum(),
        'pct_receita_estimada': 100 * (ret.janelas_crt.sum() + ret.renda_pmi_estimada.sum())
                                / ret.receita_ref.sum() if ret.receita_ref.sum() > 0 else np.nan,
    })


ch = b.groupby('grupo').apply(agrega).reset_index()
ch = ch.sort_values('inv_total_aplicacao', ascending=False)
ch.to_parquet(os.path.join(OUT, 'base_chamadas.parquet'), index=False)
ch.to_csv(os.path.join(OUT, 'base_chamadas.csv'), sep=';', index=False,
          encoding='utf-8-sig')

pd.set_option('display.width', 160)
print(f'BASE_CHAMADAS: {len(ch)} grupos')
print(ch[['grupo', 'n_aplicacao', 'n_retorno', 'taxa_estreia', 'retorno_dom',
          'retorno_intl_medio', 'pct_sinal_intl']].round(2).to_string(index=False))
