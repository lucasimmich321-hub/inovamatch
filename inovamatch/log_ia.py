"""Linhas curtas no terminal quando a IA é usada. Nunca recebe chave, senha nem texto do edital: só modelo, título e contagens."""
import sys


def log(message):
    print(f'[IA] {message}', file=sys.stderr, flush=True)


def title_of(call):
    title = (call.get('title') or 'sem título').strip()
    return title if len(title) <= 80 else title[:79] + '…'


def calling(model, call, block):
    log(f'chamando OpenAI (modelo {model}) para analisar o edital "{title_of(call)}" · {block}')


def finished(call, analysis):
    new, cached = analysis.get('new_api_calls', 0), analysis.get('cached_chunks', 0)
    if new:
        log(f'concluída: "{title_of(call)}" · {new} chamada(s) nova(s), {cached} bloco(s) do cache')
    else:
        log(f'concluída sem chamar a OpenAI: "{title_of(call)}" veio todo do cache ({cached} bloco(s))')


def failed(call, message):
    log(f'não concluída: "{title_of(call)}" · {message}')
