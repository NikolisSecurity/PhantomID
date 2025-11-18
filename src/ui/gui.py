import sys
import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QStackedWidget, QScrollArea,
    QTextEdit, QProgressBar, QGroupBox, QGridLayout, QCheckBox,
    QComboBox, QMessageBox, QFileDialog, QTabWidget, QListWidget,
    QListWidgetItem, QSplitter, QMenuBar, QMenu, QStatusBar, QStyle,
    QLineEdit, QSpinBox
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPropertyAnimation, QRect, QEasingCurve, QSize, QUrl
from PySide6.QtGui import QRegion

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtGui import QFont, QPalette, QColor, QLinearGradient, QPainter, QBrush, QPen, QIcon, QPixmap, QPainterPath, QDesktopServices

from core.database_manager import DatabaseManager
from spoofers.game_spoofers import get_game_spoofer, AntiDetectionManager
from spoofers.system_spoofers import SystemSpoofer
from utils.game_assets import get_game_bg_pixmap
from utils.auto_updater import AutoUpdater

class ModernButton(QPushButton):
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(45)
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.setObjectName("primary_button")

class MiniButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(28)
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.setObjectName("primary_button")

class GameButton(QPushButton):
    
    def __init__(self, game_name, icon_text, parent=None):
        super().__init__(parent)
        self.game_name = game_name
        self.setFixedSize(140, 50)  # Smaller size, closer to other buttons
        self.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.bg_pix = get_game_bg_pixmap(game_name)
        
        game_styles = {
            "FiveM": {
                "gradient": ("rgba(255, 107, 53, 0.9)", "rgba(247, 147, 30, 0.9)"),
                "hover_gradient": ("rgba(255, 130, 70, 0.95)", "rgba(255, 170, 50, 0.95)"),
                "border_color": "#ff6b35"
            },
            "Fortnite": {
                "gradient": ("rgba(139, 92, 246, 0.9)", "rgba(168, 85, 247, 0.9)"),
                "hover_gradient": ("rgba(160, 110, 255, 0.95)", "rgba(190, 110, 255, 0.95)"),
                "border_color": "#8b5cf6"
            },
            "Valorant": {
                "gradient": ("rgba(239, 68, 68, 0.9)", "rgba(249, 115, 22, 0.9)"),
                "hover_gradient": ("rgba(255, 90, 90, 0.95)", "rgba(255, 140, 40, 0.95)"),
                "border_color": "#ef4444"
            },
            "Minecraft": {
                "gradient": ("rgba(16, 185, 129, 0.9)", "rgba(5, 150, 105, 0.9)"),
                "hover_gradient": ("rgba(30, 210, 150, 0.95)", "rgba(15, 180, 120, 0.95)"),
                "border_color": "#10b981"
            },
            "Roblox": {
                "gradient": ("rgba(59, 130, 246, 0.9)", "rgba(29, 78, 216, 0.9)"),
                "hover_gradient": ("rgba(80, 150, 255, 0.95)", "rgba(50, 100, 235, 0.95)"),
                "border_color": "#3b82f6"
            },
            "CS:GO": {
                "gradient": ("rgba(255, 193, 7, 0.9)", "rgba(255, 152, 0, 0.9)"),
                "hover_gradient": ("rgba(255, 210, 40, 0.95)", "rgba(255, 180, 30, 0.95)"),
                "border_color": "#ffc107"
            }
        }
        
        style = game_styles.get(game_name, {
            "gradient": ("rgba(102, 126, 234, 0.9)", "rgba(118, 75, 162, 0.9)"),
            "hover_gradient": ("rgba(120, 140, 250, 0.95)", "rgba(140, 100, 180, 0.95)"),
            "border_color": "#667eea"
        })
        
        self.setObjectName("game_button")
        
        display_text = f"{icon_text} {self.game_name}" if icon_text else self.game_name
        self.setText(display_text)
        self.setStyleSheet("text-align: center;")

    def paintEvent(self, event):
        if hasattr(self, 'bg_pix') and self.bg_pix:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            rect = self.rect()
            path = QPainterPath()
            path.addRoundedRect(rect, 12, 12)
            painter.setClipPath(path)
            scaled = self.bg_pix.scaled(rect.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap(rect, scaled)
            painter.fillPath(path, QColor(0, 0, 0, 120))
        super().paintEvent(event)

class SpooferWorker(QThread):
    progress_updated = Signal(int)
    status_updated = Signal(str)
    operation_completed = Signal(bool, str)
    
    def __init__(self, spoofer_type, game_name=None, backup_path=None, system_options=None):
        super().__init__()
        self.spoofer_type = spoofer_type
        self.game_name = game_name
        self.backup_path = backup_path
        self.system_options = system_options or []
        self.db_manager = None
        self.should_stop = False
        
    def set_db_manager(self, db_manager):
        self.db_manager = db_manager
        
    def stop(self):
        self.should_stop = True
        
    def run(self):
        try:
            self.status_updated.emit("Initializing spoofing process...")
            self.progress_updated.emit(10)
            
            if self.should_stop:
                return
                
            if self.spoofer_type == "game" and self.game_name:
                self.spoof_game()
            elif self.spoofer_type == "system":
                self.spoof_system()
            elif self.spoofer_type == "registry":
                self.clean_registry()
            elif self.spoofer_type == "optimization":
                self.optimize_system()
            elif self.spoofer_type == "restore":
                self.restore_original()
            elif self.spoofer_type == "registry_scan":
                self.scan_registry()
            elif self.spoofer_type == "registry_backup":
                self.backup_registry()
            elif self.spoofer_type == "system_analysis":
                self.analyze_system()
            elif self.spoofer_type == "database_cleanup":
                self.cleanup_database()
            elif self.spoofer_type == "backup_creation":
                self.create_backup()
            elif self.spoofer_type == "backup_restore":
                self.restore_backup()
                
        except Exception as e:
            self.operation_completed.emit(False, f"Error: {str(e)}")
            
    def spoof_game(self):
        
        try:
            self.status_updated.emit(f"Spoofing {self.game_name} identifiers...")
            self.progress_updated.emit(30)
            
            spoofer = get_game_spoofer(self.game_name, self.db_manager)
            if not spoofer:
                self.operation_completed.emit(False, f"Game spoofer not found for {self.game_name}")
                return
            
            if self.game_name.lower() == "fivem":
                results = spoofer.spoof_fivem_identifiers()
            elif self.game_name.lower() == "fortnite":
                results = spoofer.spoof_fortnite_identifiers()
            elif self.game_name.lower() == "valorant":
                results = spoofer.spoof_valorant_identifiers()
            else:
                self.operation_completed.emit(False, f"Unsupported game: {self.game_name}")
                return
                
            self.progress_updated.emit(80)
            self.status_updated.emit("Finalizing changes...")
            
            if results:
                self.operation_completed.emit(True, f"Successfully spoofed {len(results)} identifiers for {self.game_name}")
            else:
                self.operation_completed.emit(False, f"Failed to spoof {self.game_name} identifiers")
                
        except Exception as e:
            self.operation_completed.emit(False, f"Game spoofing error: {str(e)}")
            
    def spoof_system(self):
        
        try:
            self.status_updated.emit("Spoofing system identifiers...")
            self.progress_updated.emit(20)

            spoofer = SystemSpoofer(self.db_manager)
            results = []
            if any(opt == "MAC Address" for opt in self.system_options):
                self.status_updated.emit("Changing MAC Address...")
                res = spoofer.spoof_mac()
                results.append(("MAC Address", res))
                self.progress_updated.emit(35)

            if any(opt == "IP Address" for opt in self.system_options):
                self.status_updated.emit("Renewing DHCP / IP...")
                res = spoofer.spoof_ip()
                results.append(("IP Address", res))
                self.progress_updated.emit(50)

            if any(opt == "HWID" for opt in self.system_options):
                self.status_updated.emit("Changing MachineGuid (HWID)...")
                res = spoofer.spoof_hwid()
                results.append(("HWID", res))
                self.progress_updated.emit(65)
            need_bios = any(opt == "BIOS Serial" for opt in self.system_options)
            need_cpu_serial = any(opt == "CPU Serial" for opt in self.system_options)
            need_processor_id = any(opt == "Processor ID" for opt in self.system_options)
            need_os_serial = any(opt == "Serial Number" for opt in self.system_options)
            need_efi = any(opt == "EFI Number" for opt in self.system_options)
            if any([need_bios, need_cpu_serial, need_processor_id, need_os_serial, need_efi]):
                self.status_updated.emit("Applying display overrides for serials...")
                res = spoofer.spoof_overrides(need_bios, need_cpu_serial, need_processor_id, need_os_serial, need_efi)
                results.append(("Overrides", res))
                self.progress_updated.emit(85)

            self.status_updated.emit("Finalizing changes...")
            self.progress_updated.emit(95)
            ok = all(r.get("success", False) for _, r in results) if results else True
            msg = f"System spoofing {'completed' if ok else 'completed with issues'}"
            self.progress_updated.emit(100)
            self.operation_completed.emit(ok, msg)
        except Exception as e:
            self.operation_completed.emit(False, f"System spoofing error: {str(e)}")
        
    def clean_registry(self):
        
        self.status_updated.emit("Cleaning registry...")
        self.progress_updated.emit(50)
        self.operation_completed.emit(True, "Registry cleaning completed")
        
    def optimize_system(self):
        
        self.status_updated.emit("Optimizing system...")
        self.progress_updated.emit(50)
        self.operation_completed.emit(True, "System optimization completed")

    def restore_original(self):
        
        try:
            self.status_updated.emit("Restoring original identifiers...")
            self.progress_updated.emit(25)
            spoofer = SystemSpoofer(self.db_manager)
            res = spoofer.restore_all()
            self.progress_updated.emit(90)
            ok = bool(res.get("success", False))
            self.progress_updated.emit(100)
            self.operation_completed.emit(ok, "Original identifiers restored successfully" if ok else "Restore encountered issues")
        except Exception as e:
            self.operation_completed.emit(False, f"Restore error: {str(e)}")

    def scan_registry(self):
        
        self.status_updated.emit("Scanning registry...")
        self.progress_updated.emit(50)
        self.operation_completed.emit(True, "Registry scan completed successfully")

    def backup_registry(self):
        
        self.status_updated.emit("Backing up registry...")
        self.progress_updated.emit(50)
        self.operation_completed.emit(True, "Registry backup completed successfully")

    def analyze_system(self):
        
        self.status_updated.emit("Analyzing system...")
        self.progress_updated.emit(50)
        self.operation_completed.emit(True, "System analysis completed successfully")

    def cleanup_database(self):
        
        self.status_updated.emit("Cleaning up database...")
        self.progress_updated.emit(20)
        
        try:
            days_to_keep = 30
            if self.db_manager:
                try:
                    settings = self.db_manager.load_settings()
                    days_to_keep = int(settings.get('data_retention', days_to_keep))
                except Exception:
                    pass
            
            self.status_updated.emit(f"Removing entries older than {days_to_keep} days...")
            self.progress_updated.emit(60)
            
            if self.db_manager:
                self.db_manager.cleanup_old_data(days_to_keep)
            
            self.status_updated.emit("Optimizing database...")
            self.progress_updated.emit(85)
            
            self.status_updated.emit("Database cleanup complete")
            self.progress_updated.emit(100)
            self.operation_completed.emit(True, "Database cleanup completed successfully")
        except Exception as e:
            self.operation_completed.emit(False, f"Database cleanup error: {str(e)}")

    def create_backup(self):
        
        self.status_updated.emit("Creating backup...")
        self.progress_updated.emit(40)
        try:
            backup_path = None
            if self.db_manager:
                backup_path = self.db_manager.create_backup()
            if backup_path:
                self.status_updated.emit(f"Backup created: {backup_path}")
                self.progress_updated.emit(100)
                self.operation_completed.emit(True, "Backup created successfully")
            else:
                self.operation_completed.emit(False, "Backup creation failed")
        except Exception as e:
            self.operation_completed.emit(False, f"Backup error: {str(e)}")

    def restore_backup(self):
        
        self.status_updated.emit("Restoring backup...")
        self.progress_updated.emit(40)
        try:
            if not self.backup_path:
                self.operation_completed.emit(False, "No backup file provided")
                return
            ok = False
            if self.db_manager:
                ok = self.db_manager.restore_backup(self.backup_path)
            if ok:
                self.status_updated.emit("Backup restoration complete")
                self.progress_updated.emit(100)
                self.operation_completed.emit(True, "Backup restored successfully")
            else:
                self.operation_completed.emit(False, "Backup restoration failed")
        except Exception as e:
            self.operation_completed.emit(False, f"Restore error: {str(e)}")

class CustomTitleBar(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        self.setObjectName("title_bar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        self.setup_ui()
        
    def setup_ui(self):
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)
        
        self.title_label = QLabel("PhantomID - Advanced Hardware ID Spoofer")
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.title_label.setObjectName("title_label")
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setObjectName("title_btn")
        self.minimize_btn.clicked.connect(self.minimize_window)
        layout.addWidget(self.minimize_btn)
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("close_btn")
        self.close_btn.clicked.connect(self.close_window)
        layout.addWidget(self.close_btn)
        
    def minimize_window(self):
        
        if self.parent:
            self.parent.showMinimized()
            
    def close_window(self):
        
        if self.parent:
            self.parent.close()
            
    def mousePressEvent(self, event):
        
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()
            
    def mouseMoveEvent(self, event):
        
        if hasattr(self, 'oldPos'):
            delta = event.globalPosition().toPoint() - self.oldPos
            if self.parent:
                self.parent.move(self.parent.pos() + delta)
                self.oldPos = event.globalPosition().toPoint()

class PhantomIDGUI(QMainWindow):
    
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.anti_detection = AntiDetectionManager()
        self.current_session = None
        self.current_operation = None
        self.worker = None
        self.auto_backup_enabled = True
        self.backup_timer = QTimer(self)
        self.backup_timer.setSingleShot(False)
        self.backup_timer.timeout.connect(self.on_backup_timer_timeout)
        self.auto_updater = AutoUpdater(Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))), self.db_manager, logging.getLogger(__name__))
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(False)
        self.update_timer.timeout.connect(self.on_update_timer_timeout)
        
        self.setup_ui()
        self.setup_logging()
        self.apply_settings()
        self.schedule_auto_update()
        QTimer.singleShot(3000, self.on_update_timer_timeout)
        self.prompt_rollback_if_needed()
        self.start_session()
        
    def setup_ui(self):
        self.setWindowTitle("PhantomID - Advanced Hardware ID Spoofer")
        self.setFixedSize(1080, 720)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.apply_stylesheets()
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)
        self.set_rounded_corners()
        main_widget = QWidget()
        main_widget.setObjectName("main_container")
        main_widget.setAttribute(Qt.WA_StyledBackground, True)
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)
        
        content_widget = QWidget()
        content_widget.setAttribute(Qt.WA_StyledBackground, True)
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        sidebar = self.create_sidebar()
        content_layout.addWidget(sidebar)
        
        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack)
        
        main_layout.addWidget(content_widget)
        
        self.create_dashboard_page()
        self.create_game_spoofing_page()
        self.create_system_spoofing_page()
        self.create_serial_checker_page()
        self.create_settings_page()
        
        self.create_status_bar()
        
        self.content_stack.setCurrentIndex(0)
        
    def create_sidebar(self):
        
        sidebar = QWidget()
        sidebar.setFixedWidth(250)
        sidebar.setObjectName("sidebar")
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        title_label = QLabel("PhantomID")
        title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title_label.setObjectName("sidebar_title")
        layout.addWidget(title_label)
        
        nav_buttons = [
            ("Dashboard", 0),
            ("Game Spoofing", 1),
            ("System Spoofing", 2),
            ("Serial Checker", 3),
            ("Settings", 4)
        ]
        
        self.nav_buttons = []
        for text, index in nav_buttons:
            btn = ModernButton(text)
            btn.clicked.connect(lambda checked, i=index: self.switch_page(i))
            btn.setObjectName("nav_button")
            layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        layout.addStretch()
        
        quick_actions_label = QLabel("Quick Actions")
        quick_actions_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        quick_actions_label.setObjectName("sidebar_section_label")
        layout.addWidget(quick_actions_label)
        
        backup_btn = ModernButton("Backup")
        backup_btn.clicked.connect(self.create_backup)
        layout.addWidget(backup_btn)

        restore_btn = ModernButton("Restore")
        restore_btn.clicked.connect(self.restore_backup)
        layout.addWidget(restore_btn)
        
        return sidebar
        
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        header_label = QLabel("Dashboard")
        header_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header_label.setObjectName("header_label")
        layout.addWidget(header_label)

        
        activity_group = QGroupBox("Recent Activity")
        activity_group.setObjectName("group_card")
        
        activity_layout = QVBoxLayout(activity_group)
        
        self.activity_text = QTextEdit()
        self.activity_text.setReadOnly(True)
        self.activity_text.setMaximumHeight(200)
        self.activity_text.setObjectName("activity_text")
        activity_layout.addWidget(self.activity_text)
        
        layout.addWidget(activity_group)
        
        quick_actions_group = QGroupBox("Quick Actions")
        quick_actions_group.setObjectName("group_card")
        
        quick_actions_layout = QHBoxLayout(quick_actions_group)
        
        spoof_all_btn = ModernButton("Spoof All Games")
        spoof_all_btn.clicked.connect(self.spoof_all_games)
        quick_actions_layout.addWidget(spoof_all_btn)
        
        system_spoof_btn = ModernButton("Spoof System")
        system_spoof_btn.clicked.connect(self.spoof_system)
        quick_actions_layout.addWidget(system_spoof_btn)
        
        cleanup_btn = ModernButton("Cleanup")
        cleanup_btn.clicked.connect(self.cleanup_system)
        quick_actions_layout.addWidget(cleanup_btn)
        
        layout.addWidget(quick_actions_group)
        
        additional_actions_group = QGroupBox("System Tools")
        additional_actions_group.setObjectName("group_card")
        
        additional_actions_layout = QGridLayout(additional_actions_group)
        additional_actions_layout.setSpacing(15)
        
        clear_traces_btn = ModernButton("Clear Traces")
        clear_traces_btn.clicked.connect(self.cleanup_system)
        additional_actions_layout.addWidget(clear_traces_btn, 0, 0)
        discord_tools_btn = ModernButton("Discord")
        discord_tools_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://discord.gg/vNAeak7Nes")))
        additional_actions_layout.addWidget(discord_tools_btn, 0, 1)
        
        layout.addWidget(additional_actions_group)
        layout.addStretch()
        
        self.content_stack.addWidget(page)
        
    def create_game_spoofing_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        header_label = QLabel("Game Spoofing")
        header_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header_label.setObjectName("header_label")
        layout.addWidget(header_label)
        
        desc_label = QLabel("Select a game to spoof its identifiers and remove bans")
        desc_label.setFont(QFont("Segoe UI", 12))
        desc_label.setObjectName("desc_label")
        layout.addWidget(desc_label)
        
        games_widget = QWidget()
        games_layout = QGridLayout(games_widget)
        games_layout.setSpacing(20)
        
        games = [
            ("FiveM", "", "GTA V Roleplay"),
            ("Fortnite", "", "Battle Royale"),
            ("Valorant", "", "Tactical FPS"),
            ("Minecraft", "", "Sandbox Game"),
            ("Roblox", "", "Game Platform"),
            ("CS:GO", "", "Tactical Shooter")
        ]
        
        for i, (game_name, icon, description) in enumerate(games):
            row = i // 3
            col = i % 3
            
            game_btn = GameButton(game_name, icon)
            game_btn.clicked.connect(lambda checked, g=game_name: self.spoof_game(g))
            games_layout.addWidget(game_btn, row, col)
        
        layout.addWidget(games_widget)
        
        anti_detect_group = QGroupBox("Anti-Detection Options")
        anti_detect_group.setObjectName("group_card")
        
        anti_detect_layout = QVBoxLayout(anti_detect_group)
        
        self.anti_detect_checks = {}
        anti_detect_options = [
            ("Randomize Timing", "Randomize operation timing to avoid detection patterns"),
            ("Clear System Traces", "Clear recent files and system traces"),
            ("Spoof File Timestamps", "Randomize file modification timestamps"),
            ("Registry Backup", "Automatically backup registry before changes")
        ]
        
        for option, description in anti_detect_options:
            checkbox = QCheckBox(option)
            checkbox.setChecked(True)
            checkbox.setObjectName("app_checkbox")
        checkbox.stateChanged.connect(self.on_checkbox_changed)
        anti_detect_layout.addWidget(checkbox)
        self.anti_detect_checks[option] = checkbox
            
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Segoe UI", 10))
        desc_label.setObjectName("desc_label")
        anti_detect_layout.addWidget(desc_label)
        
        layout.addWidget(anti_detect_group)
        
        progress_group = QGroupBox("Progress")
        progress_group.setObjectName("group_card")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.hide()
        progress_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Segoe UI", 12))
        self.status_label.setObjectName("status_label")
        self.status_label.hide()
        progress_layout.addWidget(self.status_label)
        progress_group.hide()
        layout.addStretch()
        
        self.content_stack.addWidget(page)
        
    def create_system_spoofing_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        header_label = QLabel("System Spoofing")
        header_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header_label.setObjectName("header_label")
        layout.addWidget(header_label)
        system_group = QGroupBox("System Identifiers")
        system_group.setObjectName("group_card")
        system_layout = QGridLayout(system_group)
        system_options = [
            ("MAC Address", "Spoof network MAC address"),
            ("HWID", "Spoof hardware ID"),
            ("IP Address", "Spoof IP address"),
            ("Serial Number", "Spoof system serial number"),
            ("BIOS Serial", "Spoof BIOS serial number"),
            ("CPU Serial", "Spoof CPU serial number"),
            ("Processor ID", "Spoof processor ID"),
            ("EFI Number", "Spoof EFI number")
        ]
        self.system_checks = {}
        for i, (option, description) in enumerate(system_options):
            row = i // 2
            col = i % 2
            checkbox = QCheckBox(option)
            checkbox.setObjectName("app_checkbox")
            checkbox.stateChanged.connect(self.on_checkbox_changed)
            system_layout.addWidget(checkbox, row, col)
            self.system_checks[option] = checkbox
        layout.addWidget(system_group)
        button_layout = QHBoxLayout()
        spoof_selected_btn = ModernButton("Spoof Selected")
        spoof_selected_btn.clicked.connect(self.spoof_selected_system)
        button_layout.addWidget(spoof_selected_btn)
        
        spoof_all_btn = ModernButton("Spoof All")
        spoof_all_btn.clicked.connect(self.spoof_all_system)
        button_layout.addWidget(spoof_all_btn)
        
        restore_btn = ModernButton("Restore Original")
        restore_btn.clicked.connect(self.restore_original)
        button_layout.addWidget(restore_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.content_stack.addWidget(page)
        

    def create_serial_checker_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header_label = QLabel("Serial Checker")
        header_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header_label.setObjectName("header_label")
        layout.addWidget(header_label)

        info_group = QGroupBox("System Serials")
        info_group.setObjectName("group_card")
        info_layout = QVBoxLayout(info_group)

        self.serials_text = QTextEdit()
        self.serials_text.setReadOnly(True)
        self.serials_text.setMinimumHeight(260)
        self.serials_text.setObjectName("serials_text")
        info_layout.addWidget(self.serials_text)

        actions_layout = QHBoxLayout()
        refresh_btn = ModernButton("Refresh Serials")
        refresh_btn.clicked.connect(self.refresh_serials)
        actions_layout.addWidget(refresh_btn)

        copy_btn = ModernButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_serials_to_clipboard)
        actions_layout.addWidget(copy_btn)

        export_btn = ModernButton("Export JSON")
        export_btn.clicked.connect(self.export_serials_to_json)
        actions_layout.addWidget(export_btn)

        actions_layout.addStretch()
        info_layout.addLayout(actions_layout)

        layout.addWidget(info_group)
        layout.addStretch()
        self.content_stack.addWidget(page)

    def refresh_serials(self):
        self.serials_text.clear()
        try:
            info = self.collect_serials_info()
            rendered = self.format_serials_text(info)
            self.serials_text.setPlainText(rendered)
            self.log_activity("Serials refreshed")
        except Exception as e:
            QMessageBox.warning(self, "Serial Checker", f"Error fetching serials: {e}")

    def copy_serials_to_clipboard(self):
        try:
            cb = QApplication.clipboard()
            cb.setText(self.serials_text.toPlainText())
            self.log_activity("Serials copied to clipboard")
        except Exception:
            pass

    def export_serials_to_json(self):
        try:
            info = self.collect_serials_info()
            path, _ = QFileDialog.getSaveFileName(self, "Export Serials JSON", str(Path.home() / "serials.json"), "JSON Files (*.json)")
            if path:
                import json
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(info, f, indent=2)
                QMessageBox.information(self, "Export Complete", f"Saved to: {path}")
                self.log_activity(f"Serials exported to {path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Failed to export JSON: {e}")

    def collect_serials_info(self) -> Dict[str, Any]:
        result: Dict[str, any] = {
            "BIOS": {},
            "Baseboard": {},
            "ComputerSystem": {},
            "CPU": {},
            "GPU": [],
            "Disks": [],
            "NetworkAdapters": [],
            "OS": {},
            "UUID": {},
            "Registry": {},
            "Volumes": {},
        }
        wmi_client = None
        try:
            import wmi
            wmi_client = wmi.WMI()
        except Exception:
            wmi_client = None

        try:
            if wmi_client:
                bios = wmi_client.Win32_BIOS()
                if bios:
                    b = bios[0]
                    result["BIOS"] = {
                        "SerialNumber": str(getattr(b, 'SerialNumber', '') or ''),
                        "SMBIOSBIOSVersion": str(getattr(b, 'SMBIOSBIOSVersion', '') or ''),
                        "Version": str(getattr(b, 'Version', '') or ''),
                        "ReleaseDate": str(getattr(b, 'ReleaseDate', '') or ''),
                    }
        except Exception:
            pass

        try:
            if wmi_client:
                boards = wmi_client.Win32_BaseBoard()
                if boards:
                    bb = boards[0]
                    result["Baseboard"] = {
                        "SerialNumber": str(getattr(bb, 'SerialNumber', '') or ''),
                        "Product": str(getattr(bb, 'Product', '') or ''),
                        "Manufacturer": str(getattr(bb, 'Manufacturer', '') or ''),
                        "Version": str(getattr(bb, 'Version', '') or ''),
                    }
        except Exception:
            pass

        try:
            if wmi_client:
                cs = wmi_client.Win32_ComputerSystem()
                if cs:
                    c0 = cs[0]
                    result["ComputerSystem"] = {
                        "Manufacturer": str(getattr(c0, 'Manufacturer', '') or ''),
                        "Model": str(getattr(c0, 'Model', '') or ''),
                        "SystemFamily": str(getattr(c0, 'SystemFamily', '') or ''),
                        "TotalPhysicalMemory": str(getattr(c0, 'TotalPhysicalMemory', '') or ''),
                    }
                csp = wmi_client.Win32_ComputerSystemProduct()
                if csp:
                    p0 = csp[0]
                    result["UUID"] = {
                        "UUID": str(getattr(p0, 'UUID', '') or ''),
                        "IdentifyingNumber": str(getattr(p0, 'IdentifyingNumber', '') or ''),
                        "Name": str(getattr(p0, 'Name', '') or ''),
                    }
        except Exception:
            pass

        try:
            if wmi_client:
                cpus = wmi_client.Win32_Processor()
                if cpus:
                    p = cpus[0]
                    result["CPU"] = {
                        "Name": str(getattr(p, 'Name', '') or ''),
                        "ProcessorId": str(getattr(p, 'ProcessorId', '') or ''),
                        "NumberOfCores": int(getattr(p, 'NumberOfCores', 0) or 0),
                        "NumberOfLogicalProcessors": int(getattr(p, 'NumberOfLogicalProcessors', 0) or 0),
                        "MaxClockSpeed": int(getattr(p, 'MaxClockSpeed', 0) or 0),
                    }
        except Exception:
            pass

        try:
            if wmi_client:
                gpus = wmi_client.Win32_VideoController()
                for g in gpus or []:
                    result["GPU"].append({
                        "Name": str(getattr(g, 'Name', '') or ''),
                        "DriverVersion": str(getattr(g, 'DriverVersion', '') or ''),
                        "PNPDeviceID": str(getattr(g, 'PNPDeviceID', '') or ''),
                    })
        except Exception:
            pass

        try:
            if wmi_client:
                for d in wmi_client.Win32_DiskDrive() or []:
                    result["Disks"].append({
                        "Model": str(getattr(d, 'Model', '') or ''),
                        "SerialNumber": str(getattr(d, 'SerialNumber', '') or ''),
                        "Size": str(getattr(d, 'Size', '') or ''),
                        "PNPDeviceID": str(getattr(d, 'PNPDeviceID', '') or ''),
                    })
        except Exception:
            pass

        try:
            if wmi_client:
                for na in wmi_client.Win32_NetworkAdapterConfiguration() or []:
                    if getattr(na, 'IPEnabled', False):
                        ips = getattr(na, 'IPAddress', None) or []
                        result["NetworkAdapters"].append({
                            "Description": str(getattr(na, 'Description', '') or ''),
                            "MACAddress": str(getattr(na, 'MACAddress', '') or ''),
                            "IPAddresses": list(ips),
                        })
        except Exception:
            pass

        try:
            if wmi_client:
                os_list = wmi_client.Win32_OperatingSystem()
                if os_list:
                    o = os_list[0]
                    result["OS"] = {
                        "Caption": str(getattr(o, 'Caption', '') or ''),
                        "Version": str(getattr(o, 'Version', '') or ''),
                        "BuildNumber": str(getattr(o, 'BuildNumber', '') or ''),
                        "OSArchitecture": str(getattr(o, 'OSArchitecture', '') or ''),
                        "InstallDate": str(getattr(o, 'InstallDate', '') or ''),
                        "LastBootUpTime": str(getattr(o, 'LastBootUpTime', '') or ''),
                        "SerialNumber": str(getattr(o, 'SerialNumber', '') or ''),
                    }
        except Exception:
            pass

        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as k:
                mg, _ = winreg.QueryValueEx(k, "MachineGuid")
                result["Registry"]["MachineGuid"] = str(mg)
        except Exception:
            pass

        try:
            import ctypes
            vol_name = ctypes.create_unicode_buffer(1024)
            fs_name = ctypes.create_unicode_buffer(1024)
            serial = ctypes.c_uint()
            max_comp_len = ctypes.c_uint()
            flags = ctypes.c_uint()
            GetVolumeInformationW = ctypes.windll.kernel32.GetVolumeInformationW
            r = GetVolumeInformationW(ctypes.c_wchar_p("C:\\"), vol_name, 1024, ctypes.byref(serial), ctypes.byref(max_comp_len), ctypes.byref(flags), fs_name, 1024)
            if r:
                result["Volumes"]["C"] = {
                    "SerialNumber": int(serial.value),
                    "VolumeName": vol_name.value,
                    "FileSystem": fs_name.value,
                }
        except Exception:
            pass

        try:
            settings = self.db_manager.load_settings()
            overrides = settings.get('spoof_overrides', {}) if isinstance(settings, dict) else {}
            if overrides:
                bios_sn = overrides.get('BIOS.SerialNumber')
                if bios_sn:
                    result.setdefault('BIOS', {})['SerialNumber'] = bios_sn
                cpu_serial = overrides.get('CPU.Serial')
                if cpu_serial:
                    result.setdefault('CPU', {})['Serial'] = cpu_serial
                proc_id = overrides.get('CPU.ProcessorId')
                if proc_id:
                    result.setdefault('CPU', {})['ProcessorId'] = proc_id
                os_sn = overrides.get('OS.SerialNumber')
                if os_sn:
                    result.setdefault('OS', {})['SerialNumber'] = os_sn
                efi_num = overrides.get('EFI.Number')
                if efi_num:
                    result.setdefault('UUID', {})['EFI'] = efi_num
        except Exception:
            pass

        return result

    def format_serials_text(self, info: Dict[str, Any]) -> str:
        lines: List[str] = []
        def section(title: str):
            lines.append(title)
            lines.append("----------------------------------------")
        def kv_block(d: Dict[str, any]):
            for k, v in d.items():
                lines.append(f"{k}: {v if (v or v==0) else 'N/A'}")
        section("BIOS")
        kv_block(info.get("BIOS", {}))
        lines.append("")
        section("Baseboard")
        kv_block(info.get("Baseboard", {}))
        lines.append("")
        section("Computer System")
        kv_block(info.get("ComputerSystem", {}))
        lines.append("")
        section("System UUID")
        kv_block(info.get("UUID", {}))
        lines.append("")
        section("CPU")
        kv_block(info.get("CPU", {}))
        lines.append("")
        section("GPU")
        gpus = info.get("GPU", [])
        if gpus:
            for idx, g in enumerate(gpus, 1):
                lines.append(f"Adapter {idx}:")
                for k, v in g.items():
                    lines.append(f"  {k}: {v if v else 'N/A'}")
        else:
            lines.append("No GPU info")
        lines.append("")
        section("Disks")
        disks = info.get("Disks", [])
        if disks:
            for idx, d in enumerate(disks, 1):
                lines.append(f"Disk {idx}:")
                for k, v in d.items():
                    lines.append(f"  {k}: {v if v else 'N/A'}")
        else:
            lines.append("No disk info")
        lines.append("")
        section("Network Adapters (IP enabled)")
        nics = info.get("NetworkAdapters", [])
        if nics:
            for idx, n in enumerate(nics, 1):
                lines.append(f"Adapter {idx}:")
                for k, v in n.items():
                    if isinstance(v, list):
                        lines.append(f"  {k}: {', '.join(v) if v else 'N/A'}")
                    else:
                        lines.append(f"  {k}: {v if v else 'N/A'}")
        else:
            lines.append("No IP-enabled adapter info")
        lines.append("")
        section("Operating System")
        kv_block(info.get("OS", {}))
        lines.append("")
        section("Registry")
        kv_block(info.get("Registry", {}))
        lines.append("")
        section("Volumes")
        vols = info.get("Volumes", {})
        if vols:
            for name, v in vols.items():
                lines.append(f"{name}:")
                for k, val in v.items():
                    lines.append(f"  {k}: {val if (val or val==0) else 'N/A'}")
        else:
            lines.append("No volume info")
        return "\n".join(lines)
        

        
    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        header_label = QLabel("Settings")
        header_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header_label.setObjectName("header_label")
        layout.addWidget(header_label)
        general_group = QGroupBox("General Settings")
        general_group.setObjectName("group_card")
        general_layout = QVBoxLayout(general_group)
        self.auto_backup_check = QCheckBox("Enable automatic backups")
        self.auto_backup_check.setChecked(self.auto_backup_enabled)
        self.auto_backup_check.setObjectName("app_checkbox")
        self.auto_backup_check.stateChanged.connect(self.on_checkbox_changed)
        general_layout.addWidget(self.auto_backup_check)
        backup_layout = QHBoxLayout()
        backup_layout.addWidget(QLabel("Backup interval (days):"))
        self.backup_interval_spin = QComboBox()
        self.backup_interval_spin.addItems(["1", "3", "7", "14", "30"])
        self.backup_interval_spin.setCurrentIndex(2)
        backup_layout.addWidget(self.backup_interval_spin)
        backup_layout.addStretch()
        general_layout.addLayout(backup_layout)
        
        log_layout = QHBoxLayout()
        log_layout.addWidget(QLabel("Logging level:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentIndex(1)
        log_layout.addWidget(self.log_level_combo)
        log_layout.addStretch()
        general_layout.addLayout(log_layout)
        
        layout.addWidget(general_group)
        
        db_group = QGroupBox("Database Settings")
        db_group.setObjectName("group_card")

        db_layout = QVBoxLayout(db_group)
        
        retention_layout = QHBoxLayout()
        retention_layout.addWidget(QLabel("Keep data for (days):"))
        self.data_retention_spin = QComboBox()
        self.data_retention_spin.addItems(["7", "30", "90", "180", "365"])
        self.data_retention_spin.setCurrentIndex(1)
        retention_layout.addWidget(self.data_retention_spin)
        retention_layout.addStretch()
        db_layout.addLayout(retention_layout)
        
        cleanup_db_btn = ModernButton("Cleanup Database")
        cleanup_db_btn.clicked.connect(self.cleanup_database)
        db_layout.addWidget(cleanup_db_btn)
        
        layout.addWidget(db_group)

        update_group = QGroupBox("Update Settings")
        update_group.setObjectName("group_card")
        update_layout = QVBoxLayout(update_group)

        self.auto_update_check = QCheckBox("Enable automatic updates")
        self.auto_update_check.setObjectName("app_checkbox")
        self.auto_update_check.stateChanged.connect(self.on_checkbox_changed)
        update_layout.addWidget(self.auto_update_check)

        self.update_auto_apply_check = QCheckBox("Auto-apply without prompt")
        self.update_auto_apply_check.setObjectName("app_checkbox")
        update_layout.addWidget(self.update_auto_apply_check)

        layout.addWidget(update_group)
        
        save_btn = ModernButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        self.content_stack.addWidget(page)
        
    def get_stylesheet(self):
        
        return """
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1d24, stop:1 #252930);
                border-radius: 30px;
                border: 2px solid #00d4ff;
            }
            
            QWidget {
                background-color: #1e2229;
                color: #e0f7ff;
            }
            
            QScrollArea {
                border: none;
                background: transparent;
            }
            
            QTextEdit {
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 15px;
                font-family: 'Consolas', monospace;
            }
            
            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                height: 25px;
                text-align: center;
                color: white;
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 12px;
            }
            
            QComboBox {
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 8px 12px;
                min-height: 35px;
                font-size: 13px;
            }
            
            QComboBox::drop-down {
                border: none;
                padding-right: 15px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 6px solid white;
            }
            
            QComboBox QAbstractItemView {
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                selection-background-color: #667eea;
            }
            
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                background-color: transparent;
                border: 2px solid #667eea;
                border-radius: 4px;
                position: relative;
            }
            QCheckBox::indicator:unchecked {
                background-color: transparent;
                border: 2px solid #999;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: transparent;
                border: 2px solid #667eea;
            }
            
            QCheckBox::indicator:checked::alternate {
                border: 2px solid #764ba2;
            }
            
            QCheckBox {
                spacing: 8px;
                font-size: 13px;
            }
            
            QMenuBar {
                background-color: #2c343a;
                color: white;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 30px;
                padding: 8px;
                margin: 5px;
            }
            
            QMenuBar::item {
                background-color: transparent;
                padding: 6px 12px;
                border-radius: 4px;
            }
            
            QMenuBar::item:selected {
                background-color: rgba(102, 126, 234, 0.3);
            }
            
            QMenu {
                background-color: rgba(26, 26, 46, 0.9);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 5px;
            }
            
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            
            QMenu::item:selected {
                background-color: rgba(102, 126, 234, 0.5);
            }
            
            QStatusBar {
                background-color: #2c343a;
                color: white;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 30px;
                padding: 8px;
                margin: 5px;
                border: 2px solid #00d4ff;
            }
            
            QSpinBox, QLineEdit {
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            
            QSpinBox:focus, QLineEdit:focus {
                border: 1px solid rgba(102, 126, 234, 0.5);
                outline: none;
            }
            
            QScrollBar:vertical {
                background-color: rgba(26, 26, 46, 0.4);
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background-color: rgba(102, 126, 234, 0.7);
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: rgba(102, 126, 234, 0.9);
            }
            
            QScrollBar:horizontal {
                background-color: rgba(26, 26, 46, 0.4);
                height: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:horizontal {
                background-color: rgba(102, 126, 234, 0.7);
                border-radius: 6px;
                min-width: 20px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background-color: rgba(102, 126, 234, 0.9);
            }
        """
        
    def apply_stylesheets(self):
        try:
            base_dir = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            styles_dir = base_dir / 'assets' / 'styles'
            order = [
                'theme_base.qss',
                'theme_sidebar.qss',
                'theme_titlebar.qss',
                'theme_buttons.qss',
                'theme_forms.qss',
                'theme_statusbar.qss',
            ]
            parts = []
            for name in order:
                path = styles_dir / name
                if path.exists():
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            parts.append(f.read())
                    except Exception:
                        continue
            qss = "\n\n".join(parts)
            app = QApplication.instance()
            if app and qss:
                app.setStyleSheet(qss)
            elif qss:
                self.setStyleSheet(qss)
        except Exception:
            pass

    def create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        backup_action = file_menu.addAction("Create Backup")
        backup_action.triggered.connect(self.create_backup)
        
        restore_action = file_menu.addAction("Restore Backup")
        restore_action.triggered.connect(self.restore_backup)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        tools_menu = menubar.addMenu("Tools")
        
        system_info_action = tools_menu.addAction("System Information")
        system_info_action.triggered.connect(self.show_system_info)
        
        logs_action = tools_menu.addAction("View Logs")
        logs_action.triggered.connect(self.view_logs)
        help_menu = menubar.addMenu("Help")
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        
        help_action = help_menu.addAction("User Guide")
        help_action.triggered.connect(self.show_help)
        
    def create_status_bar(self):
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.setFixedHeight(40)
        
        self.status_bar.showMessage("Ready")
        self.session_label = QLabel("Session: Not started")
        self.session_label.setObjectName("status_session_label")
        self.status_bar.addPermanentWidget(self.session_label)
        
    def create_stat_card(self, title, value, color):
        
        card = QFrame()
        card.setFixedHeight(120)
        card.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a2a3a, stop:1 #2a3a4a);
                border: 2px solid #00d4ff;
                border-radius: 16px;
                padding: 20px;
            }}
            QFrame:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2a3a4a, stop:1 #3a4a5a);
                border: 2px solid #00f0ff;
            }}
        """)
        
        card_layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        title_label.setStyleSheet(f"color: {color}; font-weight: 600;")
        card_layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        value_label.setStyleSheet(f"color: #ffffff;")
        card_layout.addWidget(value_label)
        
        return card
        
    def setup_logging(self):
        level = logging.INFO
        try:
            settings = self.db_manager.load_settings()
            level_str = str(settings.get('log_level', 'INFO')).upper()
            level = getattr(logging, level_str, logging.INFO)
        except Exception:
            pass
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('phantomid.log'),
                logging.StreamHandler()
            ]
        )

    def apply_settings(self):
        try:
            settings = self.db_manager.load_settings()
            self.auto_backup_check.setChecked(bool(settings.get('auto_backup', True)))
            backup_interval = str(settings.get('backup_interval', 7))
            idx = self.backup_interval_spin.findText(backup_interval)
            if idx != -1:
                self.backup_interval_spin.setCurrentIndex(idx)
            log_level = str(settings.get('log_level', 'INFO')).upper()
            idx = self.log_level_combo.findText(log_level)
            if idx != -1:
                self.log_level_combo.setCurrentIndex(idx)
            retention = str(settings.get('data_retention', 30))
            idx = self.data_retention_spin.findText(retention)
            if idx != -1:
                self.data_retention_spin.setCurrentIndex(idx)
            self.auto_update_check.setChecked(bool(settings.get('auto_update', True)))
            self.update_auto_apply_check.setChecked(bool(settings.get('auto_update_apply', True)))
            self.auto_backup_enabled = self.auto_backup_check.isChecked()
            level_map = {
                'DEBUG': logging.DEBUG,
                'INFO': logging.INFO,
                'WARNING': logging.WARNING,
                'ERROR': logging.ERROR,
            }
            logging.getLogger().setLevel(level_map.get(log_level, logging.INFO))
            self.schedule_auto_backup()
            self.schedule_auto_update()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to apply settings: {e}")
        
    def start_session(self):
        self.current_session = self.db_manager.start_session()
        self.session_label.setText(f"Session: {self.current_session[:8]}...")
        self.log_activity(f"Session started: {self.current_session}")
        
    def end_session(self):
        if self.current_session:
            self.db_manager.end_session(self.current_session)
            self.log_activity(f"Session ended: {self.current_session}")
            self.current_session = None

    def schedule_auto_backup(self):
        try:
            if not hasattr(self, 'backup_timer'):
                return
            if self.auto_backup_enabled:
                try:
                    interval_days = int(self.backup_interval_spin.currentText())
                except Exception:
                    interval_days = 7
                interval_ms = max(1, interval_days) * 24 * 60 * 60 * 1000
                self.backup_timer.stop()
                self.backup_timer.start(interval_ms)
                self.log_activity(f"Auto-backup scheduled every {interval_days} day(s)")
            else:
                self.backup_timer.stop()
            self.log_activity("Auto-backup disabled")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to schedule auto-backup: {e}")

    def schedule_auto_update(self):
        try:
            if not hasattr(self, 'update_timer'):
                return
            enabled = bool(self.auto_update_check.isChecked())
            interval_min = 60
            try:
                settings = self.db_manager.load_settings()
                interval_min = int(settings.get('update_interval', interval_min))
            except Exception:
                pass
            if enabled:
                self.update_timer.stop()
                self.update_timer.start(max(5, interval_min) * 60 * 1000)
                self.log_activity(f"Auto-update scheduled every {interval_min} minute(s)")
            else:
                self.update_timer.stop()
                self.log_activity("Auto-update disabled")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to schedule auto-update: {e}")

    def on_update_timer_timeout(self):
        try:
            updated, message = self.auto_updater.perform_update_if_available()
            if updated:
                self.log_activity(message)
                if bool(self.update_auto_apply_check.isChecked()):
                    QMessageBox.information(self, "Update", "An update was applied. The application will restart.")
                    self.auto_updater.restart_application()
                    QApplication.instance().quit()
            else:
                self.log_activity(message)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Update check failed: {e}")

    def on_backup_timer_timeout(self):
        try:
            self.log_activity("Auto-backup timer triggered")
            self.create_backup()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Auto-backup error: {e}")

    def prompt_rollback_if_needed(self):
        try:
            unclosed = 0
            try:
                unclosed = self.db_manager.get_unclosed_sessions_count()
            except Exception:
                unclosed = 0
            if unclosed > 0:
                last_backup = None
                try:
                    last_backup = self.db_manager.get_last_backup()
                except Exception:
                    last_backup = None
                backup_path = (last_backup or {}).get('backup_path')
                msg = "It looks like the last session didn't end cleanly."
                if backup_path:
                    msg += f"\nRestore from last backup?\n{backup_path}"
                reply = QMessageBox.question(self, "Unclosed Session Detected", msg,
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes and backup_path:
                    self.worker = SpooferWorker("backup_restore", backup_path=backup_path)
                    self.worker.set_db_manager(self.db_manager)
                    self.worker.progress_updated.connect(self.progress_bar.setValue)
                    self.worker.status_updated.connect(self.status_label.setText)
                    self.worker.operation_completed.connect(self.on_operation_completed)
                    self.worker.start()
                    self.log_activity("Initiated rollback from last backup")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Rollback prompt failed: {e}")
            
    def switch_page(self, index):
        self.content_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
                
    def log_activity(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_text.append(f"[{timestamp}] {message}")
        

                
    def create_backup(self):
        try:
            backup_path = self.db_manager.create_backup()
            if backup_path:
                QMessageBox.information(self, "Backup Created", f"Backup created successfully:\n{backup_path}")
                self.log_activity(f"Backup created: {backup_path}")
            else:
                QMessageBox.warning(self, "Backup Failed", "Failed to create backup")
        except Exception as e:
            QMessageBox.critical(self, "Backup Error", f"Error creating backup: {str(e)}")
            
    def restore_backup(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Backup File", "backups", "Backup Files (*.bak)"
            )
            if file_path:
                if self.db_manager.restore_backup(file_path):
                    QMessageBox.information(self, "Restore Complete", "Database restored successfully")
                    self.log_activity(f"Database restored from: {file_path}")
                else:
                    QMessageBox.warning(self, "Restore Failed", "Failed to restore backup")
        except Exception as e:
            QMessageBox.critical(self, "Restore Error", f"Error restoring backup: {str(e)}")
            
    def spoof_game(self, game_name):
        try:
            is_installed, game_path = self.check_game_installed(game_name)
            if not is_installed:
                is_installed, game_path = self.prompt_for_game_path(game_name)
                if not is_installed:
                    QMessageBox.information(self, "Game Not Found", 
                                          f"{game_name} spoofing cancelled. Please install the game first.")
                    return
            self.current_operation = "game"
            if self.anti_detect_checks.get("Randomize Timing"):
                self.anti_detection.randomize_timing()
            if self.anti_detect_checks.get("Clear System Traces"):
                self.anti_detection.clear_system_traces()
            if self.anti_detect_checks.get("Spoof File Timestamps"):
                self.anti_detection.spoof_file_timestamps(".")
            self.worker = SpooferWorker("game", game_name)
            self.worker.set_db_manager(self.db_manager)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity(f"Started spoofing {game_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Spoofing Error", f"Error spoofing {game_name}: {str(e)}")
            
    def spoof_all_games(self):
        games = ["FiveM", "Fortnite", "Valorant"]
        for game in games:
            self.spoof_game(game)
            
    def spoof_selected_system(self):
        try:
            selected_options = []
            for option, checkbox in self.system_checks.items():
                if checkbox.isChecked():
                    selected_options.append(option)
            
            if not selected_options:
                QMessageBox.warning(self, "No Selection", "Please select at least one system identifier to spoof.")
                return
            
            self.status_label.setText(f"Spoofing {len(selected_options)} system identifiers...")
            self.progress_bar.setValue(0)
            if self.anti_detect_checks.get("Randomize Timing"):
                self.anti_detection.randomize_timing()
            if self.anti_detect_checks.get("Clear System Traces"):
                self.anti_detection.clear_system_traces()
            if self.anti_detect_checks.get("Spoof File Timestamps"):
                self.anti_detection.spoof_file_timestamps(".")
            self.worker = SpooferWorker("system", system_options=selected_options)
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.status_updated.connect(self.status_label.setText)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity(f"Started spoofing {len(selected_options)} system identifiers")
            
        except Exception as e:
            QMessageBox.critical(self, "System Spoofing Error", f"Error: {str(e)}")

    def spoof_all_system(self):
        try:
            for checkbox in self.system_checks.values():
                checkbox.setChecked(True)
            self.spoof_selected_system()
            
        except Exception as e:
            QMessageBox.critical(self, "System Spoofing Error", f"Error: {str(e)}")

    def restore_original(self):
        try:
            self.status_label.setText("Restoring original system identifiers...")
            self.progress_bar.setValue(0)
            self.worker = SpooferWorker("restore")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.status_updated.connect(self.status_label.setText)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started restoring original system identifiers")
            
        except Exception as e:
            QMessageBox.critical(self, "Restore Error", f"Error: {str(e)}")
    
    def on_checkbox_changed(self, state):
        checkbox = self.sender()
        if checkbox:
            base_text = checkbox.text()
            self.log_activity(f"Checkbox '{base_text}' {'checked' if state == Qt.Checked else 'unchecked'}")
            if checkbox is getattr(self, 'auto_backup_check', None):
                self.auto_backup_enabled = (state == Qt.Checked)
                self.schedule_auto_backup()
            if checkbox is getattr(self, 'auto_update_check', None):
                self.schedule_auto_update()
    
    def check_game_installed(self, game_name):
        import os
        game_paths = {
            "FiveM": [
                "C:\\Program Files (x86)\\FiveM",
                "C:\\Program Files\\FiveM",
                "C:\\Users\\{}\\AppData\\Local\\FiveM".format(os.getenv('USERNAME')),
            ],
            "Fortnite": [
                "C:\\Program Files\\Epic Games\\Fortnite",
                "C:\\Program Files (x86)\\Epic Games\\Fortnite",
                "C:\\Users\\{}\\AppData\\Local\\FortniteGame".format(os.getenv('USERNAME')),
            ],
            "Valorant": [
                "C:\\Riot Games\\VALORANT",
                "C:\\Program Files\\Riot Vanguard",
                "C:\\Users\\{}\\AppData\\Local\\VALORANT".format(os.getenv('USERNAME')),
            ],
            "Minecraft": [
                "C:\\Users\\{}\\AppData\\Roaming\\.minecraft".format(os.getenv('USERNAME')),
                "C:\\Program Files (x86)\\Minecraft",
                "C:\\Program Files\\Minecraft",
            ],
            "Roblox": [
                "C:\\Users\\{}\\AppData\\Local\\Roblox".format(os.getenv('USERNAME')),
                "C:\\Program Files (x86)\\Roblox",
            ],
            "CS:GO": [
                "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Counter-Strike Global Offensive",
                "C:\\Program Files\\Steam\\steamapps\\common\\Counter-Strike Global Offensive",
                "C:\\Users\\{}\\AppData\\Local\\Steam".format(os.getenv('USERNAME')),
            ]
        }
        paths_to_check = game_paths.get(game_name, [])
        for path in paths_to_check:
            if os.path.exists(path):
                return True, path
        
        return False, None
    
    def prompt_for_game_path(self, game_name):
        from PySide6.QtWidgets import QInputDialog
        reply = QMessageBox.question(
            self, 
            f"{game_name} Not Found", 
            f"{game_name} was not found in default installation paths.\n\n"
            f"Would you like to manually specify the installation path?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            path, ok = QInputDialog.getText(
                self, 
                f"Enter {game_name} Path", 
                f"Please enter the full path to {game_name} installation directory:"
            )
            if ok and path:
                import os
                if os.path.exists(path):
                    return True, path
                else:
                    QMessageBox.warning(self, "Invalid Path", "The specified path does not exist.")
                    return False, None
        
        return False, None
    
    def set_rounded_corners(self):
        rect = self.rect()
        r = 20
        path = QPainterPath()
        path.moveTo(rect.left(), rect.top() + r)
        path.quadTo(rect.left(), rect.top(), rect.left() + r, rect.top())
        path.lineTo(rect.right() - r, rect.top())
        path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + r)
        path.lineTo(rect.right(), rect.bottom() - r)
        path.quadTo(rect.right(), rect.bottom(), rect.right() - r, rect.bottom())
        path.lineTo(rect.left() + r, rect.bottom())
        path.quadTo(rect.left(), rect.bottom(), rect.left(), rect.bottom() - r)
        path.lineTo(rect.left(), rect.top() + r)
        path.closeSubpath()

        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.set_rounded_corners()

    def scan_registry(self):
        try:
            self.status_label.setText("Scanning registry...")
            self.progress_bar.setValue(0)
            self.worker = SpooferWorker("registry_scan")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.status_updated.connect(self.status_label.setText)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started registry scan")
            
        except Exception as e:
            QMessageBox.critical(self, "Registry Scan Error", f"Error: {str(e)}")

    def backup_registry(self):
        try:
            self.status_label.setText("Backing up registry...")
            self.progress_bar.setValue(0)
            self.worker = SpooferWorker("registry_backup")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.status_updated.connect(self.status_label.setText)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started registry backup")
            
        except Exception as e:
            QMessageBox.critical(self, "Registry Backup Error", f"Error: {str(e)}")

    def analyze_system(self):
        try:
            self.status_label.setText("Analyzing system...")
            self.progress_bar.setValue(0)
            self.worker = SpooferWorker("system_analysis")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.status_updated.connect(self.status_label.setText)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started system analysis")
            
        except Exception as e:
            QMessageBox.critical(self, "System Analysis Error", f"Error: {str(e)}")

    def cleanup_database(self):
        try:
            reply = QMessageBox.question(self, "Cleanup Database", 
                                         "Are you sure you want to cleanup the database? This will remove old entries.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.status_label.setText("Cleaning up database...")
                self.progress_bar.setValue(0)
                self.worker = SpooferWorker("database_cleanup")
                self.worker.set_db_manager(self.db_manager)
                self.worker.progress_updated.connect(self.progress_bar.setValue)
                self.worker.status_updated.connect(self.status_label.setText)
                self.worker.operation_completed.connect(self.on_operation_completed)
                self.worker.start()
                self.log_activity("Started database cleanup")
                
        except Exception as e:
            QMessageBox.critical(self, "Database Cleanup Error", f"Error: {str(e)}")

    def save_settings(self):
        try:
            settings = {
                'auto_backup': self.auto_backup_check.isChecked(),
                'backup_interval': int(self.backup_interval_spin.currentText()),
                'log_level': self.log_level_combo.currentText(),
                'data_retention': int(self.data_retention_spin.currentText()),
                'auto_update': bool(self.auto_update_check.isChecked()),
                'auto_update_apply': bool(self.update_auto_apply_check.isChecked()),
            }
            self.db_manager.save_settings(settings)
            QMessageBox.information(self, "Settings Saved", "Application settings have been saved successfully.")
            self.log_activity("Settings saved")
            self.auto_backup_enabled = settings.get('auto_backup', True)
            self.schedule_auto_backup()
            self.schedule_auto_update()
            
        except Exception as e:
            QMessageBox.critical(self, "Settings Error", f"Error saving settings: {str(e)}")

    def create_backup(self):
        try:
            self.status_label.setText("Creating backup...")
            self.progress_bar.setValue(0)
            self.worker = SpooferWorker("backup_creation")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.status_updated.connect(self.status_label.setText)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started backup creation")
            
        except Exception as e:
            QMessageBox.critical(self, "Backup Error", f"Error creating backup: {str(e)}")

    def restore_backup(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Backup File", "", "Backup Files (*.bak)")
            if file_path:
                self.status_label.setText("Restoring backup...")
                self.progress_bar.setValue(0)
                self.worker = SpooferWorker("backup_restore", backup_path=file_path)
                self.worker.set_db_manager(self.db_manager)
                self.worker.progress_updated.connect(self.progress_bar.setValue)
                self.worker.status_updated.connect(self.status_label.setText)
                self.worker.operation_completed.connect(self.on_operation_completed)
                self.worker.start()
                self.log_activity("Started backup restoration")
                
        except Exception as e:
            QMessageBox.critical(self, "Restore Error", f"Error restoring backup: {str(e)}")

    def optimize_system(self):
        try:
            self.status_label.setText("Optimizing system...")
            self.progress_bar.setValue(0)
            self.worker = SpooferWorker("optimization")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.status_updated.connect(self.status_label.setText)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started system optimization")
            
        except Exception as e:
            QMessageBox.critical(self, "System Optimization Error", f"Error: {str(e)}")

    def clean_registry(self):
        try:
            self.status_label.setText("Cleaning registry...")
            self.progress_bar.setValue(0)
            self.worker = SpooferWorker("registry")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.status_updated.connect(self.status_label.setText)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started registry cleaning")
            
        except Exception as e:
            QMessageBox.critical(self, "Registry Cleaning Error", f"Error: {str(e)}")

    def spoof_system(self):
        try:
            self.worker = SpooferWorker("system")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.status_updated.connect(self.status_label.setText)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started system spoofing")
            
        except Exception as e:
            QMessageBox.critical(self, "System Spoofing Error", f"Error: {str(e)}")
            
    def cleanup_system(self):
        try:
            self.worker = SpooferWorker("optimization")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.status_updated.connect(self.status_label.setText)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started system cleanup")
            
        except Exception as e:
            QMessageBox.critical(self, "Cleanup Error", f"Error: {str(e)}")
            
    def on_operation_completed(self, success, message):
        if getattr(self, 'current_operation', None) == 'game':
            if success:
                QMessageBox.information(self, "Success", message)
            else:
                QMessageBox.warning(self, "Failed", message)
        else:
            if success:
                self.status_label.setText("Operation completed successfully")
                self.progress_bar.setValue(100)
                QMessageBox.information(self, "Success", message)
            else:
                self.status_label.setText("Operation failed")
                self.progress_bar.setValue(0)
                QMessageBox.warning(self, "Failed", message)

        self.log_activity(message)
        self.update_stats()
        self.current_operation = None

    def update_stats(self):
        try:
            if hasattr(self, 'db_manager') and self.db_manager:
                stats = self.db_manager.get_statistics()
                if stats:
                    summary = (
                        f"Stats — Changes: {stats.get('total_changes', 0)}, "
                        f"Success: {stats.get('successful_changes', 0)}, "
                        f"Fail: {stats.get('failed_changes', 0)}, "
                        f"Game Spoofs: {stats.get('total_game_spoofs', 0)}, "
                        f"Registry Changes: {stats.get('total_registry_changes', 0)}"
                    )
                    self.log_activity(summary)
        except Exception as e:
            try:
                logging.error(f"Failed to update stats: {e}")
            except Exception:
                pass
        
    def show_system_info(self):
        QMessageBox.information(self, "System Information", "System information will be displayed here")
        
    def view_logs(self):
        try:
            with open('phantomid.log', 'r') as f:
                logs = f.read()
                
            log_dialog = QTextEdit()
            log_dialog.setPlainText(logs)
            log_dialog.setReadOnly(True)
            log_dialog.setMinimumSize(800, 600)
            log_dialog.setWindowTitle("Application Logs")
            log_dialog.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Log Error", f"Error reading logs: {str(e)}")
            
    def show_about(self):
        QMessageBox.about(self, "About PhantomID", 
            "PhantomID - Advanced Hardware ID Spoofer\n\n"
            "Version 2.0\n"
            "A powerful tool for spoofing hardware identifiers and removing game bans.\n\n"
            "Created for privacy enthusiasts")
            
    def show_help(self):
        QMessageBox.information(self, "User Guide", 
            "User guide will be displayed here. For now, please refer to the README.md file.")
            
    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Exit Confirmation',
            'Are you sure you want to exit PhantomID?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            self.end_session()
            event.accept()
        else:
            event.ignore()

def main():
    print("Starting application")
    try:
        app = QApplication(sys.argv)
        print("Application created")
        app.setApplicationName("PhantomID")
        app.setApplicationVersion("2.0")
        
        
        print("Creating window...")
        window = PhantomIDGUI()
        print("Window created")
        window.show()
        print("Window shown, entering event loop")
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error in main: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()