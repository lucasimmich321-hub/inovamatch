"""Origem de cada registro: "real" (coletado da fonte ou cadastrado pelo escritório) ou "demo" (fictício, gerado pelo app).

O campo `origem` é gravado em editais, startups, projetos e matches. Registros antigos sem o campo são deduzidos
pelas marcas legadas `simulated` / `demo`, para que nada criado antes desta versão perca a identificação.
"""
from html import escape

REAL, DEMO = 'real', 'demo'
LABELS = {REAL: 'Dados reais', DEMO: 'Demonstração'}


def origem(record):
    value = (record or {}).get('origem')
    if value in LABELS:
        return value
    return DEMO if (record or {}).get('simulated') or (record or {}).get('demo') else REAL


def is_demo(record):
    return origem(record) == DEMO


def label(record):
    return LABELS[origem(record)]


def badge_html(record):
    """Selo HTML só para registros de demonstração (o real é o padrão e não precisa de aviso)."""
    if not is_demo(record):
        return ''
    return f'<span class="tag demo" title="Registro fictício, sem valor real">{escape(LABELS[DEMO])}</span>'
