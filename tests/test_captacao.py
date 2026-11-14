"""Fumaça da Fase 4: status novos (com migração), datas da captação, tarefa gerada, lembretes e .ics."""
from datetime import date, timedelta

from inovamatch import applications as apps, captacao
from inovamatch.storage import Store


def test_captacao_smoke():
    store = Store({})
    store.save('applications', {'id': 'c:p', 'call_id': 'c', 'project_id': 'p', 'status': 'Aprovada', 'valor_captado': 50_000,
                                'data_submissao': '2026-10-01', 'data_resultado': '2026-11-01', 'origem': 'demo'})
    assert apps.migrate_statuses(store) == 1
    application = store.get('applications', 'c:p')
    assert application['status'] == apps.APPROVED

    on = date(2026, 11, 14)
    call = {'schedule': [{'etapa': 'Assinatura do termo', 'inicio': None, 'fim': '2026-11-17', 'page': 4, 'evidence': 'Assinatura: 17/11/2026'}]}
    suggestion = captacao.suggested_dates(call)[0]
    assert 'p. 4' in suggestion['fonte']
    pending = captacao.add_date(store, application, suggestion['titulo'], suggestion['data'], captacao.EDITAL,
                                suggestion['fonte'], confirmada=False, sugestao=suggestion['sugestao'])
    assert pending['estado'] == captacao.TO_CONFIRM and not captacao.tasks(store, 'c:p')
    captacao.confirm_date(store, pending['id'])
    captacao.add_date(store, application, 'Prestação de contas', on + timedelta(days=60))
    assert [t['titulo'] for t in captacao.tasks(store, 'c:p')][0] == 'Preparar: Assinatura do termo'
    assert store.get('tasks', pending['id'])['origem'] == 'demo'

    reminders = captacao.reminders(store, on)
    assert any(r['tipo'] == 'data' and r['dias'] == 3 and r['marco'] == 3 for r in reminders)
    ics = captacao.to_ics(store, application, 'Startup, edital; teste')
    assert ics.startswith('BEGIN:VCALENDAR') and ics.count('BEGIN:VEVENT') == 4 and 'TRIGGER:-P7D' in ics
    assert 'Startup\\, edital\\; teste' in ics.replace('\r\n ', '') and '[Demonstração]' in ics


def test_demo_carrega_3_matches_so_na_demonstracao():
    import sys
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    sys.path.insert(0, str(Path(__file__).parent))
    from nav import goto
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py'), default_timeout=60).run()
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    goto(app, 'Matches')
    assert not app.exception
    assert len([b for b in app.button if b.label == 'Gerenciar']) == 3
    statuses = {a['status'] for a in app.session_state['demo_data']['applications'].values() if a['id'].startswith('demo-call-')}
    assert statuses == {apps.SUGGESTED, apps.PREPARING, apps.APPROVED}
    assert not app.session_state['real_data'].get('applications')  # nada no modo real
