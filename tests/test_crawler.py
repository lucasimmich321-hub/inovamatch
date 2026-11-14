"""Crawler FAPESC com HTML real gravado (tests/fixtures/fapesc_html) e PDF gerado no teste. Sem rede."""
from pathlib import Path

import fitz
import pytest
import requests
from streamlit.testing.v1 import AppTest

from inovamatch import crawler
from inovamatch.call_status import call_situation
from inovamatch.crawler import (EDITAL, NOTICIA, OUTRO, RESULTADO, RETIFICACAO, AWAITING, PUBLISHED, LISTINGS,
                                DiskCache, FapescFetcher, classify, crawl, edital_year, publication_blockers, relevance)
from inovamatch.domain import today
from inovamatch.filters import filter_calls, status_group
from inovamatch.radar import parse_listing
from inovamatch.storage import Store

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / 'tests' / 'fixtures' / 'fapesc_html'
APP = str(ROOT / 'app.py')
DETAIL_65 = 'https://fapesc.sc.gov.br/edital-suplementar-de-subvencao-economica-fapesc-n-o-65-2025-programa-horizonte-europa-2026-2027/'
PDF_65 = 'https://fapesc.sc.gov.br/wp-content/uploads/2025/11/Edital-65_2025-Horizonte-Europa-assinado.pdf'


def html(name):
    return (HTML / f'{name}.html').read_bytes()


def make_pdf(text):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 550, 800), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


EDITAL_TEXT = ('EDITAL SUPLEMENTAR DE SUBVENÇÃO ECONÔMICA FAPESC N.º 65/2025\n'
               '2. DO OBJETIVO\n2.1. Apoiar empresas de base tecnológica e startups com subvenção econômica à inovação.\n'
               '4. DA ELEGIBILIDADE\n4.1. A proponente deverá ser empresa sediada no Estado de Santa Catarina.\n')


class FakeFetcher:
    """Serve respostas gravadas; URL ausente simula falha de rede."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def fetch(self, url, limit=0):
        self.calls.append(url)
        if url not in self.routes:
            raise requests.ConnectionError('sem rede no teste')
        body, ctype = self.routes[url]
        return body, ctype, url


def routes():
    return {LISTINGS['abertas']: (html('abertas'), 'text/html'),
            LISTINGS['andamento']: (html('andamento'), 'text/html'),
            LISTINGS['encerradas']: (html('encerradas'), 'text/html'),
            DETAIL_65: (html('edital_65_2025'), 'text/html'),
            PDF_65: (make_pdf(EDITAL_TEXT), 'application/pdf')}


# Um teste por tipo de item -------------------------------------------------------------

def test_classifies_real_editais_from_open_listing():
    items = parse_listing(html('abertas'), LISTINGS['abertas'])
    assert len(items) == 3 and all(classify(i['title'], i['url']) == EDITAL for i in items)


def test_classifies_real_retificacoes_from_notices():
    items = parse_listing(html('comunicados'), 'https://fapesc.sc.gov.br/comunicados/')
    kinds = {classify(i['title'], i['url']) for i in items}
    assert len(items) == 15 and kinds == {RETIFICACAO}


def test_classifies_real_resultados_from_results_page():
    items = parse_listing(html('resultados'), 'https://fapesc.sc.gov.br/divulgacao-dos-resultados/')
    kinds = [classify(i['title'], i['url']) for i in items]
    assert len(items) == 100 and EDITAL not in kinds
    # Retificação de resultado conta como retificação; nenhum dos dois é edital.
    assert kinds.count(RESULTADO) == 98 and kinds.count(RETIFICACAO) == 2


def test_classifies_news_and_other():
    assert classify('FAPESC participa de evento de inovação em Joinville', 'https://fapesc.sc.gov.br/fapesc-participa/') == NOTICIA
    assert classify('Manual de cadastramento no SIGFAPESC', 'https://fapesc.sc.gov.br/manual/') == OUTRO
    # "Edital" sem número (página institucional) não é tratado como edital.
    assert classify('Editais da FAPESC: como participar', 'https://fapesc.sc.gov.br/editais/') == OUTRO


def test_year_and_relevance_rules():
    assert edital_year('EDITAL DE CHAMADA PÚBLICA FAPESC N.º 24/2026 PROGRAMA NASCER') == 2026
    assert edital_year('Chamada sem número') is None
    assert relevance({'title': 'Programa de subvenção a startups'})[0] == 'Relevante'
    assert relevance({'title': 'Pós-graduação', 'summary': 'apoio com tecnologia'})[0] == 'Talvez'
    assert relevance({'title': 'Mobilidade internacional de estudantes'})[0] == 'Fora do foco'


# Crawl completo ---------------------------------------------------------------------------

def run(tmp_path, fake=None, **kwargs):
    fake = fake or FakeFetcher(routes())
    store = Store({})
    fetcher = FapescFetcher(fetcher=fake, cache=DiskCache(tmp_path / 'cache'))
    return store, crawl(store, fetcher=fetcher, **kwargs), fake, fetcher


def test_crawl_separates_open_closed_and_reads_only_open_pdfs(tmp_path):
    store, report, fake, _ = run(tmp_path, min_year=2025)
    calls = store.all('calls')
    open_calls = [c for c in calls if not c['source_closed']]
    assert report['found'] == 114 and report['editais'] == 114 and report['added'] == 114 and report['open'] == 3
    assert len(open_calls) == 3 and all(c['review_state'] == AWAITING for c in calls)
    assert all(status_group(c) == 'Encerrado' for c in calls if c['source_closed'])
    # Só o edital 65 tinha página/PDF disponíveis; os outros dois falham sem quebrar a coleta.
    read = next(c for c in open_calls if '65/2025' in c['title'])
    assert read['documents'] and read['pdf_url'] == PDF_65 and read['relevance'] == 'Relevante'
    assert any(c['field'] == 'state' and c['page'] == 1 and c['evidence'] for c in read['criteria'])
    failed = [c for c in open_calls if c is not read and not c.get('documents')]
    assert len(failed) == 2 and all('Leitura automática do PDF falhou' in c['extraction_warnings'][0] for c in failed)
    assert report['read'] == 1 and len(report['errors']) == 2
    # PDFs de editais encerrados nunca são baixados.
    assert not any(u.endswith('.pdf') and u != PDF_65 for u in fake.calls)
    # Padrão da lista: sem encerrados.
    assert len(filter_calls(calls, include_closed=False)) == 3


def test_year_filter_never_drops_open_listing(tmp_path):
    store, report, _, _ = run(tmp_path, min_year=2026, read_pdfs=False)
    titles = [c['title'] for c in store.all('calls')]
    assert any('54/2024' in t for t in titles)  # aberto em fluxo contínuo, mesmo antigo
    assert report['too_old'] > 0 and not any('/2025' in t for t in titles if 'em andamento' in t)


def test_cache_avoids_second_download_and_respects_budget(tmp_path):
    store, _, fake, fetcher = run(tmp_path, min_year=2025)
    first = len(fake.calls)
    fetcher2 = FapescFetcher(fetcher=fake, cache=DiskCache(tmp_path / 'cache'))
    crawl(store, fetcher=fetcher2, min_year=2025)
    # 3 listagens vêm do cache; o 65/2025 já lido não é relido; só as duas páginas que falharam são tentadas de novo.
    assert fetcher2.cache_hits == 3 and fake.calls[first:] == [c for c in fake.calls[first:] if c not in (PDF_65, DETAIL_65)]
    assert len(fake.calls) - first == 2
    budget = FapescFetcher(fetcher=FakeFetcher(routes()), use_cache=False, max_requests=1)
    report = crawl(Store({}), fetcher=budget, min_year=2025)
    assert any('Limite de requisições' in e for e in report['errors'])


def test_allowlist_blocks_other_hosts_and_offsite_redirects(tmp_path):
    fetcher = FapescFetcher(fetcher=FakeFetcher({}), use_cache=False)
    with pytest.raises(ValueError, match='fora do domínio'):
        fetcher.fetch('https://example.com/edital.pdf')

    class Redirecting(FakeFetcher):
        def fetch(self, url, limit=0):
            return b'x', 'text/html', 'https://outro.gov.br/pagina'
    with pytest.raises(ValueError, match='redirecionou'):
        FapescFetcher(fetcher=Redirecting({}), use_cache=False).fetch(LISTINGS['abertas'])


def test_network_failure_is_reported_not_raised(tmp_path):
    store, report, _, _ = run(tmp_path, fake=FakeFetcher({}))
    assert report['found'] == 0 and len(report['errors']) == 3 and store.all('scans')


def test_recrawl_preserves_human_review_and_tracks_source_listing(tmp_path):
    store, _, fake, _ = run(tmp_path, min_year=2025, read_pdfs=False)
    call = next(c for c in store.all('calls') if '65/2025' in c['title'])
    store.save('calls', {**call, 'review_state': PUBLISHED, 'criteria_complete': True})
    # A FAPESC move o 65/2025 para "em andamento".
    moved = dict(fake.routes)
    moved[LISTINGS['abertas']] = (html('abertas').replace(b'fapesc-n-o-65-2025', b'fapesc-n-o-99-2099'), 'text/html')
    inner = html('abertas').split(b'<main>', 1)[1].split(b'</main>', 1)[0]
    moved[LISTINGS['andamento']] = (html('andamento').replace(b'</main>', inner + b'</main>', 1), 'text/html')
    crawl(store, fetcher=FapescFetcher(fetcher=FakeFetcher(moved), use_cache=False), min_year=2025, read_pdfs=False)
    again = store.get('calls', call['id'])
    assert again['review_state'] == PUBLISHED and again['criteria_complete']
    assert again['source_closed'] and call_situation(again) == 'Encerrado'


def test_publication_requires_review_and_confirmed_schedule():
    call = {'criteria_complete': False}
    assert len(publication_blockers(call)) == 2
    ok = {'criteria_complete': True, 'deadline_confirmed': True, 'deadline_evidence': 'p. 3',
          'deadline': today().isoformat()}
    assert publication_blockers(ok) == []
    assert publication_blockers({**ok, 'source_closed': True})


def test_publish_button_in_review_screen():
    app = AppTest.from_file(APP, default_timeout=20).run()
    data = {}
    store = Store(data)
    ready = store.save('calls', {'title': 'Edital pronto', 'institution': 'FAPESC', 'url': 'https://fapesc.sc.gov.br/x/', 'criteria': [
        {'id': 'c1', 'field': 'state', 'scope': 'startup', 'op': 'in', 'expected': ['SC'], 'label': 'Sede', 'confirmed': True,
         'source': 'x', 'page': 1, 'evidence': 'sede em SC'}], 'criteria_complete': True, 'deadline': today().isoformat(),
        'deadline_confirmed': True, 'deadline_evidence': 'p. 3', 'review_state': AWAITING, 'relevance': 'Relevante'})
    app.session_state['real_data'] = data
    app.sidebar.radio[0].set_value('Radar de Editais').run()
    assert not app.exception
    button = next(b for b in app.button if b.label == 'Publicar para as startups')
    assert not button.disabled
    button.click().run()
    assert not app.exception
    assert app.session_state['real_data']['calls'][ready['id']]['review_state'] == PUBLISHED


def test_demo_has_open_calls_marked_as_simulated():
    from inovamatch.demo import load_demo
    store = Store({})
    load_demo(store)
    calls = store.all('calls')
    assert any(call_situation(c) == 'Aberto' for c in calls)
    assert all(c['simulated'] and c['title'].startswith('[SIMULADO]') for c in calls)
    assert all('SIMULADO' in c['opening_evidence'] for c in calls)
