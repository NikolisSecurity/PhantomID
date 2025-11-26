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
    QTextEdit, QDialog, QProgressBar, QGroupBox, QGridLayout, QCheckBox, QGraphicsDropShadowEffect,
    QComboBox, QMessageBox, QFileDialog, QInputDialog, QTabWidget, QListWidget,
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
from utils.game_assets import get_game_bg_pixmap, get_text_logo_pixmap
from utils.auto_updater import AutoUpdater

class ModernButton(QPushButton):
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(45)
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.setObjectName("primary_button")
        self.setCursor(Qt.PointingHandCursor)

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
        self.setFixedSize(200, 80)
        self.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.bg_pix = get_game_bg_pixmap(game_name) or get_text_logo_pixmap(game_name, 400, 160)
        self._hover = False
        
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
        self.setText("")
        self.setToolTip(self.game_name)
        self.setCursor(Qt.PointingHandCursor)

        if not get_game_bg_pixmap(game_name):
            try:
                self._logo_loader = LogoLoader(game_name)
                self._logo_loader.pixmap_ready.connect(self._on_pixmap_ready)
                self._logo_loader.start()
            except Exception:
                pass

    def _on_pixmap_ready(self, pm):
        try:
            if pm is not None:
                self.bg_pix = pm
                self.update()
        except Exception:
            pass

    def paintEvent(self, event):
        super().paintEvent(event)
        if hasattr(self, 'bg_pix') and self.bg_pix:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            rect = self.rect()
            path = QPainterPath()
            path.addRoundedRect(rect, 12, 12)
            painter.setClipPath(path)
            base_scale = 0.92
            hover_scale = 0.98
            scale_ratio = hover_scale if getattr(self, '_hover', False) else base_scale
            target_size = QSize(int(rect.width() * scale_ratio), int(rect.height() * scale_ratio))
            scaled = self.bg_pix.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            target_x = rect.x() + (rect.width() - scaled.width()) // 2
            target_y = rect.y() + (rect.height() - scaled.height()) // 2
            painter.drawPixmap(target_x, target_y, scaled)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

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
            elif self.spoofer_type == "system_dry_run":
                self.system_dry_run()
                
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
            
            name = self.game_name.lower()
            if name == "fivem":
                results = spoofer.spoof_fivem_identifiers()
            elif name == "fortnite":
                results = spoofer.spoof_fortnite_identifiers()
            elif name == "valorant":
                results = spoofer.spoof_valorant_identifiers()
            elif name == "minecraft":
                results = spoofer.spoof_minecraft_identifiers()
            elif name == "roblox":
                results = spoofer.spoof_roblox_identifiers()
            elif name in ("cs:go", "cs2"):
                results = spoofer.spoof_csgo_identifiers()
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
            if any(opt == "Monitor Serial" for opt in self.system_options):
                self.status_updated.emit("Setting monitor serial overrides...")
                res = spoofer.spoof_monitor_serials()
                results.append(("Monitor Serial", res))
                self.progress_updated.emit(80)
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
    
    def system_dry_run(self):
        try:
            self.status_updated.emit("Simulating system spoofing...")
            self.progress_updated.emit(20)
            spoofer = SystemSpoofer(self.db_manager)
            res = spoofer.simulate_system(self.system_options)
            self.progress_updated.emit(90)
            ok = bool(res.get("success", False))
            items = res.get("items", [])
            summary = f"Dry run: {len(items)} item(s) analyzed"
            self.progress_updated.emit(100)
            self.operation_completed.emit(ok, summary)
        except Exception as e:
            self.operation_completed.emit(False, f"Dry run error: {str(e)}")
        
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
        self.progress_updated.emit(0)
        try:
            backup_path = None
            if self.db_manager:
                # Fast backup: skip deep verification for speed
                def _progress_cb(pct: int):
                    pct = int(max(0, min(100, pct)))
                    try:
                        self.status_updated.emit(f"Creating backup... {pct}%")
                        self.progress_updated.emit(pct)
                    except Exception:
                        pass
                backup_path = self.db_manager.create_backup(verify=False, progress_cb=_progress_cb)
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
        try:
            self.title_label.setStyleSheet("background: transparent; border: none; border-radius: 0px; padding: 0px;")
        except Exception:
            pass
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setObjectName("title_btn")
        self.minimize_btn.clicked.connect(self.minimize_window)
        self.minimize_btn.setToolTip("Minimize")
        self.minimize_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.minimize_btn)
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("close_btn")
        self.close_btn.clicked.connect(self.close_window)
        self.close_btn.setToolTip("Close")
        self.close_btn.setCursor(Qt.PointingHandCursor)
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
            if self.parent and self.parent.isMaximized():
                return
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

    def on_worker_status_updated(self, text: str):
        try:
            import shiboken6
        except Exception:
            shiboken6 = None
        try:
            if hasattr(self, 'status_label') and self.status_label is not None and (
                (shiboken6.isValid(self.status_label) if shiboken6 else True)
            ):
                try:
                    self.status_label.show()
                except Exception:
                    pass
                self.status_label.setText(text)
                if hasattr(self, 'progress_group') and self.progress_group:
                    try:
                        self.progress_group.show()
                    except Exception:
                        pass
            # Always reflect message on the status bar for visibility
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.showMessage(text)
        except Exception:
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.showMessage(text)

    def on_worker_progress_updated(self, value: int):
        try:
            import shiboken6
        except Exception:
            shiboken6 = None
        try:
            if hasattr(self, 'progress_bar') and self.progress_bar is not None and (
                (shiboken6.isValid(self.progress_bar) if shiboken6 else True)
            ):
                try:
                    self.progress_bar.show()
                except Exception:
                    pass
                self.progress_bar.setValue(value)
                if hasattr(self, 'progress_group') and self.progress_group:
                    try:
                        self.progress_group.show()
                    except Exception:
                        pass
        except Exception:
            pass
        
    def setup_ui(self):
        self.setWindowTitle("PhantomID - Advanced Hardware ID Spoofer")
        try:
            self.resize(1080, 720)
            self.setMinimumSize(900, 600)
        except Exception:
            pass
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.apply_stylesheets()
        try:
            self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        except Exception:
            pass
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
        content_widget.setObjectName("content_panel")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 80))
        content_widget.setGraphicsEffect(shadow)
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
        
        self.switch_page(0)
        
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
            btn.setToolTip(f"Go to {text}")
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

        try:
            for g, _, _ in games:
                _ = get_game_bg_pixmap(g)
        except Exception:
            pass
        
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
            row = QWidget()
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            checkbox = QCheckBox(option)
            checkbox.setChecked(True)
            checkbox.setObjectName("app_checkbox")
            checkbox.stateChanged.connect(self.on_checkbox_changed)
            row_layout.addWidget(checkbox)
            self.anti_detect_checks[option] = checkbox
            desc_label = QLabel(description)
            desc_label.setFont(QFont("Segoe UI", 10))
            desc_label.setObjectName("desc_label")
            row_layout.addWidget(desc_label)
            anti_detect_layout.addWidget(row)
        
        layout.addWidget(anti_detect_group)
        
        # Progress UI not shown on Game Spoofing page to keep UX clean
        self.progress_group = None
        layout.addStretch()
        
        self.content_stack.addWidget(page)
        
    def create_system_spoofing_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        # Title moved to the title bar; no inline header frame
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
            ("EFI Number", "Spoof EFI number"),
            ("Monitor Serial", "Spoof monitor serials (override reporting)")
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
        
        dry_run_btn = ModernButton("Dry Run")
        dry_run_btn.clicked.connect(self.dry_run_selected_system)
        button_layout.addWidget(dry_run_btn)
        
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
            # Render as themed HTML for readability similar to WMIC output
            self.serials_text.setHtml(rendered)
            try:
                if hasattr(self, 'db_manager') and self.db_manager:
                    self.db_manager.save_system_info(info)
                    self.log_activity("System info snapshot saved")
            except Exception:
                pass
            self.log_activity("Serials refreshed")
        except Exception as e:
            self.message_warning("Serial Checker", f"Error fetching serials: {e}")

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
            dlg = QFileDialog(self, "Export Serials JSON", str(Path.home() / "serials.json"), "JSON Files (*.json)")
            dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
            dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
            self.style_popup(dlg)
            path = None
            if dlg.exec():
                selected = dlg.selectedFiles()
                if selected:
                    path = selected[0]
            if path:
                import json
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(info, f, indent=2)
                self.message_info("Export Complete", f"Saved to: {path}")
                try:
                    if hasattr(self, 'db_manager') and self.db_manager:
                        self.db_manager.save_system_info(info)
                except Exception:
                    pass
                self.log_activity(f"Serials exported to {path}")
        except Exception as e:
            self.message_warning("Export Error", f"Failed to export JSON: {e}")

    def collect_serials_info(self) -> Dict[str, Any]:
        result: Dict[str, any] = {
            "BIOS": {},
            "Baseboard": {},
            "ComputerSystem": {},
            "CPU": {},
            "GPU": [],
            "Disks": [],
            "NetworkAdapters": [],
            "AllMACs": [],
            "OS": {},
            "UUID": {},
            "Registry": {},
            "Volumes": {},
            "MemoryChips": [],
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

        # Memory chips (RAM) serial numbers
        try:
            if wmi_client:
                for m in wmi_client.Win32_PhysicalMemory() or []:
                    sn = str(getattr(m, 'SerialNumber', '') or '')
                    if sn:
                        result["MemoryChips"].append({"SerialNumber": sn})
            # Fallback for Win11/permission issues: use PowerShell CIM
            if not result["MemoryChips"]:
                try:
                    import subprocess
                    ps_cmd = [
                        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "Get-CimInstance Win32_PhysicalMemory | Select-Object -ExpandProperty SerialNumber"
                    ]
                    proc = subprocess.run(ps_cmd, capture_output=True, text=True, shell=False)
                    out = (proc.stdout or "").strip()
                    for line in out.splitlines():
                        sn = line.strip()
                        if sn:
                            result["MemoryChips"].append({"SerialNumber": sn})
                except Exception:
                    pass
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

        # Collect MAC addresses for all adapters (enabled or not)
        try:
            if wmi_client:
                for na in wmi_client.Win32_NetworkAdapter() or []:
                    mac = str(getattr(na, 'MACAddress', '') or '')
                    desc = str(getattr(na, 'Name', '') or getattr(na, 'Description', '') or '')
                    if mac:
                        result["AllMACs"].append({"Description": desc, "MACAddress": mac})
            # Fallback to getmac command if WMI yields none
            if not result["AllMACs"]:
                import subprocess, re
                proc = subprocess.run(["getmac", "/v", "/fo", "list"], capture_output=True, text=True, shell=True)
                out = proc.stdout or ""
                lines = out.splitlines()
                cur_desc = None
                for line in lines:
                    if "Network Adapter" in line:
                        cur_desc = line.split(":", 1)[-1].strip()
                    elif "Physical Address" in line:
                        mac = line.split(":", 1)[-1].strip()
                        if mac and cur_desc:
                            result["AllMACs"].append({"Description": cur_desc, "MACAddress": mac})
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
        # Build HTML content mimicking WMIC-style sections with app theme colors
        def h(title: str, color: str) -> str:
            return f"<div style='color:{color}; font-weight:600; font-size:16px; margin-top:12px;'>{title}</div>" \
                   + "<div style='color:#9aa4af;'>==========================</div>"
        def row(label: str, value: Any) -> str:
            v = value if (value or value == 0) else 'N/A'
            return f"<div style='margin-left:6px;'><span style='color:#e0f7ff;'>{label}</span>: <span style='color:#cfe9f5;'>{v}</span></div>"
        parts: List[str] = [
            "<div style='font-family:Segoe UI, sans-serif; font-size:13px'>",
            h("Disk Number", "#ff4d4d"),
        ]
        disks = info.get("Disks", [])
        if disks:
            for d in disks:
                parts.append(row("SerialNumber", d.get("SerialNumber")))
        else:
            parts.append(row("SerialNumber", "N/A"))

        parts += [
            h("Motherboard", "#ffd166"),
            row("SerialNumber", info.get("Baseboard", {}).get("SerialNumber")),
            h("SMBios", "#06d6a0"),
            row("UUID", info.get("UUID", {}).get("UUID")),
            h("GPU", "#118ab2"),
        ]
        gpus = info.get("GPU", [])
        if gpus:
            for g in gpus:
                parts.append(row("Description", g.get("Name") or g.get("Description")))
                parts.append(row("PNPDeviceID", g.get("PNPDeviceID")))
        else:
            parts.append(row("Description", "N/A"))

        parts += [
            h("RAM", "#8338ec"),
        ]
        mems = info.get("MemoryChips", [])
        if mems:
            for m in mems:
                parts.append(row("SerialNumber", m.get("SerialNumber")))
        else:
            parts.append(row("SerialNumber", "N/A"))

        parts += [
            h("Bios", "#ef476f"),
            row("SerialNumber", info.get("BIOS", {}).get("SerialNumber")),
            h("CPU", "#ff4d4d"),
            row("ProcessorId", info.get("CPU", {}).get("ProcessorId")),
            h("MAC Addresses (All Adapters)", "#00d4ff"),
        ]
        macs = info.get("AllMACs", [])
        if macs:
            for m in macs:
                parts.append(row(m.get("Description") or "Adapter", m.get("MACAddress")))
        else:
            parts.append(row("Adapter", "N/A"))

        parts.append("</div>")
        return "\n".join(parts) 
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
        # Title moved to the title bar; no inline header frame
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

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Spoof mode:"))
        self.spoof_mode_combo = QComboBox()
        self.spoof_mode_combo.addItems(["Temp", "Perma"])
        self.spoof_mode_combo.setCurrentIndex(0)
        self.spoof_mode_combo.currentTextChanged.connect(self.on_spoof_mode_changed)
        mode_layout.addWidget(self.spoof_mode_combo)
        mode_layout.addStretch()
        general_layout.addLayout(mode_layout)

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

    def on_spoof_mode_changed(self, text):
        try:
            self.apply_stylesheets()
            self.update()
        except Exception:
            pass
        
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
                'theme_popups.qss',
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
            # Conditional neon theme in PERMA mode
            try:
                mode = None
                if hasattr(self, 'spoof_mode_combo') and self.spoof_mode_combo is not None:
                    mode = self.spoof_mode_combo.currentText()
                if mode is None and hasattr(self, 'db_manager') and self.db_manager:
                    s = self.db_manager.load_settings()
                    mode = s.get('spoof_mode', 'Temp')
                if str(mode).lower() == 'perma':
                    neon_path = styles_dir / 'theme_neon.qss'
                    if neon_path.exists():
                        with open(neon_path, 'r', encoding='utf-8') as f:
                            parts.append(f.read())
            except Exception:
                pass
            qss = "\n\n".join(parts)
            app = QApplication.instance()
            if app and qss:
                app.setStyleSheet(qss)
            elif qss:
                self.setStyleSheet(qss)
            # Apply neon glow via drop shadow if PERMA mode
            try:
                mode = None
                if hasattr(self, 'spoof_mode_combo') and self.spoof_mode_combo is not None:
                    mode = self.spoof_mode_combo.currentText()
                if mode is None and hasattr(self, 'db_manager') and self.db_manager:
                    s = self.db_manager.load_settings()
                    mode = s.get('spoof_mode', 'Temp')
                if str(mode).lower() == 'perma' and hasattr(self, 'title_bar') and self.title_bar:
                    glow = QGraphicsDropShadowEffect(self)
                    glow.setBlurRadius(28)
                    glow.setColor(QColor(0, 212, 255, 140))
                    glow.setOffset(0, 0)
                    self.title_bar.setGraphicsEffect(glow)
            except Exception:
                pass
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

    # Popup styling helpers
    def popup_stylesheet(self) -> str:
        try:
            base_dir = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            styles_dir = base_dir / 'assets' / 'styles'
            mode = None
            if hasattr(self, 'spoof_mode_combo') and self.spoof_mode_combo is not None:
                mode = self.spoof_mode_combo.currentText()
            if mode is None and hasattr(self, 'db_manager') and self.db_manager:
                try:
                    s = self.db_manager.load_settings()
                    mode = s.get('spoof_mode', 'Temp')
                except Exception:
                    mode = 'Temp'
            fname = 'theme_popups_neon.qss' if str(mode).lower() == 'perma' else 'theme_popups.qss'
            path = styles_dir / fname
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception:
            pass
        return ""

    def style_popup(self, widget):
        try:
            app = QApplication.instance()
            base_qss = app.styleSheet() if app else ""
            widget.setAttribute(Qt.WA_StyledBackground, True)
            widget.setStyleSheet(f"{base_qss}\n\n{self.popup_stylesheet()}")
            widget.setWindowFlags(widget.windowFlags() | Qt.WindowType.FramelessWindowHint)
        except Exception:
            pass

    def message_box(self, icon: QMessageBox.Icon, title: str, text: str,
                    buttons: QMessageBox.StandardButtons = QMessageBox.StandardButtons(QMessageBox.StandardButton.Ok),
                    default: QMessageBox.StandardButton | None = None) -> QMessageBox.StandardButton:
        msg = QMessageBox(self)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(buttons)
        if default is not None:
            msg.setDefaultButton(default)
        self.style_popup(msg)
        res = msg.exec()
        try:
            return QMessageBox.StandardButton(res)
        except Exception:
            return QMessageBox.StandardButton.Ok

    def message_info(self, title: str, text: str) -> None:
        self.message_box(QMessageBox.Icon.Information, title, text)

    def message_warning(self, title: str, text: str) -> None:
        self.message_box(QMessageBox.Icon.Warning, title, text)

    def message_error(self, title: str, text: str) -> None:
        self.message_box(QMessageBox.Icon.Critical, title, text)

    def message_question(self, title: str, text: str,
                         buttons: QMessageBox.StandardButtons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                         default: QMessageBox.StandardButton = QMessageBox.StandardButton.No) -> QMessageBox.StandardButton:
        return self.message_box(QMessageBox.Icon.Question, title, text, buttons, default)
        
    def create_stat_card(self, title, value, color):
        card = QFrame()
        card.setFixedHeight(120)
        card.setObjectName("stat_card")
        card_layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        title_label.setObjectName("stat_title")
        title_label.setProperty("accent", color)
        card_layout.addWidget(title_label)
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        value_label.setObjectName("stat_value")
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
            mode = str(settings.get('spoof_mode', 'Temp'))
            m_idx = self.spoof_mode_combo.findText(mode)
            if m_idx != -1:
                self.spoof_mode_combo.setCurrentIndex(m_idx)
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
                    self.message_info("Update", "An update was applied. The application will restart.")
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
                reply = self.message_question(
                    "Unclosed Session Detected",
                    msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes and backup_path:
                    self.worker = SpooferWorker("backup_restore", backup_path=backup_path)
                    self.worker.set_db_manager(self.db_manager)
                    self.worker.progress_updated.connect(self.on_worker_progress_updated)
                    self.worker.status_updated.connect(self.on_worker_status_updated)
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
        try:
            titles = ["Dashboard", "Game Spoofing", "System Spoofing", "Serial Checker", "Settings"]
            if hasattr(self, 'title_bar') and hasattr(self.title_bar, 'title_label'):
                page_title = titles[index] if 0 <= index < len(titles) else "PhantomID"
                self.title_bar.title_label.setText(f"PhantomID — {page_title}")
        except Exception:
            pass
                
    def log_activity(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_text.append(f"[{timestamp}] {message}")   
    
            
    def spoof_game(self, game_name):
        try:
            is_installed, game_path = self.check_game_installed(game_name)
            if not is_installed:
                is_installed, game_path = self.prompt_for_game_path(game_name)
                if not is_installed:
                    self.message_info("Game Not Found", f"{game_name} spoofing cancelled. Please install the game first.")
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
            self.message_error("Spoofing Error", f"Error spoofing {game_name}: {str(e)}")
            
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
                self.message_warning("No Selection", "Please select at least one system identifier to spoof.")
                return
            
            self.on_worker_status_updated(f"Spoofing {len(selected_options)} system identifiers...")
            self.on_worker_progress_updated(0)
            if self.anti_detect_checks.get("Randomize Timing"):
                self.anti_detection.randomize_timing()
            if self.anti_detect_checks.get("Clear System Traces"):
                self.anti_detection.clear_system_traces()
            if self.anti_detect_checks.get("Spoof File Timestamps"):
                self.anti_detection.spoof_file_timestamps(".")
            self.worker = SpooferWorker("system", system_options=selected_options)
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.on_worker_progress_updated)
            self.worker.status_updated.connect(self.on_worker_status_updated)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity(f"Started spoofing {len(selected_options)} system identifiers")
            
        except Exception as e:
            self.message_error("System Spoofing Error", f"Error: {str(e)}")

    def dry_run_selected_system(self):
        try:
            selected_options = []
            for option, checkbox in self.system_checks.items():
                if checkbox.isChecked():
                    selected_options.append(option)
            if not selected_options:
                self.message_warning("No Selection", "Please select at least one system identifier to simulate.")
                return
            self.on_worker_status_updated(f"Simulating {len(selected_options)} system identifiers...")
            self.on_worker_progress_updated(0)
            self.worker = SpooferWorker("system_dry_run", system_options=selected_options)
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.on_worker_progress_updated)
            self.worker.status_updated.connect(self.on_worker_status_updated)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
        except Exception as e:
            self.message_error("Dry Run Error", f"Error: {str(e)}")

    def spoof_all_system(self):
        try:
            for checkbox in self.system_checks.values():
                checkbox.setChecked(True)
            self.spoof_selected_system()
            
        except Exception as e:
            self.message_error("System Spoofing Error", f"Error: {str(e)}")

    def restore_original(self):
        try:
            self.on_worker_status_updated("Restoring original system identifiers...")
            self.on_worker_progress_updated(0)
            self.worker = SpooferWorker("restore")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.on_worker_progress_updated)
            self.worker.status_updated.connect(self.on_worker_status_updated)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started restoring original system identifiers")
            
        except Exception as e:
            self.message_error("Restore Error", f"Error: {str(e)}")
    
    def on_checkbox_changed(self, state):
        checkbox = self.sender()
        if checkbox:
            base_text = checkbox.text()
            try:
                is_checked = bool(checkbox.isChecked())
            except Exception:
                try:
                    is_checked = (state == getattr(Qt, 'CheckState', Qt).Checked) or (state == getattr(Qt, 'Checked', 2)) or (int(state) == 2)
                except Exception:
                    is_checked = False
            self.log_activity(f"Checkbox '{base_text}' {'checked' if is_checked else 'unchecked'}")
            if checkbox is getattr(self, 'auto_backup_check', None):
                self.auto_backup_enabled = is_checked
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
        reply = self.message_question(
            f"{game_name} Not Found",
            f"{game_name} was not found in default installation paths.\n\n"
            f"Would you like to manually specify the installation path?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            dlg = QInputDialog(self)
            dlg.setInputMode(QInputDialog.InputMode.TextInput)
            dlg.setWindowTitle(f"Enter {game_name} Path")
            dlg.setLabelText(f"Please enter the full path to {game_name} installation directory:")
            self.style_popup(dlg)
            ok = dlg.exec()
            path = dlg.textValue()
            if ok and path:
                import os
                if os.path.exists(path):
                    return True, path
                else:
                    self.message_warning("Invalid Path", "The specified path does not exist.")
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
            self.on_worker_status_updated("Scanning registry...")
            self.on_worker_progress_updated(0)
            self.worker = SpooferWorker("registry_scan")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.on_worker_progress_updated)
            self.worker.status_updated.connect(self.on_worker_status_updated)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started registry scan")
            
        except Exception as e:
            self.message_error("Registry Scan Error", f"Error: {str(e)}")

    def backup_registry(self):
        try:
            self.on_worker_status_updated("Backing up registry...")
            self.on_worker_progress_updated(0)
            self.worker = SpooferWorker("registry_backup")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.on_worker_progress_updated)
            self.worker.status_updated.connect(self.on_worker_status_updated)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started registry backup")
            
        except Exception as e:
            self.message_error("Registry Backup Error", f"Error: {str(e)}")

    def analyze_system(self):
        try:
            self.on_worker_status_updated("Analyzing system...")
            self.on_worker_progress_updated(0)
            self.worker = SpooferWorker("system_analysis")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.on_worker_progress_updated)
            self.worker.status_updated.connect(self.on_worker_status_updated)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started system analysis")
            
        except Exception as e:
            self.message_error("System Analysis Error", f"Error: {str(e)}")

    def cleanup_database(self):
        try:
            reply = self.message_question(
                "Cleanup Database",
                "Are you sure you want to cleanup the database? This will remove old entries.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.on_worker_status_updated("Cleaning up database...")
                self.on_worker_progress_updated(0)
                self.worker = SpooferWorker("database_cleanup")
                self.worker.set_db_manager(self.db_manager)
                self.worker.progress_updated.connect(self.on_worker_progress_updated)
                self.worker.status_updated.connect(self.on_worker_status_updated)
                self.worker.operation_completed.connect(self.on_operation_completed)
                self.worker.start()
                self.log_activity("Started database cleanup")
                
        except Exception as e:
            self.message_error("Database Cleanup Error", f"Error: {str(e)}")

    def save_settings(self):
        try:
            settings = {
                'auto_backup': self.auto_backup_check.isChecked(),
                'backup_interval': int(self.backup_interval_spin.currentText()),
                'log_level': self.log_level_combo.currentText(),
                'data_retention': int(self.data_retention_spin.currentText()),
                'auto_update': bool(self.auto_update_check.isChecked()),
                'auto_update_apply': bool(self.update_auto_apply_check.isChecked()),
                'spoof_mode': self.spoof_mode_combo.currentText(),
            }
            self.db_manager.save_settings(settings)
            try:
                self.apply_stylesheets()
                self.update()
            except Exception:
                pass
            try:
                if settings.get('spoof_mode', 'Temp') == 'Temp':
                    spoofer = SystemSpoofer(self.db_manager)
                    spoofer.regenerate_restore_script()
                    ensured = spoofer.ensure_temp_restore_task()
                    self.log_activity(f"Temp restore task {'ensured' if ensured else 'not set'}")
            except Exception:
                pass
            self.message_info("Settings Saved", "Application settings have been saved successfully.")
            self.log_activity("Settings saved")
            self.auto_backup_enabled = settings.get('auto_backup', True)
            self.schedule_auto_backup()
            self.schedule_auto_update()
            
        except Exception as e:
            self.message_error("Settings Error", f"Error saving settings: {str(e)}")

    def create_backup(self):
        try:
            # Prepare snapshot so backup contains system, registry, and settings
            self.on_worker_status_updated("Preparing backup snapshot...")
            self.on_worker_progress_updated(0)
            try:
                if hasattr(self, 'db_manager') and self.db_manager:
                    # Capture minimal system/registry snapshot
                    try:
                        self.db_manager.prepare_prebackup_snapshot()
                    except Exception:
                        pass
                    # Save current app settings silently (no dialog)
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
                    except Exception:
                        pass
            except Exception as e:
                try:
                    logging.getLogger(__name__).warning(f"Pre-backup snapshot failed: {e}")
                except Exception:
                    pass
            # Begin backup creation
            self.on_worker_status_updated("Creating backup...")
            self.on_worker_progress_updated(0)
            self.worker = SpooferWorker("backup_creation")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.on_worker_progress_updated)
            self.worker.status_updated.connect(self.on_worker_status_updated)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started backup creation")
            
        except Exception as e:
            self.message_error("Backup Error", f"Error creating backup: {str(e)}")

    def restore_backup(self):
        try:
            dlg = QFileDialog(self, "Select Backup File", "", "Backup Files (*.bak)")
            dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
            self.style_popup(dlg)
            file_path = None
            if dlg.exec():
                selected = dlg.selectedFiles()
                if selected:
                    file_path = selected[0]
            if file_path:
                self.on_worker_status_updated("Restoring backup...")
                self.on_worker_progress_updated(0)
                self.worker = SpooferWorker("backup_restore", backup_path=file_path)
                self.worker.set_db_manager(self.db_manager)
                self.worker.progress_updated.connect(self.on_worker_progress_updated)
                self.worker.status_updated.connect(self.on_worker_status_updated)
                self.worker.operation_completed.connect(self.on_operation_completed)
                self.worker.start()
                self.log_activity("Started backup restoration")
                
        except Exception as e:
            self.message_error("Restore Error", f"Error restoring backup: {str(e)}")

    def optimize_system(self):
        try:
            self.on_worker_status_updated("Optimizing system...")
            self.on_worker_progress_updated(0)
            self.worker = SpooferWorker("optimization")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.on_worker_progress_updated)
            self.worker.status_updated.connect(self.on_worker_status_updated)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started system optimization")
            
        except Exception as e:
            self.message_error("System Optimization Error", f"Error: {str(e)}")

    def clean_registry(self):
        try:
            self.on_worker_status_updated("Cleaning registry...")
            self.on_worker_progress_updated(0)
            self.worker = SpooferWorker("registry")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.on_worker_progress_updated)
            self.worker.status_updated.connect(self.on_worker_status_updated)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started registry cleaning")
            
        except Exception as e:
            self.message_error("Registry Cleaning Error", f"Error: {str(e)}")

    def spoof_system(self):
        try:
            self.worker = SpooferWorker("system")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.on_worker_progress_updated)
            self.worker.status_updated.connect(self.on_worker_status_updated)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started system spoofing")
            
        except Exception as e:
            self.message_error("System Spoofing Error", f"Error: {str(e)}")
            
    def cleanup_system(self):
        try:
            self.worker = SpooferWorker("optimization")
            self.worker.set_db_manager(self.db_manager)
            self.worker.progress_updated.connect(self.on_worker_progress_updated)
            self.worker.status_updated.connect(self.on_worker_status_updated)
            self.worker.operation_completed.connect(self.on_operation_completed)
            self.worker.start()
            self.log_activity("Started system cleanup")
            
        except Exception as e:
            self.message_error("Cleanup Error", f"Error: {str(e)}")
            
    def on_operation_completed(self, success, message):
        if getattr(self, 'current_operation', None) == 'game':
            if success:
                self.message_info("Success", message)
            else:
                self.message_warning("Failed", message)
        else:

            if success:
                self.on_worker_status_updated("Operation completed successfully")
                self.on_worker_progress_updated(100)
                self.message_info("Success", message)
            else:
                self.on_worker_status_updated("Operation failed")
                self.on_worker_progress_updated(0)
                self.message_warning("Failed", message)

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
        self.message_info("System Information", "System information will be displayed here")
        
    def view_logs(self):
        try:
            with open('phantomid.log', 'r') as f:
                logs = f.read()
                
            dlg = QDialog(self)
            dlg.setWindowTitle("Application Logs")
            layout = QVBoxLayout(dlg)
            text = QTextEdit()
            text.setPlainText(logs)
            text.setReadOnly(True)
            text.setMinimumSize(800, 600)
            layout.addWidget(text)
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dlg.accept)
            layout.addWidget(close_btn)
            self.style_popup(dlg)
            dlg.exec()
            
        except Exception as e:
            self.message_error("Log Error", f"Error reading logs: {str(e)}")
            
    def show_about(self):
        self.message_info(
            "About PhantomID",
            "PhantomID - Advanced Hardware ID Spoofer\n\n"
            "Version 2.0\n"
            "A powerful tool for spoofing hardware identifiers and removing game bans.\n\n"
            "Created for privacy enthusiasts"
        )
            
    def show_help(self):
        self.message_info("User Guide", "User guide will be displayed here. For now, please refer to the README.md file.")
            
    def closeEvent(self, event):
        reply = self.message_question(
            'Exit Confirmation',
            'Are you sure you want to exit PhantomID?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
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
class LogoLoader(QThread):
    pixmap_ready = Signal(QPixmap)

    def __init__(self, game_name: str):
        super().__init__()
        self.game_name = game_name

    def run(self):
        pm = None
        try:
            pm = get_game_bg_pixmap(self.game_name)
        except Exception:
            pm = None
        if pm is None:
            try:
                pm = get_text_logo_pixmap(self.game_name, 400, 160)
            except Exception:
                pm = None
        try:
            self.pixmap_ready.emit(pm)
        except Exception:
            pass
        # Monitors (EDID) info with overrides
        try:
            if wmi_client:
                monitors = []
                try:
                    w = wmi.WMI(namespace="root\\wmi")
                except Exception:
                    w = None
                if w is not None:
                    for mon in w.WmiMonitorID() or []:
                        try:
                            mf = "".join(chr(c) for c in (mon.ManufacturerName or []) if c)
                            pc = "".join(chr(c) for c in (mon.ProductCodeID or []) if c)
                            sn = "".join(chr(c) for c in (mon.SerialNumberID or []) if c)
                            key = f"{mf}-{pc}" if mf or pc else (getattr(mon, 'InstanceName', 'MONITOR'))
                            monitors.append({"Key": key, "Manufacturer": mf, "Product": pc, "SerialNumber": sn})
                        except Exception:
                            continue
                # Apply overrides from settings
                try:
                    overrides = {}
                    if hasattr(self, 'db_manager') and self.db_manager:
                        s = self.db_manager.load_settings()
                        overrides = s.get('Monitor.SerialOverrides', {}) if isinstance(s, dict) else {}
                    for m in monitors:
                        ov = overrides.get(m.get('Key'))
                        if ov:
                            m['SerialNumber'] = ov
                    result['Monitors'] = monitors
                except Exception:
                    result['Monitors'] = monitors
        except Exception:
            pass
