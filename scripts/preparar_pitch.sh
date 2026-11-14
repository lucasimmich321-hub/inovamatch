#!/usr/bin/env bash
# Prepara e abre o app para o pitch: empresas fictícias + critérios curados do 65/2025, tudo em SQLite local.
# Seguro de repetir: o seed só regrava as empresas; validações feitas por você ficam no .db e em data/curadoria.
# Sem rede e sem IA (lê só o cache local do crawler). O .db fica fora do git.
set -euo pipefail
cd "$(dirname "$0")/.."
export INOVAMATCH_STORAGE=sqlite
export INOVAMATCH_DB="${INOVAMATCH_DB:-data/teste_match.db}"
.venv/bin/python scripts/seed_match_test.py "$INOVAMATCH_DB"
exec .venv/bin/streamlit run app.py --server.port "${PORT:-8502}"
