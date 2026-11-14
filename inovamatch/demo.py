"""Dados integralmente fictícios; nunca inseridos no SQLite de produção."""
from datetime import timedelta
from .domain import today


def _demo_schedule(days, source):
    day = lambda n: (today() + timedelta(days=n)).isoformat()
    rows = [('Submissão das propostas', day(-10), day(days)), ('Divulgação do resultado final', day(days + 20), day(days + 20)),
            ('Contratação e assinatura do termo de outorga', day(days + 35), day(days + 35))]
    return [{'etapa': etapa, 'inicio': start, 'fim': end, 'page': None, 'source': source, 'continuous': False,
             'evidence': f'SIMULADO · {etapa}'} for etapa, start, end in rows]


def load_demo(store):
    records = [
        ('demo-verde', 'Araucária Tech', 'SC', '2020-01-10', 'Tecnologia', 30_000),
        # Horizonte (Saúde, SC): atende o edital Saúde e Impacto e não atende o Inovação Catarinense (área temática).
        ('demo-fora', 'Horizonte Digital', 'SC', '2020-03-01', 'Saúde', 30_000),
        ('demo-pendente', 'Semente Lab', None, None, None, None),
    ]
    for sid, name, state, opened, sector, counterpart in records:
        if store.get('startups', sid):
            continue
        store.save('startups', {'id': sid, 'name': name, 'state': state, 'city': 'Joaçaba' if state == 'SC' else '',
                               'opened_on': opened, 'cnpj': '', 'legal_type': 'Sociedade Limitada', 'size': 'ME',
                               'sector': sector, 'description': 'Startup fictícia para demonstração.',
                               'counterpart': counterpart, 'documents': ['Cartão CNPJ', 'Certidão fiscal'], 'simulated': True, 'origem': 'demo'})
        store.save('projects', {'id': 'project-' + sid, 'startup_id': sid, 'name': 'Plataforma ' + name,
                               'objective': 'Digitalizar processos de pequenas empresas.', 'description': 'Projeto simulado.',
                               'theme': sector, 'stage': 'MVP' if sid == 'demo-fora' else 'Protótipo', 'requested': 100_000, 'budget': 130_000,
                               'expenses': ['Equipamentos', 'Bolsas'], 'team': 'Equipe fictícia multidisciplinar', 'simulated': True, 'origem': 'demo'})
    for idx, title, days, theme in [(1, 'Inovação Catarinense', 25, 'Tecnologia'), (2, 'Saúde e Impacto', 5, 'Saúde')]:
        cid = f'demo-call-{idx}'
        if store.get('calls', cid):
            continue
        source = f'SIMULADO · regulamento de demonstração {idx}'
        specs = [
            ('state', 'in', ['SC'], 'Sede em Santa Catarina', 'A empresa deve estar sediada em SC.'),
            ('age_months', 'min', 24, 'CNPJ há pelo menos 24 meses', 'Tempo mínimo de constituição: 24 meses.'),
            ('legal_type', 'in', ['Sociedade Limitada'], 'Natureza jurídica', 'São admitidas sociedades limitadas.'),
            ('theme', 'in', [theme], 'Área temática do projeto', f'O projeto deve pertencer à área {theme}.'),
            ('requested', 'max', 150_000, 'Teto por projeto', 'O valor solicitado deve ser de até R$ 150.000,00.'),
            ('counterpart_pct', 'min', 10, 'Contrapartida financeira', 'Exige-se 10% do orçamento total como contrapartida.'),
            ('documents', 'contains_all', ['Cartão CNPJ', 'Certidão fiscal'], 'Documentos para candidatura',
             'Apresentar cartão CNPJ e certidão fiscal.'),
            ('expenses', 'subset', ['Equipamentos', 'Bolsas'], 'Despesas permitidas', 'Financiáveis: equipamentos e bolsas.'),
            # Critérios preferenciais (opcionais): não impedem, só variam a nota.
            ('stage', 'in', ['MVP', 'Em operação'], 'Estágio preferencial (MVP ou em operação)',
             'Terão preferência projetos em MVP ou em operação.', False),
            ('counterpart_pct', 'min', 25, 'Contrapartida de 25% ou mais (pontuação extra)', 'Contrapartida acima de 25% soma pontos.', False),
            ('budget', 'min', 150_000, 'Orçamento a partir de R$ 150 mil (prioridade)', 'Projetos a partir de R$ 150 mil têm prioridade.', False),
            ('size', 'in', ['EPP'], 'Porte preferencial: EPP', 'Empresas de pequeno porte têm prioridade.', False),
        ]
        from .matching import FIELDS
        criteria = [{'id': f'criterion-{i}', 'field': field, 'scope': FIELDS[field][1], 'op': op, 'expected': expected,
                     'label': label, 'evidence': evidence, 'source': source, 'page': i + 1, 'mandatory': required[0] if required else True,
                     'confirmed': True}
                    for i, (field, op, expected, label, evidence, *required) in enumerate(specs)]
        store.save('calls', {'id': cid, 'title': f'[SIMULADO] {title}', 'institution': 'Instituição fictícia',
                             'url': '', 'source_label': source, 'simulated': True, 'origem': 'demo', 'criteria': criteria,
                             'criteria_complete': True, 'deadline': (today() + timedelta(days=days)).isoformat(),
                             'deadline_confirmed': True, 'deadline_evidence': f'Inscrições até {days} dias após carregar a demonstração.',
                             # Abertura confirmada (fictícia) para a demo ter edital "Aberto" pelo mesmo cálculo do produto.
                             'opening_date': (today() - timedelta(days=10)).isoformat(), 'opening_confirmed': True,
                             'opening_evidence': 'SIMULADO · inscrições abertas desde 10 dias antes de carregar a demonstração.',
                             # Cronograma FICTÍCIO: alimenta as datas sugeridas da aba Captação na demonstração.
                             'schedule': _demo_schedule(days, source),
                             'review_state': 'Publicado', 'relevance': 'Relevante',
                             'summary': 'Edital fictício, sem oportunidade real de financiamento.'})


def demo_matches(store):
    """8 matches FICTÍCIOS prontos para a página Matches (só na base de demonstração, via "Carregar demonstração").

    Os 3 primeiros: recém-criado (Sugerido), checklist pela metade (Em preparação) e Aprovado com captação.
    Mais 3 startups fictícias e 5 matches (Inscrito, Reprovado, Desistiu, Em preparação, Aprovado) para o dashboard.
    Todos ligados a editais e projetos existentes (nenhum match órfão).
    """
    from .applications import APPROVED, NOT_SUBMITTED, PREPARING, REJECTED, SUBMITTED, SUGGESTED, update_application
    from .link_checklist import DOCS, build_checklist
    from .portfolio import register_application
    from .vault import startup_documents
    from . import captacao

    if not store.get('calls', 'demo-call-1'):
        return []
    day = lambda n: (today() + timedelta(days=n)).isoformat()
    from .matching import FIELDS
    if not store.get('calls', 'demo-call-3'):
        # Edital fictício já encerrado: o match aprovado precisa de um edital com resultado divulgado.
        base = store.get('calls', 'demo-call-1')
        source = 'SIMULADO · regulamento de demonstração 3'
        # Aceita Tecnologia e Saúde (a Oeste Energia, de Energia, fica de fora: é o match Reprovado).
        criteria = [{**c, 'expected': ['Tecnologia', 'Saúde'], 'label': 'Área temática do projeto',
                     'evidence': 'O projeto deve pertencer às áreas Tecnologia ou Saúde.'} if c['field'] == 'theme' else c
                    for c in base['criteria']]
        # Preferenciais só deste edital (opcionais): variam a nota sem impedir.
        criteria += [{'id': f'criterion-c3-{i}', 'field': f, 'scope': FIELDS[f][1], 'op': op, 'expected': exp, 'label': label,
                      'evidence': label + '.', 'source': source, 'page': 20 + i, 'mandatory': False, 'confirmed': True}
                     for i, (f, op, exp, label) in enumerate([('city', 'in', ['Chapecó'], 'Prioridade para sede em Chapecó'),
                                                             ('sector', 'in', ['Saúde'], 'Área prioritária: Saúde'),
                                                             ('requested', 'max', 95_000, 'Pedido de até R$ 95 mil (prioridade)')])]
        store.save('calls', {**base, 'id': 'demo-call-3', 'title': '[SIMULADO] Subvenção Inovação (encerrado)', 'source_label': source,
                             'criteria': criteria,
                             'deadline': day(-60), 'opening_date': day(-100), 'deadline_evidence': 'SIMULADO · inscrições encerradas.',
                             'opening_evidence': 'SIMULADO · inscrições abertas de 100 a 60 dias atrás.',
                             'schedule': [{'etapa': e, 'inicio': a, 'fim': b, 'page': None, 'source': source, 'continuous': False,
                                           'evidence': f'SIMULADO · {e}'} for e, a, b in
                                          [('Submissão das propostas', day(-100), day(-60)), ('Divulgação do resultado final', day(-20), day(-20)),
                                           ('Assinatura do termo de outorga', day(3), day(3))]],
                             'summary': 'Edital fictício encerrado, usado só para demonstrar a gestão da captação.'})
    extra = [('demo-agro', 'Vale Agro Digital', 'Tecnologia', '2019-06-01', 40_000, 120_000, 'MVP', [('CNPJ', None), ('Certidões', 120)]),
             ('demo-energia', 'Oeste Energia', 'Energia', '2021-02-15', 20_000, 140_000, 'Protótipo', [('CNPJ', None)]),
             ('demo-bio', 'Serra Biotec', 'Saúde', '2018-09-10', 35_000, 90_000, 'Em operação', [('CNPJ', None)])]
    for sid, name, sector, opened, counterpart, requested, stage, docs in extra:
        for tipo, days in docs:
            if not store.get('documents', f'demo-doc-{sid}-{tipo}'):
                store.save('documents', {'id': f'demo-doc-{sid}-{tipo}', 'startup_id': sid, 'tipo': tipo, 'nome': f'{tipo} (fictício).pdf',
                                         'arquivo': None, 'mime': 'application/pdf', 'tamanho': 0, 'demo': True, 'origem': 'demo',
                                         'validade': day(days) if days is not None else None})
        if store.get('startups', sid):
            continue
        store.save('startups', {'id': sid, 'name': name, 'state': 'SC', 'city': 'Joaçaba', 'opened_on': opened, 'cnpj': '',
                                'legal_type': 'Sociedade Limitada', 'size': 'ME', 'sector': sector,
                                'description': 'Startup fictícia para demonstração.', 'counterpart': counterpart,
                                'documents': ['Cartão CNPJ', 'Certidão fiscal'], 'simulated': True, 'origem': 'demo'})
        store.save('projects', {'id': 'project-' + sid, 'startup_id': sid, 'name': 'Projeto ' + name, 'objective': 'Projeto simulado.',
                                'description': 'Projeto simulado.', 'theme': sector, 'stage': stage, 'requested': requested,
                                'budget': requested + counterpart, 'expenses': ['Equipamentos', 'Bolsas'],
                                'team': 'Equipe fictícia', 'simulated': True, 'origem': 'demo'})
    plan = [('demo-call-2', 'demo-fora', SUGGESTED), ('demo-call-1', 'demo-pendente', PREPARING), ('demo-call-3', 'demo-verde', APPROVED),
            ('demo-call-1', 'demo-agro', SUBMITTED), ('demo-call-3', 'demo-energia', REJECTED), ('demo-call-3', 'demo-agro', NOT_SUBMITTED),
            ('demo-call-2', 'demo-bio', PREPARING), ('demo-call-3', 'demo-bio', APPROVED)]
    created = []
    for call_id, startup_id, status in plan:
        call, startup, project = store.get('calls', call_id), store.get('startups', startup_id), store.get('projects', 'project-' + startup_id)
        if not (call and startup and project) or store.get('applications', f'{call_id}:{project["id"]}'):
            continue
        record = register_application(store, call, startup, project)
        store.save('applications', {**record, 'simulated': True, 'origem': 'demo'})
        if status == SUGGESTED:
            update_application(store, record['id'], status=SUGGESTED)
        elif status == SUBMITTED:
            update_application(store, record['id'], status=SUBMITTED, data_submissao=day(-3))
        elif status == REJECTED:
            update_application(store, record['id'], status=REJECTED, data_submissao=day(-62), data_resultado=day(-20),
                               motivo='Reprovada no mérito', motivo_obs='Dado de demonstração.')
        elif status == NOT_SUBMITTED:
            update_application(store, record['id'], status=NOT_SUBMITTED, motivo='Desistência da startup', motivo_obs='Dado de demonstração.')
        elif status == APPROVED and startup_id != 'demo-verde':
            update_application(store, record['id'], status=APPROVED, data_submissao=day(-62), data_resultado=day(-20), valor_captado=60_000)
        elif status == PREPARING:
            # Metade do checklist marcada e um documento do cofre vinculado.
            items = [i for i in build_checklist(store, call, startup, project) if i['marcavel']]
            for item in items[:len(items) // 2]:
                store.save('tasks', {'id': f'{call_id}:{project["id"]}:chk:{item["id"]}', 'call_id': call_id, 'project_id': project['id'],
                                     'criterion_id': item['id'], 'kind': 'checklist', 'done': True, 'origem': 'demo'})
            doc_item = next((i for i in items if i['secao'] == DOCS), None)
            docs = startup_documents(store, startup_id)
            if doc_item and docs:
                store.save('tasks', {'id': f'{call_id}:{project["id"]}:link:{doc_item["id"]}', 'kind': 'doc_link', 'call_id': call_id,
                                     'project_id': project['id'], 'doc_id': docs[0]['id'], 'origem': 'demo'})
        else:
            application = update_application(store, record['id'], status=APPROVED, data_submissao=day(-62), data_resultado=day(-20),
                                             valor_captado=90_000)
            for s in captacao.suggested_dates(call, today()):
                captacao.add_date(store, application, s['titulo'], s['data'], captacao.EDITAL, s['fonte'], True, s['sugestao'])
            captacao.add_date(store, application, 'Liberação de parcela · 1ª parcela', day(30))
            captacao.add_date(store, application, 'Prestação de contas', day(200), confirmada=False)
            for index, task in enumerate(captacao.tasks(store, application['id'])):
                captacao.update_task(store, task['id'], responsavel='Equipe do escritório (fictícia)',
                                     status='Em andamento' if index == 0 else 'A fazer')
            captacao.add_task(store, application, 'Abrir conta específica do projeto', day(-1), 'Startup (fictícia)')
        created.append(record['id'])
    return created
