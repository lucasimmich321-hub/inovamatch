"""Planos (SIMULAÇÃO): o que cada plano libera. Sem login, sem cobrança e sem persistência; preços a definir."""

PLANS = ['Gratuito', 'Básico', 'Intermediário', 'Premium', 'Institucional']
DEFAULT = 'Institucional'  # padrão da simulação (e da demonstração): tudo liberado

# Recurso → plano mínimo.
FEATURES = {
    'requirements': 'Básico',          # requisitos atendidos/não atendidos, pontos que reduzem a compatibilidade, sugestões
    'manage': 'Intermediário',         # Gerenciar completo: checklist, documentos, captação (datas, tarefas, lembretes, .ics)
    'draft': 'Premium',                # gerar rascunho da proposta (.txt)
    'copilot': 'Premium',              # espaço "Copiloto de IA" (Em breve; sem chamada real)
    'multi_startup': 'Institucional',  # visão de várias startups (portfólio, acompanhamento, resultados)
}
FEATURE_NAMES = {'requirements': 'Requisitos, pontos que reduzem a compatibilidade e explicação da nota',
                 'manage': 'Gerenciar completo do match (andamento, checklist, documentos e captação)',
                 'draft': 'Gerar rascunho da proposta (.txt)',
                 'copilot': 'Copiloto de IA', 'multi_startup': 'Visão de várias startups'}

# Tabela da tela "Planos". "Em breve" = não construído; nunca aparece como funcionando.
COMPARISON = [
    ('Cadastro de startups e projetos', 'Sim', 'Sim', 'Sim', 'Sim', 'Sim'),
    ('Recomendação de editais e matchmaking', 'Sim', 'Sim', 'Sim', 'Sim', 'Sim'),
    ('Nota de 0 a 10 (calculada por regras) e aviso de match forte', 'Sim', 'Sim', 'Sim', 'Sim', 'Sim'),
    ('Explicação da nota', '—', 'Sim', 'Sim', 'Sim', 'Sim'),
    ('Requisitos atendidos e não atendidos', '—', 'Sim', 'Sim', 'Sim', 'Sim'),
    ('Pontos que reduzem a compatibilidade e sugestões', '—', 'Sim', 'Sim', 'Sim', 'Sim'),
    ('Gerenciar: andamento e resultado, checklist, documentos e captação (.ics)', '—', '—', 'Sim', 'Sim', 'Sim'),
    ('Gerar rascunho da proposta', '—', '—', '—', 'Sim', 'Sim'),
    ('Copiloto de IA', '—', '—', '—', 'Em breve', 'Em breve'),
    ('Visão de várias startups', '—', '—', '—', '—', 'Sim'),
    ('Dashboard institucional (no Início)', '—', '—', '—', '—', 'Sim'),
    ('Alertas por e-mail', 'Em breve', 'Em breve', 'Em breve', 'Em breve', 'Em breve'),
    ('Preço', 'A definir', 'A definir', 'A definir', 'A definir', 'A definir'),
]


def normalize(plan):
    return plan if plan in PLANS else DEFAULT


def allows(plan, feature):
    return PLANS.index(normalize(plan)) >= PLANS.index(FEATURES[feature])


def required(feature):
    return FEATURES[feature]

# Pessoa fictícia de cada plano (perfil de DEMONSTRAÇÃO; não é login real).
PERSONAS = {
    'Gratuito': ('Lucas Andrade', 'Fundador de startup'),
    'Básico': ('Beatriz Lima', 'Sócia de startup'),
    'Intermediário': ('Rafael Costa', 'Analista de captação'),
    'Premium': ('Juliana Prado', 'Consultora de projetos'),
    'Institucional': ('Marina Souza', 'Coordenadora do escritório de projetos'),
}


def initials(name):
    parts = name.split()
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else '')).upper()
