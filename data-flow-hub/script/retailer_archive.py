"""Archive state is separate from setup; keys, store codes and history survive."""
from datetime import datetime,timezone
from flask import request,jsonify
from database import get_db_connection
def archive_state(db,rid):
    row=db.execute('SELECT archived,changed_at FROM retailer_archive WHERE retailer_id=?',(rid,)).fetchone()
    return {'archived':bool(row['archived']) if row else False,'archiveChangedAt':row['changed_at'] if row else None}
def register_archive_routes(app,error):
    with get_db_connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS retailer_archive(retailer_id TEXT PRIMARY KEY,archived INTEGER NOT NULL,changed_at TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS retailer_archive_events(id INTEGER PRIMARY KEY AUTOINCREMENT,retailer_id TEXT NOT NULL,action TEXT NOT NULL,changed_at TEXT NOT NULL)')
    @app.route('/api/v1/retailers/archive',methods=['POST'])
    @app.route('/api/v1/retailers/restore',methods=['POST'])
    def archive_retailers():
        body=request.get_json(silent=True);ids=body.get('ids') if isinstance(body,dict) else None
        if not isinstance(ids,list) or not ids or len(ids)>1000 or any(not isinstance(rid,str) or not rid for rid in ids):return error('Select one or more retailers.')
        ids=list(dict.fromkeys(ids));marks=','.join('?' for _ in ids);archived=request.path.endswith('/archive')
        with get_db_connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute(f'SELECT COUNT(*) FROM retailer_configs WHERE id IN ({marks})',ids).fetchone()[0]!=len(ids):return error('A selected retailer no longer exists.',404)
            if archived and db.execute(f'SELECT id FROM batch_attempts WHERE retailer_id IN ({marks}) LIMIT 1',ids).fetchone():return error('Wait for or cancel running jobs before archiving.',409)
            changed=[];stamp=datetime.now(timezone.utc).isoformat()
            for rid in ids:
                if archive_state(db,rid)['archived']==archived:continue
                db.execute('INSERT INTO retailer_archive VALUES(?,?,?) ON CONFLICT(retailer_id) DO UPDATE SET archived=excluded.archived,changed_at=excluded.changed_at',(rid,int(archived),stamp))
                db.execute('INSERT INTO retailer_archive_events(retailer_id,action,changed_at) VALUES(?,?,?)',(rid,'Archived' if archived else 'Restored',stamp));changed.append(rid)
        return jsonify(success=True,changedIds=changed,archived=archived)
    @app.route('/api/v1/retailers/<rid>/archive-history')
    def archive_history(rid):
        with get_db_connection() as db:events=[dict(row) for row in db.execute('SELECT action,changed_at FROM retailer_archive_events WHERE retailer_id=? ORDER BY id DESC',(rid,))]
        return jsonify(success=True,events=events)
