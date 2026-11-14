"""Origem de cada registro: "real" (coletado da fonte ou cadastrado pelo escritório) ou "demo" (fictício, gerado pelo app).

O campo `origem` é gravado em editais, startups, projetos e matches. Registros antigos sem o campo são deduzidos
pelas marcas legadas `simulated` / `demo`, para que nada criado antes desta versão perca a identificação.
"""
from html import escape

REAL, DEMO = 'real', 'demo'
LABELS = {REAL: 'Dados reais', DEMO: 'Demonstração'}


def from_crawler(record):
    """Edital coletado por uma fonte automática (crawler da FAPESC): nunca é fictício, seja qual for outra marca."""
    return bool((record or {}).get('source_id'))


def origem(record):
    if from_crawler(record):
        return REAL
    value = (record or {}).get('origem')
    if value in LABELS:
        return value
    return DEMO if (record or {}).get('simulated') or (record or {}).get('demo') else REAL


def is_demo(record):
    return origem(record) == DEMO


def label(record):
    return LABELS[origem(record)]


FICTITIOUS = 'Fictício'
SIMULATION = 'Simulação'  # o único edital inventado da demonstração (só para "Simular retificação")


def provenance(record, kind=None):
    """Texto do selo de origem: "Fictício" (demonstração), "Real (FAPESC)" (edital real com órgão conhecido) ou "Real"."""
    if (record or {}).get('simulacao'):
        return SIMULATION
    if is_demo(record):
        return FICTITIOUS
    institution = ((record or {}).get('institution') or '').strip()
    if kind == 'call' and institution and institution != 'Revisar instituição':
        return f'Real ({institution})'
    return 'Real'


def match_provenance(application, call, startup):
    """Match é fictício se ele, o edital ou a startup for de demonstração."""
    return FICTITIOUS if any(is_demo(r) for r in (application, call, startup) if r) else 'Real'


def badge_html(text):
    """Selo pequeno e discreto de origem (texto + cor; o fictício em laranja)."""
    css = 'fict' if text in (FICTITIOUS, SIMULATION) else 'real'
    title = ('Edital inventado, só para simular uma retificação' if text == SIMULATION
             else 'Registro fictício, criado para demonstração' if css == 'fict' else 'Registro real')
    return f'<span class="im-origin im-origin-{css}" title="{title}">{escape(text)}</span>'
