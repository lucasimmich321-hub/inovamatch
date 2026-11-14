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
