"""Demonstração: startups, matches e captação FICTÍCIOS sobre editais REAIS do crawler; nunca entra na base real.

Inventado aqui: as 5 startups (e projetos), os matches delas, a captação do aprovado e um único edital de
simulação (SIM_CALL_ID), que só existe para o botão "Simular retificação".
"""
from datetime import timedelta
from .domain import today
from .origin import from_crawler


def demo_cnpj(n):
    """CNPJ alfanumérico FICTÍCIO (prefixo DEMO) com dígitos verificadores válidos, para o cadastro passar na validação."""
    base = f'DEMO{n:08d}'
    nums = [ord(c) - 48 for c in base]
    for weights in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        rem = sum(a * b for a, b in zip(nums, weights)) % 11
        nums.append(0 if rem < 2 else 11 - rem)
    return base + ''.join(str(d) for d in nums[12:])


# Startups em formação, de propósito (caso legítimo): sem CNPJ, data de abertura, natureza jurídica e porte.
NO_CNPJ_IDS = ('demo-pendente',)


def _cnpj_fields(sid):
    if sid in NO_CNPJ_IDS:
        return {'cnpj': '', 'sem_cnpj': True, 'opened_on': None, 'legal_type': None, 'size': None}
    return {'cnpj': demo_cnpj(STARTUP_IDS.index(sid) + 1), 'sem_cnpj': False}


# Startups FICTÍCIAS: uma por perfil (plans.PERSONA_STARTUP) e a Semente Lab, em formação (sem CNPJ).
STARTUPS = [
    # id, nome, UF, abertura, área, contrapartida, valor pedido, estágio
    ('demo-fora', 'Horizonte Digital', 'SC', '2020-03-01', 'Saúde', 30_000, 100_000, 'MVP'),          # Lucas · Gratuito
    ('demo-bio', 'Serra Biotec', 'SC', '2018-09-10', 'Saúde', 35_000, 90_000, 'Em operação'),        # Beatriz · Básico
    ('demo-agro', 'Vale Agro Digital', 'SC', '2019-06-01', 'Tecnologia', 40_000, 120_000, 'MVP'),     # Rafael · Intermediário
    ('demo-verde', 'Araucária Tech', 'SC', '2020-01-10', 'Tecnologia', 30_000, 100_000, 'Protótipo'),  # Juliana · Premium
    ('demo-pendente', 'Semente Lab', None, None, None, None, 100_000, 'Protótipo'),                   # em formação
]
STARTUP_IDS = tuple(row[0] for row in STARTUPS)
# Único edital inventado: existe só para o botão "Simular retificação" (selo "Simulação").
SIM_CALL_ID = 'demo-call-sim'


def load_demo(store):
    """Startups e projetos FICTÍCIOS e o edital de simulação. Os editais de verdade vêm do crawler (copy_real_calls)."""
    for sid, name, state, opened, sector, counterpart, requested, stage in STARTUPS:
        if store.get('startups', sid):
            continue
        store.save('startups', {'id': sid, 'name': name, 'state': state, 'city': 'Joaçaba' if state == 'SC' else '',
                               'opened_on': opened, 'cnpj': '', 'legal_type': 'Sociedade Limitada', 'size': 'ME',
                               'sector': sector, 'description': 'Startup fictícia para demonstração.',
                               'counterpart': counterpart, 'simulated': True, 'origem': 'demo',
                               'documents': ['Certidão fiscal'] if sid in NO_CNPJ_IDS else ['Cartão CNPJ', 'Certidão fiscal'],
                               **_cnpj_fields(sid)})
        store.save('projects', {'id': 'project-' + sid, 'startup_id': sid, 'name': 'Projeto ' + name,
                               'objective': 'Projeto fictício para demonstração.', 'description': 'Projeto fictício.',
                               'theme': sector, 'stage': stage, 'requested': requested, 'budget': requested + (counterpart or 0),
                               'expenses': ['Equipamentos', 'Bolsas'], 'team': 'Equipe fictícia', 'simulated': True, 'origem': 'demo'})
    if not store.get('calls', SIM_CALL_ID):
        source = 'SIMULAÇÃO · texto inventado para testar a retificação'
        store.save('calls', {'id': SIM_CALL_ID, 'title': '[SIMULAÇÃO] Edital de teste para "Simular retificação"',
                             'institution': 'Simulação (não é edital real)', 'url': '', 'source_label': source,
                             'simulated': True, 'simulacao': True, 'origem': 'demo', 'criteria': [], 'criteria_complete': False,
                             'deadline': (today() + timedelta(days=25)).isoformat(), 'deadline_confirmed': True,
                             'deadline_evidence': 'SIMULAÇÃO · prazo inventado.',
                             'opening_date': (today() - timedelta(days=10)).isoformat(), 'opening_confirmed': True,
                             'opening_evidence': 'SIMULAÇÃO · abertura inventada.', 'review_state': 'Publicado',
                             'relevance': 'Relevante',
                             'summary': 'Edital inventado, sem oportunidade real: serve só para mostrar o que acontece quando '
                                        'um edital é retificado (botão "Simular retificação").'})


def copy_real_calls(store, calls):
    """Copia para a base da demonstração os editais REAIS do crawler (sem alterar nada neles)."""
    count = 0
    for call in calls:
        if from_crawler(call) and not store.get('calls', call['id']):
            store.save('calls', dict(call))
            count += 1
    return count


def _ranked(calls, closed):
    """Editais reais do crawler: abertos (ou fechados) primeiro os com critérios lidos do PDF, depois pelo prazo."""
    from .crawler import edital_year
    pool = [c for c in calls if from_crawler(c) and bool(c.get('source_closed')) == closed]
    if closed:  # encerrado: o mais recente (ano no título), para o "Aprovado" ser plausível
        return sorted(pool, key=lambda c: (c.get('relevance') != 'Relevante', -(edital_year(c.get('title', '')) or 0), c.get('title', ''), c['id']))
    return sorted(pool, key=lambda c: (not c.get('criteria'), c.get('deadline') is None, c.get('deadline') or '', c['id']))


def demo_matches(store):
    """Até 5 matches FICTÍCIOS (startups fictícias × editais REAIS do crawler), um status cada.

    Sugerido (Horizonte) e Em preparação (Semente Lab) e Inscrito (Vale Agro) em editais abertos;
    Aprovado com captação (Araucária) e Reprovado (Serra Biotec) num edital já encerrado.
    Sem edital real na base, nenhum match é criado (a tela avisa; nada é inventado no lugar).
    """
    from .applications import APPROVED, PREPARING, REJECTED, SUBMITTED, SUGGESTED, update_application
    from .link_checklist import DOCS, build_checklist
    from .portfolio import register_application
    from .vault import startup_documents
    from . import captacao

    calls = store.all('calls')
    opened, closed = _ranked(calls, False), _ranked(calls, True)
    day = lambda n: (today() + timedelta(days=n)).isoformat()
    plan = []
    if opened:
        plan += [(opened[0], 'demo-fora', SUGGESTED), (opened[1 % len(opened)], 'demo-pendente', PREPARING),
                 (opened[1 % len(opened)], 'demo-agro', SUBMITTED)]
    if closed:
        plan += [(closed[0], 'demo-verde', APPROVED), (closed[0], 'demo-bio', REJECTED)]
    created = []
    for call, startup_id, status in plan:
        startup, project = store.get('startups', startup_id), store.get('projects', 'project-' + startup_id)
        if not (startup and project) or store.get('applications', f'{call["id"]}:{project["id"]}'):
            continue
        record = register_application(store, call, startup, project)
        store.save('applications', {**record, 'simulated': True, 'origem': 'demo'})
        if status == SUGGESTED:
            update_application(store, record['id'], status=SUGGESTED)
        elif status == SUBMITTED:
            update_application(store, record['id'], status=SUBMITTED, data_submissao=day(-3))
        elif status == REJECTED:
            update_application(store, record['id'], status=REJECTED, data_submissao=day(-62), data_resultado=day(-20),
                               motivo='Reprovada no mérito', motivo_obs='Dado fictício de demonstração.')
        elif status == PREPARING:
            # Metade do checklist marcada e um documento do cofre vinculado.
            items = [i for i in build_checklist(store, call, startup, project) if i['marcavel']]
            for item in items[:len(items) // 2]:
                store.save('tasks', {'id': f'{call["id"]}:{project["id"]}:chk:{item["id"]}', 'call_id': call['id'],
                                     'project_id': project['id'], 'criterion_id': item['id'], 'kind': 'checklist', 'done': True,
                                     'origem': 'demo'})
            doc_item = next((i for i in items if i['secao'] == DOCS), None)
            docs = startup_documents(store, startup_id)
            if doc_item and docs:
                store.save('tasks', {'id': f'{call["id"]}:{project["id"]}:link:{doc_item["id"]}', 'kind': 'doc_link',
                                     'call_id': call['id'], 'project_id': project['id'], 'doc_id': docs[0]['id'], 'origem': 'demo'})
        else:  # Aprovado: valor e captação FICTÍCIOS (datas manuais, tarefas e lembretes)
            application = update_application(store, record['id'], status=APPROVED, data_submissao=day(-62),
                                             data_resultado=day(-20), valor_captado=90_000)
            for s in captacao.suggested_dates(call, today()):  # só se o cronograma real tiver datas futuras
                captacao.add_date(store, application, s['titulo'], s['data'], captacao.EDITAL, s['fonte'], True, s['sugestao'])
            captacao.add_date(store, application, 'Assinatura do termo de outorga', day(3))
            captacao.add_date(store, application, 'Liberação de parcela · 1ª parcela', day(30))
            captacao.add_date(store, application, 'Prestação de contas', day(200), confirmada=False)
            for index, task in enumerate(captacao.tasks(store, application['id'])):
                captacao.update_task(store, task['id'], responsavel='Equipe do escritório (fictícia)',
                                     status='Em andamento' if index == 0 else 'A fazer')
            captacao.add_task(store, application, 'Abrir conta específica do projeto', day(-1), 'Startup (fictícia)')
        created.append(record['id'])
    return created


def simulate_rectification(store, call_id):
    """Só na demonstração: muda o texto de um edital fictício e registra a nova versão (fica "Alterado")."""
    import hashlib
    from datetime import datetime, timedelta as delta
    from .domain import now_iso
    from .versioning import register
    call = store.get('calls', call_id)
    if not call or call.get('origem') != 'demo':
        raise ValueError('Retificação simulada só existe para editais da demonstração.')
    source = 'SIMULADO · texto do regulamento'
    base = [{'page': 1, 'text': (call.get('summary') or '') + ' ' + ' '.join(c.get('evidence', '') for c in call.get('criteria', []))}]
    if not any(v['source'] == source for v in call.get('versions') or []):
        first = (datetime.fromisoformat(now_iso()) - delta(days=7)).isoformat(timespec='seconds')
        call = register(call, source, hashlib.sha256(repr(base).encode()).hexdigest(), base, when=first)
    number = sum(v['source'] == source for v in call['versions'])
    pages = base + [{'page': 2, 'text': f'RETIFICAÇÃO SIMULADA nº {number}: alterado o item de documentos exigidos '
                                         f'(inclusão de declaração fictícia nº {number}).'}]
    call = register(call, source, hashlib.sha256(repr(pages).encode()).hexdigest(), pages)
    return store.save('calls', call)


