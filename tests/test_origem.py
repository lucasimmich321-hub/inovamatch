"""Fumaça da Fase 0: campo origem (real x demo) gravado e visível."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
from inovamatch.demo import load_demo
from inovamatch.office_stats import demo_applications
from inovamatch.portfolio import register_application
from inovamatch.storage import Store
from nav import carregar_demo, goto
from demo_fixture import fixture_calls

BAND = 'Demonstração: startups e matches são fictícios; editais são reais'

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


def test_origem_gravada_em_editais_startups_e_matches(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    demo = Store({})
    load_demo(demo)
    demo_applications(demo)
    for kind in ('calls', 'startups', 'projects', 'applications'):
        assert {r['origem'] for r in demo.all(kind)} == {'demo'}, kind
    real = Store({})
    real.save('startups', {'id': 's1', 'name': 'Real SA', 'simulated': False})
    assert real.get('startups', 's1')['origem'] == 'real'
    # Match com edital fictício é demonstração, mesmo que a startup seja real.
    match = register_application(real, demo.get('calls', 'demo-call-sim'), real.get('startups', 's1'), {'id': 'p1', 'name': 'P'})
    assert match['origem'] == 'demo'


def test_modo_demonstracao_mostra_aviso_e_selo(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    app = AppTest.from_file(APP, default_timeout=60).run()
    carregar_demo(app)
    app = goto(app, 'Editais', open_first=False)
    assert not app.exception
    assert any(BAND in h.value for h in app.get('html'))
    table = next(d for d in app.dataframe if 'Origem' in d.value.columns).value
    # Editais reais (aqui, de teste no formato do crawler) e o único inventado, com selo "Simulação".
    assert set(table['Origem']) == {'Real (FAPESC)', 'Simulação'}
    goto(app, 'Matches')
    assert any(BAND in h.value for h in app.get('html'))  # faixa em todas as páginas


def test_selo_de_origem_real_fapesc_e_ficticio():
    from inovamatch.origin import match_provenance, provenance
    crawler = {'title': 'Edital X', 'institution': 'FAPESC', 'source_id': 'fapesc', 'origem': 'real'}
    assert provenance(crawler, 'call') == 'Real (FAPESC)'
    # Coletado pelo crawler nunca vira fictício, mesmo com marca legada errada.
    assert provenance({**crawler, 'simulated': True, 'origem': 'demo'}, 'call') == 'Real (FAPESC)'
    demo = Store({})
    load_demo(demo)
    assert {provenance(c, 'call') for c in demo.all('calls')} == {'Simulação'}
    assert {provenance(s) for s in demo.all('startups')} == {'Fictício'}
    assert match_provenance(None, crawler, demo.get('startups', 'demo-verde')) == 'Fictício'
    assert match_provenance(None, crawler, {'name': 'Real SA', 'origem': 'real'}) == 'Real'


def test_dashboard_nos_dados_reais(monkeypatch):
    from inovamatch import dashboard
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    real = fixture_calls(Store({}))
    # Defesa: mesmo se um registro fictício entrasse na base real, ficaria fora dos números.
    real.save('startups', {'id': 'x', 'name': 'Fictícia', 'origem': 'demo'})
    assert dashboard.build(real, only_real=True)['startups'] == 0
    real.delete('startups', 'x')
    app = AppTest.from_file(APP, default_timeout=60).run()
    carregar_demo(app)
    assert any('Valores fictícios: startups e matches de demonstração' in h.value for h in app.get('html'))
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.session_state['real_data'] = real.data
    app.run()
    html = ' '.join(h.value for h in app.get('html'))
    assert 'Sem dados reais ainda' in html and 'Fictício' not in html and BAND not in html
    # Base real não vazia: a demonstração continua acessível pelo menu do usuário (Institucional).
    assert any(b.label == 'Carregar demonstração' for b in app.button)
    assert any('Nesta base: 0 startup(s), 3 edital(is) e 0 match(es), todos reais.' in c.value for c in app.caption)


def test_demo_sem_editais_reais_avisa_e_nao_inventa(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    app = AppTest.from_file(APP, default_timeout=60).run()
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()  # sem semear: cache vazio (conftest)
    assert not app.exception
    assert any('Nenhum edital real coletado ainda' in h.value for h in app.get('html'))
    data = app.session_state['demo_data']
    assert not data.get('applications') and [c['id'] for c in data['calls'].values()] == ['demo-call-sim']


def test_menu_do_usuario_base_e_alertas_ocultos(monkeypatch):
    """Menu do usuário: botão único com o nome; base/demonstração só no Institucional; Alertas fora do menu por padrão."""
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    monkeypatch.delenv('INOVAMATCH_SHOW_ALERTAS', raising=False)
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not any(b.label == 'Trocar perfil ou exportar' for b in app.button)
    base = next(s for s in app.selectbox if s.label == 'Base de dados')
    base.set_value('Demonstração').run()
    assert app.session_state['dataset'] == 'Demonstração'
    assert any('no menu do usuário (canto inferior esquerdo)' in h.value for h in app.get('html'))
    goto(app, 'Alertas')
    assert [t.value for t in app.title] == ['Início']  # rota oculta: continua onde estava
    app.session_state['plan'] = 'Básico'
    app.run()
    assert not any(s.label == 'Base de dados' for s in app.selectbox)
    assert not any(b.label == 'Carregar demonstração' for b in app.button)


def test_csv_de_dado_ficticio_tem_coluna_origem():
    from inovamatch import dashboard, office_stats
    from inovamatch.demo import demo_matches, load_demo
    from inovamatch.link_checklist import to_csv as checklist_csv
    store = Store({})
    load_demo(store)
    fixture_calls(store)
    demo_matches(store)
    office = office_stats.to_csv(office_stats.compute(store)['rows'])
    assert office.splitlines()[0].endswith(',origem') and 'Fictício' in office
    report = dashboard.to_csv(dashboard.build(store)['rows'])
    assert report.splitlines()[0].endswith(',origem') and 'Fictício' in report
    assert checklist_csv([], origem='Fictício').splitlines()[0].endswith(',Origem')


def test_link_cadastrar_startup_abre_aba_de_cadastro(monkeypatch):
    """"Cadastrar startup →" pede a aba de cadastro; o pedido vale enquanto o usuário está em Startups."""
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    app = AppTest.from_file(APP, default_timeout=60).run()
    goto(app, 'Matches')
    next(b for b in app.button if b.label == 'Cadastrar startup →').click().run()
    assert not app.exception and [t.value for t in app.title] == ['Startups']
    assert app.session_state['open_tab'] == ('Startups', 'cadastro')
    goto(app, 'Editais', open_first=False)
    assert 'open_tab' not in app.session_state


def test_menu_do_streamlit_oculto_e_selo_ficticio_nos_matches(monkeypatch):
    import tomllib
    config = tomllib.loads((Path(APP).parent / '.streamlit' / 'config.toml').read_text())
    assert config['client']['toolbarMode'] == 'minimal'  # sem três pontinhos (Print, Record, "Made with") e sem Deploy
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    app = AppTest.from_file(APP, default_timeout=60).run()
    html = ' '.join(h.value for h in app.get('html'))
    assert '[data-testid="stMainMenu"]' in html and 'margin-top:auto' in html  # reforço do CSS e bloco do usuário no rodapé
    carregar_demo(app)
    goto(app, 'Matches')
    html = ' '.join(h.value for h in app.get('html'))
    assert html.count('im-origin-fict') >= 5 and BAND in html  # cada match fictício com selo, faixa no topo
