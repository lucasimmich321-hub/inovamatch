"""Lote 1: fluxo contínuo, filtro e selo de status, limpeza de UI, acessibilidade e higiene."""
import re
from datetime import timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from inovamatch.acceptance import reference_cases
from inovamatch.call_status import call_situation, CONTINUOUS, CONTINUOUS_PENDING, UNKNOWN
from inovamatch.domain import today
from inovamatch.extraction import suggest
from inovamatch.matching import match
from inovamatch.storage import Store

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / 'app.py')


@pytest.fixture(autouse=True)
def session_mode(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)


def clean(app):
    assert not app.exception, [x.value for x in app.exception]
    return app


def fixture_call(fixture_id, **extra):
    """Edital montado a partir do snapshot oficial, como o radar faria após ler o PDF."""
    fixture = next(f for f in reference_cases() if f['id'] == fixture_id)
    analysis = suggest(fixture['pages'], fixture['pdf_url'])
    return {'id': fixture_id, 'title': fixture['title'], 'institution': 'FAPESC', 'url': fixture['call_url'],
            'criteria': analysis['criteria'], 'recurring_schedule': analysis['recurring_schedule'],
            'deadline_candidates': analysis['deadline_candidates'], 'criteria_complete': False, **extra}


CONFIRMED_FLOW = {'registration_status': CONTINUOUS, 'registration_status_confirmed': True,
                  'registration_status_evidence': 'Propostas recebidas em fluxo contínuo (item 7).'}


# T1 ---------------------------------------------------------------------

def test_flag_without_confirmation_is_continuous_to_confirm():
    assert call_situation({'recurring_schedule': True}) == CONTINUOUS_PENDING


def test_continuous_confirmed_in_review():
    assert call_situation({'recurring_schedule': True, **CONFIRMED_FLOW}) == CONTINUOUS
    # Confirmação humana com evidência basta, mesmo sem a pista da extração.
    assert call_situation(dict(CONFIRMED_FLOW)) == CONTINUOUS


def test_no_flag_and_no_confirmation_stays_unknown():
    assert call_situation({}) == UNKNOWN
    # Confirmação sem evidência não vale.
    assert call_situation({**CONFIRMED_FLOW, 'registration_status_evidence': ''}) == UNKNOWN


def test_continuous_never_computes_deadline_and_respects_guards():
    deadline = (today() - timedelta(days=3)).isoformat()
    call = {**CONFIRMED_FLOW, 'deadline': deadline, 'deadline_confirmed': True, 'deadline_evidence': 'x'}
    assert call_situation(call) == CONTINUOUS  # data vencida não vira "Encerrado"
    # Conflito não resolvido continua prevalecendo: nada é confirmado.
    assert call_situation({**CONFIRMED_FLOW, 'conflicts': [{'id': 'c', 'resolved': False}]}) == UNKNOWN
    assert call_situation({'recurring_schedule': True, 'conflicts': [{'id': 'c', 'resolved': False}]}) == UNKNOWN
    # Prazo confirmado à mão prevalece sobre a simples pista de recorrência.
    future = (today() + timedelta(days=10)).isoformat()
    flagged = {'recurring_schedule': True, 'deadline': future, 'deadline_confirmed': True, 'deadline_evidence': 'x',
               'opening_date': today().isoformat(), 'opening_confirmed': True, 'opening_evidence': 'y'}
    assert call_situation(flagged) == 'Aberto'


def test_match_semantics_unchanged_by_continuous_status():
    startup = {'id': 's', 'name': 'S', 'state': 'SC'}
    project = {'id': 'p', 'startup_id': 's', 'name': 'P'}
    base = fixture_call('fapesc_54_2024')
    before = match(base, startup, project)
    after = match({**base, **CONFIRMED_FLOW}, startup, project)
    assert (before['verdict'], before['blockers'], before['pending']) == (after['verdict'], after['blockers'], after['pending'])


def test_review_form_confirms_continuous_and_rejects_dates_together():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    app.sidebar.radio[0].set_value('Radar de Editais').run()
    next(r for r in app.radio if r.label == 'Origem').set_value('Cadastro manual').run()
    next(x for x in app.text_input if x.label == 'Título do edital *').set_value('Chamada em fluxo contínuo')
    next(x for x in app.text_input if x.label == 'Referência da fonte *').set_value('Regulamento')
    next(b for b in app.button if b.label == 'Criar edital para revisão').click().run()
    clean(app)
    status = next(s for s in app.selectbox if s.label == 'Situação declarada explicitamente pela fonte')
    assert CONTINUOUS in status.options
    status.set_value(CONTINUOUS)
    next(x for x in app.text_area if x.label == 'Trecho oficial que declara a situação das inscrições').set_value('Fluxo contínuo, item 7.')
    next(x for x in app.checkbox if x.label.startswith('Conferi esta situação')).check()
    next(x for x in app.date_input if x.label.startswith('Data-limite de inscrição')).set_value(today() + timedelta(days=5))
    next(x for x in app.text_area if x.label.startswith('Trecho e página que comprovam')).set_value('Página 2.')
    next(x for x in app.checkbox if x.label == 'Confirmei o prazo na fonte e nas retificações').check()
    next(b for b in app.button if b.label == 'Salvar revisão do edital').click().run()
    clean(app)
    assert any('Fluxo contínuo não tem data-limite' in e.value for e in app.error)
    next(x for x in app.checkbox if x.label == 'Confirmei o prazo na fonte e nas retificações').uncheck()
    next(b for b in app.button if b.label == 'Salvar revisão do edital').click().run()
    clean(app)
    call = next(iter(app.session_state['real_data']['calls'].values()))
    assert call_situation(call) == CONTINUOUS and not call['deadline_confirmed']
    assert any('Sem data-limite · fluxo contínuo' in i.value for i in app.info)


# T2 ---------------------------------------------------------------------

def test_status_groups_with_official_fixtures():
    from inovamatch.filters import filter_calls, status_group, STATUS_FILTERS
    flow_pending = fixture_call('fapesc_54_2024')          # "em Fluxo Contínuo" no título e no cronograma
    flow_confirmed = fixture_call('fapesc_66_2025', **CONFIRMED_FLOW)
    closed = fixture_call('fapesc_66_2025', id='closed', recurring_schedule=False,
                          deadline=(today() - timedelta(days=1)).isoformat(), deadline_confirmed=True, deadline_evidence='p. 6')
    unknown = fixture_call('fapesc_66_2025', id='unknown', recurring_schedule=False)
    calls = [flow_pending, flow_confirmed, closed, unknown]
    assert flow_pending['recurring_schedule'] and flow_confirmed['recurring_schedule']
    assert [status_group(c) for c in calls] == ['Fluxo contínuo', 'Fluxo contínuo', 'Encerrado', 'Não confirmado']
    ids = lambda statuses: [c['id'] for c in filter_calls(calls, statuses=statuses)]
    assert ids(['Fluxo contínuo']) == ['fapesc_54_2024', 'fapesc_66_2025']
    assert ids(['Encerrado', 'Não confirmado']) == ['closed', 'unknown']
    assert ids(['Aberto']) == []
    assert ids(None) == ids([]) == [c['id'] for c in calls]
    assert set(STATUS_FILTERS) == {'Aberto', 'Fluxo contínuo', 'Encerrado', 'Futuro', 'Não confirmado'}


def test_radar_status_pills_filter_the_list():
    from inovamatch.filters import STATUS_FILTERS
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    data = {}
    store = Store(data)
    store.save('calls', fixture_call('fapesc_54_2024', title='Inova Talentos'))
    store.save('calls', fixture_call('fapesc_66_2025', title='Horizonte Europa', recurring_schedule=False))
    app.session_state['real_data'] = data
    app.sidebar.radio[0].set_value('Radar de Editais').run()
    clean(app)
    pills = next(p for p in app.get('button_group') if p.label == 'Situação das inscrições')
    assert list(pills.options) == list(STATUS_FILTERS)
    pills.set_value(['Fluxo contínuo']).run()
    clean(app)
    titles = next(t for t in app.dataframe if 'Título' in t.value.columns).value['Título'].tolist()
    assert titles == ['Inova Talentos']


# T3 ---------------------------------------------------------------------

def test_status_badge_has_text_and_color_class():
    import app as ui
    for call, text, css in [({'recurring_schedule': True}, CONTINUOUS_PENDING, 's-flow-pending'),
                            (dict(CONFIRMED_FLOW), CONTINUOUS, 's-flow'), ({}, UNKNOWN, 's-unknown')]:
        html = ui.status_badge(call)
        assert css in html and f'Inscrições: {text}' in html
        assert ui.status_text(call).endswith(text)
    assert ui.deadline_label(dict(CONFIRMED_FLOW)) == 'Sem data-limite · fluxo contínuo'


# T4 ---------------------------------------------------------------------

def test_timestamps_and_scan_headers_in_portuguese():
    import app as ui
    assert ui.when('2026-11-14T09:05:33-03:00') == '14/11/2026 09:05'
    assert ui.when(None) == 'Não registrada' and ui.when('ontem') == 'ontem'
    rows = ui.scan_rows({'results': [{'institution': 'FAPESC', 'url': 'https://x', 'found': 3, 'added': 2,
                                      'status': 'Consulta concluída', 'error': ''}]})
    assert list(rows[0]) == ['Instituição', 'Links encontrados', 'Novos', 'Situação da consulta', 'Erro', 'Página consultada']


def test_scan_progress_caption_is_cleared(monkeypatch):
    from inovamatch import radar

    def fake_scan(store, notices, source_ids=None, progress=None):
        progress('Consultando FAPESC…')
        return {'sources': [], 'found': 0, 'added': 0, 'errors': [], 'searched_at': '2026-11-14T09:05:00-03:00',
                'results': [{'institution': 'FAPESC', 'url': 'https://x', 'found': 0, 'added': 0, 'status': 'Consulta concluída', 'error': ''}]}
    monkeypatch.setattr(radar, 'scan', fake_scan)
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    app.sidebar.radio[0].set_value('Radar de Editais').run()
    next(b for b in app.button if b.label == 'Buscar editais agora').click().run()
    clean(app)
    captions = [c.value for c in app.caption]
    assert not any('Consultando' in c for c in captions)
    assert any(c.startswith('Última busca: 14/11/2026 09:05') for c in captions)
