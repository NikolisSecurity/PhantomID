import sqlite3
import json
import os
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib

class DatabaseManager:
    def __init__(self, db_path: str = 'phantomid.db'):
        self.db_path = db_path
        self.backup_dir = 'backups'
        self.logger = logging.getLogger(__name__)
        self.setup_database()
        
    def setup_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            change_type TEXT NOT NULL,
            original_value TEXT,
            new_value TEXT,
            category TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN DEFAULT TRUE,
            error_message TEXT,
            session_id TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            info_key TEXT NOT NULL,
            info_value TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_spoofs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_name TEXT NOT NULL,
            spoof_type TEXT NOT NULL,
            original_value TEXT,
            new_value TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN DEFAULT TRUE,
            anti_detection_level INTEGER DEFAULT 1
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS registry_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registry_path TEXT NOT NULL,
            key_name TEXT NOT NULL,
            original_value TEXT,
            new_value TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN DEFAULT TRUE
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS backup_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_name TEXT NOT NULL,
            backup_path TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            file_hash TEXT,
            size_bytes INTEGER
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            end_time DATETIME,
            total_changes INTEGER DEFAULT 0,
            successful_changes INTEGER DEFAULT 0,
            failed_changes INTEGER DEFAULT 0
        )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_type ON changes(change_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_timestamp ON changes(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_spoofs_game ON game_spoofs(game_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_registry_path ON registry_changes(registry_path)')
        
        conn.commit()
        conn.close()
        
    def create_backup(self) -> Optional[str]:
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f'phantomid_backup_{timestamp}.bak'
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            shutil.copy2(self.db_path, backup_path)
            
            with open(backup_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            file_size = os.path.getsize(backup_path)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO backup_metadata (backup_name, backup_path, file_hash, size_bytes) VALUES (?, ?, ?, ?)',
                (backup_name, backup_path, file_hash, file_size)
            )
            conn.commit()
            conn.close()
            
            self.logger.info(f'Database backup created: {backup_path}')
            return backup_path
            
        except Exception as e:
            self.logger.error(f'Failed to create backup: {e}')
            return None
    
    def restore_backup(self, backup_path: str) -> bool:
        try:
            if not os.path.exists(backup_path):
                self.logger.error(f'Backup file not found: {backup_path}')
                return False
            
            self.create_backup()
            
            shutil.copy2(backup_path, self.db_path)
            
            self.logger.info(f'Database restored from backup: {backup_path}')
            return True
            
        except Exception as e:
            self.logger.error(f'Failed to restore backup: {e}')
            return False

    def get_last_backup(self) -> Optional[Dict[str, Any]]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT backup_name, backup_path, created_at, file_hash, size_bytes
                FROM backup_metadata
                ORDER BY datetime(created_at) DESC
                LIMIT 1
            ''')
            row = cursor.fetchone()
            conn.close()
            if not row:
                return None
            return {
                'backup_name': row[0],
                'backup_path': row[1],
                'created_at': row[2],
                'file_hash': row[3],
                'size_bytes': row[4],
            }
        except Exception as e:
            self.logger.error(f'Failed to get last backup: {e}')
            return None

    def get_unclosed_sessions_count(self) -> int:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM sessions WHERE end_time IS NULL')
            count = cursor.fetchone()[0]
            conn.close()
            return int(count or 0)
        except Exception as e:
            self.logger.error(f'Failed to count unclosed sessions: {e}')
            return 0

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for key, value in settings.items():
                try:
                    stored = json.dumps(value)
                except Exception:
                    stored = json.dumps(str(value))
                cursor.execute('INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)', (key, stored))
            conn.commit()
            conn.close()
            self.logger.info('Settings saved successfully')
            return True
        except Exception as e:
            self.logger.error(f'Failed to save settings: {e}')
            return False

    def load_settings(self) -> Dict[str, Any]:
        settings: Dict[str, Any] = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM app_settings')
            for key, value_json in cursor.fetchall():
                try:
                    settings[key] = json.loads(value_json)
                except Exception:
                    settings[key] = value_json
            conn.close()
        except Exception as e:
            self.logger.error(f'Failed to load settings: {e}')
        return settings

    def get_setting(self, key: str, default: Any = None) -> Any:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM app_settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            conn.close()
            if row is None:
                return default
            try:
                return json.loads(row[0])
            except Exception:
                return row[0]
        except Exception as e:
            self.logger.error(f'Failed to get setting {key}: {e}')
            return default
    
    def start_session(self) -> str:
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sessions (session_id) VALUES (?)', (session_id,))
        conn.commit()
        conn.close()
        
        return session_id
    
    def end_session(self, session_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM changes WHERE session_id = ?', (session_id,))
        total_changes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM changes WHERE session_id = ? AND success = TRUE', (session_id,))
        successful_changes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM changes WHERE session_id = ? AND success = FALSE', (session_id,))
        failed_changes = cursor.fetchone()[0]
        
        cursor.execute('''
            UPDATE sessions 
            SET end_time = CURRENT_TIMESTAMP, 
                total_changes = ?, 
                successful_changes = ?, 
                failed_changes = ?
            WHERE session_id = ?
        ''', (total_changes, successful_changes, failed_changes, session_id))
        
        conn.commit()
        conn.close()
    
    def save_change(self, change_type: str, original_value: str, new_value: str, 
                   category: str = 'general', session_id: str = None, 
                   success: bool = True, error_message: str = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO changes (change_type, original_value, new_value, category, 
                               session_id, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (change_type, original_value, new_value, category, session_id, success, error_message))
        
        conn.commit()
        conn.close()
    
    def save_game_spoof(self, game_name: str, spoof_type: str, original_value: str, 
                       new_value: str, anti_detection_level: int = 1, success: bool = True):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO game_spoofs (game_name, spoof_type, original_value, 
                                   new_value, anti_detection_level, success)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (game_name, spoof_type, original_value, new_value, anti_detection_level, success))
        
        conn.commit()
        conn.close()
    
    def save_registry_change(self, registry_path: str, key_name: str, original_value: str, 
                           new_value: str, success: bool = True):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO registry_changes (registry_path, key_name, original_value, 
                                        new_value, success)
            VALUES (?, ?, ?, ?, ?)
        ''', (registry_path, key_name, original_value, new_value, success))
        
        conn.commit()
        conn.close()
    
    def get_changes_history(self, limit: int = 100) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT change_type, original_value, new_value, category, 
                   timestamp, success, error_message
            FROM changes 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        changes = []
        for row in cursor.fetchall():
            changes.append({
                'change_type': row[0],
                'original_value': row[1],
                'new_value': row[2],
                'category': row[3],
                'timestamp': row[4],
                'success': row[5],
                'error_message': row[6]
            })
        
        conn.close()
        return changes
    
    def get_game_spoofs(self, game_name: str = None) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if game_name:
            cursor.execute('''
                SELECT game_name, spoof_type, original_value, new_value, 
                       timestamp, success, anti_detection_level
                FROM game_spoofs 
                WHERE game_name = ? 
                ORDER BY timestamp DESC
            ''', (game_name,))
        else:
            cursor.execute('''
                SELECT game_name, spoof_type, original_value, new_value, 
                       timestamp, success, anti_detection_level
                FROM game_spoofs 
                ORDER BY timestamp DESC
            ''')
        
        spoofs = []
        for row in cursor.fetchall():
            spoofs.append({
                'game_name': row[0],
                'spoof_type': row[1],
                'original_value': row[2],
                'new_value': row[3],
                'timestamp': row[4],
                'success': row[5],
                'anti_detection_level': row[6]
            })
        
        conn.close()
        return spoofs
    
    def get_original_values(self) -> Dict[str, str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT change_type, original_value 
            FROM changes 
            WHERE success = TRUE
            ORDER BY timestamp DESC
        ''')
        
        original_values = {}
        for row in cursor.fetchall():
            if row[0] not in original_values:
                original_values[row[0]] = row[1]
        
        conn.close()
        return original_values
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM changes 
            WHERE timestamp < datetime('now', '-' || ? || ' days')
        ''', (days_to_keep,))
        
        cursor.execute('''
            DELETE FROM game_spoofs 
            WHERE timestamp < datetime('now', '-' || ? || ' days')
        ''', (days_to_keep,))
        
        cursor.execute('''
            DELETE FROM registry_changes 
            WHERE timestamp < datetime('now', '-' || ? || ' days')
        ''', (days_to_keep,))
        
        cursor.execute('VACUUM')
        
        conn.commit()
        conn.close()
        
        self.logger.info(f'Database cleanup completed, kept data from last {days_to_keep} days')
    
    def get_statistics(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute('SELECT COUNT(*) FROM changes')
        stats['total_changes'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM changes WHERE success = TRUE')
        stats['successful_changes'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM changes WHERE success = FALSE')
        stats['failed_changes'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM game_spoofs')
        stats['total_game_spoofs'] = cursor.fetchone()[0]
        stats['games_spoofed'] = stats['total_game_spoofs']
        
        cursor.execute('SELECT COUNT(*) FROM registry_changes')
        stats['total_registry_changes'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM changes WHERE change_type LIKE '%cleanup%' OR change_type LIKE '%clear%'")
        stats['system_cleanups'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()')
        stats['database_size_bytes'] = cursor.fetchone()[0]
        
        conn.close()
        return stats