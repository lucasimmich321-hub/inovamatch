"""O que precisa de atenção num match ou numa startup: impedimentos (vermelho) e "falta preencher" (âmbar).

Regras únicas, usadas no card da lista, no topo do painel, na tabela de requisitos, no Início e em Startups.
"""
from .applications import APPROVED, PREPARING, SUGGESTED
from .matching import FAIL, FIELDS, PENDING

OPEN = (SUGGESTED, PREPARING)  # depois da inscrição, prazo encerrado ou requisito não impede mais nada
MET, NOT_MET, OPTIONAL_NOT_MET, NO_DATA, TO_CHECK = 'Atendido', 'Não atendido', 'Opcional não atendido', 'Sem dado', 'A verificar'
SEVERITY = {NOT_MET: 'fail', OPTIONAL_NOT_MET: 'warn', NO_DATA: 'warn', TO_CHECK: 'warn', MET: 'ok'}
STARTUP_FIELDS = {'state': 'estado', 'city': 'cidade', 'opened_on': 'data de abertura', 'cnpj': 'CNPJ', 'sector': 'área de atuação',
                  'legal_type': 'natureza jurídica', 'size': 'porte', 'counterpart': 'contrapartida disponível'}


def _missing(value):
    return value is None or value == '' or value == []


def _first_lower(text):
    return text[:1].lower() + text[1:]  # "Tempo de CNPJ" → "tempo de CNPJ" (siglas intactas)


def requirement_state(row):
    """Texto da coluna Resultado. "Sem dado" só quando falta o dado da startup/projeto; o resto pendente é "A verificar"."""
    if row['status'] == FAIL:
        return NOT_MET if row.get('mandatory', True) else OPTIONAL_NOT_MET
    if row['status'] == PENDING:
        return NO_DATA if row.get('field') in FIELDS and row.get('field') != 'manual' and _missing(row.get('actual')) else TO_CHECK
    return MET


def impediments(result, application=None):
    """(motivo curto, [itens]). Vazio quando nada impede ou o match já passou da inscrição."""
    if application and application.get('status') not in OPEN:
        return '', []
    closed = [r for r in result['rows'] if r['id'] == 'deadline' and r['status'] == FAIL]
    failed = [r for r in result['rows'] if r['id'] != 'deadline' and r['status'] == FAIL and r.get('mandatory', True)]
    no_data = [r for r in result['rows'] if r.get('mandatory', True) and requirement_state(r) == NO_DATA]
    items = (['Edital encerrado (' + r['reason'].lower() + ')' for r in closed] + ['Não atende: ' + r['requirement'] for r in failed]
             + ['Sem dado para avaliar: ' + r['requirement'] for r in no_data])
    reason = ('edital encerrado' if closed else 'requisito obrigatório não atendido' if failed
              else 'falta dado obrigatório para avaliar' if no_data else '')
    return reason, items


def pendencies(result, application=None, checklist_totals=None, dates=None, tasks=None):
    """Lista de "Falta preencher: …" (sem o prefixo)."""
    out = []
    for scope, label in (('startup', 'dados da startup'), ('project', 'dados do projeto')):
        names = sorted({_first_lower(FIELDS[r['field']][0]) for r in result['rows']
                        if r.get('scope') == scope and requirement_state(r) == NO_DATA})
        if names:
            out.append(f'{label} ({", ".join(names)})')
    totals = checklist_totals or {}
    if totals.get('docs_missing'):
        out.append(f"{totals['docs_missing']} documento(s) do checklist")
    if totals.get('docs_expired'):
        out.append(f"{totals['docs_expired']} documento(s) vencido(s) para substituir")
    if application is not None and application.get('valor_solicitado') is None:
        out.append('valor solicitado')
    if application is not None and application.get('status') == APPROVED:
        if not any(d.get('estado') == 'confirmada' for d in dates or []):
            out.append('datas da captação (confirme ao menos uma)')
        unassigned = sum(1 for t in tasks or [] if t.get('status') != 'Feito' and not t.get('responsavel'))
        if unassigned:
            out.append(f'responsável de {unassigned} tarefa(s)')
    return out


def startup_gaps(startup, projects):
    """O que falta no cadastro da startup para os matches serem avaliados."""
    out = [label for field, label in STARTUP_FIELDS.items() if _missing(startup.get(field))]
    gaps = [f'cadastro ({", ".join(out)})'] if out else []
    if not projects:
        gaps.append('projeto (nenhum cadastrado)')
    return gaps
