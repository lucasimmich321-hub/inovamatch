"""O mesmo repositório em memória de sessão ou SQLite local, sem servidor extra."""
import copy
import json
import sqlite3
import uuid
from pathlib import Path
from .domain import now_iso, validate_project, validate_startup

COLLECTIONS = ('startups', 'projects', 'calls', 'analyses', 'tasks', 'scans', 'applications')


class Store:
    def __init__(self, data=None, path=None):
        self.data = data if data is not None else {}
        self.path = str(path) if path else None
        for collection in COLLECTIONS:
            self.data.setdefault(collection, {})
        if self.path:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.execute('CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, payload TEXT NOT NULL, PRIMARY KEY(kind,id))')

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def all(self, kind):
        self._kind(kind)
        if not self.path:
            return copy.deepcopy(list(self.data[kind].values()))
        with self._connect() as conn:
            return [json.loads(row[0]) for row in conn.execute('SELECT payload FROM records WHERE kind=? ORDER BY rowid', (kind,))]

    def get(self, kind, record_id):
        return next((r for r in self.all(kind) if r['id'] == record_id), None)

    def save(self, kind, record):
        self._kind(kind)
        r = copy.deepcopy(record)
        if kind == 'startups':
            r = validate_startup(r)
        if kind == 'projects':
            r = validate_project(r, {s['id'] for s in self.all('startups')})
        r['id'] = str(r.get('id') or uuid.uuid4().hex)
        r['updated_at'] = now_iso()
        if self.path:
            with self._connect() as conn:
                conn.execute('INSERT INTO records(kind,id,payload) VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload',
                             (kind, r['id'], json.dumps(r, ensure_ascii=False)))
        else:
            self.data[kind][r['id']] = r
        return r

    @staticmethod
    def _kind(kind):
        if kind not in COLLECTIONS:
            raise ValueError('Coleção desconhecida.')

    def export(self):
        return json.dumps({'schema_version': 1, 'exported_at': now_iso(),
                           **{k: self.all(k) for k in COLLECTIONS}}, ensure_ascii=False, indent=2)

    def upsert_call(self, call):
        from .radar import canonical_url
        key = call.get('dedup_key') or canonical_url(call.get('url', ''))
        existing = next((c for c in self.all('calls') if c.get('dedup_key') == key), None) if key else None
        if existing:
            # Uma nova coleta nunca sobrescreve a revisão humana.
            existing['last_seen_at'] = now_iso()
            return self.save('calls', existing), False
        return self.save('calls', {**call, 'dedup_key': key}), True
