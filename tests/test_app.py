"""Fluxos reais do Streamlit sem browser externo ou serviços pagos."""
from pathlib import Path
from datetime import timedelta
from inovamatch.domain import today
import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


@pytest.fixture(autouse=True)
def session_mode(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)


def clean(app):
    assert not app.exception, [x.value for x in app.exception]
    return app


def button(app, label):
    return next(b for b in app.button if b.label == label)


def navigate(app, page):
    app.sidebar.radio[0].set_value(page).run()
    return clean(app)


def test_all_pages_and_demo_matching_and_copilot():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    assert app.title[0].value == 'Sua próxima oportunidade, mais perto.'
    button(app, 'Carregar demonstração').click().run()
    clean(app)
    assert app.session_state['dataset'] == 'Demonstração'
    assert [m.value for m in app.metric][:2] == ['2', '3']
    for page in ['Cadastrar Startup', 'Cadastrar Projeto', 'Radar de Editais', 'Match Inteligente', 'Copiloto de Captação']:
        navigate(app, page)
    assert len(app.checkbox) > 0
    app.checkbox[0].check().run()
    clean(app)
    assert any(t['done'] for t in app.session_state['demo_data']['tasks'].values())
    navigate(app, 'Match Inteligente')
    button(app, 'Analisar e registrar candidatura').click().run()
    clean(app)
    button(app, 'Comparar todas as startups e projetos').click().run()
    clean(app)
    assert len(app.session_state['demo_data']['analyses']) == 3
    assert app.dataframe[-1].value['Resultado'].tolist() == ['Potencialmente elegível', 'Com impedimentos', 'Precisa de informações']


def test_live_create_and_edit_startup_then_create_project():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    navigate(app, 'Cadastrar Startup')
    next(x for x in app.text_input if x.label == 'Nome da startup *').set_value('Startup ao vivo')
    button(app, 'Salvar startup').click().run()
    clean(app)
    data = app.session_state['real_data']
    assert len(data['startups']) == 1
    sid = next(iter(data['startups']))
    next(s for s in app.selectbox if s.label == 'Novo cadastro ou editar').set_value(sid).run()
    next(x for x in app.text_input if x.label == 'Nome da startup *').set_value('Startup editada')
    button(app, 'Salvar startup').click().run()
    clean(app)
    assert app.session_state['real_data']['startups'][sid]['name'] == 'Startup editada'
    navigate(app, 'Cadastrar Projeto')
    next(x for x in app.text_input if x.label == 'Nome do projeto *').set_value('Projeto ao vivo')
    button(app, 'Salvar projeto').click().run()
    clean(app)
    assert len(app.session_state['real_data']['projects']) == 1
    assert next(iter(app.session_state['real_data']['projects'].values()))['startup_id'] == sid
    next(x for x in app.text_input if x.label == 'Nome do projeto *').set_value('Projeto editado')
    button(app, 'Salvar projeto').click().run()
    clean(app)
    assert len(app.session_state['real_data']['projects']) == 1
    assert next(iter(app.session_state['real_data']['projects'].values()))['name'] == 'Projeto editado'


def test_session_isolation_and_empty_pages():
    first = clean(AppTest.from_file(APP, default_timeout=20).run())
    button(first, 'Carregar demonstração').click().run()
    second = clean(AppTest.from_file(APP, default_timeout=20).run())
    assert second.session_state['real_data']['startups'] == {}
    for page in ['Radar de Editais', 'Cadastrar Projeto', 'Match Inteligente', 'Copiloto de Captação']:
        navigate(second, page)


def test_dashboard_open_call_and_criterion_edit():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    button(app, 'Carregar demonstração').click().run()
    next(b for b in app.button if b.label == 'Ver edital →').click().run()
    clean(app)
    assert app.session_state['page'] == 'Radar de Editais'
    select = next(s for s in app.selectbox if s.label == 'Adicionar ou editar critério')
    select.set_value('criterion-0').run()
    clean(app)
    next(x for x in app.text_input if x.label == 'Nome do requisito').set_value('Estado revisado')
    button(app, 'Salvar critério').click().run()
    clean(app)
    call_id = next(s for s in app.selectbox if s.label == 'Selecione um edital para revisar').value
    call = app.session_state['demo_data']['calls'][call_id]
    assert not call['criteria_complete']
    assert any(c['label'] == 'Estado revisado' for c in call['criteria'])


def test_manual_call_criterion_evidence_and_deadline_review():
    app = clean(AppTest.from_file(APP, default_timeout=20).run())
    navigate(app, 'Radar de Editais')
    next(r for r in app.radio if r.label == 'Origem').set_value('Cadastro manual').run()
    next(x for x in app.text_input if x.label == 'Título do edital *').set_value('Edital da apresentação')
    next(x for x in app.text_input if x.label == 'Referência da fonte *').set_value('Regulamento de teste')
    button(app, 'Criar edital para revisão').click().run()
    clean(app)
    next(x for x in app.text_area if x.label == 'Valores exigidos / permitidos — um por linha').set_value('SC')
    next(x for x in app.text_area if x.label == 'Trecho literal de evidência').set_value('A sede deve estar em SC.')
    next(x for x in app.checkbox if x.label == 'Conferi esta exigência na fonte').check()
    button(app, 'Salvar critério').click().run()
    clean(app)
    call = next(iter(app.session_state['real_data']['calls'].values()))
    assert call['criteria'][0]['confirmed']
    assert not call['criteria_complete']
    next(x for x in app.date_input if x.label.startswith('Data-limite de inscrição')).set_value(today() + timedelta(days=2))
    next(x for x in app.text_area if x.label.startswith('Trecho e página que comprovam')).set_value('Página 2: inscrições até a data informada, às 18h.')
    next(x for x in app.checkbox if x.label == 'Confirmei o prazo na fonte e nas retificações').check()
    next(x for x in app.checkbox if x.label.startswith('Revisei integralmente')).check()
    button(app, 'Salvar revisão do edital').click().run()
    clean(app)
    call = next(iter(app.session_state['real_data']['calls'].values()))
    assert call['deadline_confirmed'] and call['criteria_complete']


def test_automatic_pdf_analysis_prefills_review_and_integrates_portfolio(monkeypatch):
    import copy
    from inovamatch.acceptance import reference_cases
    from inovamatch.extraction import suggest
    from inovamatch.radar import canonical_url
    from inovamatch.storage import Store
    from inovamatch import radar
    fixture = next(f for f in reference_cases() if f['id'] == 'fapesc_66_2025')
    def fake_import(url):
        if url == fixture['call_url']:
            return {'url': url, 'pages': [{'page': None, 'text': 'Página oficial do edital.'}], 'criteria': [],
                    'attachments': [{'title': 'ACESSE O EDITAL COMPLETO', 'url': fixture['pdf_url']}],
                    'extractor_version': '2.0'}
        assert url == fixture['pdf_url']
        return {'url': url, 'pages': fixture['pages'], 'attachments': [], 'document_sha256': fixture['pdf_sha256'],
                **suggest(fixture['pages'], url)}
    monkeypatch.setattr(radar, 'import_url', fake_import)
    store = Store()
    startup = store.save('startups', {'name': 'Startup fictícia do teste', 'state': 'SC'})
    store.save('projects', {'name': 'Projeto fictício', 'startup_id': startup['id'], 'requested': 900000, 'budget': 1000000})
    call, _ = store.upsert_call({'title': fixture['title'], 'institution': 'FAPESC', 'url': fixture['call_url'],
                                'dedup_key': canonical_url(fixture['call_url']), 'criteria': [], 'criteria_complete': False,
                                'deadline_confirmed': False, 'simulated': False})
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state['real_data'] = store.data
    clean(app.run())
    navigate(app, 'Radar de Editais')
    button(app, 'Analisar requisitos automaticamente').click().run()
    clean(app)
    current = app.session_state['real_data']['calls'][call['id']]
    assert len(current['criteria']) > 10
    assert len(current['documents']) == 2
    assert len(app.session_state['real_data']['analyses']) == 1
    assert [tab.label for tab in app.tabs] == ['Resumo', 'Requisitos', 'Documentação', 'Compatibilidade', 'Fonte']
    state_rule = next(c for c in current['criteria'] if c['field'] == 'state')
    next(s for s in app.selectbox if s.label == 'Adicionar ou editar critério').set_value(state_rule['id']).run()
    clean(app)
    assert next(x for x in app.text_area if x.label == 'Valores exigidos / permitidos — um por linha').value == 'SC'
    assert not next(x for x in app.checkbox if x.label == 'Conferi esta exigência na fonte').value
    next(x for x in app.checkbox if x.label == 'Conferi esta exigência na fonte').check()
    button(app, 'Salvar critério').click().run()
    clean(app)
    revised = app.session_state['real_data']['calls'][call['id']]
    rule = next(c for c in revised['criteria'] if c['id'] == state_rule['id'])
    assert rule['confirmed'] and rule['extracted'] and rule['validation_status'] == 'validated'
    navigate(app, 'Copiloto de Captação')
    button(app, 'Iniciar preparação desta candidatura').click().run()
    clean(app)
    assert len(app.session_state['real_data']['applications']) == 1
    navigate(app, 'Portfólio da Incubadora')
    button(app, 'Recalcular todo o portfólio').click().run()
    clean(app)
    assert app.dataframe[0].value['Candidaturas em preparação'].tolist() == [1]
