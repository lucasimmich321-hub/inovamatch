"""Produto para o escritório de projetos: 4 telas, vínculos edital × startup, cofre, checklist, candidaturas e painel."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from nav import goto

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


def open_app(data, page='Editais', focus='pub'):
    """Abre o app com os dados; por padrão no detalhe do edital publicado (aba Startups compatíveis)."""
    app = AppTest.from_file(APP, default_timeout=20).run()
    app.session_state['real_data'] = data
    if focus:
        app.session_state['focus_call'] = focus
    goto(app, page)
    return clean(app)


# T3 ------------------------------------------------------------------------------------------

def test_five_task_pages_with_real_navigation():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    assert [t.value for t in app.title] == ['Início']
    for page in ['Editais', 'Startups', 'Candidaturas', 'Alertas', 'Início']:
        goto(app, page)
        clean(app)
        assert [t.value for t in app.title] == [page]


def test_dataset_choice_survives_page_changes():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    for page in ['Editais', 'Startups', 'Início']:
        goto(app, page)
        assert app.session_state['dataset'] == 'Demonstração' and app.sidebar.selectbox[0].value == 'Demonstração'


def test_compatible_startups_in_call_detail_with_verdict_and_reason():
    app = open_app(office_data())
    summary = next(d for d in app.dataframe if 'Motivo principal' in d.value.columns).value
    assert summary['Proponente'].tolist() == ['Startup SC', 'Startup PR']
    assert summary['Resultado'].tolist() == ['Atende', 'Não atende']
    assert summary['Motivo principal'].tolist()[1] == 'Não atende: Sede em SC'
    review = open_app(office_data(), focus='rev')
    assert any('Edital ainda em revisão' in c.value for c in review.caption)


def test_open_link_shows_reasons_and_starts_candidacy():
    data = office_data()
    app = open_app(data)
    reasons = next(d for d in app.dataframe if 'Justificativa' in d.value.columns).value
    assert 'Sede em SC' in reasons['Requisito'].tolist()
    assert any(b.label == 'Gerar rascunho da candidatura (.txt)' for b in app.get('download_button'))
    next(b for b in app.button if b.label == 'Iniciar candidatura').click().run()
    clean(app)
    assert app.session_state['real_data']['applications']['pub:p-sc']['status'] == 'Em preparação'


def test_legacy_page_names_and_ai_compare_land_on_call_detail():
    data = office_data()
    app = AppTest.from_file(APP, default_timeout=20)
    app.session_state['real_data'] = data
    # O botão "Comparar com startups" do ai_ui (não alterado) grava estes dois valores.
    app.session_state['page'] = 'Match Inteligente'
    app.session_state['match_call'] = 'rev'
    app.run()
    clean(app)
    assert [t.value for t in app.title] == ['Editais']
    assert next(s for s in app.selectbox if s.label == 'Selecione um edital para revisar').value == 'rev'


def test_home_shows_deadlines_review_and_coming_soon():
    app = open_app(office_data(), 'Início', focus=None)
    assert any(m.value.startswith('**Prazos que vencem** · 2') for m in app.markdown)
    assert any(m.value.startswith('**Editais para revisar** · 1') for m in app.markdown)
    assert any('Em breve' in h.value and 'Visão da startup' in h.value for h in app.get('html'))


# T4 · cofre de documentos -------------------------------------------------------------------

from datetime import timedelta  # noqa: E402

from inovamatch import vault  # noqa: E402
from inovamatch.link_checklist import DATA, DEADLINE, DOCS, MANUAL, build_checklist, summary, to_csv, to_pdf  # noqa: E402

PDF = b'%PDF-1.4\n%fake minimal\n'
PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 20


@pytest.fixture
def vault_dir(tmp_path, monkeypatch):
    monkeypatch.setenv('INOVAMATCH_VAULT', str(tmp_path / 'vault'))
    return tmp_path / 'vault'


def test_valid_upload_is_stored_outside_public_folder_with_random_name(vault_dir):
    store = Store(office_data())
    doc = vault.add_document(store, 's-sc', 'CNPJ', 'Cartão CNPJ.pdf', PDF, today() + timedelta(days=90))
    assert doc['nome'] == 'Cartao CNPJ.pdf' and doc['tipo'] == 'CNPJ' and doc['mime'] == 'application/pdf'
    stored = vault_dir / doc['arquivo']
    assert stored.exists() and stored.read_bytes() == PDF and 'Cartao' not in stored.name
    assert vault.read_document(doc) == PDF and vault.validity_status(doc) == vault.OK


@pytest.mark.parametrize('name,data,message', [
    ('script.html', b'<script>alert(1)</script>', 'Tipo de arquivo não permitido'),
    ('planilha.exe', b'MZ' + b'0' * 10, 'Tipo de arquivo não permitido'),
    ('falso.pdf', b'<html>nao e pdf</html>', 'não corresponde'),
    ('imagem.png', PDF, 'não corresponde'),
    ('vazio.pdf', b'', 'vazio'),
])
def test_invalid_type_or_content_is_rejected(vault_dir, name, data, message):
    store = Store(office_data())
    with pytest.raises(ValueError, match=message):
        vault.add_document(store, 's-sc', 'Outro', name, data)
    assert store.all('documents') == [] and not vault_dir.exists()


def test_size_limit(vault_dir):
    store = Store(office_data())
    with pytest.raises(ValueError, match='5 MB'):
        vault.add_document(store, 's-sc', 'Balanço', 'grande.pdf', PDF + b'0' * vault.MAX_BYTES)


@pytest.mark.parametrize('name,expected', [('../x.pdf', 'x.pdf'), ('..\\..\\windows\\win.pdf', 'win.pdf'),
                                           ('/abs/path/Certidão Fiscal.PDF', 'Certidao Fiscal.pdf'), ('.hidden.png', 'hidden.png'),
                                           ('a<b>|c?.docx', 'abc.docx')])
def test_malicious_names_are_sanitized(vault_dir, name, expected):
    assert vault.sanitize_filename(name) == expected
    store = Store(office_data())
    data = PNG if expected.endswith('.png') else b'PK\x03\x04rest' if expected.endswith('.docx') else PDF
    doc = vault.add_document(store, 's-sc', 'Outro', name, data)
    assert doc['nome'] == expected and (vault_dir / doc['arquivo']).resolve().parent.parent == vault_dir.resolve()


def test_expired_and_expiring_validity(vault_dir):
    on = today()
    assert vault.validity_status({'validade': (on - timedelta(days=1)).isoformat()}) == vault.EXPIRED
    assert vault.validity_status({'validade': (on + timedelta(days=30)).isoformat()}) == vault.SOON
    assert vault.validity_status({'validade': (on + timedelta(days=31)).isoformat()}) == vault.OK
    assert vault.validity_status({}) == vault.NO_DATE


def test_replace_and_remove_delete_old_files(vault_dir):
    store = Store(office_data())
    doc = vault.add_document(store, 's-sc', 'Pitch', 'pitch.pdf', PDF)
    old = vault_dir / doc['arquivo']
    new = vault.replace_document(store, doc['id'], 'pitch-v2.png', PNG)
    assert not old.exists() and (vault_dir / new['arquivo']).read_bytes() == PNG and new['nome'] == 'pitch-v2.png'
    assert vault.remove_document(store, doc['id']) and store.all('documents') == []
    assert not (vault_dir / new['arquivo']).exists()


def test_path_outside_vault_is_never_read(vault_dir):
    assert vault.read_document({'arquivo': '../../outside.pdf'}) is None


# T4b · checklist do vínculo ligado ao cofre -----------------------------------------------------

def checklist_call():
    rules = [
        {'id': 'docs', 'field': 'documents', 'scope': 'startup', 'op': 'contains_all', 'label': 'Documentos',
         'expected': ['Contrato social', 'Certidão negativa de débitos', 'Cartão CNPJ'], 'mandatory': True, 'confirmed': True,
         'page': 5, 'evidence': '6.1 Apresentar contrato social, certidão negativa e cartão CNPJ.', 'source': 'edital.pdf'},
        {'id': 'opt', 'field': 'documents', 'scope': 'startup', 'op': 'contains_all', 'label': 'Pitch',
         'expected': ['Pitch deck'], 'mandatory': False, 'confirmed': True, 'page': 6, 'evidence': 'Opcional: pitch.', 'source': 'edital.pdf'},
        {'id': 'sede', 'field': 'state', 'scope': 'startup', 'op': 'in', 'expected': ['SC'], 'label': 'Sede em SC', 'confirmed': True,
         'mandatory': True, 'page': 3, 'evidence': '4.1 sediada em SC', 'source': 'edital.pdf'},
        {'id': 'man', 'field': 'manual', 'scope': 'project', 'op': 'manual', 'expected': 'Carta de anuência da ICT',
         'label': 'Anuência da ICT', 'mandatory': True, 'page': 8, 'evidence': '7.2 carta de anuência', 'source': 'edital.pdf'},
    ]
    return {'id': 'call', 'title': 'Edital X', 'criteria': rules, 'deadline': (today() + timedelta(days=9)).isoformat(),
            'deadline_confirmed': True, 'deadline_evidence': 'Cronograma p. 7', 'deadline_page': 7}


def test_checklist_marks_sent_missing_expired_from_vault(vault_dir):
    store = Store(office_data())
    vault.add_document(store, 's-sc', 'Contrato social', 'contrato.pdf', PDF)
    vault.add_document(store, 's-sc', 'Certidões', 'cnd.pdf', PDF, today() - timedelta(days=2))
    startup, project = store.get('startups', 's-sc'), store.get('projects', 'p-sc')
    items = build_checklist(store, checklist_call(), startup, project)
    docs = {i['item']: i for i in items if i['secao'] == DOCS}
    assert docs['Contrato social']['situacao'] == 'Enviado'
    assert docs['Certidão negativa de débitos']['situacao'] == 'Vencido'
    assert docs['Cartão CNPJ']['situacao'] == 'Falta'
    assert docs['Pitch deck']['situacao'] == 'Opcional (não enviado)'  # opcional nunca conta como falta
    assert all(i['pagina'] and i['trecho'] for i in docs.values())
    data = next(i for i in items if i['secao'] == DATA)
    assert data['item'] == 'Sede em SC' and data['cadastrado'] == 'SC' and data['exigido'] == 'SC' and data['situacao'] == 'Atende'
    assert [i['item'] for i in items if i['secao'] == MANUAL] == ['Anuência da ICT']
    deadline = next(i for i in items if i['secao'] == DEADLINE)
    assert deadline['situacao'] == '9 dias restantes' and deadline['pagina'] == 7
    assert summary(items) == {'docs_total': 3, 'docs_sent': 1, 'docs_missing': 1, 'docs_expired': 1}


def test_checklist_exports_csv_and_pdf(vault_dir):
    store = Store(office_data())
    items = build_checklist(store, checklist_call(), store.get('startups', 's-sc'), store.get('projects', 'p-sc'))
    csv_text = to_csv(items, {'manual:man': True})
    assert csv_text.startswith('﻿Seção,Item,Situação') and 'Anuência da ICT' in csv_text and ',Sim' in csv_text
    pdf = to_pdf(items, 'Checklist · Edital X', 'Startup SC · Projeto SC')
    assert pdf.startswith(b'%PDF')


def test_unconfirmed_and_continuous_deadlines_in_checklist(vault_dir):
    store = Store(office_data())
    s, p = store.get('startups', 's-sc'), store.get('projects', 'p-sc')
    call = {**checklist_call(), 'deadline_confirmed': False}
    assert next(i for i in build_checklist(store, call, s, p) if i['secao'] == DEADLINE)['situacao'] == 'Prazo não confirmado'
    flow = {**call, 'registration_status': 'Fluxo contínuo', 'registration_status_confirmed': True, 'registration_status_evidence': 'x'}
    assert next(i for i in build_checklist(store, flow, s, p) if i['secao'] == DEADLINE)['situacao'] == 'Fluxo contínuo (sem data-limite)'


def test_link_screen_shows_checklist_and_vault_tab(vault_dir):
    data = office_data()
    store = Store(data)
    store.save('calls', {**store.get('calls', 'pub'), 'criteria': checklist_call()['criteria']})
    vault.add_document(store, 's-sc', 'Contrato social', 'contrato.pdf', PDF)
    app = open_app(data)
    assert any(c.label.startswith('Cartão CNPJ — Falta') for c in app.checkbox)
    assert any(b.label == 'Exportar checklist (PDF)' for b in app.get('download_button'))
    marker = next(c for c in app.checkbox if c.label.startswith('Cartão CNPJ'))
    marker.check().run()
    clean(app)
    assert any(t.get('kind') == 'checklist' and t['done'] for t in app.session_state['real_data']['tasks'].values())
    goto(app, 'Startups')
    clean(app)
    table = next(d for d in app.dataframe if 'Validade' in d.value.columns)
    assert table.value['Tipo'].tolist() == ['Contrato social']


def test_demo_documents_are_fictitious_and_flagged():
    store = Store({})
    from inovamatch.demo import load_demo
    load_demo(store)
    vault.demo_documents(store)
    docs = store.all('documents')
    assert docs and all(d['demo'] and d['arquivo'] is None and '(fictício)' in d['nome'] for d in docs)
    assert any(vault.validity_status(d) == vault.EXPIRED for d in docs)


# T5 · candidaturas e resultado --------------------------------------------------------------

from inovamatch import applications as apps  # noqa: E402
from inovamatch.portfolio import register_application  # noqa: E402


def started(store):
    call, startup, project = store.get('calls', 'pub'), store.get('startups', 's-sc'), store.get('projects', 'p-sc')
    store.save('projects', {**project, 'requested': 80_000})
    return register_application(store, call, startup, store.get('projects', 'p-sc'))


def test_register_keeps_requested_value_and_flow_to_approved():
    store = Store(office_data())
    application = started(store)
    assert application['status'] == apps.PREPARING and application['valor_solicitado'] == 80_000
    sub = apps.update_application(store, application['id'], status=apps.SUBMITTED, data_submissao='2026-10-01')
    assert sub['status'] == apps.SUBMITTED and sub['motivo'] is None
    ok = apps.update_application(store, application['id'], status=apps.APPROVED, data_resultado='2026-11-01', valor_captado=75_000)
    assert ok['valor_captado'] == 75_000 and ok['data_submissao'] == '2026-10-01'


@pytest.mark.parametrize('fields,message', [
    ({'status': 'Ganhou'}, 'Status'),
    ({'status': apps.SUBMITTED}, 'data de submissão'),
    ({'status': apps.APPROVED, 'data_submissao': '2026-10-01'}, 'data do resultado'),
    ({'status': apps.APPROVED, 'data_submissao': '2026-10-01', 'data_resultado': '2026-09-01', 'valor_captado': 1}, 'anterior'),
    ({'status': apps.APPROVED, 'data_submissao': '2026-10-01', 'data_resultado': '2026-11-01'}, 'valor captado'),
    ({'status': apps.SUBMITTED, 'data_submissao': '2026-10-01', 'valor_captado': 10}, 'só vale'),
    ({'status': apps.REJECTED, 'data_submissao': '2026-10-01', 'data_resultado': '2026-11-01'}, 'motivo'),
    ({'status': apps.NOT_SUBMITTED, 'motivo': 'Outro'}, 'Observação'),
    ({'status': apps.PREPARING, 'valor_solicitado': -5}, 'maior ou igual a zero'),
])
def test_application_validation(fields, message):
    store = Store(office_data())
    application = started(store)
    with pytest.raises(ValueError, match=message):
        apps.update_application(store, application['id'], **fields)


def test_lost_reason_and_suggestion_is_never_saved_automatically():
    store = Store(office_data())
    application = started(store)
    expired = {**store.get('calls', 'pub'), 'deadline': '2026-01-10'}
    assert apps.suggest_reason({**application, 'status': apps.NOT_SUBMITTED}, expired) == 'Prazo perdido'
    assert apps.suggest_reason({**application, 'status': apps.REJECTED}, None, {'blockers': 1}) == 'Inelegível'
    assert apps.suggest_reason({**application, 'status': apps.REJECTED}, None, {'blockers': 0}, {'docs_missing': 2}) == \
        'Documentação incorreta ou incompleta'
    assert apps.suggest_reason(application) is None
    assert store.get('applications', application['id']).get('motivo') is None
    lost = apps.update_application(store, application['id'], status=apps.NOT_SUBMITTED, motivo='Desistência da startup', motivo_obs=' mudou de foco ')
    assert lost['motivo'] == 'Desistência da startup' and lost['motivo_obs'] == 'mudou de foco'
    back = apps.update_application(store, application['id'], status=apps.PREPARING)
    assert back['motivo'] is None  # motivo só existe para perda


def test_result_form_on_link_screen():
    data = office_data()
    store = Store(data)
    started(store)
    app = open_app(data)
    assert any(e.label == 'Registrar andamento e resultado' for e in app.expander)
    next(s for s in app.selectbox if s.label == 'Status da candidatura').set_value(apps.NOT_SUBMITTED)
    next(b for b in app.button if b.label == 'Salvar andamento').click().run()
    clean(app)
    assert any('Escolha o motivo' in e.value for e in app.error)
    assert any('Sugestão de motivo' in c.value for c in app.caption)
    assert app.session_state['real_data']['applications']['pub:p-sc']['status'] == apps.PREPARING
    next(s for s in app.selectbox if s.label == 'Motivo (se reprovada ou não submetida)').set_value('Prazo perdido')
    next(s for s in app.selectbox if s.label == 'Status da candidatura').set_value(apps.NOT_SUBMITTED)
    next(b for b in app.button if b.label == 'Salvar andamento').click().run()
    clean(app)
    saved = app.session_state['real_data']['applications']['pub:p-sc']
    assert saved['status'] == apps.NOT_SUBMITTED and saved['motivo'] == 'Prazo perdido'


def test_follow_up_table_by_call_with_documents_count(tmp_path, monkeypatch):
    monkeypatch.setenv('INOVAMATCH_VAULT', str(tmp_path / 'vault'))
    data = office_data()
    store = Store(data)
    store.save('calls', {**store.get('calls', 'pub'), 'criteria': checklist_call()['criteria']})
    vault.add_document(store, 's-sc', 'Contrato social', 'contrato.pdf', PDF)
    started(store)
    app = open_app(data, 'Startups')
    table = next(d for d in app.dataframe if 'Documentos' in d.value.columns).value
    assert table.to_dict('records') == [{'Origem': 'Dados reais', 'Startup': 'Startup SC', 'Projeto': 'Projeto SC', 'Edital': 'Edital publicado',
                                         'Documentos': '1 de 3', 'Candidatura': 'Em preparação', 'Solicitado': 'R$ 80.000,00',
                                         'Captado': '—', 'Motivo': '—'}]
    next(s for s in app.selectbox if s.label == 'Filtrar por edital').set_value('pub').run()
    clean(app)
    table = next(d for d in app.dataframe if 'Documentos' in d.value.columns).value
    assert table['Startup'].tolist() == ['Startup SC', 'Startup PR']
    assert table['Candidatura'].tolist() == ['Em preparação', 'Não iniciada']


# T6 · painel do escritório ------------------------------------------------------------------

from inovamatch import office_stats  # noqa: E402


def demo_store():
    from inovamatch.demo import load_demo
    store = Store({})
    load_demo(store)
    office_stats.demo_applications(store)
    return store


def test_four_numbers_from_demo_applications():
    stats = office_stats.compute(demo_store())
    assert stats['captado'] == 230_000            # 120k + 60k + 50k aprovados
    assert stats['deixou_de_captar'] == 410_000   # solicitado das 3 reprovadas + 2 não submetidas
    assert stats['taxa_aprovacao'] == 0.5         # 3 aprovadas / (3 aprovadas + 3 reprovadas)
    assert stats['em_andamento'] == 2 and stats['finalizadas'] == 8 and stats['simulated']
    assert sum(stats['reasons'].values()) == 5 and stats['reasons']['Prazo perdido'] == 1
    assert stats['by_agency']['Agência fictícia A']['Captado'] == 170_000
    assert set(stats['by_startup']) == {'Araucária Tech', 'Horizonte Digital', 'Semente Lab'}


def test_period_filter_and_empty_rate():
    store = demo_store()
    on = today()
    recent = office_stats.compute(store, on - timedelta(days=100), on)
    assert recent['finalizadas'] == 3 and recent['captado'] == 50_000  # resultados há 60, 80 e 40 dias
    empty = office_stats.compute(store, date(2000, 1, 1), date(2000, 12, 31))
    assert empty['finalizadas'] == 0 and empty['taxa_aprovacao'] is None and empty['em_andamento'] == 2
    assert office_stats.period_bounds('Ano anterior', date(2026, 11, 14)) == (date(2025, 1, 1), date(2025, 12, 31))


def test_csv_export_neutralizes_formulas():
    store = demo_store()
    rows = office_stats.compute(store)['rows'] + [{'agencia': '=HYPERLINK("x")', 'edital': 'e', 'startup': 's', 'status': 'Aprovada',
                                                   'valor_solicitado': 1, 'valor_captado': 1, 'data_submissao': None,
                                                   'data_resultado': None, 'motivo': '', 'motivo_obs': '', 'simulada': False}]
    text = office_stats.to_csv(rows)
    assert text.startswith('﻿agencia,edital,startup,status') and "'=HYPERLINK" in text and text.count('\n') == 12


def test_panel_screen_with_demo_and_empty_state():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    goto(app, 'Candidaturas')  # resultados do escritório: Candidaturas › Resultados
    clean(app)
    assert any('Nenhuma candidatura finalizada' in i.value for i in app.info)
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    goto(app, 'Candidaturas')
    clean(app)
    metrics = {m.label: m.value for m in app.metric}
    assert metrics['Captado'] == 'R$ 230.000,00' and metrics['Deixou de captar'] == 'R$ 410.000,00'
    assert metrics['Taxa de aprovação'] == '50%' and metrics['Em andamento'] == '2'
    assert any('Dados de demonstração' in i.value for i in app.info)
    assert any(e.label == 'Como cada número é calculado' for e in app.expander)
    assert any(b.label == 'Exportar candidaturas (CSV)' for b in app.get('download_button'))
    assert any('Agência' in d.value.columns for d in app.dataframe)


from datetime import date  # noqa: E402
