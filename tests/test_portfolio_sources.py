from datetime import timedelta
import pytest
from inovamatch.demo import load_demo
from inovamatch.domain import today
from inovamatch.filters import filter_calls
from inovamatch.matching import PASS, FAIL, PENDING, evaluate, match
from inovamatch.portfolio import overview, recalculate, register_application
from inovamatch.radar import scan, validate_url
from inovamatch.sources import SOURCES
from inovamatch.storage import Store


def c(**changes):
    return {'id': 'r', 'label': 'Regra', 'field': 'state', 'scope': 'startup', 'op': 'eq', 'expected': 'SC',
            'confirmed': True, 'mandatory': True, 'source': 'edital.pdf', 'evidence': 'Exigência explícita.', **changes}


@pytest.mark.parametrize('criterion,startup,project,status', [
    (c(), {'state': 'sc'}, {}, PASS),
    (c(op='neq'), {'state': 'SC'}, {}, FAIL),
    (c(op='not_in', expected=['SC']), {'state': 'PR'}, {}, PASS),
    (c(field='sector', op='contains', expected='tecnologia'), {'sector': 'Tecnologia da informação'}, {}, PASS),
    (c(field='trl', scope='project', op='eq', expected=4.0), {}, {'trl': 4}, PASS),
    (c(field='expenses', scope='project', op='disjoint', expected=['Salários']), {}, {'expenses': ['Salários']}, FAIL),
    (c(field='partners', scope='project', op='present'), {}, {'partners': []}, PENDING),
])
def test_additional_operators(criterion, startup, project, status):
    assert evaluate(criterion, startup, project)['status'] == status


def test_a_mandatory_alignment_failure_blocks_independently_of_dimension_totals():
    call = {'criteria': [c(field='theme', scope='project', op='in', expected=['Saúde'], dimension='alignment')],
            'criteria_complete': True, 'deadline': (today() + timedelta(days=5)).isoformat(),
            'deadline_confirmed': True, 'deadline_evidence': 'Até a data.'}
    result = match(call, {}, {'theme': 'Tecnologia'})
    assert result['verdict'] == 'Com impedimentos'
    assert result['dimensions']['alignment']['blockers'] == 1
    assert set(result['dimensions']) == {'eligibility', 'alignment', 'readiness'}


@pytest.mark.parametrize('sqlite', [False, True])
def test_scale_recalculation_after_edit_and_application_tracking(sqlite, tmp_path):
    store = Store(path=tmp_path / 'db.sqlite' if sqlite else None)
    load_demo(store)
    assert recalculate(store) == 6
    assert len(store.all('analyses')) == 6
    startup = store.get('startups', 'demo-verde')
    project = store.get('projects', 'project-demo-verde')
    call = store.get('calls', 'demo-call-1')
    register_application(store, call, startup, project)
    stats = overview(store)
    assert stats['startups'] == 3 and stats['projects'] == 3 and stats['preparing'] == 1
    assert stats['eligible'] == 1
    store.save('startups', {**startup, 'state': 'PR'})
    assert recalculate(store, startup_id=startup['id']) == 2
    assert overview(store)['eligible'] == 0
    assert store.get('analyses', 'demo-call-1:project-demo-verde')['verdict'] == 'Com impedimentos'


def test_source_failure_does_not_drop_successful_sources(monkeypatch):
    from inovamatch.radar import Fetcher
    def fake_fetch(self, url, limit=0):
        if 'finep' in url:
            raise ValueError('Conteúdo dinâmico indisponível')
        return b'<main><a href="https://fapesc.sc.gov.br/edital-001/">Edital de Chamada Publica FAPESC 001/2026</a></main>', 'text/html', url
    monkeypatch.setattr(Fetcher, 'fetch', fake_fetch)
    store = Store()
    report = scan(store, source_ids=['finep', 'fapesc'])
    assert len(report['errors']) == 1 and report['found'] == 1 and report['added'] == 1
    assert len(report['results']) == 2
    assert store.all('calls')[0]['institution'] == 'FAPESC'


def test_source_parser_ignores_navigation_procurement_and_standalone_amendments():
    html = '''<nav><a href="/fundo-verde/outro/">Editais e outras chamadas públicas</a></nav><main>
    <a href="/chamada1.pdf">Edital CAMP Viva Agua - Inscrições encerradas</a>
    <a href="/retificacao.pdf">Edital de Retificação nº 8</a>
    <a href="/pregao.pdf">Edital de Pregão nº 10/2026</a></main>'''
    calls = SOURCES['brde'].parse(html, 'https://www.brde.com.br/fundo-verde/')
    assert len(calls) == 1 and 'encerradas' in calls[0]['source_status'].lower()
    assert not calls[0]['deadline_confirmed']


def test_filtering_does_not_estimate_unknown_funding_or_deadline():
    known = {'id': 'k', 'institution': 'FAPESC', 'funding': 100000, 'criteria': [c(op='in', expected=['SC'])],
             'deadline': (today() + timedelta(days=3)).isoformat(), 'deadline_confirmed': True, 'deadline_evidence': 'Até a data.'}
    unknown = {'id': 'u', 'institution': 'CNPq', 'criteria': []}
    assert filter_calls([known, unknown], institutions=['FAPESC']) == [known]
    assert filter_calls([known, unknown], min_value=50000, state='SC', max_days=7) == [known]
    assert filter_calls([known, unknown], max_days=1) == []


@pytest.mark.parametrize('url', ['https://embrapii.org.br/transparencia/', 'https://sebrae.com.br/sites/PortalSebrae/editais', 'https://www.brde.com.br/fundo-verde/'])
def test_new_official_domains_allowed_but_lookalikes_rejected(url):
    assert validate_url(url) == url
    with pytest.raises(ValueError):
        validate_url(url.replace('.br/', '.br.evil.com/'))
