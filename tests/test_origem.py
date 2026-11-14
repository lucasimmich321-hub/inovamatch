"""Fumaça da Fase 0: campo origem (real x demo) gravado e visível."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
from inovamatch.demo import load_demo
from inovamatch.office_stats import demo_applications
from inovamatch.portfolio import register_application
from inovamatch.storage import Store
from nav import goto

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
    match = register_application(real, demo.get('calls', 'demo-call-1'), real.get('startups', 's1'), {'id': 'p1', 'name': 'P'})
    assert match['origem'] == 'demo'


def test_modo_demonstracao_mostra_aviso_e_selo(monkeypatch):
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    app = AppTest.from_file(APP, default_timeout=60).run()
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    app = goto(app, 'Editais', open_first=False)
    assert not app.exception
    assert any('Você está na Demonstração' in w.value for w in app.warning)
    table = next(d for d in app.dataframe if 'Origem' in d.value.columns).value
    assert set(table['Origem']) == {'Fictício'}  # selo novo: "Fictício" / "Real (FAPESC)"


def test_selo_de_origem_real_fapesc_e_ficticio():
    from inovamatch.origin import match_provenance, provenance
    crawler = {'title': 'Edital X', 'institution': 'FAPESC', 'source_id': 'fapesc', 'origem': 'real'}
    assert provenance(crawler, 'call') == 'Real (FAPESC)'
    # Coletado pelo crawler nunca vira fictício, mesmo com marca legada errada.
    assert provenance({**crawler, 'simulated': True, 'origem': 'demo'}, 'call') == 'Real (FAPESC)'
    demo = Store({})
    load_demo(demo)
    assert {provenance(c, 'call') for c in demo.all('calls')} == {'Fictício'}
    assert {provenance(s) for s in demo.all('startups')} == {'Fictício'}
    assert match_provenance(None, crawler, demo.get('startups', 'demo-verde')) == 'Fictício'
    assert match_provenance(None, crawler, {'name': 'Real SA', 'origem': 'real'}) == 'Real'


def test_dashboard_nos_dados_reais(monkeypatch):
    from inovamatch import dashboard
    from inovamatch.demo import add_example_startups
    monkeypatch.delenv('INOVAMATCH_STORAGE', raising=False)
    real = Store({})
    add_example_startups(real)  # só fictícias na base real
    assert dashboard.build(real, only_real=True)['startups'] == 0
    demo = Store({})
    load_demo(demo)
    assert dashboard.build(demo)['fictitious']
    app = AppTest.from_file(APP, default_timeout=60).run()
    next(b for b in app.button if b.label == 'Carregar demonstração').click().run()
    assert any('Valores fictícios: startups e matches de demonstração' in h.value for h in app.get('html'))
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.session_state['real_data'] = real.data
    app.run()
    assert any('Sem dados reais ainda' in h.value for h in app.get('html'))
    # Sem o bloco da lateral, com a base real não vazia não há como ir para a demonstração.
    assert not any(b.label == 'Carregar demonstração' for b in app.button)
