# -*- coding: utf-8 -*-
"""
Helpers de PRESENÇA Wikipedia/Wikidata para o índice de soft power (Texto 1, bloco 1C).

Método adaptado do Pantheon/Hidalgo (MIT Media Lab, Nature sdata201575): o alcance
simbólico global de uma obra é proxyado por L = nº de edições de idioma da Wikipedia
em que ela tem artigo, complementado por pageviews (atenção) e sitelinks (notabilidade).

urllib puro (o .venv não tem `requests`). Cache por IMDb ID em JSON → reruns grátis,
espelhando o cache do TMDb (s25). Resolve obra→Wikidata por IMDb ID (propriedade P345).
"""
import urllib.request, urllib.parse, json, os, time

UA = {'User-Agent': 'FSA-academic-research/1.0 (contact: cainanbaladez@yahoo.com.br)'}
# sitelinks que NÃO são Wikipedias de idioma (não contam para L)
EXCLUDE = {'commonswiki', 'specieswiki', 'metawiki', 'sourceswiki', 'mediawikiwiki',
           'wikidatawiki', 'foundationwiki'}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def qid_from_imdb(tt):
    """Item Wikidata (Q...) cujo IMDb ID (P345) == tt; None se não houver."""
    url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'query', 'list': 'search', 'srsearch': f'haswbstatement:P345={tt}', 'format': 'json'})
    hits = _get(url).get('query', {}).get('search', [])
    return hits[0]['title'] if hits else None


def sitelinks(qid):
    url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'wbgetentities', 'ids': qid, 'props': 'sitelinks', 'format': 'json'})
    return _get(url)['entities'][qid].get('sitelinks', {})


def pageviews(lang, title, start='2024010100', end='2024123100'):
    """Soma de pageviews mensais de um artigo num idioma (Wikimedia REST; dados ≥ 2015)."""
    proj = lang.replace('_', '-') + '.wikipedia'
    t = urllib.parse.quote(title.replace(' ', '_'), safe='')
    url = (f'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/'
           f'{proj}/all-access/all-agents/{t}/monthly/{start}/{end}')
    try:
        return sum(it['views'] for it in _get(url).get('items', []))
    except Exception:
        return 0


def measure(tt, cache_dir, sleep=0.03):
    """Resolve e mede uma obra por IMDb ID, com cache local (1 JSON por tconst).
    Retorna dict: tconst, qid, L, L_nonpten, sitelinks, pv2024, langs."""
    os.makedirs(cache_dir, exist_ok=True)
    fp = os.path.join(cache_dir, f'{tt}.json')
    if os.path.exists(fp):
        return json.load(open(fp, encoding='utf-8'))
    rec = {'tconst': tt, 'qid': None, 'L': 0, 'L_nonpten': 0, 'sitelinks': 0, 'pv2024': 0, 'langs': []}
    try:
        q = qid_from_imdb(tt); rec['qid'] = q
        if q:
            sl = sitelinks(q); rec['sitelinks'] = len(sl)
            wikis = sorted(k[:-4] for k in sl if k.endswith('wiki') and k not in EXCLUDE)
            rec['langs'] = wikis
            rec['L'] = len(wikis)
            rec['L_nonpten'] = len([l for l in wikis if l not in ('pt', 'en')])
            pv = 0
            for k, v in sl.items():
                if k.endswith('wiki') and k not in EXCLUDE:
                    pv += pageviews(k[:-4], v['title']); time.sleep(sleep)
            rec['pv2024'] = pv
    except Exception as e:
        rec['erro'] = f'{type(e).__name__}: {e}'
    json.dump(rec, open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
    return rec
