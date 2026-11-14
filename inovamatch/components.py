"""Componentes visuais reutilizados em todas as telas (HTML para st.html). Cores em tokens CSS definidos no app."""
from html import escape
from .icons import icon

# Situação → (classe CSS, ícone). Sempre ícone + texto, nunca só cor.
CHIP = {'Aberto': ('ok', 'check'), 'Fluxo contínuo': ('info', 'refresh'), 'Futuro': ('muted', 'calendar'),
        'Em breve': ('muted', 'calendar'), 'Encerrado': ('muted', 'x'), 'Não confirmado': ('warn', 'help'),
        'Demonstração': ('warn', 'flask'),
        # Captação: estado e procedência de cada data importante.
        'A confirmar': ('warn', 'help'), 'Confirmada': ('ok', 'check'), 'Do edital': ('info', 'file'), 'Manual': ('muted', 'tag'),
        'Aprovado': ('ok', 'check'), 'Impedido': ('fail', 'alert')}


def chip(text, kind=None, icon_name=None):
    css, name = CHIP.get(text, (kind or 'muted', icon_name or 'tag'))
    return f'<span class="im-chip im-chip-{css}">{icon(name, 14)}{escape(text)}</span>'


def card(title, subtitle='', chips=(), facts=(), summary=''):
    """facts: [(ícone, texto)]. summary é cortado em 2 linhas via CSS."""
    facts_html = ''.join(f'<span class="im-fact">{icon(i, 15)}{escape(t)}</span>' for i, t in facts if t)
    return (f'<div class="im-card"><div class="im-chips">{"".join(chips)}</div>'
            f'<div class="im-card-title">{escape(title)}</div>'
            + (f'<div class="im-card-sub">{escape(subtitle)}</div>' if subtitle else '')
            + (f'<div class="im-facts">{facts_html}</div>' if facts_html else '')
            + (f'<p class="im-summary">{escape(summary)}</p>' if summary else '') + '</div>')


def empty_state(title, text):
    return f'<div class="im-empty">{icon("radar", 28)}<div class="im-empty-title">{escape(title)}</div><p>{escape(text)}</p></div>'


def band(kind, title, items=(), prefix=''):
    """Faixa de atenção no topo: kind 'fail' (vermelho, impedimento) ou 'warn' (âmbar, falta preencher). Ícone + texto."""
    lis = ''.join(f'<li>{escape(prefix + i)}</li>' for i in items)
    role = ' role="alert"' if kind == 'fail' else ''
    return (f'<div class="im-band im-band-{kind}"{role}>{icon("alert", 18)}<div><strong>{escape(title)}</strong>'
            + (f'<ul>{lis}</ul>' if lis else '') + '</div></div>')


def locked(plan, feature, current):
    """Recurso bloqueado pelo plano (simulação). O link para a tela Planos vem logo abaixo, como st.page_link."""
    return (f'<div class="im-empty">{icon("lock", 26)}<div class="im-empty-title">Disponível no plano {escape(plan)}</div>'
            f'<p>{escape(feature)}. Plano atual (simulação): {escape(current)}.</p></div>')
