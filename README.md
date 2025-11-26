# 🛡️ PhantomID v2.5 — Hardware ID Spoofer

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows-blue?style=for-the-badge&logo=windows" alt="Platform">
  <img src="https://img.shields.io/badge/Language-Python-yellow?style=for-the-badge&logo=python" alt="Language">
</p>


<p align="center">
  <img src="https://img.shields.io/github/stars/NikolisSecurity/PhantomID?style=social">
  <img src="https://img.shields.io/github/v/release/NikolisSecurity/PhantomID">
  <img src="https://img.shields.io/github/downloads/NikolisSecurity/PhantomID/total">
  <a href="https://discord.gg/rfWdrewbAz" target="_blank">
    <img src="https://img.shields.io/badge/Discord-Join%20Server-7289DA?logo=discord&logoColor=white" alt="Join our Discord">
  </a>
</p>

## 📋 Overview
PhantomID is a Windows hardware ID spoofing toolkit focused on safe, reversible changes. It provides Temp and Perma modes, per‑game spoofing, and a modern PySide6 UI.

**What’s New in v2**
- Spoof Mode: Temp or Perma — switch in Settings.
- Win10 compatibility with robust path and registry handling.
- Monitor serial overrides (reported values) and improved RAM serial detection (PowerShell CIM fallback).
- Safer MAC + HWID spoofing with automatic backup, verification, and Temp revert scheduling.
- Unified themed popups; two UI themes:
  - Black/Red (Temp)
  - Neon Dark (Perma) with cyan accents
- Cleaner Game Spoofing UI (logo‑only buttons, no progress bar).
- Build script to generate a single `PhantomID.exe` via PyInstaller.

## ✨ Features
- Spoof Mode: Temp or Perma
- Spoof MAC Address (NIC `NetworkAddress`) with adapter restart
- Spoof Hardware ID (MachineGuid)
- Spoof IP Address (DHCP renew / static when safe)
- Reported SeriaSerial Overl Overrides: BIOS/CPU/Processor/OS/EFI (non‑destructive)
- Monitor rides (reported via serial checker)
- System Serial Checker with Win11 RAM serial fallback
- Per‑game spoofers: FiveM, Fortnite, Valorant, Minecraft, Roblox, CS:GO/CS2
- Backups, history database, and auto‑updater

## 🔧 Requirements
- Windows 10
- Python 3.8+
- Required Python packages:
  - PySide6
  - requests
  - wmi
  - pywin32
  - sqlite3 (included with Python)

## 📥 Installation
1. Clone or download this repository:

```bash
git clone https://github.com/NikolisSecurity/PhantomID.git
```

2. Install required packages:

```bash
pip install -r requirements.txt
 ```

3. Run the application:

```bash
python spoofer.py
 ```

## ❓ FAQ
- Does this bypass anti‑cheat? No guarantees. Use responsibly and respect TOS.
- Temp vs Perma?
  - Temp: Creates a restore script and startup hook; reverts MAC/HWID after reboot.
  - Perma: Applies changes and switches the UI to Neon Dark.
- Win11 support?
  - _No. Win11 paths and registry exports are not supported._
- Will this harm my PC?
  - Spoofs are guarded, logged, and backed up. Always create a system restore point.
## ⚠️ Warning
- Use this tool responsibly and at your own risk
- Modifying hardware identifiers may affect system functionality
- Some changes require administrator privileges
- Always create a system restore point before making changes
## 🔍 Troubleshooting
- Run as administrator for MAC/HWID changes and Temp startup hook creation.
- Temp revert verification:
  - Script: `backups/registry/phantomid_restore.cmd` contains reg commands and `exit /b 0`.
  - Startup hook: Task Scheduler `PhantomID_TempRestore` (admin) or HKCU Run value.
- RAM serials on Win11: if WMI is empty, PowerShell CIM fallback fills serials.
- If a spoof fails, use “Restore Original” or Dry Run first to preview changes.

## 📜 License
This software is provided as-is without any warranty. Use at your own risk.

## 📞 Contact
For issues or feature requests, please open an issue on the GitHub repository.

Made with ❤️ for privacy enthusiasts
