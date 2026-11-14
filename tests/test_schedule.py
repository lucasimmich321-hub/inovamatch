"""Cronograma em quadro, prazo sugerido e regressões (PA e falso recorrente) com trechos oficiais gravados."""
import json
from pathlib import Path

import pytest

from nav import goto
from inovamatch.documents import merge_analysis
from inovamatch.extraction import suggest
from inovamatch.matching import PENDING, match
from inovamatch.schedule import date_cell, deadline_fields, parse_schedule, submission_row

FIXTURES = sorted((Path(__file__).resolve().parent / 'fixtures' / 'cronogramas').glob('*.json'))
CASES = [json.loads(p.read_text(encoding='utf-8')) for p in FIXTURES]


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_submission_window_from_official_schedule(case):
    rows = parse_schedule(case['pages'], case['pdf_url'])
    row = submission_row(rows)
    assert {'inicio': row['inicio'], 'fim': row['fim']} == case['expected_submission']
    assert row['page'] and row['evidence'] and row['source'] == case['pdf_url']


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_deadline_is_prefilled_but_not_confirmed(case):
    result = suggest(case['pages'], case['pdf_url'])
    assert result['deadline'] == case['expected_submission']['fim']
    assert result['deadline_confirmed'] is False and result['opening_confirmed'] is False
    assert result['opening_date'] == case['expected_submission']['inicio']
    assert result['deadline_evidence'].startswith('Cronograma, p. ')
    # Prazo sugerido não conta no match: continua pendente até a confirmação humana.
    deadline_row = next(r for r in match(result, {'id': 's'}, {'id': 'p'})['rows'] if r['id'] == 'deadline')
    assert deadline_row['status'] == PENDING


def test_nascer_to_be_defined_rows_are_none():
    nascer = next(c for c in CASES if c['id'] == 'nascer_24_2026')
    rows = {r['etapa']: r for r in parse_schedule(nascer['pages'])}
    assert rows['Pitch Day Regional']['inicio'] is None and rows['Pitch Day Regional']['fim'] is None
    assert rows['Evento Super Pitch Day']['fim'] is None


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_no_false_para_state_and_no_false_recurring(case):
    result = suggest(case['pages'], case['pdf_url'])
    assert not any(isinstance(c.get('expected'), list) and 'PA' in c['expected'] for c in result['criteria'])
    assert result['recurring_schedule'] is False


def test_para_state_only_when_written_as_state():
    pages = [{'page': 1, 'text': '4. DA ELEGIBILIDADE\n4.1. A empresa deverá ser sediada no Estado do Pará.'}]
    assert any(c['field'] == 'state' and c['expected'] == ['PA'] for c in suggest(pages, 'x')['criteria'])
    pages = [{'page': 1, 'text': '4. DA ELEGIBILIDADE\n4.1. Parágrafo primeiro. A empresa deverá ser sediada em Santa Catarina para executar o objeto.'}]
    states = [c['expected'] for c in suggest(pages, 'x')['criteria'] if c['field'] == 'state']
    assert states and all('PA' not in s for s in states)


def test_monthly_bolsista_rule_is_not_recurring_submission():
    text = '5. CRONOGRAMA\n14.1. Será permitida a substituição de bolsista, mediante solicitação, até o dia 5 (cinco) de cada mês.'
    assert suggest([{'page': 1, 'text': text}], 'x')['recurring_schedule'] is False
    text = '4.3.3. Ser submetida na plataforma FAPESC até o dia 10 (dez) de cada mês, conforme cronograma.'
    assert suggest([{'page': 1, 'text': text}], 'x')['recurring_schedule'] is True


@pytest.mark.parametrize('line,expected', [
    ('De 05/05/2026 a 15/06/2026', ('2026-05-05', '2026-06-15', True)),
    ('04/09/2026 a 05/10/2026', ('2026-09-04', '2026-10-05', True)),
    ('21/07/2026', ('2026-07-21', '2026-07-21', True)),
    ('Até 30/06/2026', (None, '2026-06-30', True)),
    ('A definir', (None, None, True)),
    ('Fluxo contínuo, após o lançamento do Edital FAPESC, até 30/06/2028', (None, '2028-06-30', True)),
    ('Resultado divulgado em 10/10/2026 no site', (None, None, False)),
    ('31/02/2026', (None, None, True)),
])
def test_date_cells(line, expected):
    assert date_cell(line) == expected


def test_merge_keeps_confirmed_dates_and_refreshes_suggestion():
    case = next(c for c in CASES if c['id'] == 'gcub_53_2026')
    imported = {**suggest(case['pages'], case['pdf_url']), 'url': case['pdf_url'], 'pages': case['pages']}
    fresh = merge_analysis({'id': 'x', 'title': 't', 'criteria': []}, imported)
    assert fresh['deadline'] == '2026-10-05' and not fresh['deadline_confirmed'] and fresh['schedule']
    confirmed = {'id': 'y', 'title': 't', 'criteria': [], 'deadline': '2026-10-06', 'deadline_confirmed': True,
                 'deadline_evidence': 'Retificação, p. 1', 'opening_date': '2026-09-05', 'opening_confirmed': True,
                 'opening_evidence': 'Retificação'}
    merged = merge_analysis(confirmed, imported)
    assert merged['deadline'] == '2026-10-06' and merged['deadline_confirmed']
    assert merged['opening_date'] == '2026-09-05' and merged['opening_confirmed']


def test_deadline_fields_without_submission_row():
    assert deadline_fields([{'etapa': 'Resultado final', 'inicio': '2026-01-01', 'fim': '2026-01-01', 'page': 1, 'evidence': ''}]) == {}


def test_review_screen_shows_schedule_and_unconfirmed_suggestion():
    from streamlit.testing.v1 import AppTest
    from inovamatch.storage import Store
    case = next(c for c in CASES if c['id'] == 'nascer_24_2026')
    imported = {**suggest(case['pages'], case['pdf_url']), 'url': case['pdf_url'], 'pages': case['pages']}
    call = merge_analysis({'id': 'nascer', 'title': case['title'], 'institution': 'FAPESC', 'url': case['call_url'],
                           'criteria': [], 'relevance': 'Relevante'}, imported)
    data = {}
    Store(data).save('calls', call)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    app.session_state['real_data'] = data
    goto(app, 'Editais')
    assert not app.exception
    assert any('Prazo sugerido: 15/06/2026' in w.value for w in app.warning)
    table = next(d for d in app.dataframe if 'Etapa' in d.value.columns)
    assert 'A definir' in table.value['Fim'].tolist()
