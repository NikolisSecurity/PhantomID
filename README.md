# PhantomID - Advanced Hardware ID Spoofer

PhantomID is a comprehensive hardware identification spoofing tool designed to help users modify their system identifiers and remove game bans. This enhanced version includes advanced database functionality, game-specific spoofing capabilities, and both CLI and GUI interfaces.

## Features

### 🔧 Enhanced Database System
- **SQLite Database**: Comprehensive tracking of all changes with detailed logging
- **Change History**: Complete audit trail of all spoofing operations
- **Backup Management**: Automatic backup creation and restoration
- **Statistics**: Detailed analytics of spoofing activities
- **Multi-table Schema**: Separate tables for system changes, game spoofs, backups, and configuration

### 🎮 Game Spoofing Capabilities
- **FiveM Spoofing**: Complete ban removal for GTA V roleplay servers
- **Fortnite Spoofing**: Epic Games anti-cheat bypass
- **Valorant Spoofing**: Riot Vanguard hardware ID modification
- **CS:GO Spoofing**: Steam hardware ID spoofing
- **Minecraft Spoofing**: Mojang/Microsoft account spoofing
- **Roblox Spoofing**: Platform-specific identifier modification
- **PUBG Spoofing**: Battlegrounds hardware ID spoofing
- **Apex Legends Spoofing**: EA anti-cheat bypass
- **Overwatch Spoofing**: Blizzard hardware ID modification
- **League of Legends**: Riot Games anti-cheat bypass

### 🖥️ System Spoofing
- **MAC Address Spoofing**: Network interface identifier modification
- **HWID Spoofing**: Hardware ID registry modification
- **IP Address Spoofing**: Network address spoofing
- **Serial Number Spoofing**: BIOS, CPU, and system serial modification
- **Registry Management**: Safe Windows registry operations
- **File Backup**: Automatic backup of modified files

### 🖥️ User Interfaces

#### Command Line Interface (CLI)
- **Comprehensive Commands**: Full-featured CLI with intuitive commands
- **Progress Indicators**: Real-time operation feedback
- **Color-coded Output**: Enhanced readability with colorama
- **Batch Operations**: Execute multiple spoofing operations
- **Configuration Management**: Easy configuration file management

#### Graphical User Interface (GUI)
- **Modern PyQt5 Design**: Professional and intuitive interface with enhanced aesthetics
- **Dark Theme**: Modern dark theme with customizable colors and gradients
- **Animated Elements**: Smooth animations and hover effects for better UX
- **Tabbed Interface**: Organized sections for different functionalities
- **Real-time Progress**: Live progress bars and status updates
- **System Tray Integration**: Minimize to system tray functionality
- **Multi-threading**: Non-blocking operations with background threads
- **GitHub Integration**: Direct links to repository and documentation
- **Automatic Updates**: Built-in updater from GitHub repository

### 🔧 Advanced Features
- **Configuration Management**: Comprehensive settings system
- **Error Handling**: Robust error handling and recovery
- **Logging System**: Detailed logging with multiple log levels
- **Backup/Restore**: Complete system state backup and restoration
- **Auto-backup**: Automatic backup before operations
- **Statistics**: Detailed usage statistics and analytics
- **GitHub Auto-Updater**: Automatic updates from GitHub repository
- **Enhanced GUI**: Modern styling with animations and effects
- **Cross-platform Compatibility**: Windows registry handling with proper imports

## Installation

### Prerequisites
- Python 3.7 or higher
- Windows 10/11 (Administrator privileges recommended)
- Internet connection for dependencies

### Quick Install
```bash
# Clone the repository
git clone https://github.com/NikolisSecurity/PhantomID.git
cd PhantomID

# Install dependencies
pip install -r requirements.txt

# Run the application
python phantomid.py
```

### Dependencies
```
# Core dependencies
colorama>=0.4.6
wmi>=1.5.1
requests>=2.31.0

# GUI Framework
PyQt5>=5.15.9
PyQt5-tools>=5.15.9

# System utilities
psutil>=5.9.5
pywin32>=306

# Network utilities
netifaces>=0.11.0
scapy>=2.5.0

# Additional utilities
pyinstaller>=5.13.0
python-dotenv>=1.0.0
cryptography>=41.0.4
```

## Usage

### GUI Interface
```bash
# Launch GUI (default)
python phantomid.py

# Explicitly launch GUI
python phantomid.py --gui
```

### CLI Interface
```bash
# Launch CLI
python phantomid.py --cli

# Get help
python phantomid.py --help

# System spoofing examples
python phantomid.py system --all                    # Spoof all system identifiers
python phantomid.py system --mac                    # Spoof MAC address
python phantomid.py system --hwid                   # Spoof HWID
python phantomid.py system --ip                     # Spoof IP address
python phantomid.py system --serial                 # Spoof serial numbers

# Game spoofing examples
python phantomid.py game --game fivem               # Spoof FiveM
python phantomid.py game --game fortnite            # Spoof Fortnite
python phantomid.py game --game valorant            # Spoof Valorant

# Backup operations
python phantomid.py backup --create                 # Create backup
python phantomid.py backup --restore 1              # Restore backup ID 1
python phantomid.py backup --list                   # List backups

# Configuration management
python phantomid.py config --set interface=Wi-Fi    # Set configuration
python phantomid.py config --get interface          # Get configuration
python phantomid.py config --list                   # List all configuration

# System information
python phantomid.py info --system                   # Show system info
python phantomid.py info --games                    # Show installed games
python phantomid.py info --database                 # Show database stats
```

## Database Schema

### Tables
- **changes**: System spoofing operations history
- **system_info**: Current system information snapshots
- **game_spoofs**: Game-specific spoofing records
- **backups**: Backup creation and restoration logs
- **configuration**: Application configuration settings
- **logs**: Detailed operation logs

### Key Features
- **Change Tracking**: Every modification is logged with before/after values
- **Rollback Support**: Easy restoration of previous states
- **Statistics**: Comprehensive analytics and reporting
- **Multi-user Support**: User-based operation tracking
- **Timestamp Management**: Precise timing for all operations

## Game Spoofing Details

### FiveM Spoofing
- Clears FiveM cache and configuration files
- Modifies registry entries for hardware identification
- Backs up original files before modification
- Removes ban data from local storage
- Updates machine identification tokens

### Fortnite Spoofing
- Epic Games launcher cache clearing
- Hardware ID registry modification
- Anti-cheat bypass implementation
- Account token refresh
- System fingerprint modification

### Valorant Spoofing
- Riot Vanguard hardware ID spoofing
- Registry key modification for anti-cheat
- System identifier randomization
- Network adapter spoofing
- BIOS information modification

## GitHub Auto-Updater

### Automatic Updates
PhantomID now includes a built-in automatic updater that fetches the latest version from your GitHub repository:

- **GitHub Integration**: Direct connection to `https://github.com/NikolisSecurity/PhantomID`
- **Version Checking**: Automatic comparison of local vs. remote versions
- **One-Click Updates**: Simple update process with progress indication
- **Backup Before Update**: Automatic backup of current version before updating
- **Update Notifications**: Visual notifications when updates are available
- **Manual Update Check**: Check for updates anytime via menu or sidebar button

### Update Process
1. Application checks for updates on startup
2. Compares local version with GitHub releases
3. Downloads update package if newer version available
4. Creates backup of current installation
5. Installs update automatically
6. Restarts application with new version

## Configuration

### Configuration File (config.json)
```json
{
    "interface": "Ethernet",
    "auto_backup": true,
    "backup_retention_days": 30,
    "log_level": "INFO",
    "database_path": "phantomid.db",
    "backup_path": "backups",
    "log_path": "logs",
    "game_settings": {
        "fivem": {
            "clear_cache": true,
            "modify_registry": true,
            "backup_files": true
        },
        "fortnite": {
            "clear_cache": true,
            "modify_registry": true,
            "backup_files": true
        }
    },
    "spoofing_settings": {
        "randomize_mac": true,
        "randomize_hwid": true,
        "randomize_serials": true,
        "preserve_network_settings": false
    },
    "gui_settings": {
        "theme": "dark",
        "window_size": "800x600",
        "auto_save": true,
        "show_notifications": true
    }
}
```

## Safety Features

### Backup System
- **Automatic Backups**: Created before every operation
- **Manual Backups**: User-initiated backup creation
- **Selective Restoration**: Restore specific components
- **Full System Restore**: Complete system state restoration
- **Backup Verification**: Integrity checking of backup files

### Error Handling
- **Operation Rollback**: Automatic rollback on failure
- **Error Recovery**: Graceful handling of system errors
- **Validation Checks**: Pre-operation system validation
- **Permission Management**: Administrator privilege handling
- **Network Safety**: Safe network configuration modification
- **Import Safety**: Proper Windows registry imports with fallback handling

## Troubleshooting

### Common Issues
1. **Administrator Privileges**: Run as administrator for full functionality
2. **Antivirus Detection**: Add to antivirus exclusions if flagged
3. **Network Issues**: Check network adapter settings after MAC spoofing
4. **Game Detection**: Ensure games are properly installed and detected
5. **Database Issues**: Check database file permissions and location
6. **GUI Launch Issues**: Ensure all PyQt5 dependencies are properly installed
7. **Update Failures**: Check internet connection for GitHub updater functionality

### Log Files
- Located in `logs/` directory
- Detailed operation logs with timestamps
- Error messages and stack traces
- System information snapshots
- Configuration change tracking

### Support
- Check GitHub issues for known problems
- Review log files for error details
- Ensure all dependencies are properly installed
- Verify system compatibility and requirements

## Security Considerations

### Data Protection
- All spoofing operations are logged locally
- No data is transmitted to external servers
- Encrypted configuration storage
- Secure backup file handling
- Privacy-focused design

### System Safety
- Safe registry modification practices
- File backup before modification
- Operation rollback capabilities
- System validation before changes
- Network configuration preservation

## License

This project is for educational and legitimate use only. Users are responsible for complying with all applicable laws and terms of service. The developers are not responsible for any misuse of this software.

## Disclaimer

This tool is designed for legitimate purposes such as:
- Privacy protection
- System testing and development
- Educational research
- Legitimate ban appeals
- Hardware troubleshooting

Use responsibly and in accordance with all applicable laws and service terms.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For support and questions:
- GitHub Issues: Report bugs and request features
- Documentation: Comprehensive usage guide
- Community: Join discussions and share experiences

---

**PhantomID** - Advanced Hardware ID Spoofer by Nikolis Security
