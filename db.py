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
                company_name TEXT,
                linkedin_url TEXT,
                updated_at INTEGER
            )
            ''')
            # Migration: Add company_name column if it doesn't exist
            self._migrate_add_company_name()
            # Migration: Add linkedin_url column if it doesn't exist
            self._migrate_add_linkedin_url()

    def _migrate_add_company_name(self):
        """Migration method to add company_name column to existing tables."""
        try:
            # Check if company_name column already exists
            cursor = self._conn.execute("PRAGMA table_info(profiles)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'company_name' not in columns:
                print("Migrating database: Adding company_name column...")
                self._conn.execute('ALTER TABLE profiles ADD COLUMN company_name TEXT')
                print("Migration completed successfully!")
            else:
                print("Database already up to date - company_name column exists.")
        except Exception as e:
            print(f"Migration error: {e}")

    def _migrate_add_linkedin_url(self):
        """Migration method to add linkedin_url column to existing tables."""
        try:
            # Check if linkedin_url column already exists
            cursor = self._conn.execute("PRAGMA table_info(profiles)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'linkedin_url' not in columns:
                print("Migrating database: Adding linkedin_url column...")
                self._conn.execute('ALTER TABLE profiles ADD COLUMN linkedin_url TEXT')
                print("Migration completed successfully!")
            else:
                print("Database already up to date - linkedin_url column exists.")
        except Exception as e:
            print(f"Migration error: {e}")

    def upsert_profile(self, user_id: str, name: str, role: str, description: str, keywords: str, company_name: str = None, linkedin_url: str = None):
        now = int(time.time())
        with self._conn:
            self._conn.execute('''
                INSERT INTO profiles (user_id, name, role, description, keywords, company_name, linkedin_url, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                  name=excluded.name,
                  role=excluded.role,
                  description=excluded.description,
                  keywords=excluded.keywords,
                  company_name=excluded.company_name,
                  linkedin_url=excluded.linkedin_url,
                  updated_at=excluded.updated_at
            ''', (user_id, name, role, description, keywords, company_name, linkedin_url, now))

    def get_profile(self, user_id: str) -> Optional[Dict]:
        cur = self._conn.execute('SELECT user_id, name, role, description, keywords, company_name, linkedin_url, updated_at FROM profiles WHERE user_id = ?', (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {k: row[k] for k in row.keys()}

    def search(self, keyword: str, limit: int = 20) -> List[Dict]:
        kw = f'%{keyword}%'
        sql = '''
        SELECT user_id, name, role, description, keywords, company_name, linkedin_url,
          (CASE WHEN lower(name) LIKE ? THEN 1 ELSE 0 END)
          + (CASE WHEN lower(role) LIKE ? THEN 1 ELSE 0 END)
          + (CASE WHEN lower(description) LIKE ? THEN 1 ELSE 0 END)
          + (CASE WHEN lower(keywords) LIKE ? THEN 1 ELSE 0 END)
          + (CASE WHEN lower(company_name) LIKE ? THEN 1 ELSE 0 END)
          + (CASE WHEN lower(linkedin_url) LIKE ? THEN 1 ELSE 0 END) AS score
        FROM profiles
        WHERE lower(name) LIKE ? OR lower(role) LIKE ? OR lower(description) LIKE ? 
        OR lower(keywords) LIKE ? OR lower(company_name) LIKE ? OR lower(linkedin_url) LIKE ?
        ORDER BY score DESC, updated_at DESC
        LIMIT ?
        '''
        cur = self._conn.execute(sql, (kw, kw, kw, kw, kw, kw, kw, kw, kw, kw, kw, kw, limit))
        rows = cur.fetchall()
        results = []
        for r in rows:
            # compute which keywords matched (simple intersection)
            matched = []
            klist = [k.strip() for k in (r['keywords'] or '').split(',') if k.strip()]
            search_fields = [
                (r['name'] or '').lower(),
                (r['role'] or '').lower(),
                (r['description'] or '').lower(),
                (r['company_name'] or '').lower(),
                (r['linkedin_url'] or '').lower()
            ]
            
            # Check which keywords and fields matched
            for k in klist:
                if keyword in k.lower():
                    matched.append(k)
            
            # Add field names that matched
            if keyword in (r['name'] or '').lower():
                matched.append('name')
            if keyword in (r['company_name'] or '').lower():
                matched.append('company')
            
            results.append({
                'user_id': r['user_id'],
                'name': r['name'],
                'role': r['role'],
                'description': r['description'],
                'keywords': r['keywords'],
                'company_name': r['company_name'],
                'linkedin_url': r['linkedin_url'],
                'matched_keywords': ', '.join(matched) if matched else 'profile match'
            })
        return results

    def search_roles(self, keyword: str, limit: int = 20) -> List[Dict]:
        """Search for profiles by role only."""
        kw = f'%{keyword}%'
        sql = '''
        SELECT user_id, name, role, description, keywords, company_name, linkedin_url
        FROM profiles
        WHERE lower(role) LIKE ?
        ORDER BY updated_at DESC
        LIMIT ?
        '''
        cur = self._conn.execute(sql, (kw, limit))
        rows = cur.fetchall()
        return [{
            'user_id': r['user_id'],
            'name': r['name'],
            'role': r['role'],
            'description': r['description'],
            'keywords': r['keywords'],
            'company_name': r['company_name'],
            'linkedin_url': r['linkedin_url']
        } for r in rows]

    def list_all_profiles(self) -> List[Dict]:
        """Get all profile names ordered by most recently updated."""
        cur = self._conn.execute('SELECT user_id, name FROM profiles ORDER BY updated_at DESC')
        rows = cur.fetchall()
        return [{'user_id': r['user_id'], 'name': r['name']} for r in rows]
