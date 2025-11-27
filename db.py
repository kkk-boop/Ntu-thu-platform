import sqlite3
import time
from typing import Optional, List, Dict

class Database:
    def __init__(self, path: str = 'profiles.db'):
        self._path = path
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_table()

    def _ensure_table(self):
        with self._conn:
            self._conn.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                role TEXT,
                description TEXT,
                keywords TEXT,
                updated_at INTEGER
            )
            ''')

    def upsert_profile(self, user_id: str, name: str, role: str, description: str, keywords: str):
        now = int(time.time())
        with self._conn:
            self._conn.execute('''
                INSERT INTO profiles (user_id, name, role, description, keywords, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                  name=excluded.name,
                  role=excluded.role,
                  description=excluded.description,
                  keywords=excluded.keywords,
                  updated_at=excluded.updated_at
            ''', (user_id, name, role, description, keywords, now))

    def get_profile(self, user_id: str) -> Optional[Dict]:
        cur = self._conn.execute('SELECT user_id, name, role, description, keywords, updated_at FROM profiles WHERE user_id = ?', (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {k: row[k] for k in row.keys()}

    def search(self, keyword: str, limit: int = 20) -> List[Dict]:
        kw = f'%{keyword}%'
        sql = '''
        SELECT user_id, name, role, description, keywords,
          (CASE WHEN lower(role) LIKE ? THEN 1 ELSE 0 END)
          + (CASE WHEN lower(description) LIKE ? THEN 1 ELSE 0 END)
          + (CASE WHEN lower(keywords) LIKE ? THEN 1 ELSE 0 END) AS score
        FROM profiles
        WHERE lower(role) LIKE ? OR lower(description) LIKE ? OR lower(keywords) LIKE ?
        ORDER BY score DESC, updated_at DESC
        LIMIT ?
        '''
        cur = self._conn.execute(sql, (kw, kw, kw, kw, kw, kw, limit))
        rows = cur.fetchall()
        results = []
        for r in rows:
            # compute which keywords matched (simple intersection)
            matched = []
            klist = [k.strip() for k in (r['keywords'] or '').split(',') if k.strip()]
            for k in klist:
                if keyword in k.lower() or keyword in (r['role'] or '').lower() or keyword in (r['description'] or '').lower():
                    matched.append(k)
            results.append({
                'user_id': r['user_id'],
                'name': r['name'],
                'role': r['role'],
                'description': r['description'],
                'keywords': r['keywords'],
                'matched_keywords': ', '.join(matched)
            })
        return results
