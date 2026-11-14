"""Planos (SIMULAÇÃO): o que cada plano libera. Sem login, sem cobrança e sem persistência; preços a definir."""

PLANS = ['Gratuito', 'Básico', 'Intermediário', 'Premium', 'Institucional']
DEFAULT = 'Institucional'  # padrão da simulação (e da demonstração): tudo liberado

# Recurso → plano mínimo.
FEATURES = {
    'requirements': 'Básico',          # requisitos atendidos/não atendidos, pontos que reduzem a compatibilidade, sugestões
    'manage': 'Intermediário',         # Gerenciar completo: checklist, documentos, captação (datas, tarefas, lembretes, .ics)
    'copilot': 'Premium',              # espaço "Copiloto de IA" (Em breve; sem chamada real)
    'multi_startup': 'Institucional',  # visão de várias startups (portfólio, acompanhamento, resultados)
}
FEATURE_NAMES = {'requirements': 'Requisitos e pontos que reduzem a compatibilidade', 'manage': 'Gerenciar completo do match',
                 'copilot': 'Copiloto de IA', 'multi_startup': 'Visão de várias startups'}

# Tabela da tela "Planos". "Em breve" = não construído; nunca aparece como funcionando.
COMPARISON = [
    ('Cadastro de startups e projetos', 'Sim', 'Sim', 'Sim', 'Sim', 'Sim'),
    ('Recomendação de editais e matchmaking', 'Sim', 'Sim', 'Sim', 'Sim', 'Sim'),
    ('Aviso de match forte (na tela)', 'Sim', 'Sim', 'Sim', 'Sim', 'Sim'),
    ('Requisitos atendidos e não atendidos', '—', 'Sim', 'Sim', 'Sim', 'Sim'),
    ('Pontos que reduzem a compatibilidade e sugestões', '—', 'Sim', 'Sim', 'Sim', 'Sim'),
    ('Gerenciar: checklist, documentos e captação (.ics)', '—', '—', 'Sim', 'Sim', 'Sim'),
    ('Copiloto de IA', '—', '—', '—', 'Em breve', 'Em breve'),
    ('Visão de várias startups', '—', '—', '—', '—', 'Sim'),
    ('Dashboard do escritório', '—', '—', '—', '—', 'Em breve'),
    ('Alertas por e-mail', 'Em breve', 'Em breve', 'Em breve', 'Em breve', 'Em breve'),
    ('Preço', 'A definir', 'A definir', 'A definir', 'A definir', 'A definir'),
]


def normalize(plan):
    return plan if plan in PLANS else DEFAULT


def allows(plan, feature):
    return PLANS.index(normalize(plan)) >= PLANS.index(FEATURES[feature])


def required(feature):
    return FEATURES[feature]
