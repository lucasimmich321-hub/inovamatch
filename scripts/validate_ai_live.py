"""Ensaio pago OPCIONAL. Sem --execute ou sem segredos não chama a API.

python scripts/validate_ai_live.py --execute --output work/validacao-ia-real.json
Não passe segredos em argumentos, arquivos de saída ou no chat.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inovamatch.ai_config import load_config, SessionAccess
from inovamatch.ai_engine import analyze_document, attach_analysis, AIError
from inovamatch.ai_ui import analysis_report
from inovamatch.documents import automatic_analysis
from inovamatch.radar import scan
from inovamatch.storage import Store


def run(execute):
    import streamlit as st
    config = load_config(secret_getter=lambda name: st.secrets.get(name))
    if not execute or not config.ready:
        return {'status': 'not_executed', 'api_called': False,
                'reason': 'É necessário --execute, OPENAI_API_KEY e INOVAMATCH_DEMO_PASSWORD com pelo menos 12 caracteres, configurados apenas no servidor.'}
    store = Store()
    scanned = scan(store)
    call = next((c for c in store.all('calls') if '66/2025' in c['title']), None)
    if not call:
        return {'status': 'not_executed', 'api_called': False, 'reason': 'O edital de referência não foi encontrado na consulta oficial.', 'scan': scanned}
    try:
        call = automatic_analysis(store, call)
        doc = next(d for d in call['documents'] if d['kind'] == 'Edital principal')
        access = SessionAccess()
        access.login(config.password, config)
        result = analyze_document(doc, [4,5,7], access, config)
        updated = attach_analysis(call, result)
        report = analysis_report(updated)
        report.update(status='executed', api_called=result['new_api_calls'] > 0, scan=scanned,
                      acceptance_scope='Citações e formato foram verificados; mapeamentos e obrigações ainda requerem conferência humana.')
        return report
    except AIError as exc:
        return {'status': 'not_completed', 'reason': str(exc), 'usage': access.usage if 'access' in locals() else []}
    except Exception:
        return {'status': 'not_completed', 'reason': 'A fonte, o PDF ou a configuração não permitiu concluir o ensaio. Nenhum detalhe de credencial é exibido.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', default='work/validacao-ia-real.json')
    args = parser.parse_args()
    report = run(args.execute)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'report': str(output), 'api_called': report.get('api_called')}, ensure_ascii=False))
    raise SystemExit(0 if report['status'] == 'executed' else 2)
