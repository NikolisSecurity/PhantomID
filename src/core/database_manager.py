import os
import json
import sqlite3
import shutil
import logging
import uuid
import typing
import ctypes
try:
    import winreg  # Windows registry access
except Exception:  # pragma: no cover
    winreg = None
from datetime import datetime, timedelta
from pathlib import Path


class DatabaseManager:
    def __init__(self, db_path: str | None = None):
        self.logger = logging.getLogger(__name__)
        base_dir = Path(__file__).resolve().parents[2]
        self.base_dir = base_dir
        self.db_path = Path(db_path) if db_path else base_dir / 'phantomid.db'
        self.conn = sqlite3.connect(self.db_path.as_posix(), check_same_thread=False)
        self.conn.execute('PRAGMA foreign_keys = ON')
        self.setup_database()

    # ---------- Schema ----------
    def setup_database(self) -> None:
        cur = self.conn.cursor()

        # Core tables
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS changes (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                   category TEXT,
                   item TEXT,
                   original_value TEXT,
                   new_value TEXT,
                   success INTEGER DEFAULT 1,
                   error_message TEXT DEFAULT '',
                   session_id TEXT
               )'''
        )

        cur.execute(
            '''CREATE TABLE IF NOT EXISTS game_spoofs (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                   game TEXT,
                   spoof_type TEXT,
                   original_value TEXT,
                   new_value TEXT,
                   success INTEGER DEFAULT 1,
                   anti_detection_level INTEGER DEFAULT 0,
                   session_id TEXT
               )'''
        )

        # Keep legacy name and user-requested names
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS registry_changes (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                   key_path TEXT,
                   value_name TEXT,
                   original_value TEXT,
                   new_value TEXT,
                   success INTEGER DEFAULT 1,
                   session_id TEXT
               )'''
        )

        # Baseline snapshot of registry values
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS registry (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                   key_path TEXT,
                   value_name TEXT,
                   value TEXT,
                   session_id TEXT
               )'''
        )

        # Spoofed registry changes (requested table name)
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS registry_spoof (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                   key_path TEXT,
                   value_name TEXT,
                   original_value TEXT,
                   spoofed_value TEXT,
                   success INTEGER DEFAULT 1,
                   session_id TEXT
               )'''
        )

        # Settings and sessions
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS app_settings (
                   key TEXT PRIMARY KEY,
                   value TEXT NOT NULL
               )'''
        )
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS sessions (
                   id TEXT PRIMARY KEY,
                   started_at TEXT,
                   ended_at TEXT
               )'''
        )

        # Backup metadata
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS backup_metadata (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   created_at TEXT NOT NULL,
                   file_path TEXT NOT NULL,
                   size_bytes INTEGER NOT NULL,
                   included_tables TEXT NOT NULL
               )'''
        )

        # System info snapshots (store JSON)
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS system_info (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   collected_at TEXT NOT NULL,
                   info_json TEXT NOT NULL
               )'''
        )

        self.conn.commit()

        # ---------- Lightweight migrations ----------
        def _ensure_columns(table: str, required_cols: list[tuple[str, str]]):
            try:
                cur.execute(f"PRAGMA table_info({table})")
                existing = {row[1] for row in cur.fetchall()}  # second field is name
                for col_name, col_type in required_cols:
                    if col_name not in existing:
                        try:
                            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                        except Exception as e:
                            self.logger.warning(f"Migration: failed to add column {col_name} to {table}: {e}")
                self.conn.commit()
            except Exception as e:
                self.logger.warning(f"Migration: failed PRAGMA for {table}: {e}")

        _ensure_columns('changes', [
            ('success', 'INTEGER DEFAULT 1'),
            ('error_message', "TEXT DEFAULT ''"),
            ('session_id', 'TEXT')
        ])
        _ensure_columns('game_spoofs', [
            ('success', 'INTEGER DEFAULT 1'),
            ('anti_detection_level', 'INTEGER DEFAULT 0'),
            ('session_id', 'TEXT')
        ])
        _ensure_columns('registry_changes', [
            ('success', 'INTEGER DEFAULT 1'),
            ('session_id', 'TEXT')
        ])

        # Ensure backup_metadata has required columns and map legacy names
        try:
            cur.execute("PRAGMA table_info(backup_metadata)")
            bm_cols = {row[1] for row in cur.fetchall()}  # column names
            if 'file_path' not in bm_cols:
                cur.execute('ALTER TABLE backup_metadata ADD COLUMN file_path TEXT')
            if 'size_bytes' not in bm_cols:
                cur.execute('ALTER TABLE backup_metadata ADD COLUMN size_bytes INTEGER')
            if 'included_tables' not in bm_cols:
                cur.execute('ALTER TABLE backup_metadata ADD COLUMN included_tables TEXT')
            # Map legacy backup_path -> file_path if present
            cur.execute("PRAGMA table_info(backup_metadata)")
            bm_cols2 = {row[1] for row in cur.fetchall()}
            if 'backup_path' in bm_cols2 and 'file_path' in bm_cols2:
                try:
                    cur.execute("UPDATE backup_metadata SET file_path = COALESCE(file_path, backup_path)")
                except Exception:
                    pass
            self.conn.commit()
        except Exception as e:
            self.logger.warning(f"Migration: backup_metadata columns ensure failed: {e}")

        # Sessions table compatibility: rebuild if schema is missing required columns
        try:
            cur.execute("PRAGMA table_info(sessions)")
            cols = [row[1] for row in cur.fetchall()]
            required = {'id', 'started_at', 'ended_at'}
            if not set(cols) >= required:
                cur.execute("ALTER TABLE sessions RENAME TO sessions_old")
                cur.execute(
                    '''CREATE TABLE IF NOT EXISTS sessions (
                           id TEXT PRIMARY KEY,
                           started_at TEXT,
                           ended_at TEXT
                       )'''
                )
                # Migrate any available data
                try:
                    cur.execute("PRAGMA table_info(sessions_old)")
                    old_info = cur.fetchall()
                    old_cols = [row[1] for row in old_info]
                    col_idx = {name: i for i, name in enumerate(old_cols)}
                    cur.execute(f"SELECT {', '.join(old_cols)} FROM sessions_old")
                    rows = cur.fetchall()
                    for r in rows:
                        sid = None
                        if 'id' in col_idx:
                            sid = r[col_idx['id']]
                        elif 'session_id' in col_idx:
                            sid = r[col_idx['session_id']]
                        else:
                            sid = uuid.uuid4().hex
                        started_at = r[col_idx['started_at']] if 'started_at' in col_idx else None
                        ended_at = r[col_idx['ended_at']] if 'ended_at' in col_idx else None
                        cur.execute(
                            'INSERT OR IGNORE INTO sessions (id, started_at, ended_at) VALUES (?, ?, ?)',
                            (sid, started_at, ended_at)
                        )
                    cur.execute('DROP TABLE sessions_old')
                except Exception:
                    try:
                        cur.execute('DROP TABLE sessions_old')
                    except Exception:
                        pass
                self.conn.commit()
        except Exception as e:
            self.logger.warning(f"Migration: sessions table rebuild failed: {e}")

        self.conn.commit()

    # ---------- Backup and Restore ----------
    def create_backup(self, verify: bool = False, progress_cb: typing.Callable[[int], None] | None = None) -> str | None:
        try:
            backups_dir = self.base_dir / 'backups'
            backups_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = backups_dir / f'phantomid_backup_{ts}.bak'

            # Use SQLite's backup API with a dedicated read-only snapshot connection
            b_conn = sqlite3.connect(backup_path.as_posix())
            try:
                # Incremental backup with progress reporting if callback provided
                def _progress(remaining: int, total: int):
                    if progress_cb:
                        try:
                            pct = 0
                            if total > 0:
                                pct = int(max(0, min(100, round(100 - (remaining / total) * 100))))
                            progress_cb(pct)
                        except Exception:
                            pass
                # Open a separate read connection with a short busy timeout to avoid hangs
                read_conn = sqlite3.connect(self.db_path.as_posix(), check_same_thread=False, timeout=2)
                try:
                    read_conn.execute('PRAGMA busy_timeout=2000')
                    # Start a read transaction to get a consistent snapshot
                    try:
                        read_conn.execute('BEGIN')
                    except Exception:
                        pass
                    try:
                        # Use reasonable page chunk to get periodic callbacks
                        read_conn.backup(b_conn, pages=1000, progress=_progress)
                    except TypeError:
                        # Older Python without progress support: fall back to one-shot
                        read_conn.backup(b_conn)
                        if progress_cb:
                            progress_cb(100)
                except sqlite3.OperationalError as e:
                    # Fallback: use iterdump if backup API hits busy conditions
                    if progress_cb:
                        try:
                            progress_cb(1)
                        except Exception:
                            pass
                    dump_lines = []
                    try:
                        for i, line in enumerate(read_conn.iterdump()):
                            dump_lines.append(line)
                            if progress_cb and (i % 1000 == 0):
                                # Approximate progress during dump
                                try:
                                    progress_cb(min(90, 10 + (i // 1000)))
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    try:
                        b_conn.executescript('\n'.join(dump_lines))
                    except Exception:
                        raise
                finally:
                    try:
                        read_conn.close()
                    except Exception:
                        pass
                try:
                    self.conn.commit()
                except Exception:
                    pass
            finally:
                try:
                    b_conn.commit()
                except Exception:
                    pass
                b_conn.close()

            # Collect included tables; optionally verify row counts for deep validation
            table_names: list[str] = []
            table_counts: dict[str, int] | None = None
            if verify:
                verify_conn = sqlite3.connect(backup_path.as_posix())
                table_counts = {}
                try:
                    curv = verify_conn.cursor()
                    curv.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    table_names = [row[0] for row in curv.fetchall()]
                    for t in table_names:
                        try:
                            curv.execute(f'SELECT COUNT(*) FROM {t}')
                            table_counts[t] = int(curv.fetchone()[0])
                        except Exception:
                            table_counts[t] = -1
                finally:
                    verify_conn.close()
            else:
                # Quick path: read table names without counting rows
                quick_conn = sqlite3.connect(backup_path.as_posix())
                try:
                    curq = quick_conn.cursor()
                    curq.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    table_names = [row[0] for row in curq.fetchall()]
                finally:
                    quick_conn.close()

            # Record metadata (supports legacy schemas)
            cur = self.conn.cursor()
            cur.execute("PRAGMA table_info(backup_metadata)")
            bm_info = cur.fetchall()
            bm_cols = {row[1]: {'notnull': row[3], 'type': row[2]} for row in bm_info}
            included_payload = (
                json.dumps({'names': table_names, 'row_counts': table_counts})
                if verify else
                json.dumps({'names': table_names})
            )
            values = {
                'created_at': datetime.now().isoformat(timespec='seconds'),
                'file_path': backup_path.as_posix(),
                'size_bytes': backup_path.stat().st_size,
                'included_tables': included_payload,
            }
            if 'backup_name' in bm_cols:
                values['backup_name'] = backup_path.name
            if 'backup_path' in bm_cols:
                values['backup_path'] = backup_path.as_posix()
            insert_cols = [c for c in ['created_at','file_path','size_bytes','included_tables','backup_name','backup_path'] if c in bm_cols]
            placeholders = ', '.join(['?'] * len(insert_cols))
            cur.execute(
                f"INSERT INTO backup_metadata ({', '.join(insert_cols)}) VALUES ({placeholders})",
                [values[c] for c in insert_cols]
            )
            self.conn.commit()
            if progress_cb:
                try:
                    progress_cb(100)
                except Exception:
                    pass
            self.logger.info(
                f"Backup created: {backup_path}"
                + (f" row counts: {table_counts}" if verify else " (fast mode)")
            )
            return backup_path.as_posix()
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            return None

    def restore_backup(self, backup_file_path: str) -> bool:
        try:
            src = Path(backup_file_path)
            if not src.exists():
                self.logger.error(f"Backup file not found: {backup_file_path}")
                return False
            # Close existing connection before overwriting
            try:
                self.conn.close()
            except Exception:
                pass
            shutil.copy2(src.as_posix(), self.db_path.as_posix())
            # Reopen connection and ensure schema/migrations applied
            self.conn = sqlite3.connect(self.db_path.as_posix(), check_same_thread=False)
            self.conn.execute('PRAGMA foreign_keys = ON')
            self.setup_database()
            self.logger.info("Backup restored and schema verified")
            return True
        except Exception as e:
            self.logger.error(f"Backup restore failed: {e}")
            return False

    # ---------- CRUD helpers ----------
    # Sessions
    def start_session(self) -> str:
        try:
            session_id = uuid.uuid4().hex
            self.conn.execute(
                'INSERT INTO sessions (id, started_at, ended_at) VALUES (?, ?, ?)',
                (session_id, datetime.now().isoformat(timespec='seconds'), None)
            )
            self.conn.commit()
            return session_id
        except Exception as e:
            self.logger.warning(f"start_session failed: {e}")
            # Fallback to deterministic value
            return uuid.uuid4().hex

    def end_session(self, session_id: str) -> None:
        try:
            self.conn.execute(
                'UPDATE sessions SET ended_at=? WHERE id=? AND (ended_at IS NULL OR ended_at="")',
                (datetime.now().isoformat(timespec='seconds'), session_id)
            )
            self.conn.commit()
        except Exception as e:
            self.logger.warning(f"end_session failed: {e}")

    def get_unclosed_sessions_count(self) -> int:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sessions WHERE ended_at IS NULL OR ended_at='' ")
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0
        except Exception as e:
            self.logger.warning(f"get_unclosed_sessions_count failed: {e}")
            return 0

    def get_last_backup(self) -> dict | None:
        try:
            cur = self.conn.cursor()
            query = 'SELECT created_at, file_path, size_bytes, included_tables FROM backup_metadata ORDER BY created_at DESC LIMIT 1'
            try:
                cur.execute(query)
            except Exception:
                # Fallback to legacy column name
                cur.execute('SELECT created_at, backup_path, size_bytes, included_tables FROM backup_metadata ORDER BY created_at DESC LIMIT 1')
            row = cur.fetchone()
            if not row:
                return None
            try:
                tables = json.loads(row[3]) if row[3] else []
            except Exception:
                tables = []
            return {
                'created_at': row[0],
                'backup_path': row[1],
                'size_bytes': int(row[2] or 0),
                'included_tables': tables,
            }
        except Exception as e:
            self.logger.warning(f"get_last_backup failed: {e}")
            return None

    def save_change(self, item: str, original_value: str, new_value: str,
                    category: str = 'system', success: bool = True,
                    error_message: str | None = None, session_id: str | None = None) -> None:
        try:
            self.conn.execute(
                'INSERT INTO changes (timestamp, category, item, original_value, new_value, success, error_message, session_id) '
                'VALUES (datetime(\'now\'), ?, ?, ?, ?, ?, ?, ?)',
                (category, item, original_value, new_value, 1 if success else 0, error_message or '', session_id)
            )
            self.conn.commit()
        except Exception as e:
            self.logger.warning(f"save_change failed: {e}")

    def save_game_spoof(self, game: str, spoof_type: str, original_value: str, new_value: str,
                         success: bool = True, anti_detection_level: int = 0, session_id: str | None = None) -> None:
        try:
            self.conn.execute(
                'INSERT INTO game_spoofs (timestamp, game, spoof_type, original_value, new_value, success, anti_detection_level, session_id) '
                'VALUES (datetime(\'now\'), ?, ?, ?, ?, ?, ?, ?)',
                (game, spoof_type, original_value, new_value, 1 if success else 0, anti_detection_level, session_id)
            )
            self.conn.commit()
        except Exception as e:
            self.logger.warning(f"save_game_spoof failed: {e}")

    def save_registry_change(self, key_path: str, value_name: str, original_value: str, new_value: str,
                             success: bool = True, session_id: str | None = None) -> None:
        try:
            # Legacy/primary table
            self.conn.execute(
                'INSERT INTO registry_changes (timestamp, key_path, value_name, original_value, new_value, success, session_id) '
                'VALUES (datetime(\'now\'), ?, ?, ?, ?, ?, ?)',
                (key_path, value_name, original_value, new_value, 1 if success else 0, session_id)
            )
            # Requested table name mirror
            self.conn.execute(
                'INSERT INTO registry_spoof (timestamp, key_path, value_name, original_value, spoofed_value, success, session_id) '
                'VALUES (datetime(\'now\'), ?, ?, ?, ?, ?, ?)',
                (key_path, value_name, original_value, new_value, 1 if success else 0, session_id)
            )
            self.conn.commit()
        except Exception as e:
            self.logger.warning(f"save_registry_change failed: {e}")

    def save_registry_snapshot(self, key_path: str, value_name: str, value: str, session_id: str | None = None) -> None:
        try:
            self.conn.execute(
                'INSERT INTO registry (timestamp, key_path, value_name, value, session_id) '
                'VALUES (datetime(\'now\'), ?, ?, ?, ?)',
                (key_path, value_name, value, session_id)
            )
            self.conn.commit()
        except Exception as e:
            self.logger.warning(f"save_registry_snapshot failed: {e}")

    def save_system_info(self, info: dict) -> None:
        try:
            # Detect schema: JSON row or key-value rows
            cur = self.conn.cursor()
            cur.execute("PRAGMA table_info(system_info)")
            cols = [row[1] for row in cur.fetchall()]
            if 'info_json' in cols and 'collected_at' in cols:
                self.conn.execute(
                    'INSERT INTO system_info (collected_at, info_json) VALUES (?, ?)',
                    (datetime.now().isoformat(timespec='seconds'), json.dumps(info))
                )
            elif {'category', 'info_key', 'info_value', 'timestamp'}.issubset(set(cols)):
                # Flatten structure into key-value rows
                def _emit(category: str, key: str, value: typing.Any):
                    try:
                        self.conn.execute(
                            'INSERT INTO system_info (category, info_key, info_value, timestamp) '
                            'VALUES (?, ?, ?, datetime("now"))',
                            (category, key, json.dumps(value))
                        )
                    except Exception:
                        pass
                for category, data in (info or {}).items():
                    if isinstance(data, dict):
                        for k, v in data.items():
                            _emit(str(category), str(k), v)
                    elif isinstance(data, list):
                        for idx, item in enumerate(data):
                            _emit(str(category), str(idx), item)
                    else:
                        _emit(str(category), 'value', data)
            else:
                # Unknown schema: store a minimal JSON-like row if possible
                try:
                    self.conn.execute(
                        'INSERT INTO system_info (timestamp, info_value) VALUES (datetime("now"), ?)',
                        (json.dumps(info),)
                    )
                except Exception:
                    pass
            self.conn.commit()
        except Exception as e:
            self.logger.warning(f"save_system_info failed: {e}")

    def prepare_prebackup_snapshot(self) -> None:
        """
        Capture a lightweight system/registry snapshot so backups include meaningful data
        even if the user hasn't opened the serials page.

        This collects a minimal set of identifiers via WMI and registry and stores them
        using save_system_info and save_registry_snapshot. All failures are logged but
        do not raise.
        """
        try:
            info: dict = {
                "BIOS": {},
                "Baseboard": {},
                "ComputerSystem": {},
                "CPU": {},
                "OS": {},
                "UUID": {},
                "Volumes": {},
            }
            # --- WMI-based collection ---
            try:
                import wmi  # lazily import; available per requirements
                w = wmi.WMI()
                try:
                    bios = w.Win32_BIOS()
                    if bios:
                        b = bios[0]
                        info["BIOS"]["SerialNumber"] = str(getattr(b, 'SerialNumber', '') or '')
                        info["BIOS"]["Version"] = str(getattr(b, 'Version', '') or '')
                except Exception:
                    pass
                try:
                    bb = w.Win32_BaseBoard()
                    if bb:
                        b = bb[0]
                        info["Baseboard"]["SerialNumber"] = str(getattr(b, 'SerialNumber', '') or '')
                        info["Baseboard"]["Product"] = str(getattr(b, 'Product', '') or '')
                except Exception:
                    pass
                try:
                    cs = w.Win32_ComputerSystem()
                    if cs:
                        c = cs[0]
                        info["ComputerSystem"]["Manufacturer"] = str(getattr(c, 'Manufacturer', '') or '')
                        info["ComputerSystem"]["Model"] = str(getattr(c, 'Model', '') or '')
                except Exception:
                    pass
                try:
                    cpu = w.Win32_Processor()
                    if cpu:
                        p = cpu[0]
                        info["CPU"]["ProcessorId"] = str(getattr(p, 'ProcessorId', '') or '')
                except Exception:
                    pass
                try:
                    os_list = w.Win32_OperatingSystem()
                    if os_list:
                        o = os_list[0]
                        info["OS"]["SerialNumber"] = str(getattr(o, 'SerialNumber', '') or '')
                        info["OS"]["Version"] = str(getattr(o, 'Version', '') or '')
                        info["OS"]["BuildNumber"] = str(getattr(o, 'BuildNumber', '') or '')
                except Exception:
                    pass
            except Exception:
                pass

            # --- Volume serial for C: ---
            try:
                vol_name = ctypes.create_unicode_buffer(1024)
                fs_name = ctypes.create_unicode_buffer(1024)
                serial = ctypes.c_uint()
                max_comp_len = ctypes.c_uint()
                flags = ctypes.c_uint()
                GetVolumeInformationW = ctypes.windll.kernel32.GetVolumeInformationW
                r = GetVolumeInformationW(ctypes.c_wchar_p("C:\\"), vol_name, 1024,
                                          ctypes.byref(serial), ctypes.byref(max_comp_len), ctypes.byref(flags), fs_name, 1024)
                if r:
                    info["Volumes"]["C"] = {
                        "SerialNumber": int(serial.value),
                        "VolumeName": vol_name.value,
                        "FileSystem": fs_name.value,
                    }
            except Exception:
                pass

            # Save the system info snapshot
            try:
                self.save_system_info(info)
            except Exception:
                pass

            # --- Registry keys snapshot ---
            def _read_reg(root, path: str, name: str) -> str:
                if winreg is None:
                    return ''
                try:
                    key = winreg.OpenKey(root, path, 0, winreg.KEY_READ | getattr(winreg, 'KEY_WOW64_64KEY', 0))
                    val, _typ = winreg.QueryValueEx(key, name)
                    winreg.CloseKey(key)
                    if isinstance(val, bytes):
                        try:
                            return val.hex()
                        except Exception:
                            return ''
                    return str(val)
                except Exception:
                    return ''

            reg_items = [
                (getattr(winreg, 'HKEY_LOCAL_MACHINE', None), r"SOFTWARE\Microsoft\Cryptography", "MachineGuid"),
                (getattr(winreg, 'HKEY_LOCAL_MACHINE', None), r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "ProductName"),
                (getattr(winreg, 'HKEY_LOCAL_MACHINE', None), r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "CurrentBuild"),
                (getattr(winreg, 'HKEY_LOCAL_MACHINE', None), r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "InstallDate"),
            ]
            for root, path, name in reg_items:
                try:
                    if root is None:
                        continue
                    value = _read_reg(root, path, name)
                    if value:
                        self.save_registry_snapshot(path, name, value)
                except Exception:
                    pass
        except Exception as e:
            try:
                self.logger.warning(f"prepare_prebackup_snapshot failed: {e}")
            except Exception:
                pass

    def save_settings(self, settings: dict) -> None:
        try:
            cur = self.conn.cursor()
            for k, v in settings.items():
                cur.execute(
                    'INSERT INTO app_settings (key, value) VALUES (?, ?) '
                    'ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                    (str(k), json.dumps(v))
                )
            self.conn.commit()
        except Exception as e:
            self.logger.warning(f"save_settings failed: {e}")

    def get_setting(self, key: str, default=None):
        try:
            cur = self.conn.cursor()
            cur.execute('SELECT value FROM app_settings WHERE key=?', (key,))
            row = cur.fetchone()
            if not row:
                return default
            try:
                return json.loads(row[0])
            except Exception:
                return row[0]
        except Exception:
            return default

    def load_settings(self) -> dict:
        settings: dict = {}
        try:
            cur = self.conn.cursor()
            cur.execute('SELECT key, value FROM app_settings')
            for key, value in cur.fetchall():
                try:
                    settings[str(key)] = json.loads(value)
                except Exception:
                    settings[str(key)] = value
        except Exception as e:
            self.logger.warning(f"load_settings failed: {e}")
        return settings

    def get_statistics(self) -> dict:
        stats = {
            'total_changes': 0,
            'successful_changes': 0,
            'failed_changes': 0,
            'total_game_spoofs': 0,
            'total_registry_changes': 0,
        }
        try:
            cur = self.conn.cursor()
            cur.execute('SELECT COUNT(*) FROM changes')
            stats['total_changes'] = int(cur.fetchone()[0])
            cur.execute('SELECT COUNT(*) FROM changes WHERE success=1')
            stats['successful_changes'] = int(cur.fetchone()[0])
            cur.execute('SELECT COUNT(*) FROM changes WHERE success=0')
            stats['failed_changes'] = int(cur.fetchone()[0])
            cur.execute('SELECT COUNT(*) FROM game_spoofs')
            stats['total_game_spoofs'] = int(cur.fetchone()[0])
            # Prefer registry_changes; fallback to registry_spoof if empty
            cur.execute('SELECT COUNT(*) FROM registry_changes')
            stats['total_registry_changes'] = int(cur.fetchone()[0])
        except Exception as e:
            self.logger.warning(f"get_statistics failed: {e}")
        return stats

    def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM changes WHERE datetime(timestamp) < datetime('now', ?)",
                        (f'-{int(days_to_keep)} days',))
            cur.execute("DELETE FROM game_spoofs WHERE datetime(timestamp) < datetime('now', ?)",
                        (f'-{int(days_to_keep)} days',))
            cur.execute("DELETE FROM registry_changes WHERE datetime(timestamp) < datetime('now', ?)",
                        (f'-{int(days_to_keep)} days',))
            cur.execute("DELETE FROM registry_spoof WHERE datetime(timestamp) < datetime('now', ?)",
                        (f'-{int(days_to_keep)} days',))
            self.conn.commit()
        except Exception as e:
            self.logger.warning(f"cleanup_old_data failed: {e}")

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass