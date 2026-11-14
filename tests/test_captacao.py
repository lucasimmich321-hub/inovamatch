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


def test_demo_carrega_8_matches_so_na_demonstracao():
    import sys
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    sys.path.insert(0, str(Path(__file__).parent))
    from nav import goto
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py'), default_timeout=60).run()
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    goto(app, 'Matches')
    assert not app.exception
    assert len([b for b in app.button if b.label == 'Gerenciar']) == 8
    statuses = {a['status'] for a in app.session_state['demo_data']['applications'].values() if a['id'].startswith('demo-call-')}
    assert statuses == set(apps.STATUSES)  # o ciclo inteiro aparece na demonstração
    assert not app.session_state['real_data'].get('applications')  # nada no modo real


def test_exigencia_com_contexto_e_primeiro_match_da_demo_atende():
    import app as ui
    from inovamatch.demo import demo_matches, load_demo
    from inovamatch.matching import match
    store = Store({})
    load_demo(store)
    demo_matches(store)
    call, startup, project = store.get('calls', 'demo-call-2'), store.get('startups', 'demo-fora'), store.get('projects', 'project-demo-fora')
    result = match(call, startup, project)
    assert result['verdict'] == 'Potencialmente elegível'
    texts = {r['requirement']: ui.requirement_text(r) for r in result['rows']}
    assert texts['CNPJ há pelo menos 24 meses'] == 'mínimo de 24 meses'
    assert texts['Teto por projeto'] == 'até R$ 150.000,00'
    assert texts['Contrapartida financeira'].startswith('mínimo de 10% de contrapartida')
    assert texts['Prazo de inscrição'].startswith('até ')
    assert ui.requirement_text({'expected': 5, 'field': 'trl', 'op': 'min', 'mandatory': False}) == 'mínimo de TRL 5'


def test_impedido_e_pendencias_visiveis_na_demo():
    import sys
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    sys.path.insert(0, str(Path(__file__).parent))
    from nav import goto
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py'), default_timeout=60).run()
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    goto(app, 'Matches')
    html = ' '.join(h.value for h in app.get('html'))
    assert 'im-chip-fail' in html and 'Impedido' in html and 'pendência(s)' in html  # selos no card
    app.session_state['active_match'] = 'demo-call-1:project-demo-pendente'  # Semente Lab: em formação e faltam dados
    app.run()
    html = ' '.join(h.value for h in app.get('html'))
    assert 'Não atende por ora: CNPJ há pelo menos 24 meses (ação sugerida: abrir o CNPJ)' in html
    assert 'Falta preencher: dados da startup' in html
    table = next(d for d in app.dataframe if 'Exigência' in d.value.columns).value
    assert 'Não atende por ora' in table['Resultado'].tolist() and 'Sem dado' in table['Resultado'].tolist()


def test_planos_simulados_liberam_e_bloqueiam():
    import sys
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    sys.path.insert(0, str(Path(__file__).parent))
    from nav import goto
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py'), default_timeout=60).run()
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    assert app.session_state['plan'] == 'Institucional'
    app.session_state['active_match'] = 'demo-call-1:project-demo-pendente'
    goto(app, 'Matches')
    assert any('Exigência' in d.value.columns for d in app.dataframe)  # Institucional: tudo liberado
    app.session_state['plan'] = 'Gratuito'
    app.run()
    html = ' '.join(h.value for h in app.get('html'))
    assert not app.exception and 'Disponível no plano Básico' in html and 'Disponível no plano Intermediário' in html
    assert not any('Exigência' in d.value.columns for d in app.dataframe)
    goto(app, 'Planos')
    table = next(d for d in app.dataframe if 'Recurso' in d.value.columns).value
    assert 'Em breve' in table['Premium'].tolist() and set(table.iloc[-1, 1:]) == {'A definir'}


def test_nota_e_dashboard_institucional():
    import sys
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from inovamatch import score
    from inovamatch.demo import demo_matches, load_demo
    from inovamatch.matching import match
    sys.path.insert(0, str(Path(__file__).parent))
    from nav import goto
    store = Store({})
    load_demo(store)
    demo_matches(store)
    blocked = match(store.get('calls', 'demo-call-3'), store.get('startups', 'demo-energia'), store.get('projects', 'project-demo-energia'))
    assert score.compute(blocked)['value'] <= score.BLOCKER_CAP  # impedimento limita a nota
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py'), default_timeout=60).run()
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    goto(app, 'Início')
    metrics = {m.label: m.value for m in app.metric}
    assert not app.exception and metrics['Startups no portfólio'] == '6' and metrics['Nota média'].endswith('/ 10')
    assert any(d.label == 'Exportar relatório (CSV)' for d in app.get('download_button'))
    app.session_state['plan'] = 'Básico'
    app.run()
    assert 'Startups no portfólio' not in {m.label for m in app.metric}  # Início simples fora do Institucional


def test_alertas_simulados_por_plano():
    import sys
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    sys.path.insert(0, str(Path(__file__).parent))
    from nav import goto
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py'), default_timeout=60).run()
    goto(app, 'Alertas')
    assert any('Nenhum aviso agora' in h.value for h in app.get('html'))  # modo real vazio
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    goto(app, 'Alertas')
    assert not app.exception and 6 <= len(app.code) <= 8
    assert any('Simulação: nada é enviado' in h.value for h in app.get('html'))
    app.session_state['plan'] = 'Gratuito'
    app.run()
    assert len(app.code) == 2 and any('Disponível no plano Básico' in h.value for h in app.get('html'))


def test_hash_do_edital_e_retificacao_simulada():
    import sys
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from inovamatch import versioning
    sys.path.insert(0, str(Path(__file__).parent))
    from nav import goto
    call = versioning.register({'id': 'c'}, 'fonte', 'a1', [{'text': 'Prazo  ATÉ\n10/12'}])
    assert call['versions'][0]['changed'] == versioning.FIRST and not call.get('altered')
    same_text = versioning.register(call, 'fonte', 'a2', [{'text': 'prazo até 10/12'}])  # só o arquivo (e a formatação)
    assert same_text['versions'][-1]['changed'] == versioning.FILE and not same_text.get('altered')
    changed = versioning.register(same_text, 'fonte', 'a3', [{'text': 'prazo até 20/12'}])
    assert changed['altered'] and changed['versions'][-1]['changed'] == versioning.BOTH
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py'), default_timeout=60).run()
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    from inovamatch.demo import simulate_rectification
    simulate_rectification(Store(app.session_state['demo_data']), 'demo-call-2')
    goto(app, 'Alertas')
    assert any('Edital alterado' in t.label for t in app.tabs) and any('foi alterado em' in c.value for c in app.code)
    app.session_state['active_match'] = 'demo-call-2:project-demo-fora'
    goto(app, 'Matches')
    assert any('Edital alterado em' in h.value for h in app.get('html'))


def test_dados_reais_com_startups_de_exemplo_e_publicacao_rapida(monkeypatch):
    import sys
    from datetime import timedelta
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    from inovamatch.domain import today
    sys.path.insert(0, str(Path(__file__).parent))
    from nav import goto
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py'), default_timeout=60).run()
    assert any(s.label == 'Trocar perfil (simulação)' for s in app.selectbox)  # perfil fictício no pé da barra lateral
    html = ' '.join(h.value for h in app.get('html'))
    assert 'Marina Souza' in html and 'Plano Institucional' in html  # nome e plano em duas linhas, fora do botão
    assert any('Trocar perfil ou exportar' in str(p.proto) for p in app.get('popover'))
    goto(app, 'Startups')
    next(b for b in app.button if b.label == 'Adicionar startups de exemplo (fictícias)').click().run()
    real = app.session_state['real_data']
    assert len(real['startups']) == 6 and all(s['origem'] == 'demo' for s in real['startups'].values())
    Store(real).save('calls', {'id': 'real-1', 'title': 'Edital real de teste', 'institution': 'FAPESC', 'url': 'https://fapesc.sc.gov.br/x',
                               'origem': 'real', 'deadline': (today() + timedelta(days=20)).isoformat(), 'deadline_confirmed': False,
                               'deadline_evidence': 'Cronograma, p. 3: submissão até a data.', 'criteria': []})
    goto(app, 'Editais')
    next(c for c in app.checkbox if c.label.startswith('Conferi o prazo')).check()
    next(c for c in app.checkbox if c.label.startswith('Revisei os critérios')).check()
    next(b for b in app.button if b.label == 'Confirmar e publicar').click().run()
    call = real['calls']['real-1']
    assert call['review_state'] == 'Publicado' and call['deadline_confirmed'] and call['origem'] == 'real'
    assert not app.exception
