import logging
import uuid
import random
import string
import time
import json
import os
import sys
from typing import Dict, Any, Optional

try:
    import wmi  # type: ignore
except Exception:
    wmi = None

try:
    import winreg as reg  # type: ignore
except Exception:
    reg = None

from core.database_manager import DatabaseManager

class SystemSpoofer:

    NETWORK_CLASS_KEY = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
    MACHINE_GUID_KEY = r"SOFTWARE\Microsoft\Cryptography"
    MACHINE_GUID_VALUE = "MachineGuid"

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or DatabaseManager()
        self.logger = logging.getLogger(__name__)
        try:
            info = self._get_os_info()
            self.is_win11 = bool(info.get("is_win11", False))
            self.product_name = str(info.get("product_name", "Windows"))
            self.build_number = str(info.get("build_number", ""))
        except Exception:
            self.is_win11 = False
            self.product_name = "Windows"
            self.build_number = ""

    def _ensure_backups_dir(self) -> str:
        import os
        d = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), 'backups', 'registry')
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        return d

    def _get_os_info(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {}
        try:
            if reg is not None:
                with reg.OpenKey(reg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
                    try:
                        product, _ = reg.QueryValueEx(k, "ProductName")
                    except Exception:
                        product = "Windows"
                    try:
                        build, _ = reg.QueryValueEx(k, "CurrentBuild")
                    except Exception:
                        try:
                            build, _ = reg.QueryValueEx(k, "CurrentBuildNumber")
                        except Exception:
                            build = ""
                    info["product_name"] = str(product)
                    info["build_number"] = str(build)
                    try:
                        num = int(str(build)) if str(build).isdigit() else 0
                    except Exception:
                        num = 0
                    info["is_win11"] = bool(num >= 22000 or ("Windows 11" in str(product)))
                    return info
        except Exception:
            pass
        try:
            import platform
            ver = platform.version()
            release = platform.release()
            info["product_name"] = "Windows"
            info["build_number"] = ver
            try:
                num = int(str(ver).split(".")[-1])
            except Exception:
                num = 0
            info["is_win11"] = bool(num >= 22000 or release == "11")
        except Exception:
            info["product_name"] = "Windows"
            info["build_number"] = ""
            info["is_win11"] = False
        return info

    def spoof_monitor_serials(self) -> Dict[str, Any]:
        results: Dict[str, Any] = {"success": False, "overrides": {}}
        try:
            if wmi is None:
                results["error"] = "WMI not available"
                return results
            try:
                w = wmi.WMI(namespace="root\\wmi")
            except Exception as e:
                results["error"] = f"WMI init failed: {e}"
                return results
            overrides: Dict[str, str] = {}
            try:
                for mon in w.WmiMonitorID():
                    try:
                        mf = "".join(chr(c) for c in (mon.ManufacturerName or []) if c)
                        pc = "".join(chr(c) for c in (mon.ProductCodeID or []) if c)
                        sn = "".join(chr(c) for c in (mon.SerialNumberID or []) if c)
                        key = f"{mf}-{pc}" if mf or pc else (getattr(mon, 'InstanceName', 'MONITOR'))
                        new_sn = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12))
                        overrides[key] = new_sn
                    except Exception:
                        continue
            except Exception as e:
                results["error"] = f"Monitor enumeration failed: {e}"
                return results
            if self.db_manager:
                self.db_manager.save_settings({"Monitor.SerialOverrides": overrides})
            results["success"] = True
            results["overrides"] = overrides
            # Temp mode: override exists only in app settings; reboot clears effect automatically
            return results
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _backup_registry_key(self, key_path: str, label: str) -> bool:
        import subprocess
        try:
            out_dir = self._ensure_backups_dir()
            safe_label = label.replace('\\', '_').replace(':', '_').replace('/', '_')
            fname = f"{safe_label}.reg"
            target = os.path.join(out_dir, fname)
            upper = key_path.upper()
            if not (upper.startswith('HKLM\\') or upper.startswith('HKEY_LOCAL_MACHINE\\') or upper.startswith('HKCU\\') or upper.startswith('HKEY_CURRENT_USER\\')):
                full_key = 'HKLM\\' + key_path
            else:
                full_key = key_path
            r = subprocess.run(["reg", "export", full_key, target, "/y"], capture_output=True, text=True, shell=False)
            ok = (r.returncode == 0)
            if not ok:
                self.logger.warning(f"Backup failed for {key_path}: {r.stderr.strip()[:200]}")
            return ok
        except Exception as e:
            self.logger.warning(f"Backup error for {key_path}: {e}")
            return False

    def _is_admin(self) -> bool:
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _restart_adapter(self, adapter: Dict[str, Any]) -> None:
        try:
            if adapter.get("wmi_obj") is not None:
                nic = adapter["wmi_obj"]
                try:
                    nic.Disable()
                except Exception:
                    pass
                time.sleep(0.8)
                try:
                    nic.Enable()
                    return
                except Exception:
                    pass
        except Exception:
            pass
        try:
            import subprocess
            name = str(adapter.get("description") or "")
            if name:
                subprocess.run(["netsh", "interface", "set", "interface", f"name={name}", "admin=disabled"], capture_output=True, text=True, shell=False)
                time.sleep(0.8)
                subprocess.run(["netsh", "interface", "set", "interface", f"name={name}", "admin=enabled"], capture_output=True, text=True, shell=False)
        except Exception:
            pass

    def _generate_mac(self) -> str:
        
        b0 = random.randint(0x00, 0xFF)
        b0 = (b0 | 0x02) & 0xFE
        rest = [random.randint(0x00, 0xFF) for _ in range(5)]
        mac_bytes = [b0] + rest
        return ''.join(f"{b:02X}" for b in mac_bytes)

    def _open_key(self, root, path, write: bool = False):
        if reg is None:
            raise RuntimeError("winreg not available on this platform")
        access = reg.KEY_READ | (reg.KEY_WRITE if write else 0)
        return reg.OpenKey(root, path, 0, access)

    def _get_reg_value(self, root, path: str, name: str) -> Optional[str]:
        try:
            with self._open_key(root, path, False) as hkey:
                val, _type = reg.QueryValueEx(hkey, name)
                return str(val) if val is not None else None
        except Exception:
            return None

    def _set_reg_value(self, root, path: str, name: str, value: Optional[str]) -> bool:
        try:
            with self._open_key(root, path, True) as hkey:
                if value is None:
                    try:
                        reg.DeleteValue(hkey, name)
                    except Exception:
                        pass
                else:
                    reg.SetValueEx(hkey, name, 0, reg.REG_SZ, value)
            return True
        except Exception as e:
            self.logger.error(f"Failed setting registry {path} {name}: {e}")
            return False

    def _find_adapter_subkey_by_guid(self, guid: str) -> Optional[str]:
        
        if reg is None:
            return None
        try:
            with self._open_key(reg.HKEY_LOCAL_MACHINE, self.NETWORK_CLASS_KEY, False) as class_key:
                i = 0
                while True:
                    try:
                        subname = reg.EnumKey(class_key, i)
                    except OSError:
                        break
                    i += 1
                    subpath = f"{self.NETWORK_CLASS_KEY}\\{subname}"
                    try:
                        val = self._get_reg_value(reg.HKEY_LOCAL_MACHINE, subpath, "NetCfgInstanceId")
                        if val and val.lower() == guid.lower():
                            return subpath
                    except Exception:
                        continue
        except Exception:
            return None
        return None

    def _get_ip_enabled_adapter(self) -> Optional[Dict[str, Any]]:
        if wmi is None:
            return None
        try:
            c = wmi.WMI()
            for nic in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
                return {
                    "setting_id": getattr(nic, "SettingID", None),
                    "description": getattr(nic, "Description", None),
                    "mac_address": getattr(nic, "MACAddress", None),
                    "wmi_obj": nic,
                }
        except Exception:
            return None
        return None

    def spoof_mac(self) -> Dict[str, Any]:
        
        result = {"success": False, "error": None}
        adapter = self._get_ip_enabled_adapter()
        if adapter is None or adapter.get("setting_id") is None:
            result["error"] = "No IP-enabled adapter found"
            return result
        if not self._is_admin():
            result["error"] = "Administrator privileges required"
            return result

        guid = adapter["setting_id"]
        subkey = self._find_adapter_subkey_by_guid(guid)
        if subkey is None:
            result["error"] = "Adapter registry subkey not found"
            return result

        original = self._get_reg_value(reg.HKEY_LOCAL_MACHINE, subkey, "NetworkAddress")
        self._backup_registry_key(subkey, f"{subkey}_NetworkAddress")
        new_mac = self._generate_mac()
        success = self._set_reg_value(reg.HKEY_LOCAL_MACHINE, subkey, "NetworkAddress", new_mac)

        if not success:
            result["error"] = "Failed to write MAC to registry"
            if self.db_manager:
                self.db_manager.save_change("mac_address", str(original), str(new_mac), category="system", success=False, error_message=result["error"]) 
            return result

        if self.db_manager:
            self.db_manager.save_registry_change(subkey, "NetworkAddress", str(original), new_mac, success=True)
            self.db_manager.save_change("mac_address", str(original), new_mac, category="system")
            settings = self.db_manager.load_settings()
            mac_backups = settings.get("mac_original_values", {})
            mac_backups[guid] = original
            mac_subkeys = settings.get("mac_subkeys", {})
            mac_subkeys[guid] = subkey
            self.db_manager.save_settings({"mac_original_values": mac_backups, "mac_subkeys": mac_subkeys})

        self._restart_adapter(adapter)

        applied = self._get_reg_value(reg.HKEY_LOCAL_MACHINE, subkey, "NetworkAddress")
        if self._get_mode() == 'temp':
            cmds = []
            hk_subkey = "HKLM\\" + subkey
            if original:
                cmds.append(f'reg add "{hk_subkey}" /v NetworkAddress /t REG_SZ /d {original} /f')
            else:
                cmds.append(f'reg delete "{hk_subkey}" /v NetworkAddress /f')
            self._schedule_revert_commands(cmds)
        result.update({"success": bool(success and applied == new_mac), "before": original, "after": new_mac, "adapter_guid": guid, "registry_key": subkey})
        return result

    def spoof_ip(self) -> Dict[str, Any]:
        
        result = {"success": False, "error": None}
        if wmi is None:
            result["error"] = "WMI not available"
            return result

        try:
            c = wmi.WMI()
            target_nic = None
            for nic in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
                target_nic = nic
                break

            if target_nic is None:
                result["error"] = "No IP-enabled adapter found"
                return result

            ips = list(getattr(target_nic, "IPAddress", []) or [])
            subnets = list(getattr(target_nic, "IPSubnet", []) or [])
            gateways = list(getattr(target_nic, "DefaultIPGateway", []) or [])

            def pick_ipv4(items):
                for val in items:
                    try:
                        parts = str(val).split(".")
                        if len(parts) == 4 and all(p.isdigit() for p in parts):
                            return str(val)
                    except Exception:
                        continue
                return None

            current_ip = pick_ipv4(ips)
            subnet_mask = pick_ipv4(subnets)
            gateway = pick_ipv4(gateways)

            if not current_ip or not subnet_mask:
                try:
                    target_nic.EnableDHCP()
                except Exception:
                    pass
                try:
                    target_nic.RenewDHCPLease()
                    if self.db_manager:
                        self.db_manager.save_change("ip_address", "unknown", "DHCP renewed", category="system")
                    result["success"] = True
                except Exception as e:
                    result["error"] = f"Failed to renew DHCP: {e}"
                return result

            octets = current_ip.split(".")
            prefix = ".".join(octets[:3])
            original_last = int(octets[3])

            candidates = [i for i in range(2, 255) if i != original_last]
            try:
                if gateway:
                    g_last = int(gateway.split(".")[3])
                    candidates = [i for i in candidates if i != g_last]
            except Exception:
                pass

            new_last = random.choice(candidates) if candidates else (original_last + 1) % 254 or 2
            new_ip = f"{prefix}.{new_last}"

            static_ok = False
            try:
                res = target_nic.EnableStatic([new_ip], [subnet_mask])
                static_ok = (res is None) or (isinstance(res, tuple) and res[0] == 0)
                if static_ok and gateway:
                    try:
                        gw_res = target_nic.SetGateways([gateway], [1])
                    except Exception:
                        pass
                try:
                    dns = list(getattr(target_nic, "DNSServerSearchOrder", []) or [])
                    if dns:
                        target_nic.SetDNSServerSearchOrder(dns)
                except Exception:
                    pass
            except Exception as e:
                static_ok = False
                self.logger.warning(f"Static IP assignment failed, will fallback to DHCP: {e}")

            if static_ok:
                if self.db_manager:
                    self.db_manager.save_change("ip_address", current_ip, new_ip, category="system")
                result.update({"success": True, "before": current_ip, "after": new_ip, "method": "static"})
                return result

            try:
                target_nic.EnableDHCP()
            except Exception:
                pass
            try:
                target_nic.RenewDHCPLease()
                if self.db_manager:
                    self.db_manager.save_change("ip_address", current_ip, "DHCP renewed", category="system")
                result.update({"success": True, "before": current_ip, "after": "dhcp", "method": "dhcp"})
            except Exception as e:
                result["error"] = f"Failed to renew DHCP: {e}"
            return result
        except Exception as e:
            result["error"] = str(e)
            return result

    def spoof_hwid(self) -> Dict[str, Any]:
        
        result = {"success": False, "error": None}
        if reg is None:
            result["error"] = "winreg not available"
            return result
        if not self._is_admin():
            result["error"] = "Administrator privileges required"
            return result
        try:
            original = self._get_reg_value(reg.HKEY_LOCAL_MACHINE, self.MACHINE_GUID_KEY, self.MACHINE_GUID_VALUE)
            self._backup_registry_key(self.MACHINE_GUID_KEY, "SOFTWARE_Microsoft_Cryptography_MachineGuid")
            new_guid = str(uuid.uuid4())
            ok = self._set_reg_value(reg.HKEY_LOCAL_MACHINE, self.MACHINE_GUID_KEY, self.MACHINE_GUID_VALUE, new_guid)
            if not ok:
                result["error"] = "Failed to set MachineGuid"
                if self.db_manager:
                    self.db_manager.save_change("hwid", str(original), new_guid, category="system", success=False, error_message=result["error"]) 
                return result
            if self.db_manager:
                self.db_manager.save_registry_change(self.MACHINE_GUID_KEY, self.MACHINE_GUID_VALUE, str(original), new_guid, success=True)
                self.db_manager.save_change("hwid", str(original), new_guid, category="system")
                self.db_manager.save_settings({"original_machine_guid": original})
            if self._get_mode() == 'temp':
                cmds = []
                if original:
                    cmds.append('reg add "HKLM\\SOFTWARE\\Microsoft\\Cryptography" /v MachineGuid /t REG_SZ /d ' + str(original) + ' /f')
                self._schedule_revert_commands(cmds)
            result.update({"success": True, "before": original, "after": new_guid})
        except Exception as e:
            result["error"] = str(e)
        return result

    def spoof_overrides(self, need_bios: bool = False, need_cpu_serial: bool = False,
                         need_processor_id: bool = False, need_os_serial: bool = False,
                         need_efi: bool = False) -> Dict[str, Any]:
        
        overrides: Dict[str, str] = {}
        if need_bios:
            overrides["BIOS.SerialNumber"] = "PHANTOM-" + ''.join(random.choice('0123456789ABCDEF') for _ in range(16))
        if need_cpu_serial:
            overrides["CPU.Serial"] = ''.join(random.choice('0123456789ABCDEF') for _ in range(16))
        if need_processor_id:
            overrides["CPU.ProcessorId"] = ''.join(random.choice('0123456789ABCDEF') for _ in range(16))
        if need_os_serial:
            overrides["OS.SerialNumber"] = ''.join(random.choice(string.digits) for _ in range(20))
        if need_efi:
            overrides["EFI.Number"] = str(uuid.uuid4()).upper()

        if not overrides:
            return {"success": True, "overrides": {}}

        try:
            existing = {}
            if self.db_manager:
                existing = self.db_manager.get_setting("spoof_overrides", {})
                combined = {**existing, **overrides}
                self.db_manager.save_settings({"spoof_overrides": combined})
                # Save each logical override change into changes table
                for k, v in overrides.items():
                    self.db_manager.save_change(k, str(existing.get(k, "")), v, category="system")
            return {"success": True, "overrides": overrides}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def simulate_system(self, options: Optional[list] = None) -> Dict[str, Any]:
        results: Dict[str, Any] = {"success": True, "items": []}
        try:
            opts = options or []
            if any(o == "MAC Address" for o in opts):
                adapter = self._get_ip_enabled_adapter()
                before = None
                if adapter and adapter.get("setting_id"):
                    subkey = self._find_adapter_subkey_by_guid(adapter["setting_id"])
                    if subkey:
                        before = self._get_reg_value(reg.HKEY_LOCAL_MACHINE, subkey, "NetworkAddress")
                after = self._generate_mac()
                results["items"].append({"type": "MAC Address", "before": before, "after": after})
            if any(o == "IP Address" for o in opts):
                current = None
                new_ip = None
                if wmi is not None:
                    try:
                        c = wmi.WMI()
                        target_nic = None
                        for nic in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
                            target_nic = nic
                            break
                        if target_nic:
                            ips = list(getattr(target_nic, "IPAddress", []) or [])
                            for val in ips:
                                parts = str(val).split(".")
                                if len(parts) == 4 and all(p.isdigit() for p in parts):
                                    current = str(val)
                                    break
                            if current:
                                octets = current.split(".")
                                prefix = ".".join(octets[:3])
                                original_last = int(octets[3])
                                candidates = [i for i in range(2, 255) if i != original_last]
                                new_last = candidates[0] if candidates else (original_last + 1) % 254 or 2
                                new_ip = f"{prefix}.{new_last}"
                    except Exception:
                        pass
                results["items"].append({"type": "IP Address", "before": current, "after": new_ip})
            if any(o == "HWID" for o in opts):
                before = self._get_reg_value(reg.HKEY_LOCAL_MACHINE, self.MACHINE_GUID_KEY, self.MACHINE_GUID_VALUE)
                after = str(uuid.uuid4())
                results["items"].append({"type": "HWID", "before": before, "after": after})
            need_bios = any(o == "BIOS Serial" for o in opts)
            need_cpu_serial = any(o == "CPU Serial" for o in opts)
            need_processor_id = any(o == "Processor ID" for o in opts)
            need_os_serial = any(o == "Serial Number" for o in opts)
            need_efi = any(o == "EFI Number" for o in opts)
            if any([need_bios, need_cpu_serial, need_processor_id, need_os_serial, need_efi]):
                overrides: Dict[str, str] = {}
                if need_bios:
                    overrides["BIOS.SerialNumber"] = "PHANTOM-" + ''.join(random.choice('0123456789ABCDEF') for _ in range(16))
                if need_cpu_serial:
                    overrides["CPU.Serial"] = ''.join(random.choice('0123456789ABCDEF') for _ in range(16))
                if need_processor_id:
                    overrides["CPU.ProcessorId"] = ''.join(random.choice('0123456789ABCDEF') for _ in range(16))
                if need_os_serial:
                    overrides["OS.SerialNumber"] = ''.join(random.choice(string.digits) for _ in range(20))
                if need_efi:
                    overrides["EFI.Number"] = str(uuid.uuid4()).upper()
                results["items"].append({"type": "Overrides", "after": overrides})
            return results
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restore_all(self) -> Dict[str, Any]:
        
        outcomes: Dict[str, Any] = {"success": True}
        try:
            original_guid = None
            if self.db_manager:
                original_guid = self.db_manager.get_setting("original_machine_guid", None)
            if original_guid:
                self._set_reg_value(reg.HKEY_LOCAL_MACHINE, self.MACHINE_GUID_KEY, self.MACHINE_GUID_VALUE, str(original_guid))
                if self.db_manager:
                    self.db_manager.save_change("hwid_restore", "spoofed", str(original_guid), category="system")
        except Exception as e:
            outcomes["success"] = False
            outcomes["hwid_error"] = str(e)

        try:
            mac_backups = {}
            if self.db_manager:
                mac_backups = self.db_manager.get_setting("mac_original_values", {})
            restored = []
            for guid, original in mac_backups.items():
                subkey = self._find_adapter_subkey_by_guid(guid)
                if subkey:
                    self._set_reg_value(reg.HKEY_LOCAL_MACHINE, subkey, "NetworkAddress", original if original else None)
                    restored.append(guid)
                    if self.db_manager:
                        self.db_manager.save_change("mac_restore", "spoofed", str(original), category="system")
            if restored:
                outcomes["mac_restored"] = restored
        except Exception as e:
            outcomes["success"] = False
            outcomes["mac_error"] = str(e)

        try:
            if self.db_manager:
                self.db_manager.save_settings({"spoof_overrides": {}})
                self.db_manager.save_change("overrides_clear", "active", "cleared", category="system")
        except Exception as e:
            outcomes["success"] = False
            outcomes["overrides_error"] = str(e)

        return outcomes
    def _get_mode(self) -> str:
        try:
            if self.db_manager:
                settings = self.db_manager.load_settings()
                return str(settings.get('spoof_mode', 'Temp')).lower()
        except Exception:
            pass
        return 'temp'

    def _schedule_revert_commands(self, commands: list[str]) -> None:
        try:
            base = self._ensure_backups_dir()
            script_path = os.path.join(base, 'phantomid_restore.cmd')
            # Ensure script exists with header
            if not os.path.exists(script_path) or os.path.getsize(script_path) == 0:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write('@echo off\n')
                    f.write('REM PhantomID temp restore script\n')
            # Append commands
            with open(script_path, 'a', encoding='utf-8') as fa:
                for cmd in commands:
                    fa.write(cmd + '\n')
                fa.write('exit /b 0\n')
            # Schedule on startup (admin path if possible)
            self.ensure_temp_restore_task(script_path)
        except Exception as e:
            self.logger.warning(f"Failed to schedule revert task: {e}")

    def ensure_temp_restore_task(self, script_path: Optional[str] = None) -> bool:
        try:
            base = self._ensure_backups_dir()
            sp = script_path or os.path.join(base, 'phantomid_restore.cmd')
            if not os.path.exists(sp):
                with open(sp, 'w', encoding='utf-8') as f:
                    f.write('@echo off\n')
                    f.write('REM PhantomID temp restore script\n')
                    f.write('exit /b 0\n')
            if self._is_admin():
                import subprocess
                subprocess.run(['schtasks', '/Delete', '/TN', 'PhantomID_TempRestore', '/F'], capture_output=True, text=True, shell=False)
                r = subprocess.run([
                    'schtasks', '/Create', '/SC', 'ONSTART', '/RL', 'HIGHEST', '/TN', 'PhantomID_TempRestore', '/TR', sp, '/F'
                ], capture_output=True, text=True, shell=False)
                return r.returncode == 0
            # Fallback: HKCU Run (no admin required)
            if reg is not None:
                try:
                    key = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, reg.KEY_SET_VALUE)
                except Exception:
                    key = reg.CreateKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
                reg.SetValueEx(key, 'PhantomID_TempRestore', 0, reg.REG_SZ, sp)
                reg.CloseKey(key)
                return True
            return False
        except Exception as e:
            self.logger.warning(f"Failed to ensure temp restore task: {e}")
            return False

    def regenerate_restore_script(self) -> bool:
        try:
            base = self._ensure_backups_dir()
            sp = os.path.join(base, 'phantomid_restore.cmd')
            settings = self.db_manager.load_settings() if self.db_manager else {}
            lines = ['@echo off', 'REM PhantomID temp restore script']
            # MachineGuid
            orig_guid = str(settings.get('original_machine_guid') or '')
            if orig_guid:
                lines.append('reg add "HKLM\\SOFTWARE\\Microsoft\\Cryptography" /v MachineGuid /t REG_SZ /d ' + orig_guid + ' /f')
            # MAC addresses
            mac_originals = settings.get('mac_original_values', {}) or {}
            mac_subkeys = settings.get('mac_subkeys', {}) or {}
            for guid, orig in mac_originals.items():
                subkey = mac_subkeys.get(guid)
                if not subkey:
                    continue
                hk_subkey = 'HKLM\\' + subkey
                if orig:
                    lines.append(f'reg add "{hk_subkey}" /v NetworkAddress /t REG_SZ /d {orig} /f')
                else:
                    lines.append(f'reg delete "{hk_subkey}" /v NetworkAddress /f')
            lines.append('exit /b 0')
            with open(sp, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines) + "\n")
            self.ensure_temp_restore_task(sp)
            return True
        except Exception as e:
            self.logger.warning(f"Failed to regenerate restore script: {e}")
            return False
