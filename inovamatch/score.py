"""Nota de 0 a 10 por match, CALCULADA POR REGRAS (transparente, sem IA e sem chance de aprovação).

Regra:
- Cada requisito vale um peso: obrigatório 2, opcional 1.
- Atendido ganha o peso inteiro; pendente (sem dado ou a verificar) ganha metade; não atendido ganha zero.
- Nota = 10 × pontos ganhos ÷ pontos possíveis, com 1 casa decimal.
- Impedimento (requisito obrigatório não atendido, inclusive prazo encerrado) limita a nota a 4,0.
- Match já inscrito, aprovado, reprovado ou desistente: o prazo de inscrição sai da conta.
"""
from .matching import FAIL, PASS, PENDING

MANDATORY_WEIGHT, OPTIONAL_WEIGHT = 2, 1
BLOCKER_CAP = 4.0
STRONG = 8.0  # "Match forte" a partir desta nota
LABEL = 'calculado por regras'


def compute(result, application=None):
    """Com o match já inscrito (ou depois), o prazo de inscrição encerrado não pesa mais na nota."""
    from .attention import OPEN
    rows = result.get('rows') or []
    if application and application.get('status') not in OPEN:
        rows = [r for r in rows if r.get('id') != 'deadline']
    possible = earned = 0.0
    counts = {'mandatory_met': 0, 'mandatory_total': 0, 'optional_met': 0, 'optional_total': 0, 'pending': 0, 'blockers': 0}
    for row in rows:
        mandatory = row.get('mandatory', True)
        weight = MANDATORY_WEIGHT if mandatory else OPTIONAL_WEIGHT
        possible += weight
        counts['mandatory_total' if mandatory else 'optional_total'] += 1
        if row['status'] == PASS:
            earned += weight
            counts['mandatory_met' if mandatory else 'optional_met'] += 1
        elif row['status'] == PENDING:
            earned += weight / 2
            counts['pending'] += 1
        elif row['status'] == FAIL and mandatory:
            counts['blockers'] += 1
    raw = round(10 * earned / possible, 1) if possible else 0.0
    capped = counts['blockers'] > 0 and raw > BLOCKER_CAP
    value = BLOCKER_CAP if capped else raw
    return {'value': value, 'raw': raw, 'capped': capped, 'strong': value >= STRONG, **counts}


def text(value):
    return f'{value:.1f}'.replace('.', ',')


def explanation(info):
    """Frases curtas para mostrar a regra aplicada a este match (plano Básico em diante)."""
    lines = [f"Obrigatórios atendidos: {info['mandatory_met']} de {info['mandatory_total']} (peso {MANDATORY_WEIGHT} cada).",
             f"Opcionais atendidos: {info['optional_met']} de {info['optional_total']} (peso {OPTIONAL_WEIGHT} cada).",
             f"Pendentes (sem dado ou a verificar): {info['pending']}, valem metade do peso.",
             'Não atendidos valem zero.']
    if info['capped']:
        lines.append(f"Há impedimento: a nota {text(info['raw'])} foi limitada a {text(BLOCKER_CAP)}.")
    return lines
