from datetime import date, timedelta
import copy
import json
import pytest

from inovamatch.demo import load_demo
from inovamatch.domain import deadline_info, today, valid_cnpj
from inovamatch.extraction import extract_pdf, suggest
from inovamatch.matching import FAIL, PASS, PENDING, checklist, evaluate, fingerprint, match, months_between
from inovamatch.radar import canonical_url, parse_listing, pdf_call, scan, validate_url
from inovamatch.storage import Store


@pytest.fixture(params=['session', 'sqlite'])
def store(request, tmp_path):
    return Store(path=tmp_path / 'db.sqlite' if request.param == 'sqlite' else None)


def criterion(**changes):
    return {'id': 'sc', 'field': 'state', 'scope': 'startup', 'op': 'in', 'expected': ['SC'],
            'confirmed': True, 'mandatory': True, 'source': 'https://fapesc.sc.gov.br/teste/',
            'evidence': 'A sede deve ser em Santa Catarina.', **changes}


def reviewed_call(**changes):
    return {'id': 'test', 'title': 'Edital de teste', 'criteria': [criterion()], 'criteria_complete': True,
            'deadline': (today() + timedelta(days=10)).isoformat(), 'deadline_confirmed': True,
            'deadline_evidence': 'Inscrições até a data indicada.', 'url': 'https://fapesc.sc.gov.br/teste/', **changes}


def test_startup_create_edit_and_export(store):
    saved = store.save('startups', {'name': 'Minha startup', 'state': 'SC', 'counterpart': 0})
    updated = store.save('startups', {**saved, 'name': 'Outro nome'})
    assert len(store.all('startups')) == 1
    assert store.get('startups', updated['id'])['name'] == 'Outro nome'
    assert json.loads(store.export())['startups'][0]['counterpart'] == 0


def test_sqlite_survives_repository_reopen(tmp_path):
    path = tmp_path / 'data.db'
    saved = Store(path=path).save('startups', {'name': 'Persistente'})
    assert Store(path=path).get('startups', saved['id'])['name'] == 'Persistente'


def test_project_creation_relationship_and_budget(store):
    startup = store.save('startups', {'name': 'A'})
    project = store.save('projects', {'name': 'P', 'startup_id': startup['id'], 'requested': 100, 'budget': 200})
    assert project['budget'] == 200
    with pytest.raises(ValueError):
        store.save('projects', {'name': 'P', 'startup_id': 'missing'})
    with pytest.raises(ValueError):
        store.save('projects', {**project, 'requested': 300})


@pytest.mark.parametrize('record', [{'name': ''}, {'name': 'X', 'cnpj': '123'},
                                     {'name': 'X', 'counterpart': -1}, {'name': 'X', 'state': 'XX'},
                                     {'name': 'X', 'counterpart': float('nan')},
                                     {'name': 'X', 'opened_on': (today() + timedelta(days=1)).isoformat()}])
def test_invalid_startup(record):
    with pytest.raises(ValueError):
        Store().save('startups', record)


def test_cnpj_check_digits():
    assert valid_cnpj('11.222.333/0001-81')
    assert not valid_cnpj('11.222.333/0001-82')
    assert not valid_cnpj('00.000.000/0000-00')


@pytest.mark.parametrize('actual,expected', [('SC', PASS), ('PR', FAIL), (None, PENDING), ('', PENDING)])
def test_region(actual, expected):
    assert evaluate(criterion(), {'state': actual}, {})['status'] == expected


@pytest.mark.parametrize('change', [{'confirmed': False}, {'source': ''}, {'evidence': ''}, {'scope': 'project'},
                                    {'op': 'unknown'}, {'field': 'unknown'}])
def test_uncertain_requirement_stays_pending(change):
    assert evaluate(criterion(**change), {'state': 'SC'}, {})['status'] == PENDING


def test_mandatory_failure_blocks_but_optional_failure_does_not():
    call = reviewed_call()
    assert match(call, {'state': 'PR'}, {})['verdict'] == 'Com impedimentos'
    call['criteria'][0]['mandatory'] = False
    result = match(call, {'state': 'PR'}, {})
    assert result['blockers'] == 0
    assert result['rows'][0]['status'] == FAIL


def test_no_criteria_or_incomplete_review_never_eligible():
    assert match(reviewed_call(criteria=[]), {'state': 'SC'}, {})['pending'] == 1
    assert match(reviewed_call(criteria_complete=False), {'state': 'SC'}, {})['verdict'] == 'Precisa de informações'


def test_manual_rule_never_auto_approves():
    c = criterion(field='manual', scope='project', op='manual', expected='Inovação comprovada')
    assert evaluate(c, {}, {'manual': 'Sim'})['status'] == PENDING


def test_counterpart_unknown_vs_zero_and_real_base():
    c = criterion(field='counterpart_pct', op='min', expected=10)
    assert evaluate(c, {'counterpart': None}, {'budget': 100})['status'] == PENDING
    assert evaluate(c, {'counterpart': 0}, {'budget': 100})['status'] == FAIL
    assert evaluate(c, {'counterpart': 20}, {'budget': 100})['status'] == PASS
    assert evaluate(c, {'counterpart': 20}, {'budget': 0})['status'] == PENDING


def test_months_and_explicit_reference():
    assert months_between(date(2024, 1, 31), date(2026, 1, 30)) == 23
    c = criterion(field='age_months', op='min', expected=24, reference_date='2026-01-31')
    assert evaluate(c, {'opened_on': '2024-01-31'}, {}, date(2025, 1, 1))['status'] == PASS


def test_lists_and_financial_limits():
    docs = criterion(field='documents', op='contains_all', expected=['Certidão', 'CNPJ'])
    assert evaluate(docs, {'documents': ['certidao', 'cnpj']}, {})['status'] == PASS
    assert evaluate(docs, {'documents': ['CNPJ']}, {})['status'] == FAIL
    expenses = criterion(field='expenses', scope='project', op='subset', expected=['Bolsas'])
    assert evaluate(expenses, {}, {'expenses': ['Bolsas', 'Marketing']})['status'] == FAIL
    limit = criterion(field='requested', scope='project', op='max', expected=100)
    assert evaluate(limit, {}, {'requested': 100})['status'] == PASS
    assert evaluate(limit, {}, {'requested': 101})['status'] == FAIL


@pytest.mark.parametrize('delta,status', [(-1, 'expired'), (0, 'soon'), (7, 'soon'), (8, 'open')])
def test_deadlines(delta, status):
    on = date(2026, 5, 1)
    c = reviewed_call(deadline=(on + timedelta(days=delta)).isoformat())
    assert deadline_info(c, on)['status'] == status
    assert deadline_info(c, on)['days'] == delta
    if delta == -1:
        assert match(c, {'state': 'SC'}, {}, on)['blockers'] == 1
    c['deadline_confirmed'] = False
    assert deadline_info(c, on)['days'] is None


def test_deadline_without_evidence_is_unknown():
    assert deadline_info(reviewed_call(deadline_evidence=''))['days'] is None


def test_demo_three_outcomes_and_no_duplicate_load():
    store = Store()
    load_demo(store)
    load_demo(store)
    assert len(store.all('startups')) == 3
    assert len(store.all('calls')) == 2
    call = store.get('calls', 'demo-call-1')
    outcomes = []
    for p in store.all('projects'):
        outcomes.append(match(call, store.get('startups', p['startup_id']), p)['verdict'])
    # Semente Lab está em formação (sem CNPJ, de propósito): tempo de CNPJ "não atende por ora" → impedimento.
    assert outcomes == ['Potencialmente elegível', 'Com impedimentos', 'Com impedimentos']
    assert all(c['simulated'] for c in store.all('calls'))


def test_startup_sem_cnpj_nao_atende_por_ora_e_nao_vira_pendencia():
    from inovamatch import attention
    store = Store()
    load_demo(store)
    call, startup = store.get('calls', 'demo-call-1'), store.get('startups', 'demo-pendente')
    assert startup['sem_cnpj'] and not startup['cnpj']
    rows = [r for r in match(call, startup, store.get('projects', 'project-demo-pendente'))['rows'] if r.get('field') == 'age_months']
    assert rows and attention.requirement_state(rows[0]) == 'Não atende por ora' and 'abrir o CNPJ' in rows[0]['reason']
    gaps = ' '.join(attention.startup_gaps(startup, [1]))
    assert 'CNPJ' not in gaps and 'data de abertura' not in gaps
    others = [s for s in store.all('startups') if s['id'] != 'demo-pendente']
    assert all(valid_cnpj(s['cnpj']) for s in others)


def test_checklist_tracks_blockers_pending_documents_and_sources():
    call = reviewed_call(criteria=[criterion(), criterion(id='docs', field='documents', op='contains_all', expected=['Certidão'])])
    result = match(call, {'state': 'PR'}, {})
    tasks = checklist(result)
    assert any('Impedimento' in t['category'] for t in tasks)
    assert any('Verificação' in t['category'] for t in tasks)
    assert all(t['source'] for t in tasks)
    assert any(t['id'] == 'docs' for t in tasks)


def test_dedup_keeps_human_review(store):
    first, created = store.upsert_call({'title': 'Edital 1', 'url': 'https://fapesc.sc.gov.br/edital-1/?utm_source=x'})
    assert created
    first = store.save('calls', {**first, 'title': 'Revisado', 'criteria': [criterion()]})
    second, created = store.upsert_call({'title': 'Não sobrescrever', 'url': 'https://fapesc.sc.gov.br/edital-1#top'})
    assert not created
    assert second['id'] == first['id']
    assert second['title'] == 'Revisado'
    assert second['criteria'] == [criterion()]


def test_listing_dedup_and_no_invented_deadline():
    html = '''<main><a href="/edital-01/">Edital de Chamada Pública FAPESC 01/2026</a>
    <a href="/edital-01/?utm_source=x">Edital de Chamada Pública FAPESC 01/2026</a>
    <a href="/edital-02/">Edital FAPESC inovação 02/2026 em 15/12/2026</a>
    <a href="/contato/">Contato</a><a href="/chamadas-abertas/">Editais e chamadas abertas</a></main>'''
    result = parse_listing(html)
    assert len(result) == 2
    assert all(not c['deadline_confirmed'] and c['deadline'] is None for c in result)
    assert result[1]['dates_found'] == ['15/12/2026']


def test_scan_failure_is_saved_without_fake_results(monkeypatch):
    from inovamatch import radar
    def fail(*args, **kwargs):
        raise ValueError('Fonte indisponível')
    monkeypatch.setattr(radar.Fetcher, 'fetch', fail)
    store = Store()
    report = scan(store)
    assert report['errors'] and report['found'] == 0
    assert len(store.all('calls')) == 0
    assert len(store.all('scans')) == 1


@pytest.mark.parametrize('url', ['http://fapesc.sc.gov.br/a', 'https://localhost/a', 'https://127.0.0.1/a',
                                 'https://fapesc.sc.gov.br.evil.com/a', 'https://user:pass@fapesc.sc.gov.br/a',
                                 'https://fapesc.sc.gov.br:444/a'])
def test_network_url_boundaries(url):
    with pytest.raises(ValueError):
        validate_url(url)


def pdf_bytes(text):
    import pymupdf as fitz
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((50, 60), text)
    result = doc.tobytes()
    doc.close()
    return result


def test_pdf_extraction_pages_suggestions_and_content_dedup(store):
    data = pdf_bytes('Inscricoes de propostas ate 20/12/2026.\nEmpresa com CNPJ de no minimo 24 meses. Contrapartida obrigatoria.')
    extracted = extract_pdf(data)
    assert extracted[0]['page'] == 1
    suggested = suggest(extracted, 'teste.pdf')
    assert suggested['deadline'] == '2026-12-20'
    assert not suggested['deadline_confirmed']
    assert suggested['criteria'][0]['expected'] == 24
    assert not suggested['criteria'][0]['confirmed']
    store.upsert_call(pdf_call(data, 'a.pdf'))
    _, created = store.upsert_call(pdf_call(data, 'b.pdf'))
    assert not created


def test_scanned_or_corrupt_pdf_reports_error():
    with pytest.raises(ValueError, match='selecionável'):
        extract_pdf(pdf_bytes(''))
    with pytest.raises(ValueError):
        extract_pdf(b'not a pdf')


def test_unchanged_scan_does_not_reset_preparation_revision():
    call = reviewed_call()
    original = fingerprint(call, {'name': 'Startup'}, {'name': 'Projeto'})
    call['last_seen_at'] = '2026-11-13T22:00:00-03:00'
    call['updated_at'] = '2026-11-13T22:00:00-03:00'
    assert fingerprint(call, {'name': 'Startup'}, {'name': 'Projeto'}) == original
    call['criteria'][0]['expected'] = ['PR']
    assert fingerprint(call, {'name': 'Startup'}, {'name': 'Projeto'}) != original


def test_official_page_exposes_unique_pdf_attachments_for_review(monkeypatch):
    from inovamatch import radar
    html = b'''<main><h1>Edital de teste</h1><a href="/edital.pdf">Edital completo</a>
    <a href="/edital.pdf">Mesmo documento</a><a href="/anexo.pdf">Anexo I</a></main>'''
    monkeypatch.setattr(radar.Fetcher, 'fetch', lambda self, url, limit: (html, 'text/html', url))
    call = radar.import_url('https://fapesc.sc.gov.br/edital-teste/')
    assert len(call['attachments']) == 2
    assert call['attachments'][0]['url'] == 'https://fapesc.sc.gov.br/edital.pdf'
    assert not call['deadline_confirmed'] and not call['criteria_complete']


def test_log_da_ia_no_terminal_sem_texto_do_edital(capsys):
    from inovamatch import log_ia
    call = {'title': 'Edital Nascer 24/2026', 'text': 'TEXTO SIGILOSO DO EDITAL'}
    log_ia.calling('gpt-teste', call, 'bloco 1 de 2 · páginas 1, 2')
    log_ia.finished(call, {'new_api_calls': 2, 'cached_chunks': 0})
    err = capsys.readouterr().err
    assert '[IA] chamando OpenAI (modelo gpt-teste) para analisar o edital "Edital Nascer 24/2026"' in err
    assert '[IA] concluída' in err and 'SIGILOSO' not in err
