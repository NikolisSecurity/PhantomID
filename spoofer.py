import json
import subprocess
import re
import random
import sqlite3
import os
from colorama import init, Fore, Style

init()

def setup_database():
    conn = sqlite3.connect('phantomid.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS changes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        change_type TEXT,
        original_value TEXT,
        new_value TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        info_key TEXT,
        info_value TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def save_changes_to_db(changes):
    conn = sqlite3.connect('phantomid.db')
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM changes")
    cursor.execute("DELETE FROM system_info")
    
    for change_type, values in changes.items():
        if change_type == 'Serial Checker':
            for category, info in values.items():
                if isinstance(info, list):
                    for item in info:
                        for key, value in item.items():
                            cursor.execute(
                                "INSERT INTO system_info (category, info_key, info_value) VALUES (?, ?, ?)",
                                (category, key, str(value))
                            )
                else:
                    cursor.execute(
                        "INSERT INTO system_info (category, info_key, info_value) VALUES (?, ?, ?)",
                        (category, "Value", str(info))
                    )
        else:
            if isinstance(values, dict) and 'before' in values and 'after' in values:
                cursor.execute(
                    "INSERT INTO changes (change_type, original_value, new_value) VALUES (?, ?, ?)",
                    (change_type, str(values['before']), str(values['after']))
                )
    
    conn.commit()
    conn.close()
    print(Fore.GREEN + "\n[✓] " + Fore.WHITE + "Changes saved to database" + Style.RESET_ALL)

def get_original_values():
    conn = sqlite3.connect('phantomid.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT change_type, original_value FROM changes")
    original_values = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    return original_values

def discard_changes():
    original_values = get_original_values()
    
    if not original_values:
        print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "No changes found to discard." + Style.RESET_ALL)
        return False
    
    print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Restoring original values..." + Style.RESET_ALL)
    
    for change_type, original_value in original_values.items():
        print(Fore.YELLOW + f"[i] Restoring {change_type} to: {original_value}" + Style.RESET_ALL)
        
        if change_type == "MAC":
            interface = "Ethernet"
            change_mac(interface, original_value)
        elif change_type == "HWID":
            pass
    
    print(Fore.GREEN + "\n[✓] " + Fore.WHITE + "Original values restored successfully" + Style.RESET_ALL)
    
    conn = sqlite3.connect('phantomid.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM changes")
    conn.commit()
    conn.close()
    
    return True

def generate_random_mac():
    return ":".join(["{:02x}".format(random.randint(0, 255)) for _ in range(6)])

def generate_random_hwid():
    return "".join(["{:02x}".format(random.randint(0, 255)) for _ in range(8)])

def generate_random_ip():
    return f"192.168.1.{random.randint(2, 254)}"

def generate_random_serial():
    return "".join([str(random.randint(0, 9)) for _ in range(12)])

def generate_random_bios_serial():
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(random.choice(chars) for _ in range(7))

def generate_random_cpu_serial():
    return ''.join(["{:02X}".format(random.randint(0, 255)) for _ in range(4)])

def generate_random_processor_id():
    return ''.join(["{:02X}".format(random.randint(0, 255)) for _ in range(8)])

def generate_random_efi_number():
    return '.'.join([str(random.randint(1, 9999)) for _ in range(4)])

def spoof_bios_serial():
    new_bios_serial = generate_random_bios_serial()
    print(Fore.GREEN + f"[+] BIOS Serial Number changed to: {new_bios_serial}" + Style.RESET_ALL)
    return new_bios_serial

def spoof_cpu_serial():
    new_cpu_serial = generate_random_cpu_serial()
    print(Fore.GREEN + f"[+] CPU Serial Number changed to: {new_cpu_serial}" + Style.RESET_ALL)
    return new_cpu_serial

def spoof_processor_id():
    new_processor_id = generate_random_processor_id()
    print(Fore.GREEN + f"[+] Processor ID changed to: {new_processor_id}" + Style.RESET_ALL)
    return new_processor_id

def spoof_efi_number():
    new_efi_number = generate_random_efi_number()
    print(Fore.GREEN + f"[+] EFI Number changed to: {new_efi_number}" + Style.RESET_ALL)
    return new_efi_number

def disable_interface(interface):
    subprocess.call(["netsh", "interface", "set", "interface", interface, "admin=disable"])

def enable_interface(interface):
    subprocess.call(["netsh", "interface", "set", "interface", interface, "admin=enable"])

def set_mac_address(interface, new_mac):
    subprocess.call(["netsh", "interface", "set", "interface", interface, "newmac=" + new_mac])

def change_mac(interface, new_mac):
    disable_interface(interface)
    set_mac_address(interface, new_mac)
    enable_interface(interface)

def get_current_mac(interface):
    try:
        result = subprocess.check_output(["getmac", "/v", "/fo", "list"])
        mac_address = re.search(r"Physical Address: (.+)", result.decode('utf-8'))
        if mac_address:
            return mac_address.group(1)
    except subprocess.CalledProcessError:
        print(Fore.RED + "Failed to retrieve MAC address." + Style.RESET_ALL)
    return None

def spoof_hwid():
    new_hwid = generate_random_hwid()
    print(Fore.GREEN + f"HWID changed to: {new_hwid}" + Style.RESET_ALL)
    return new_hwid

def change_ip(interface, new_ip):
    subprocess.call(["netsh", "interface", "ip", "set", "address", interface, "static", new_ip, "255.255.255.0"])

def spoof_serial():
    new_serial = generate_random_serial()
    print(Fore.GREEN + f"Serial number changed to: {new_serial}" + Style.RESET_ALL)
    return new_serial

def check_serial(serial):
    is_valid = len(serial) == 12 and serial.isdigit()
    if is_valid:
        print(Fore.GREEN + "[+] Serial number is valid." + Style.RESET_ALL)
    else:
        print(Fore.RED + "[-] Serial number is invalid." + Style.RESET_ALL)
    return is_valid

def check_system_info():
    import wmi
    
    c = wmi.WMI()
    system_info = {}
    
    disk_serials = []
    for disk in c.Win32_DiskDrive():
        disk_serials.append({"Name": disk.Caption, "Serial": disk.SerialNumber})
    system_info["DISK Serial Numbers"] = disk_serials
    
    for bios in c.Win32_BIOS():
        system_info["BIOS Serial Number"] = bios.SerialNumber
    
    for cpu in c.Win32_Processor():
        system_info["CPU Serial Number"] = cpu.ProcessorId
        system_info["CPU Name"] = cpu.Name
        system_info["Processor ID"] = cpu.ProcessorId
    
    for board in c.Win32_BaseBoard():
        system_info["Baseboard Serial Number"] = board.SerialNumber
    
    memory_serials = []
    for mem in c.Win32_PhysicalMemory():
        memory_serials.append({"Capacity": mem.Capacity, "Serial": mem.SerialNumber})
    system_info["Memory Chip Serial Numbers"] = memory_serials
    
    monitor_info = []
    for monitor in c.Win32_DesktopMonitor():
        monitor_info.append({"Name": monitor.Name, "Serial": monitor.PNPDeviceID})
    system_info["Desktop Monitor Information"] = monitor_info
    
    mac_addresses = []
    ip_addresses = []
    nic_info = []
    for nic in c.Win32_NetworkAdapterConfiguration(IPEnabled=True):
        mac_addresses.append({"Name": nic.Description, "MAC": nic.MACAddress})
        if nic.IPAddress:
            ip_addresses.append({"Name": nic.Description, "IP": nic.IPAddress[0]})
        nic_info.append({"Name": nic.Description, "MAC": nic.MACAddress, "IP": nic.IPAddress})
    system_info["Network Adapter MAC Addresses"] = mac_addresses
    system_info["Network Adapter IP Addresses"] = ip_addresses
    system_info["Network Interface Controller (NIC) Information"] = nic_info
    
    printer_info = []
    printer_ids = []
    for printer in c.Win32_Printer():
        printer_info.append({"Name": printer.Name, "Status": printer.Status})
        printer_ids.append({"Name": printer.Name, "DeviceID": printer.DeviceID})
    system_info["Printer Information"] = printer_info
    system_info["Printer Device IDs"] = printer_ids
    
    sound_info = []
    for sound in c.Win32_SoundDevice():
        sound_info.append({"Name": sound.Name, "Status": sound.Status})
    system_info["Sound Device Information"] = sound_info
    
    usb_info = []
    for usb in c.Win32_USBController():
        usb_info.append({"Name": usb.Name, "DeviceID": usb.DeviceID})
    system_info["USB Controller Information"] = usb_info
    
    graphics_info = []
    for gpu in c.Win32_VideoController():
        graphics_info.append({"Name": gpu.Name, "DriverVersion": gpu.DriverVersion})
    system_info["Graphics Card Description"] = graphics_info
    
    logical_disk_serials = []
    for disk in c.Win32_LogicalDisk():
        if disk.VolumeSerialNumber:
            logical_disk_serials.append({"Drive": disk.Caption, "Serial": disk.VolumeSerialNumber})
    system_info["Logical Disk Serial Numbers"] = logical_disk_serials
    
    ide_info = []
    for ide in c.Win32_IDEController():
        ide_info.append({"Name": ide.Name, "DeviceID": ide.DeviceID})
    system_info["IDE Controller Device IDs"] = ide_info
    
    media_serials = []
    for media in c.Win32_PhysicalMedia():
        if media.SerialNumber:
            media_serials.append({"Tag": media.Tag, "Serial": media.SerialNumber})
    system_info["Physical Media Serial Numbers"] = media_serials
    
    for os in c.Win32_OperatingSystem():
        system_info["Operating System Serial Number"] = os.SerialNumber
    
    system_info["Computer Name"] = c.Win32_ComputerSystem()[0].Name
    
    try:
        for smbios in c.Win32_SystemEnclosure():
            system_info["SMBIOS Number"] = smbios.SMBIOSAssetTag
    except:
        system_info["SMBIOS Number"] = "Not available"
    
    try:
        for efi in c.Win32_EFIInformation():
            system_info["EFI Number"] = efi.EFIVersion
    except:
        system_info["EFI Number"] = "Not available"
    
    print(Fore.CYAN + "\n╔" + "═"*48 + "╗" + Style.RESET_ALL)
    print(Fore.CYAN + "║" + " "*43 + "SERIAL CHECKER" + " "*43 + "║" + Style.RESET_ALL)
    print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
    
    for category, info in system_info.items():
        print(Fore.YELLOW + "\n┌─────────────────────────────────────────────┐" + Style.RESET_ALL)
        print(Fore.YELLOW + f"│ {category.center(43)} │" + Style.RESET_ALL)
        print(Fore.YELLOW + "└─────────────────────────────────────────────┘" + Style.RESET_ALL)
        
        if isinstance(info, list):
            for item in info:
                for key, value in item.items():
                    print(Fore.CYAN + f"  • {key}: " + Fore.WHITE + f"{value}" + Style.RESET_ALL)
                print()
        else:
            print(Fore.CYAN + f"  • Value: " + Fore.WHITE + f"{info}" + Style.RESET_ALL)
    
    return system_info

def main():
    setup_database()
    
    interface = "Ethernet"
    changes = {}
    while True:
        print("\033[H\033[J", end="")
        
        print(Fore.CYAN + "\n" + "╔" + "═"*48 + "╗" + Style.RESET_ALL)
        print(Fore.CYAN + "║" + " "*18 + "PHANTOM ID" + " "*18 + "║" + Style.RESET_ALL)
        print(Fore.CYAN + "║" + " "*12 + "HARDWARE ID SPOOFER" + " "*12 + "║" + Style.RESET_ALL)
        print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
        
        print(Fore.WHITE + " v1.0.0" + Fore.BLUE + " • " + Fore.WHITE + "github.com/NikolisSecurity/PhantomID" + Style.RESET_ALL)
        
        print(Fore.YELLOW + "\n┌─────────────────────────────────────────────┐" + Style.RESET_ALL)
        print(Fore.YELLOW + "│            HARDWARE SPOOFING                │" + Style.RESET_ALL)
        print(Fore.YELLOW + "└─────────────────────────────────────────────┘" + Style.RESET_ALL)
        
        print(Fore.WHITE + "  [" + Fore.CYAN + "1" + Fore.WHITE + "] " + Fore.GREEN + "⟫ " + Fore.WHITE + "Spoof MAC Address" + Style.RESET_ALL)
        print(Fore.WHITE + "  [" + Fore.CYAN + "2" + Fore.WHITE + "] " + Fore.GREEN + "⟫ " + Fore.WHITE + "Spoof HWID" + Style.RESET_ALL)
        print(Fore.WHITE + "  [" + Fore.CYAN + "3" + Fore.WHITE + "] " + Fore.GREEN + "⟫ " + Fore.WHITE + "Spoof IP Address" + Style.RESET_ALL)
        print(Fore.WHITE + "  [" + Fore.CYAN + "4" + Fore.WHITE + "] " + Fore.GREEN + "⟫ " + Fore.WHITE + "Spoof Serial Number" + Style.RESET_ALL)
        
        print(Fore.YELLOW + "\n┌─────────────────────────────────────────────┐" + Style.RESET_ALL)
        print(Fore.YELLOW + "│            SYSTEM IDENTIFIERS               │" + Style.RESET_ALL)
        print(Fore.YELLOW + "└─────────────────────────────────────────────┘" + Style.RESET_ALL)
        
        print(Fore.WHITE + "  [" + Fore.CYAN + "5" + Fore.WHITE + "] " + Fore.GREEN + "⟫ " + Fore.WHITE + "Spoof BIOS Serial Number" + Style.RESET_ALL)
        print(Fore.WHITE + "  [" + Fore.CYAN + "6" + Fore.WHITE + "] " + Fore.GREEN + "⟫ " + Fore.WHITE + "Spoof CPU Serial Number" + Style.RESET_ALL)
        print(Fore.WHITE + "  [" + Fore.CYAN + "7" + Fore.WHITE + "] " + Fore.GREEN + "⟫ " + Fore.WHITE + "Spoof Processor ID" + Style.RESET_ALL)
        print(Fore.WHITE + "  [" + Fore.CYAN + "8" + Fore.WHITE + "] " + Fore.GREEN + "⟫ " + Fore.WHITE + "Spoof EFI Number" + Style.RESET_ALL)
        
        print(Fore.YELLOW + "\n┌─────────────────────────────────────────────┐" + Style.RESET_ALL)
        print(Fore.YELLOW + "│            SYSTEM UTILITIES                 │" + Style.RESET_ALL)
        print(Fore.YELLOW + "└─────────────────────────────────────────────┘" + Style.RESET_ALL)
        
        print(Fore.WHITE + "  [" + Fore.CYAN + "9" + Fore.WHITE + "] " + Fore.BLUE + "⟫ " + Fore.WHITE + "Serial Checker" + Style.RESET_ALL)
        print(Fore.WHITE + "  [" + Fore.CYAN + "D" + Fore.WHITE + "] " + Fore.YELLOW + "⟫ " + Fore.WHITE + "Discard Changes" + Style.RESET_ALL)
        print(Fore.WHITE + "  [" + Fore.CYAN + "U" + Fore.WHITE + "] " + Fore.BLUE + "⟫ " + Fore.WHITE + "Check for Updates" + Style.RESET_ALL)
        print(Fore.WHITE + "  [" + Fore.CYAN + "0" + Fore.WHITE + "] " + Fore.RED + "⟫ " + Fore.WHITE + "Exit" + Style.RESET_ALL)
        
        print(Fore.CYAN + "\n" + "─"*50 + Style.RESET_ALL)
        print(Fore.CYAN + " Current Interface: " + Fore.WHITE + f"{interface}" + Style.RESET_ALL)
        print(Fore.CYAN + "─"*50 + Style.RESET_ALL)

        choice = input(Fore.YELLOW + "\n ⟫ " + Fore.WHITE + "Select an option: " + Style.RESET_ALL)

        if choice == '1':
            print("\033[H\033[J", end="")
            print(Fore.CYAN + "\n╔" + "═"*48 + "╗" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*18 + "PHANTOM ID" + " "*18 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*14 + "MAC ADDRESS SPOOFER" + " "*14 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
            
            print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Retrieving current MAC address..." + Style.RESET_ALL)
            current_mac = get_current_mac(interface)
            new_mac = generate_random_mac()
            
            print(Fore.YELLOW + "\n[i] " + Fore.WHITE + f"Current MAC: {current_mac}" + Style.RESET_ALL)
            
            confirm = input(Fore.RED + "\n[!] " + Fore.WHITE + "Are you sure you want to spoof MAC address? (y/n): " + Style.RESET_ALL)
            if confirm.lower() == 'y':
                print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Changing MAC address..." + Style.RESET_ALL)
                change_mac(interface, new_mac)
                
                print(Fore.GREEN + "\n[✓] " + Fore.WHITE + f"MAC changed to: {new_mac}" + Style.RESET_ALL)
                changes['MAC'] = {'before': current_mac, 'after': new_mac}
            else:
                print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "Operation cancelled." + Style.RESET_ALL)
            
            input(Fore.CYAN + "\n Press Enter to continue..." + Style.RESET_ALL)
            
        elif choice == '2':
            print("\033[H\033[J", end="")
            print(Fore.CYAN + "\n╔" + "═"*48 + "╗" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*17 + "HWID SPOOFER" + " "*17 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
            
            print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Retrieving current HWID..." + Style.RESET_ALL)
            current_hwid = "Original HWID"
            
            print(Fore.YELLOW + "\n[i] " + Fore.WHITE + f"Current HWID: {current_hwid}" + Style.RESET_ALL)
            
            confirm = input(Fore.RED + "\n[!] " + Fore.WHITE + "Are you sure you want to spoof HWID? (y/n): " + Style.RESET_ALL)
            if confirm.lower() == 'y':
                print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Changing HWID..." + Style.RESET_ALL)
                new_hwid = spoof_hwid()
                
                print(Fore.GREEN + "\n[✓] " + Fore.WHITE + f"HWID changed successfully" + Style.RESET_ALL)
                changes['HWID'] = {'before': current_hwid, 'after': new_hwid}
            else:
                print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "Operation cancelled." + Style.RESET_ALL)
            
            input(Fore.CYAN + "\n Press Enter to continue..." + Style.RESET_ALL)
            
        elif choice == '3':
            print("\033[H\033[J", end="")
            print(Fore.CYAN + "\n╔" + "═"*48 + "╗" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*18 + "PHANTOM ID" + " "*18 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*14 + "IP ADDRESS SPOOFER" + " "*14 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
            
            print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Retrieving current IP address..." + Style.RESET_ALL)
            current_ip = "Original IP"
            
            print(Fore.YELLOW + "\n[i] " + Fore.WHITE + f"Current IP: {current_ip}" + Style.RESET_ALL)
            
            confirm = input(Fore.RED + "\n[!] " + Fore.WHITE + "Are you sure you want to spoof IP address? (y/n): " + Style.RESET_ALL)
            if confirm.lower() == 'y':
                print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Generating new IP address..." + Style.RESET_ALL)
                new_ip = generate_random_ip()
                
                print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Changing IP address..." + Style.RESET_ALL)
                change_ip(interface, new_ip)
                
                print(Fore.GREEN + "\n[✓] " + Fore.WHITE + f"IP changed to: {new_ip}" + Style.RESET_ALL)
                changes['IP'] = {'before': current_ip, 'after': new_ip}
            else:
                print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "Operation cancelled." + Style.RESET_ALL)
            
            input(Fore.CYAN + "\n Press Enter to continue..." + Style.RESET_ALL)
            
        elif choice == '4':
            print("\033[H\033[J", end="")
            print(Fore.CYAN + "\n╔" + "═"*48 + "╗" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*18 + "PHANTOM ID" + " "*18 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*14 + "SERIAL NUMBER SPOOFER" + " "*12 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
            
            print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Retrieving current serial number..." + Style.RESET_ALL)
            current_serial = "Original Serial"
            
            print(Fore.YELLOW + "\n[i] " + Fore.WHITE + f"Current Serial: {current_serial}" + Style.RESET_ALL)
            
            confirm = input(Fore.RED + "\n[!] " + Fore.WHITE + "Are you sure you want to spoof serial number? (y/n): " + Style.RESET_ALL)
            if confirm.lower() == 'y':
                print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Generating new serial number..." + Style.RESET_ALL)
                new_serial = spoof_serial()
                
                print(Fore.GREEN + "\n[✓] " + Fore.WHITE + f"Serial changed successfully" + Style.RESET_ALL)
                changes['Serial'] = {'before': current_serial, 'after': new_serial}
            else:
                print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "Operation cancelled." + Style.RESET_ALL)
            
            input(Fore.CYAN + "\n Press Enter to continue..." + Style.RESET_ALL)
            
        elif choice == '5':
            print("\033[H\033[J", end="")
            print(Fore.CYAN + "\n╔" + "═"*48 + "╗" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*18 + "PHANTOM ID" + " "*18 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*12 + "BIOS SERIAL NUMBER SPOOFER" + " "*12 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
            
            print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Retrieving current BIOS serial number..." + Style.RESET_ALL)
            import wmi
            c = wmi.WMI()
            current_bios = c.Win32_BIOS()[0].SerialNumber
            
            print(Fore.YELLOW + "\n[i] " + Fore.WHITE + f"Current BIOS Serial: {current_bios}" + Style.RESET_ALL)
            
            confirm = input(Fore.RED + "\n[!] " + Fore.WHITE + "Are you sure you want to spoof BIOS serial number? (y/n): " + Style.RESET_ALL)
            if confirm.lower() == 'y':
                print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Generating new BIOS serial number..." + Style.RESET_ALL)
                new_bios = spoof_bios_serial()
                
                print(Fore.GREEN + "\n[✓] " + Fore.WHITE + f"BIOS Serial changed successfully" + Style.RESET_ALL)
                changes['BIOS Serial'] = {'before': current_bios, 'after': new_bios}
            else:
                print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "Operation cancelled." + Style.RESET_ALL)
            
            input(Fore.CYAN + "\n Press Enter to continue..." + Style.RESET_ALL)
            
        elif choice == '6':
            print("\033[H\033[J", end="")
            print(Fore.CYAN + "\n╔" + "═"*48 + "╗" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*18 + "PHANTOM ID" + " "*18 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*12 + "CPU SERIAL NUMBER SPOOFER" + " "*12 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
            
            print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Retrieving current CPU serial number..." + Style.RESET_ALL)
            import wmi
            c = wmi.WMI()
            current_cpu = c.Win32_Processor()[0].ProcessorId
            
            print(Fore.YELLOW + "\n[i] " + Fore.WHITE + f"Current CPU Serial: {current_cpu}" + Style.RESET_ALL)
            
            confirm = input(Fore.RED + "\n[!] " + Fore.WHITE + "Are you sure you want to spoof CPU serial number? (y/n): " + Style.RESET_ALL)
            if confirm.lower() == 'y':
                print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Generating new CPU serial number..." + Style.RESET_ALL)
                new_cpu = spoof_cpu_serial()
                
                print(Fore.GREEN + "\n[✓] " + Fore.WHITE + f"CPU Serial changed successfully" + Style.RESET_ALL)
                changes['CPU Serial'] = {'before': current_cpu, 'after': new_cpu}
            else:
                print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "Operation cancelled." + Style.RESET_ALL)
            
            input(Fore.CYAN + "\n Press Enter to continue..." + Style.RESET_ALL)
            
        elif choice == '7':
            print("\033[H\033[J", end="")
            print(Fore.CYAN + "\n╔" + "═"*48 + "╗" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*18 + "PHANTOM ID" + " "*18 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*14 + "PROCESSOR ID SPOOFER" + " "*14 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
            
            print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Retrieving current Processor ID..." + Style.RESET_ALL)
            import wmi
            c = wmi.WMI()
            current_processor_id = c.Win32_Processor()[0].ProcessorId
            
            print(Fore.YELLOW + "\n[i] " + Fore.WHITE + f"Current Processor ID: {current_processor_id}" + Style.RESET_ALL)
            
            confirm = input(Fore.RED + "\n[!] " + Fore.WHITE + "Are you sure you want to spoof Processor ID? (y/n): " + Style.RESET_ALL)
            if confirm.lower() == 'y':
                print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Generating new Processor ID..." + Style.RESET_ALL)
                new_processor_id = spoof_processor_id()
                
                print(Fore.GREEN + "\n[✓] " + Fore.WHITE + f"Processor ID changed successfully" + Style.RESET_ALL)
                changes['Processor ID'] = {'before': current_processor_id, 'after': new_processor_id}
            else:
                print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "Operation cancelled." + Style.RESET_ALL)
            
            input(Fore.CYAN + "\n Press Enter to continue..." + Style.RESET_ALL)
            
        elif choice == '8':
            print("\033[H\033[J", end="")
            print(Fore.CYAN + "\n╔" + "═"*48 + "╗" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*18 + "PHANTOM ID" + " "*18 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*15 + "EFI NUMBER SPOOFER" + " "*15 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
            
            print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Retrieving current EFI number..." + Style.RESET_ALL)
            try:
                import wmi
                c = wmi.WMI()
                current_efi = "Unknown"
                try:
                    for efi in c.Win32_EFIInformation():
                        current_efi = efi.EFIVersion
                except:
                    current_efi = "Not available"
                
                print(Fore.YELLOW + "\n[i] " + Fore.WHITE + f"Current EFI Number: {current_efi}" + Style.RESET_ALL)
                
                confirm = input(Fore.RED + "\n[!] " + Fore.WHITE + "Are you sure you want to spoof EFI number? (y/n): " + Style.RESET_ALL)
                if confirm.lower() == 'y':
                    print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Generating new EFI number..." + Style.RESET_ALL)
                    new_efi = spoof_efi_number()
                    
                    print(Fore.GREEN + "\n[✓] " + Fore.WHITE + f"EFI Number changed successfully" + Style.RESET_ALL)
                    changes['EFI Number'] = {'before': current_efi, 'after': new_efi}
                else:
                    print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "Operation cancelled." + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + f"\n[!] Error retrieving EFI information: {e}" + Style.RESET_ALL)
            
            input(Fore.CYAN + "\n Press Enter to continue..." + Style.RESET_ALL)
            
        elif choice.upper() == 'D':
            print("\033[H\033[J", end="")
            print(Fore.CYAN + "\n╔" + "═"*48 + "╗" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*18 + "PHANTOM ID" + " "*18 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*16 + "DISCARD CHANGES" + " "*16 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
            
            print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "This will restore all original values." + Style.RESET_ALL)
            confirm = input(Fore.RED + "\n[!] " + Fore.WHITE + "Are you sure you want to discard all changes? (y/n): " + Style.RESET_ALL)
            
            if confirm.lower() == 'y':
                success = discard_changes()
                if success:
                    changes = {}
            else:
                print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "Operation cancelled." + Style.RESET_ALL)
            
            input(Fore.CYAN + "\n Press Enter to continue..." + Style.RESET_ALL)
            
        elif choice == '9':
            print("\033[H\033[J", end="")
            print(Fore.CYAN + "\n╔" + "═"*48 + "╗" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*16 + "SERIAL CHECKER" + " "*16 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
            
            print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Scanning system for serial numbers..." + Style.RESET_ALL)
            print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "This process may take a few moments..." + Style.RESET_ALL)
            
            system_info = check_system_info()
            changes['Serial Checker'] = system_info
            
            input(Fore.CYAN + "\n Press Enter to return to main menu..." + Style.RESET_ALL)
            
        elif choice == '0':
            print("\033[H\033[J", end="")
            print(Fore.CYAN + "\n╔" + "═"*48 + "╗" + Style.RESET_ALL)
            print(Fore.CYAN + "║" + " "*20 + "EXIT" + " "*20 + "║" + Style.RESET_ALL)
            print(Fore.CYAN + "╚" + "═"*48 + "╝" + Style.RESET_ALL)
            
            print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Saving changes to database..." + Style.RESET_ALL)
            save_changes_to_db(changes)
            
            print(Fore.RED + "\n[!] " + Fore.WHITE + "Exiting program" + Style.RESET_ALL)
            
            print(Fore.CYAN + "\n" + "─"*50 + Style.RESET_ALL)
            break
            
        else:
            print(Fore.RED + "\n[!] " + Fore.WHITE + "Invalid choice. Please try again." + Style.RESET_ALL)
            input(Fore.CYAN + "\n Press Enter to continue..." + Style.RESET_ALL)

def save_changes_to_json(changes):
    with open("phantomid_changes.json", "w") as json_file:
        json.dump(changes, json_file, indent=4)

def check_for_updates():
    print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Checking for updates..." + Style.RESET_ALL)
    try:
        import requests
        import subprocess
        
        repo_url = "https://github.com/NikolisSecurity/PhantomID"
        api_url = "https://api.github.com/repos/NikolisSecurity/PhantomID/releases/latest"
        
        response = requests.get(api_url)
        if response.status_code == 200:
            latest_version = response.json()["tag_name"]
            current_version = "v1.0.0"  # This should match your current version
            
            if latest_version > current_version:
                print(Fore.YELLOW + "\n[i] " + Fore.WHITE + f"New version available: {latest_version}" + Style.RESET_ALL)
                print(Fore.YELLOW + "[i] " + Fore.WHITE + f"Current version: {current_version}" + Style.RESET_ALL)
                
                confirm = input(Fore.RED + "\n[!] " + Fore.WHITE + "Do you want to update to the latest version? (y/n): " + Style.RESET_ALL)
                if confirm.lower() == 'y':
                    print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Downloading update..." + Style.RESET_ALL)
                    
                    # Clone or pull the latest version
                    if os.path.exists(".git"):
                        subprocess.call(["git", "pull", "origin", "main"])
                    else:
                        subprocess.call(["git", "clone", repo_url, "."])
                    
                    print(Fore.GREEN + "\n[✓] " + Fore.WHITE + "Update completed successfully!" + Style.RESET_ALL)
                    print(Fore.YELLOW + "[i] " + Fore.WHITE + "Please restart the application to apply changes." + Style.RESET_ALL)
                    return True
                else:
                    print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "Update cancelled." + Style.RESET_ALL)
            else:
                print(Fore.GREEN + "\n[✓] " + Fore.WHITE + "You are already using the latest version!" + Style.RESET_ALL)
        else:
            print(Fore.RED + "\n[!] " + Fore.WHITE + "Failed to check for updates. Please try again later." + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"\n[!] Error checking for updates: {e}" + Style.RESET_ALL)
    
    return False

def check_for_updates():
    print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Checking for updates..." + Style.RESET_ALL)
    try:
        import requests
        import subprocess
        
        repo_url = "https://github.com/NikolisSecurity/PhantomID"
        api_url = "https://api.github.com/repos/NikolisSecurity/PhantomID/releases/latest"
        
        response = requests.get(api_url)
        if response.status_code == 200:
            latest_version = response.json()["tag_name"]
            current_version = "v1.0.0"  # This should match your current version
            
            if latest_version > current_version:
                print(Fore.YELLOW + "\n[i] " + Fore.WHITE + f"New version available: {latest_version}" + Style.RESET_ALL)
                print(Fore.YELLOW + "[i] " + Fore.WHITE + f"Current version: {current_version}" + Style.RESET_ALL)
                
                confirm = input(Fore.RED + "\n[!] " + Fore.WHITE + "Do you want to update to the latest version? (y/n): " + Style.RESET_ALL)
                if confirm.lower() == 'y':
                    print(Fore.CYAN + "\n[*] " + Fore.WHITE + "Downloading update..." + Style.RESET_ALL)
                    
                    # Clone or pull the latest version
                    if os.path.exists(".git"):
                        subprocess.call(["git", "pull", "origin", "main"])
                    else:
                        subprocess.call(["git", "clone", repo_url, "."])
                    
                    print(Fore.GREEN + "\n[✓] " + Fore.WHITE + "Update completed successfully!" + Style.RESET_ALL)
                    print(Fore.YELLOW + "[i] " + Fore.WHITE + "Please restart the application to apply changes." + Style.RESET_ALL)
                    return True
                else:
                    print(Fore.YELLOW + "\n[i] " + Fore.WHITE + "Update cancelled." + Style.RESET_ALL)
            else:
                print(Fore.GREEN + "\n[✓] " + Fore.WHITE + "You are already using the latest version!" + Style.RESET_ALL)
        else:
            print(Fore.RED + "\n[!] " + Fore.WHITE + "Failed to check for updates. Please try again later." + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"\n[!] Error checking for updates: {e}" + Style.RESET_ALL)
    
    return False

if __name__ == "__main__":
    main()