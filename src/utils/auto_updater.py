import os
import sys
import shutil
import zipfile
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests


class AutoUpdater:

    def __init__(self, app_dir: Path, settings_provider, logger=None):
        self.app_dir = Path(app_dir)
        self.settings = settings_provider
        self.logger = logger

    def _log(self, msg: str):
        if self.logger:
            try:
                self.logger.info(msg)
            except Exception:
                pass

    def _get_config(self) -> Dict[str, Optional[str]]:
        repo = self.settings.get_setting('update_repo', '')
        if not repo:
            repo = ''
        branch = self.settings.get_setting('update_branch', 'main')
        token = self.settings.get_setting('update_token', None)
        auto_apply = bool(self.settings.get_setting('auto_update_apply', True))
        return {
            'repo': repo,
            'branch': branch or 'main',
            'token': token,
            'auto_apply': auto_apply,
        }

    def _split_repo(self, repo: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            owner, name = repo.strip().split('/', 1)
            return owner, name
        except Exception:
            return None, None

    def _api_headers(self, token: Optional[str]) -> Dict[str, str]:
        hdrs = {
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'PhantomID-AutoUpdater'
        }
        if token:
            hdrs['Authorization'] = f'Bearer {token}'
        return hdrs

    def _latest_release_info(self, owner: str, name: str, token: Optional[str]) -> Optional[Dict[str, str]]:
        url = f'https://api.github.com/repos/{owner}/{name}/releases/latest'
        try:
            resp = requests.get(url, headers=self._api_headers(token), timeout=20)
        except Exception as e:
            self._log(f'GitHub API request failed: {e}')
            return None
        if resp.status_code != 200:
            self._log(f'GitHub API error ({resp.status_code}): {resp.text[:200]}')
            return None
        data = resp.json()
        return {
            'id': str(data.get('id')) if data.get('id') is not None else None,
            'tag': data.get('tag_name'),
            'name': data.get('name') or data.get('tag_name') or 'latest',
            'zipball_url': data.get('zipball_url')
        }

    def _get_local_release_tag(self) -> Optional[str]:
        try:
            tag = self.settings.get_setting('last_release_tag', None)
            if tag:
                return tag
            legacy = self.settings.get_setting('last_update_sha', None)
            return legacy
        except Exception:
            return None

    def _set_local_release_tag(self, tag: str):
        try:
            self.settings.save_settings({'last_release_tag': tag})
        except Exception:
            pass

    def check_update_available(self) -> Tuple[bool, Optional[str]]:
        cfg = self._get_config()
        owner, name = self._split_repo(cfg['repo'] or '')
        if not owner or not name:
            self._log('Updater: GitHub repo not configured (expected owner/repo).')
            return False, None
        latest = self._latest_release_info(owner, name, cfg['token'])
        if not latest or not latest.get('tag'):
            return False, None
        local_tag = self._get_local_release_tag()
        self._log(f'Updater: local_tag={local_tag}, remote_tag={latest.get("tag")}')
        return (local_tag != latest.get('tag')), latest.get('tag')

    def _download_release_zip(self, owner: str, name: str, tag: str, token: Optional[str]) -> Optional[Path]:
        zip_url = f'https://api.github.com/repos/{owner}/{name}/zipball/{tag}'
        updates_dir = self.app_dir / 'updates'
        updates_dir.mkdir(parents=True, exist_ok=True)
        zip_path = updates_dir / f'{name}-{tag}.zip'
        try:
            r = requests.get(zip_url, headers=self._api_headers(token), stream=True, timeout=60)
            if r.status_code != 200:
                self._log(f'Download failed ({r.status_code}) for {zip_url}')
                return None
            with open(zip_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return zip_path
        except Exception as e:
            self._log(f'Error downloading release zip: {e}')
            return None

    def _apply_zip(self, zip_path: Path) -> bool:
        excluded_top = {'backups', 'updates', '.git', '.github', '__pycache__'}
        excluded_files = {'phantomid.db', 'phantomid.log'}
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_p = Path(tmpdir)
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(tmpdir_p)
                roots = [p for p in tmpdir_p.iterdir() if p.is_dir()]
                src_root = roots[0] if roots else tmpdir_p
                for item in src_root.iterdir():
                    name = item.name
                    if name in excluded_top:
                        continue
                    dst = self.app_dir / name
                    if item.is_dir():
                        self._copytree_overwrite(item, dst)
                    else:
                        if name in excluded_files:
                            continue
                        shutil.copy2(item, dst)
            return True
        except Exception as e:
            self._log(f'Error applying update: {e}')
            return False

    def _copytree_overwrite(self, src: Path, dst: Path):
        if dst.exists():
            for root, dirs, files in os.walk(src):
                rel = Path(root).relative_to(src)
                target_root = dst / rel
                target_root.mkdir(parents=True, exist_ok=True)
                for d in dirs:
                    (target_root / d).mkdir(parents=True, exist_ok=True)
                for f in files:
                    if f == '__pycache__':
                        continue
                    shutil.copy2(Path(root) / f, target_root / f)
        else:
            shutil.copytree(src, dst, dirs_exist_ok=True)

    def perform_update_if_available(self) -> Tuple[bool, str]:
        cfg = self._get_config()
        owner, name = self._split_repo(cfg['repo'] or '')
        if not owner or not name:
            return False, 'GitHub repo not configured (owner/repo).'
        available, remote_tag = self.check_update_available()
        if not available or not remote_tag:
            return False, 'No updates found.'
        zip_path = self._download_release_zip(owner, name, remote_tag, cfg['token'])
        if not zip_path:
            return False, 'Failed to download release.'
        applied = self._apply_zip(zip_path)
        if not applied:
            return False, 'Failed to apply update.'
        self._set_local_release_tag(remote_tag)
        return True, f'Updated to release {remote_tag} successfully.'

    def restart_application(self):
        try:
            exe = shutil.which('python') or os.environ.get('PYTHON_EXECUTABLE') or sys.executable
            target = str(self.app_dir / 'spoofer.py')
            subprocess.Popen([exe, target], cwd=str(self.app_dir))
        except Exception:
            pass
