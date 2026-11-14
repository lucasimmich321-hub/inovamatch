"""Motor conservador: falta de informação ou evidência nunca é aprovação."""
from datetime import date
import hashlib
import json
from .domain import deadline_info, missing, normalize, today

PASS = 'ATENDIDO'
FAIL = 'NÃO ATENDIDO'
PENDING = 'PENDENTE DE VERIFICAÇÃO'

FIELDS = {
    'state': ('Estado', 'startup'), 'city': ('Cidade', 'startup'),
    'cnpj': ('CNPJ informado', 'startup'), 'age_months': ('Tempo de CNPJ em meses', 'startup'),
    'legal_type': ('Natureza jurídica', 'startup'), 'size': ('Porte', 'startup'),
    'sector': ('Área de atuação', 'startup'), 'documents': ('Documentos declarados disponíveis', 'startup'),
    'counterpart': ('Contrapartida disponível em R$', 'startup'),
    'counterpart_pct': ('Contrapartida / orçamento total (%)', 'startup'),
    'theme': ('Área temática', 'project'), 'stage': ('Estágio de desenvolvimento', 'project'),
    'requested': ('Valor solicitado em R$', 'project'), 'budget': ('Orçamento total em R$', 'project'),
    'expenses': ('Despesas previstas (categorias)', 'project'),
    'manual': ('Requisito específico / revisão humana', 'project'),
    'organization_type': ('Tipo de instituição', 'startup'),
    'execution_state': ('Estado de execução do projeto', 'project'),
    'coordinator_state': ('Estado de residência do coordenador', 'project'),
    'coordinator_degree': ('Titulação do coordenador', 'project'),
    'partners': ('Parceiros declarados', 'project'), 'partner_types': ('Tipos de parceiros', 'project'),
    'trl': ('Nível de maturidade TRL', 'project'),
    'duration_months': ('Duração do projeto em meses', 'project'),
    'project_documents': ('Documentos do projeto e da equipe', 'project'),
}
OPS = {'in': 'Um dos valores', 'contains_all': 'Contém todos', 'subset': 'Somente valores permitidos',
       'min': 'Mínimo', 'max': 'Máximo', 'present': 'Informado', 'manual': 'Revisão humana',
       'eq': 'Igual a', 'neq': 'Diferente de', 'not_in': 'Não pertence à lista',
       'contains': 'Contém', 'disjoint': 'Não contém valores proibidos'}

DIMENSIONS = {'eligibility': 'Elegibilidade obrigatória', 'alignment': 'Aderência temática e técnica',
              'readiness': 'Prontidão documental e operacional'}


def dimension_for(field):
    if field in ('theme', 'sector', 'stage', 'trl'):
        return 'alignment'
    if field in ('documents', 'project_documents', 'partners', 'partner_types'):
        return 'readiness'
    return 'eligibility'


def months_between(start, end):
    return (end.year - start.year) * 12 + end.month - start.month - (end.day < start.day)


def actual_value(criterion, startup, project, on):
    field = criterion.get('field')
    if field == 'age_months':
        if not startup.get('opened_on'):
            return None
        reference = date.fromisoformat(criterion['reference_date']) if criterion.get('reference_date') else on
        return months_between(date.fromisoformat(startup['opened_on']), reference)
    if field == 'counterpart_pct':
        if startup.get('counterpart') is None or not project.get('budget'):
            return None
        return startup['counterpart'] / project['budget'] * 100
    return (startup if criterion.get('scope') == 'startup' else project).get(field)


def evaluate(criterion, startup, project, on=None):
    c = criterion
    result = {'id': c['id'], 'requirement': c.get('label') or FIELDS.get(c.get('field'), ('Requisito',))[0],
              'scope': c.get('scope', 'project'), 'expected': c.get('expected'), 'actual': None,
              'status': PENDING, 'mandatory': c.get('mandatory', True),
              'reason': '', 'source': c.get('source', ''), 'page': c.get('page'), 'evidence': c.get('evidence', '')}
    result['dimension'] = c.get('dimension') or dimension_for(c.get('field'))
    result['field'] = c.get('field')
    result['confidence'] = c.get('confidence')
    result['review_status'] = c.get('review_status') or ('Validado' if c.get('confirmed') else 'Pendente')
    result['provisional_status'] = PENDING
    if c.get('validation_status') == 'rejected':
        result['reason'] = 'Sugestão descartada na revisão.'
        return result
    if c.get('field') not in FIELDS or c.get('op') not in OPS or c.get('op') == 'manual' or c.get('field') == 'manual':
        result['reason'] = 'Este requisito exige análise humana; a regra automática não o verifica.'
        return result
    if c.get('scope') != FIELDS[c['field']][1]:
        result['reason'] = 'Escopo incompatível com o campo. Revise o critério.'
        return result
    try:
        actual = actual_value(c, startup, project, on or today())
        result['actual'] = actual
        if missing(actual) or (c['op'] != 'present' and missing(c.get('expected'))):
            result['reason'] = 'Informação necessária ausente; complete o cadastro ou o critério.'
            return result
        op, expected = c['op'], c.get('expected')
        if op in ('min', 'max'):
            a, e = float(actual), float(expected)
            import math
            if not math.isfinite(a) or not math.isfinite(e):
                raise ValueError('Valor não finito')
            ok = a >= e if op == 'min' else a <= e
        elif op in ('in', 'not_in'):
            if not isinstance(expected, list):
                raise ValueError('Esperada lista de opções')
            ok = normalize(actual) in {normalize(x) for x in expected}
            if op == 'not_in':
                ok = not ok
        elif op in ('contains_all', 'subset', 'disjoint'):
            if not isinstance(actual, list) or not isinstance(expected, list):
                raise ValueError('Esperadas listas')
            aset, eset = {normalize(x) for x in actual}, {normalize(x) for x in expected}
            ok = eset <= aset if op == 'contains_all' else aset <= eset if op == 'subset' else not aset.intersection(eset)
        elif op in ('eq', 'neq'):
            ok = actual == expected if isinstance(actual, (int, float)) and isinstance(expected, (int, float)) else normalize(actual) == normalize(expected)
            if op == 'neq':
                ok = not ok
        elif op == 'contains':
            ok = normalize(expected) in ({normalize(x) for x in actual} if isinstance(actual, list) else normalize(actual))
        else:
            ok = not missing(actual)
        result['provisional_status'] = PASS if ok else FAIL
        validated = c.get('confirmed') and c.get('source') and c.get('evidence') and not c.get('conflict')
        if not validated:
            result['reason'] = 'Pré-comparação calculada; exigência ainda não validada com fonte ou com conflito a resolver.'
            return result
        result['status'] = result['provisional_status']
        result['reason'] = ('Dados declarados satisfazem a regra registrada; autenticidade documental não auditada.'
                            if ok else 'Dados declarados não satisfazem a exigência registrada.')
        if c['field'] == 'age_months':
            result['reason'] += f" Referência: {c.get('reference_date') or (on or today()).isoformat()}."
    except (ValueError, TypeError, KeyError, OverflowError):
        result['reason'] = 'Formato de valor ou operador incompatível; revise os dados e o critério.'
    return result


def match(call, startup, project, on=None):
    active = [c for c in call.get('criteria', []) if c.get('validation_status') != 'rejected']
    rows = [evaluate(c, startup, project, on) for c in active]
    info = deadline_info(call, on)
    rows.append({'id': 'deadline', 'requirement': 'Prazo de inscrição', 'scope': 'call',
                 'expected': call.get('deadline'), 'actual': (on or today()).isoformat(),
                 'status': PENDING if info['days'] is None else FAIL if info['days'] < 0 else PASS,
                 'mandatory': True, 'reason': info['label'], 'source': call.get('url') or call.get('source_label', ''),
                 'page': call.get('deadline_page'), 'evidence': call.get('deadline_evidence', ''), 'dimension': 'readiness'})
    if not call.get('criteria_complete') or not active:
        rows.append({'id': 'completeness', 'requirement': 'Revisão integral das exigências', 'scope': 'call',
                     'expected': 'Requisitos obrigatórios, anexos e retificações revisados', 'actual': None,
                     'status': PENDING, 'mandatory': True,
                     'reason': 'A extração básica não cobre todas as regras. Conclua a revisão integral.',
                     'source': call.get('url') or call.get('source_label', ''), 'page': None, 'evidence': '', 'dimension': 'eligibility'})
    for conflict in call.get('conflicts', []):
        if not conflict.get('resolved'):
            rows.append({'id': conflict['id'], 'requirement': 'Possível conflito entre documentos', 'scope': 'call',
                         'expected': conflict.get('description'), 'actual': None, 'status': PENDING, 'mandatory': True,
                         'reason': 'Revise as versões e registre uma resolução antes de concluir a elegibilidade.',
                         'source': ', '.join(conflict.get('sources', [])), 'page': None, 'evidence': '', 'dimension': 'eligibility'})
    blockers = [r for r in rows if r['mandatory'] and r['status'] == FAIL]
    pending = [r for r in rows if r['status'] == PENDING]
    verdict = 'Com impedimentos' if blockers else 'Precisa de informações' if pending else 'Potencialmente elegível'
    dimensions = {key: {'label': label, 'attended': 0, 'failed': 0, 'pending': 0, 'blockers': 0} for key, label in DIMENSIONS.items()}
    for row in rows:
        bucket = dimensions[row.get('dimension', 'eligibility')]
        bucket[{PASS: 'attended', FAIL: 'failed', PENDING: 'pending'}[row['status']]] += 1
        bucket['blockers'] += int(row['status'] == FAIL and row['mandatory'])
    return {'rows': rows, 'verdict': verdict, 'blockers': len(blockers), 'pending': len(pending),
            'attended': sum(r['status'] == PASS for r in rows), 'dimensions': dimensions}


def fingerprint(call, startup, project):
    volatile = {'updated_at', 'last_seen_at', 'discovered_at'}
    call_keys = {'id', 'title', 'url', 'source_label', 'criteria', 'deadline', 'deadline_confirmed',
                 'deadline_evidence', 'deadline_page', 'criteria_complete', 'conflicts'}
    content = [{k: v for k, v in call.items() if k in call_keys}]
    content += [{k: v for k, v in r.items() if k not in volatile} for r in [startup, project]]
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def checklist(result):
    tasks = []
    for row in result['rows']:
        status, field = row['status'], row['id']
        if status == FAIL and row['mandatory']:
            text = f"Avaliar impedimento obrigatório: {row['requirement']}. {row['reason']}"
            category = 'Impedimento · pode inviabilizar esta candidatura'
        elif status == PENDING:
            text = f"Verificar e documentar: {row['requirement']}. {row['reason']}"
            category = 'Verificação necessária'
        else:
            text = f"Revisar comprovação de: {row['requirement']} (exigência: {row['expected']})."
            category = 'Preparação / comprovação'
        if status != PASS and not missing(row.get('expected')):
            expectation = str(row['expected'])
            if len(expectation) > 300:
                expectation = expectation[:300] + '… (consulte a evidência integral)'
            text += f" Exigência registrada: {expectation}."
        tasks.append({'id': field, 'text': text, 'category': category,
                      'source': row['source'], 'evidence': row['evidence']})
    return tasks
