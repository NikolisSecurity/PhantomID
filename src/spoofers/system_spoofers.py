import logging
import uuid
import random
import string
import time
import json
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

        guid = adapter["setting_id"]
        subkey = self._find_adapter_subkey_by_guid(guid)
        if subkey is None:
            result["error"] = "Adapter registry subkey not found"
            return result

        original = self._get_reg_value(reg.HKEY_LOCAL_MACHINE, subkey, "NetworkAddress")
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
            self.db_manager.save_settings({"mac_original_values": mac_backups})

        try:
            if wmi is not None and adapter.get("wmi_obj") is not None:
                nic = adapter["wmi_obj"]
                try:
                    nic.Disable()
                    time.sleep(1.5)
                except Exception:
                    pass
                try:
                    nic.Enable()
                except Exception:
                    pass
        except Exception:
            pass

        result.update({"success": True, "before": original, "after": new_mac, "adapter_guid": guid, "registry_key": subkey})
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
        try:
            original = self._get_reg_value(reg.HKEY_LOCAL_MACHINE, self.MACHINE_GUID_KEY, self.MACHINE_GUID_VALUE)
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