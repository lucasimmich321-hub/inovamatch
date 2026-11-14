"""Testes nunca leem o cache local do crawler (data/cache): a demonstração só vê editais que o próprio teste semear."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(autouse=True)
def _cache_vazio(tmp_path, monkeypatch):
    monkeypatch.setenv('INOVAMATCH_CACHE', str(tmp_path / 'cache-vazio'))


@pytest.fixture(autouse=True)
def _curadoria_isolada(tmp_path, monkeypatch):
    # Teste nunca lê nem grava data/curadoria (arquivos versionados com a revisão do Kalil).
    monkeypatch.setenv('INOVAMATCH_CURADORIA', str(tmp_path / 'curadoria'))
