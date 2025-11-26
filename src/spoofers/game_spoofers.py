import winreg
import os
import json
import random
import string
import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import shutil

class GameSpoofer:
    
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
    def is_admin(self) -> bool:
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def is_win11(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
                try:
                    build, _ = winreg.QueryValueEx(k, "CurrentBuild")
                except Exception:
                    build = ""
                try:
                    num = int(str(build)) if str(build).isdigit() else 0
                except Exception:
                    num = 0
                return bool(num >= 22000)
        except Exception:
            return False
        
    def generate_random_string(self, length: int = 12, chars: str = None) -> str:
        
        if chars is None:
            chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def generate_random_hex(self, length: int = 8) -> str:
        
        return ''.join(random.choice('0123456789ABCDEF') for _ in range(length))
    
    def backup_registry_key(self, key_path: str, backup_name: str) -> bool:
        
        try:
            backup_path = f"backups/registry/{backup_name}.reg"
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            import re
            # Ensure hive prefix for reg.exe
            upper = key_path.upper()
            if not (upper.startswith('HKLM\\') or upper.startswith('HKEY_LOCAL_MACHINE\\') or upper.startswith('HKCU\\') or upper.startswith('HKEY_CURRENT_USER\\')):
                hk_prefix = "HKLM\\"
                full_key = hk_prefix + key_path
            else:
                full_key = key_path
            # Sanitize filename
            safe_backup_path = re.sub(r"[^A-Za-z0-9_\\/:.-]", "_", backup_path)
            subprocess.run([
                'reg', 'export', full_key, safe_backup_path, '/y'
            ], check=True, capture_output=True, shell=False)
            
            self.logger.info(f"Registry backup created: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup registry key {key_path}: {e}")
            return False
    
    def modify_registry_value(self, key_path: str, value_name: str, new_value: str, 
                            value_type: int = winreg.REG_SZ) -> bool:
        
        try:
            if not self.is_admin():
                self.logger.warning("Registry write skipped: Administrator privileges required")
                return False
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ):
                    pass
            except (OSError, WindowsError):
                try:
                    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                        pass
                    self.logger.info(f"Created registry key: {key_path}")
                except Exception as create_error:
                    self.logger.warning(f"Could not create registry key {key_path}: {create_error}")
                    return False
            
            kp_sanitized = key_path.replace('\\', '_')
            backup_name = f"{kp_sanitized}_{value_name}"
            self.backup_registry_key(key_path, backup_name)
            
            original_value = self.get_registry_value(key_path, value_name)
            
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, value_name, 0, value_type, new_value)
            
            if self.db_manager:
                self.db_manager.save_registry_change(key_path, value_name, str(original_value), new_value)
            
            # verify
            applied = self.get_registry_value(key_path, value_name)
            ok = (str(applied) == str(new_value))
            self.logger.info(f"Registry modified: {key_path}\\{value_name} = {new_value} (verified={ok})")
            return ok
            
        except Exception as e:
            self.logger.error(f"Failed to modify registry {key_path}\\{value_name}: {e}")
            return False
    
    def get_registry_value(self, key_path: str, value_name: str) -> Optional[str]:
        
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
                return str(value)
        except:
            return None

class FiveMSpoofer(GameSpoofer):
    
    
    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.game_name = "FiveM"
        
    def spoof_fivem_identifiers(self) -> Dict[str, str]:
        
        results = {}
        
        try:
            results['citizenfx_fp'] = self.spoof_citizenfx_fingerprint()
            
            results['steam_id'] = self.spoof_steam_id()
            
            results['rockstar_id'] = self.spoof_rockstar_id()
            
            results['discord_id'] = self.spoof_discord_id()
            
            results['license'] = self.spoof_license()
            results['license2'] = self.spoof_license2()
            
            results['fivem_token'] = self.spoof_fivem_token()
            
            results['cache_cleared'] = str(self.clear_fivem_cache())
            
            if self.db_manager:
                for spoof_type, new_value in results.items():
                    self.db_manager.save_game_spoof(
                        self.game_name, spoof_type, "original", new_value, anti_detection_level=3
                    )
            
            self.logger.info("FiveM identifiers spoofed successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"FiveM spoofing failed: {e}")
            return {}
    
    def spoof_citizenfx_fingerprint(self) -> str:
        
        new_fp = self.generate_random_hex(32)
        
        registry_paths = [
            r"SOFTWARE\CitizenFX\Fingerprint",
            r"SOFTWARE\WOW6432Node\CitizenFX\Fingerprint"
        ]
        
        for path in registry_paths:
            try:
                self.modify_registry_value(path, "Fingerprint", new_fp)
            except:
                pass
        
        return new_fp
    
    def spoof_steam_id(self) -> str:
        
        new_steam_id = self.generate_random_string(17, string.digits)
        
        steam_paths = [
            r"SOFTWARE\Valve\Steam",
            r"SOFTWARE\WOW6432Node\Valve\Steam"
        ]
        
        for path in steam_paths:
            try:
                self.modify_registry_value(path, "LastGameNameUsed", new_steam_id)
            except:
                pass
        
        return new_steam_id
    
    def spoof_rockstar_id(self) -> str:
        
        new_rockstar_id = self.generate_random_string(16, string.ascii_uppercase + string.digits)
        
        rockstar_paths = [
            r"SOFTWARE\Rockstar Games\Social Club",
            r"SOFTWARE\WOW6432Node\Rockstar Games\Social Club"
        ]
        
        for path in rockstar_paths:
            try:
                self.modify_registry_value(path, "AccountId", new_rockstar_id)
            except:
                pass
        
        return new_rockstar_id
    
    def spoof_discord_id(self) -> str:
        
        new_discord_id = self.generate_random_string(18, string.digits)
        
        discord_paths = [
            r"SOFTWARE\Discord",
            r"SOFTWARE\WOW6432Node\Discord"
        ]
        
        for path in discord_paths:
            try:
                self.modify_registry_value(path, "UserId", new_discord_id)
            except:
                pass
        
        return new_discord_id
    
    def spoof_license(self) -> str:
        
        new_license = f"license:{self.generate_random_hex(32)}"
        
        license_paths = [
            r"SOFTWARE\CitizenFX\License",
            r"SOFTWARE\WOW6432Node\CitizenFX\License"
        ]
        
        for path in license_paths:
            try:
                self.modify_registry_value(path, "License", new_license)
            except:
                pass
        
        return new_license
    
    def spoof_license2(self) -> str:
        
        new_license2 = f"license2:{self.generate_random_hex(32)}"
        
        license2_paths = [
            r"SOFTWARE\CitizenFX\License2",
            r"SOFTWARE\WOW6432Node\CitizenFX\License2"
        ]
        
        for path in license2_paths:
            try:
                self.modify_registry_value(path, "License2", new_license2)
            except:
                pass
        
        return new_license2
    
    def spoof_fivem_token(self) -> str:
        
        new_token = self.generate_random_hex(64)
        
        token_paths = [
            r"SOFTWARE\CitizenFX\Token",
            r"SOFTWARE\WOW6432Node\CitizenFX\Token"
        ]
        
        for path in token_paths:
            try:
                self.modify_registry_value(path, "Token", new_token)
            except:
                pass
        
        return new_token
    
    def clear_fivem_cache(self) -> bool:
        
        try:
            cache_paths = [
                os.path.expandvars("%localappdata%\\FiveM\\FiveM.app\\data\\cache"),
                os.path.expandvars("%localappdata%\\FiveM\\FiveM.app\\data\\nui-storage"),
                os.path.expandvars("%localappdata%\\FiveM\\FiveM.app\\crashes"),
                os.path.expandvars("%localappdata%\\FiveM\\FiveM.app\\logs")
            ]
            
            for path in cache_paths:
                if os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
                    os.makedirs(path, exist_ok=True)
            
            self.logger.info("FiveM cache cleared successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear FiveM cache: {e}")
            return False

class FortniteSpoofer(GameSpoofer):
    
    
    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.game_name = "Fortnite"
        
    def spoof_fortnite_identifiers(self) -> Dict[str, str]:
        
        results = {}
        
        try:
            results['epic_id'] = self.spoof_epic_id()
            
            results['account_id'] = self.spoof_account_id()
            
            results['device_id'] = self.spoof_device_id()
            
            results['session_id'] = self.spoof_session_id()
            
            results['hardware_hash'] = self.spoof_hardware_hash()
            
            results['machine_id'] = self.spoof_machine_id()
            
            results['cache_cleared'] = str(self.clear_fortnite_cache())
            
            results['eac_cleared'] = str(self.clear_easyanticheat())
            
            if self.db_manager:
                for spoof_type, new_value in results.items():
                    self.db_manager.save_game_spoof(
                        self.game_name, spoof_type, "original", new_value, anti_detection_level=3
                    )
            
            self.logger.info("Fortnite identifiers spoofed successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Fortnite spoofing failed: {e}")
            return {}
    
    def spoof_epic_id(self) -> str:
        
        new_epic_id = self.generate_random_hex(32)
        
        epic_paths = [
            r"SOFTWARE\Epic Games\EpicOnlineServices",
            r"SOFTWARE\WOW6432Node\Epic Games\EpicOnlineServices"
        ]
        
        for path in epic_paths:
            try:
                self.modify_registry_value(path, "UserId", new_epic_id)
            except:
                pass
        
        return new_epic_id
    
    def spoof_account_id(self) -> str:
        
        new_account_id = self.generate_random_string(32, string.ascii_lowercase + string.digits)
        
        account_paths = [
            r"SOFTWARE\Epic Games\Fortnite",
            r"SOFTWARE\WOW6432Node\Epic Games\Fortnite"
        ]
        
        for path in account_paths:
            try:
                self.modify_registry_value(path, "AccountId", new_account_id)
            except:
                pass
        
        return new_account_id
    
    def spoof_device_id(self) -> str:
        
        new_device_id = self.generate_random_hex(16)
        
        device_paths = [
            r"SOFTWARE\Epic Games\DeviceId",
            r"SOFTWARE\WOW6432Node\Epic Games\DeviceId"
        ]
        
        for path in device_paths:
            try:
                self.modify_registry_value(path, "DeviceId", new_device_id)
            except:
                pass
        
        return new_device_id
    
    def spoof_session_id(self) -> str:
        
        new_session_id = self.generate_random_string(24, string.ascii_letters + string.digits)
        
        session_paths = [
            r"SOFTWARE\Epic Games\Session",
            r"SOFTWARE\WOW6432Node\Epic Games\Session"
        ]
        
        for path in session_paths:
            try:
                self.modify_registry_value(path, "SessionId", new_session_id)
            except:
                pass
        
        return new_session_id
    
    def spoof_hardware_hash(self) -> str:
        
        new_hardware_hash = self.generate_random_hex(64)
        
        hardware_paths = [
            r"SOFTWARE\Epic Games\HardwareHash",
            r"SOFTWARE\WOW6432Node\Epic Games\HardwareHash"
        ]
        
        for path in hardware_paths:
            try:
                self.modify_registry_value(path, "HardwareHash", new_hardware_hash)
            except:
                pass
        
        return new_hardware_hash
    
    def spoof_machine_id(self) -> str:
        
        new_machine_id = self.generate_random_string(16, string.ascii_uppercase + string.digits)
        
        machine_paths = [
            r"SOFTWARE\Microsoft\Cryptography",
            r"SOFTWARE\WOW6432Node\Microsoft\Cryptography"
        ]
        
        for path in machine_paths:
            try:
                self.modify_registry_value(path, "MachineGuid", new_machine_id)
            except:
                pass
        
        return new_machine_id
    
    def clear_fortnite_cache(self) -> bool:
        
        try:
            cache_paths = [
                os.path.expandvars("%localappdata%\\FortniteGame\\Saved\\Config"),
                os.path.expandvars("%localappdata%\\FortniteGame\\Saved\\Logs"),
                os.path.expandvars("%localappdata%\\FortniteGame\\Saved\\Cloud"),
                os.path.expandvars("%localappdata%\\EpicGamesLauncher\\Saved\\Config")
            ]
            
            for path in cache_paths:
                if os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
                    os.makedirs(path, exist_ok=True)
            
            self.logger.info("Fortnite cache cleared successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear Fortnite cache: {e}")
            return False
    
    def clear_easyanticheat(self) -> bool:
        
        try:
            eac_paths = [
                os.path.expandvars("%programdata%\\EasyAntiCheat"),
                os.path.expandvars("%appdata%\\EasyAntiCheat")
            ]
            
            for path in eac_paths:
                if os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
                    os.makedirs(path, exist_ok=True)
            
            self.logger.info("EasyAntiCheat data cleared successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear EasyAntiCheat data: {e}")
            return False

class ValorantSpoofer(GameSpoofer):
    
    
    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.game_name = "Valorant"
        
    def spoof_valorant_identifiers(self) -> Dict[str, str]:
        
        results = {}
        
        try:
            results['riot_id'] = self.spoof_riot_id()
            
            results['account_id'] = self.spoof_valorant_account_id()
            
            results['hw_fingerprint'] = self.spoof_hw_fingerprint()
            
            results['machine_hash'] = self.spoof_machine_hash()
            
            results['session_token'] = self.spoof_session_token()
            
            results['client_id'] = self.spoof_client_id()
            
            results['vanguard_cleared'] = str(self.clear_vanguard_cache())
            
            if self.db_manager:
                for spoof_type, new_value in results.items():
                    self.db_manager.save_game_spoof(
                        self.game_name, spoof_type, "original", new_value, anti_detection_level=3
                    )
            
            self.logger.info("Valorant identifiers spoofed successfully")
            return results
            
        except Exception as e:
            self.logger.error(f"Valorant spoofing failed: {e}")
            return {}
    
    def spoof_riot_id(self) -> str:
        
        new_riot_id = self.generate_random_hex(32)
        
        riot_paths = [
            r"SOFTWARE\Riot Games\Riot Client",
            r"SOFTWARE\WOW6432Node\Riot Games\Riot Client"
        ]
        
        for path in riot_paths:
            try:
                self.modify_registry_value(path, "UserId", new_riot_id)
            except:
                pass
        
        return new_riot_id
    
    def spoof_valorant_account_id(self) -> str:
        
        new_account_id = self.generate_random_string(36, string.ascii_lowercase + string.digits + '-')
        
        account_paths = [
            r"SOFTWARE\Riot Games\VALORANT",
            r"SOFTWARE\WOW6432Node\Riot Games\VALORANT"
        ]
        
        for path in account_paths:
            try:
                self.modify_registry_value(path, "AccountId", new_account_id)
            except:
                pass
        
        return new_account_id
    
    def spoof_hw_fingerprint(self) -> str:
        
        new_fingerprint = self.generate_random_hex(64)
        
        fingerprint_paths = [
            r"SOFTWARE\Riot Games\Riot Client\HardwareFingerprint",
            r"SOFTWARE\WOW6432Node\Riot Games\Riot Client\HardwareFingerprint"
        ]
        
        for path in fingerprint_paths:
            try:
                self.modify_registry_value(path, "Fingerprint", new_fingerprint)
            except:
                pass
        
        return new_fingerprint
    
    def spoof_machine_hash(self) -> str:
        
        new_machine_hash = self.generate_random_hex(32)
        
        machine_paths = [
            r"SOFTWARE\Riot Games\Riot Client\MachineHash",
            r"SOFTWARE\WOW6432Node\Riot Games\Riot Client\MachineHash"
        ]
        
        for path in machine_paths:
            try:
                self.modify_registry_value(path, "Hash", new_machine_hash)
            except:
                pass
        
        return new_machine_hash
    
    def spoof_session_token(self) -> str:
        
        new_session_token = self.generate_random_string(32, string.ascii_letters + string.digits)
        
        session_paths = [
            r"SOFTWARE\Riot Games\Riot Client\Session",
            r"SOFTWARE\WOW6432Node\Riot Games\Riot Client\Session"
        ]
        
        for path in session_paths:
            try:
                self.modify_registry_value(path, "Token", new_session_token)
            except:
                pass
        
        return new_session_token
    
    def spoof_client_id(self) -> str:
        
        new_client_id = self.generate_random_hex(16)
        
        client_paths = [
            r"SOFTWARE\Riot Games\Riot Client\ClientId",
            r"SOFTWARE\WOW6432Node\Riot Games\Riot Client\ClientId"
        ]
        
        for path in client_paths:
            try:
                self.modify_registry_value(path, "Id", new_client_id)
            except:
                pass
        
        return new_client_id
    
    def clear_vanguard_cache(self) -> bool:
        
        try:
            vanguard_paths = [
                os.path.expandvars("%programdata%\\Riot Games\\Vanguard"),
                os.path.expandvars("%localappdata%\\Riot Games\\Riot Client\\Data")
            ]
            
            for path in vanguard_paths:
                if os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
                    os.makedirs(path, exist_ok=True)
            
            self.logger.info("Vanguard cache cleared successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear Vanguard cache: {e}")
            return False

class AntiDetectionManager:
    
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def randomize_timing(self, base_delay: float = 1.0) -> float:
        
        import random
        import time
        
        delay = base_delay * random.uniform(0.5, 2.0)
        time.sleep(delay)
        return delay
    
    def obfuscate_string(self, text: str) -> str:
        
        key = 0x42
        obfuscated = ''.join(chr(ord(c) ^ key) for c in text)
        return obfuscated
    
    def clear_system_traces(self):
        
        try:
            appdata = os.getenv('APPDATA')
            recent_path = os.path.join(appdata, 'Microsoft', 'Windows', 'Recent') if appdata else os.path.expandvars("%userprofile%\\Recent")
            if os.path.exists(recent_path):
                try:
                    for file in os.listdir(recent_path):
                        try:
                            file_path = os.path.join(recent_path, file)
                            if os.access(file_path, os.W_OK):
                                if os.path.isfile(file_path):
                                    os.remove(file_path)
                                elif os.path.isdir(file_path):
                                    shutil.rmtree(file_path, ignore_errors=True)
                        except (PermissionError, OSError) as file_error:
                            continue
                except (PermissionError, OSError) as dir_error:
                    self.logger.warning(f"Cannot access recent files directory: {dir_error}")
            
            temp_path = os.getenv('TEMP') or os.path.expandvars("%temp%")
            if os.path.exists(temp_path):
                try:
                    for file in os.listdir(temp_path):
                        try:
                            file_path = os.path.join(temp_path, file)
                            if os.access(file_path, os.W_OK) and file.startswith('tmp'):
                                if os.path.isfile(file_path):
                                    os.remove(file_path)
                                elif os.path.isdir(file_path):
                                    shutil.rmtree(file_path, ignore_errors=True)
                        except (PermissionError, OSError) as file_error:
                            continue
                except (PermissionError, OSError) as dir_error:
                    self.logger.warning(f"Cannot access temp directory: {dir_error}")
            
            self.logger.info("System traces cleared (accessible files only)")
            
        except Exception as e:
            self.logger.error(f"Failed to clear system traces: {e}")
    
    def spoof_file_timestamps(self, directory: str):
        
        try:
            import random
            from datetime import datetime, timedelta
            
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        random_time = datetime.now() - timedelta(days=random.randint(1, 30))
                        timestamp = random_time.timestamp()
                        
                        os.utime(file_path, (timestamp, timestamp))
                    except:
                        pass
            
            self.logger.info(f"File timestamps randomized for {directory}")
            
        except Exception as e:
            self.logger.error(f"Failed to spoof file timestamps: {e}")

# Factory function to get appropriate spoofer
def get_game_spoofer(game_name: str, db_manager=None) -> Optional[GameSpoofer]:
    
    spoofer_map = {
        'fivem': FiveMSpoofer,
        'fortnite': FortniteSpoofer,
        'valorant': ValorantSpoofer,
        'minecraft': MinecraftSpoofer,
        'roblox': RobloxSpoofer,
        'cs:go': CSGOSpoofer,
        'cs2': CSGOSpoofer,
    }
    
    game_name_lower = game_name.lower()
    if game_name_lower in spoofer_map:
        return spoofer_map[game_name_lower](db_manager)
    
    return None
# Additional safe spoofers for other games
class MinecraftSpoofer(GameSpoofer):
    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.game_name = "Minecraft"
    
    def spoof_minecraft_identifiers(self) -> Dict[str, str]:
        results: Dict[str, str] = {}
        try:
            results['client_seed'] = self.generate_random_hex(16)
            results['cache_cleared'] = str(self.clear_minecraft_cache())
            if self.db_manager:
                for spoof_type, new_value in results.items():
                    self.db_manager.save_game_spoof(self.game_name, spoof_type, "original", new_value, anti_detection_level=2)
            self.logger.info("Minecraft cache handled successfully")
            return results
        except Exception as e:
            self.logger.error(f"Minecraft spoofing failed: {e}")
            return {}
    
    def clear_minecraft_cache(self) -> bool:
        try:
            cache_paths = [
                os.path.expandvars("%appdata%\\.minecraft\\logs"),
                os.path.expandvars("%appdata%\\.minecraft\\webcache"),
                os.path.expandvars("%appdata%\\.minecraft\\crash-reports"),
            ]
            for path in cache_paths:
                if os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
                    os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear Minecraft cache: {e}")
            return False

class RobloxSpoofer(GameSpoofer):
    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.game_name = "Roblox"
    
    def spoof_roblox_identifiers(self) -> Dict[str, str]:
        results: Dict[str, str] = {}
        try:
            results['cache_cleared'] = str(self.clear_roblox_cache())
            if self.db_manager:
                for spoof_type, new_value in results.items():
                    self.db_manager.save_game_spoof(self.game_name, spoof_type, "original", new_value, anti_detection_level=2)
            self.logger.info("Roblox cache handled successfully")
            return results
        except Exception as e:
            self.logger.error(f"Roblox spoofing failed: {e}")
            return {}
    
    def clear_roblox_cache(self) -> bool:
        try:
            cache_paths = [
                os.path.expandvars("%localappdata%\\Roblox\\logs"),
                os.path.expandvars("%localappdata%\\Roblox\\Cache"),
            ]
            for path in cache_paths:
                if os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
                    os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear Roblox cache: {e}")
            return False

class CSGOSpoofer(GameSpoofer):
    def __init__(self, db_manager=None):
        super().__init__(db_manager)
        self.game_name = "CS:GO"
    
    def spoof_csgo_identifiers(self) -> Dict[str, str]:
        results: Dict[str, str] = {}
        try:
            results['cache_cleared'] = str(self.clear_csgo_cache())
            if self.db_manager:
                for spoof_type, new_value in results.items():
                    self.db_manager.save_game_spoof(self.game_name, spoof_type, "original", new_value, anti_detection_level=2)
            self.logger.info("CS:GO cache handled successfully")
            return results
        except Exception as e:
            self.logger.error(f"CS:GO spoofing failed: {e}")
            return {}
    
    def clear_csgo_cache(self) -> bool:
        try:
            base_steam = os.path.expandvars("%programfiles(x86)%\\Steam")
            candidates = [
                os.path.join(base_steam, "steamapps", "common", "Counter-Strike Global Offensive", "csgo", "logs"),
                os.path.expandvars("%localappdata%\\Temp\\csgo"),
            ]
            for path in candidates:
                if os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
                    os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear CS:GO cache: {e}")
            return False
