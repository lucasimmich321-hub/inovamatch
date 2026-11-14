"""O mesmo repositório em memória de sessão ou SQLite local, sem servidor extra."""
import copy
import json
import sqlite3
import uuid
from pathlib import Path
from .domain import now_iso, validate_project, validate_startup
from .origin import origem

COLLECTIONS = ('startups', 'projects', 'calls', 'analyses', 'tasks', 'scans', 'applications', 'documents')


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
        r['origem'] = origem(r)
        r['updated_at'] = now_iso()
        if self.path:
            with self._connect() as conn:
                conn.execute('INSERT INTO records(kind,id,payload) VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload',
                             (kind, r['id'], json.dumps(r, ensure_ascii=False)))
        else:
            self.data[kind][r['id']] = r
        return r

    def delete(self, kind, record_id):
        self._kind(kind)
        if self.path:
            with self._connect() as conn:
                conn.execute('DELETE FROM records WHERE kind=? AND id=?', (kind, str(record_id)))
        else:
            self.data[kind].pop(str(record_id), None)

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
        if call.get('pages'):
            from .versioning import register  # primeira versão (hash do arquivo e do texto) já no cadastro
            call = register(call, call.get('url') or call.get('source_label') or 'Documento sem URL',
                            call.get('document_sha256') or '', call['pages'])
        return self.save('calls', {**call, 'dedup_key': key}), True


class ScopedStore(Store):
    """Visão de UMA startup sobre a mesma base (perfis abaixo do Institucional). Editais e coletas continuam todos;
    startups, projetos, documentos, matches, tarefas e análises ficam só os dessa startup. Gravações vão para a base comum."""

    def __init__(self, base, startup_id):
        super().__init__(base.data, base.path)
        self.startup_id = startup_id

    def all(self, kind):
        rows = super().all(kind)
        if kind in ('calls', 'scans'):
            return rows
        if kind == 'startups':
            return [r for r in rows if r['id'] == self.startup_id]
        if kind in ('projects', 'documents'):
            return [r for r in rows if r.get('startup_id') == self.startup_id]
        projects = {p['id'] for p in super().all('projects') if p.get('startup_id') == self.startup_id}
        if kind == 'applications':
            return [r for r in rows if r.get('project_id') in projects]
        apps = {a['id'] for a in super().all('applications') if a.get('project_id') in projects}

        def mine(r):
            if r.get('startup_id'):
                return r['startup_id'] == self.startup_id
            if r.get('project_id'):
                return r['project_id'] in projects
            if r.get('application_id'):
                return r['application_id'] in apps
            return True  # registro sem dono (não ligado a startup)
        return [r for r in rows if mine(r)]
