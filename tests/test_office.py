"""Produto para o escritório de projetos: 4 telas, vínculos edital × startup, cofre, checklist, candidaturas e painel."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from inovamatch.crawler import AWAITING, PUBLISHED
from inovamatch.domain import today
from inovamatch.storage import Store

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


@pytest.fixture(autouse=True)
def session_mode(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)


def clean(app):
    assert not app.exception, [x.value for x in app.exception]
    return app


def office_data():
    data = {}
    store = Store(data)
    store.save('startups', {'id': 's-sc', 'name': 'Startup SC', 'state': 'SC', 'cnpj': '', 'documents': []})
    store.save('startups', {'id': 's-pr', 'name': 'Startup PR', 'state': 'PR', 'cnpj': '', 'documents': []})
    store.save('projects', {'id': 'p-sc', 'startup_id': 's-sc', 'name': 'Projeto SC'})
    store.save('projects', {'id': 'p-pr', 'startup_id': 's-pr', 'name': 'Projeto PR'})
    rule = {'id': 'sede', 'field': 'state', 'scope': 'startup', 'op': 'in', 'expected': ['SC'], 'label': 'Sede em SC',
            'confirmed': True, 'validation_status': 'validated', 'mandatory': True, 'source': 'edital.pdf', 'page': 3,
            'evidence': '4.1 A proponente deverá ser sediada em Santa Catarina.'}
    base = {'institution': 'FAPESC', 'url': 'https://fapesc.sc.gov.br/e/', 'criteria': [rule], 'criteria_complete': True,
            'deadline': today().isoformat(), 'deadline_confirmed': True, 'deadline_evidence': 'Cronograma p. 7', 'relevance': 'Relevante'}
    store.save('calls', {**base, 'id': 'pub', 'title': 'Edital publicado', 'review_state': PUBLISHED})
    store.save('calls', {**base, 'id': 'rev', 'title': 'Edital em revisão', 'review_state': AWAITING})
    return data


def open_app(data, page=None):
    app = AppTest.from_file(APP, default_timeout=20).run()
    app.session_state['real_data'] = data
    if page:
        app.sidebar.radio[0].set_value(page).run()
    else:
        app.run()
    return clean(app)


# T3 ------------------------------------------------------------------------------------------

def test_four_screens_and_links_is_the_main_one():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    assert list(app.sidebar.radio[0].options) == ['⟷  Vínculos', '◎  Editais', '◇  Startups', '▦  Painel']
    assert app.session_state['page'] == 'Vínculos'
    for page in ['Editais', 'Startups', 'Painel', 'Vínculos']:
        app.sidebar.radio[0].set_value(page).run()
        clean(app)


def test_links_show_only_published_calls_with_verdict_and_reason():
    app = open_app(office_data())
    edital = next(s for s in app.selectbox if s.label == 'Edital')
    assert [o for o in edital.options] == ['Edital publicado']
    summary = next(d for d in app.dataframe if 'Motivo principal' in d.value.columns).value
    assert summary['Startup'].tolist() == ['Startup SC', 'Startup PR']
    assert summary['Resultado'].tolist() == ['Atende', 'Não atende']
    assert summary['Motivo principal'].tolist()[1] == 'Não atende: Sede em SC'
    next(t for t in app.toggle if t.label == 'Incluir editais ainda em revisão').set_value(True).run()
    clean(app)
    assert len(next(s for s in app.selectbox if s.label == 'Edital').options) == 2


def test_open_link_shows_reasons_and_starts_candidacy():
    data = office_data()
    app = open_app(data)
    reasons = next(d for d in app.dataframe if 'Justificativa' in d.value.columns).value
    assert 'Sede em SC' in reasons['Requisito'].tolist()
    next(b for b in app.button if b.label == 'Iniciar candidatura').click().run()
    clean(app)
    assert app.session_state['real_data']['applications']['pub:p-sc']['status'] == 'Em preparação'


def test_legacy_page_names_and_ai_compare_land_on_links():
    data = office_data()
    app = AppTest.from_file(APP, default_timeout=20)
    app.session_state['real_data'] = data
    # O botão "Comparar com startups" do ai_ui grava estes dois valores (antes do rádio ser desenhado).
    app.session_state['page'] = 'Match Inteligente'
    app.session_state['match_call'] = 'rev'
    app.run()
    clean(app)
    assert app.session_state['page'] == 'Vínculos'
    assert next(s for s in app.selectbox if s.label == 'Edital').value == 'rev'


def test_panel_has_coming_soon_startup_view():
    app = open_app(office_data(), 'Painel')
    assert any('Em breve' in h.value and 'Visão da startup' in h.value for h in app.get('html'))
