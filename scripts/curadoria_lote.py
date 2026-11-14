"""Ações em lote sobre um arquivo de data/curadoria.

  descartar-manuais    marca como "Descartado" os critérios de revisão humana (campo/operador 'manual'): ficam no arquivo,
                       mas o match não os usa. Reversível (edite o critério na tela do edital ou apague o descarte no JSON).
  validar-comparaveis  marca como VALIDADOS os critérios comparáveis (campo estruturado) que ainda estão pendentes.
                       Isso é o seu "conferi na fonte": só rode depois de conferir os trechos e a página de cada um.

Uso:  .venv/bin/python scripts/curadoria_lote.py 65-2025 descartar-manuais|validar-comparaveis
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inovamatch import curadoria  # noqa: E402
from inovamatch.domain import now_iso  # noqa: E402


def manual(c):
    return c.get('field') in (None, 'manual') or c.get('op') == 'manual'


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in ('descartar-manuais', 'validar-comparaveis'):
        sys.exit(__doc__)
    path = next((p for p, _ in curadoria.entries() if sys.argv[1] in p.name), None)
    if not path:
        sys.exit('Arquivo de curadoria não achado.')
    data = dict(next(d for p, d in curadoria.entries() if p == path))
    action, changed = sys.argv[2], 0
    for c in data['criteria']:
        if action == 'descartar-manuais' and manual(c) and c.get('validation_status') != 'rejected':
            c.update(validation_status='rejected', confirmed=False, review_status='Descartado: revisão humana, fora do match')
            changed += 1
        elif action == 'validar-comparaveis' and not manual(c) and c.get('validation_status') != 'rejected' and not c.get('confirmed'):
            if not (c.get('source') and c.get('evidence')):
                continue  # sem fonte e trecho não dá para validar
            c.update(confirmed=True, validation_status='validated', review_status='Validado em lote após conferência', reviewed_at=now_iso())
            changed += 1
    note = {'descartar-manuais': 'Critérios de revisão humana descartados do match (fora da comparação automática).',
            'validar-comparaveis': 'Critérios comparáveis validados em lote pelo Kalil, após conferência.'}[action]
    data['correcoes'] = list(data.get('correcoes', [])) + [f'{now_iso()[:10]}: {note} ({changed})']
    data['estado'] = curadoria.PENDING_STATE if curadoria.counts(data['criteria'])['missing'] else curadoria.DONE_STATE
    curadoria.write(path, data)
    print(path.name, action, changed, curadoria.counts(data['criteria']))


if __name__ == '__main__':
    main()
