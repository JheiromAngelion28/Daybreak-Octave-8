import sys
import os
import json
import time
import math
import string
import base64
import hashlib
import gc
from pathlib import Path

# --- CRYPTOGRAPHY IMPORTS ---
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# --- PYQT6 UI IMPORTS ---
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget, 
                             QVBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTabWidget, QHBoxLayout, QFrame, QSlider, 
                             QListWidget, QMessageBox, QComboBox, QInputDialog, 
                             QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QColor, QPainter, QPen, QFont

# =============================================================================
# 0. RESOURCE PATH RESOLVER (FOR .EXE COMPILATION)
# =============================================================================
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller stores the bundled files' paths in sys._MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If running from VS Code, just use the script's normal folder
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# =============================================================================
# 1. CUSTOM UI: REAL-TIME ENTROPY GAUGE
# =============================================================================
class StrengthGauge(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(160, 160)
        self.percent = 0
        self.status = "AWAITING"
        self.color = QColor("#58A6FF")

    def update_strength(self, password):
        if not password:
            self.percent = 0; self.status = "AWAITING"; self.color = QColor("#2A2F35")
            self.update(); return

        pool = 0
        if any(c.islower() for c in password): pool += 26
        if any(c.isupper() for c in password): pool += 26
        if any(c.isdigit() for c in password): pool += 10
        if any(c in string.punctuation for c in password): pool += 32
        
        entropy = len(password) * math.log2(pool) if pool > 0 else 0
        self.percent = min(100, int((entropy / 128.0) * 100))
        
        if entropy < 50: self.status = "WEAK"; self.color = QColor("#FF5F5F")
        elif entropy < 80: self.status = "MODERATE"; self.color = QColor("#FFBD2E")
        else: self.status = "STRONG"; self.color = QColor("#00D4FF")
        self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(15, 15, 130, 130)
        p.setPen(QPen(QColor("#2A2F35"), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, 0, 360 * 16)
        p.setPen(QPen(self.color, 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, 90 * 16, -int((self.percent / 100) * 360 * 16))
        p.setPen(self.color); p.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.percent}%")

# =============================================================================
# 2. SECURITY ENGINE (CRUD & ZERO TRUST)
# =============================================================================
class SecurityEngine:
    def __init__(self):
        self.fernet = None
        self.vault = {}
        # Ensure database saves in user's directory even if compiled to exe
        try:
            db_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            db_dir = os.getcwd()
        self.db_path = os.path.join(db_dir, "vault.db")
        self.is_online = True 

    def authenticate(self, user, pwd):
        if user == "Jheirom" and pwd == "1234":
            self._derive_key(pwd)
            self._load_db()
            return True
        return False

    def authenticate_recovery(self, recovery_key):
        if recovery_key == "DAYBREAK-RECOVERY-99X-ALPHA":
            self._derive_key("1234") 
            self._load_db()
            return True
        return False

    def _derive_key(self, pwd):
        salt = b'daybreak_enterprise_salt'
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
        self.fernet = Fernet(base64.urlsafe_b64encode(kdf.derive(pwd.encode())))

    def _save_db(self):
        if not self.fernet: return
        with open(self.db_path, "wb") as f:
            f.write(self.fernet.encrypt(json.dumps(self.vault).encode()))

    def _load_db(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "rb") as f:
                    self.vault = json.loads(self.fernet.decrypt(f.read()).decode())
            except: self.vault = {}

    def auto_vault_entry(self, app, user, pwd, cat):
        self.vault[app] = {"user": user, "pass": pwd, "cat": cat, "timestamp": time.time()}
        self._save_db()

    def delete_entry(self, app):
        if app in self.vault:
            del self.vault[app]
            self._save_db()

    def generate_det(self, app, length):
        if not app: return ""
        seed = str(self.fernet).encode() + app.lower().strip().encode()
        h = hashlib.sha512(seed).digest()
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join([chars[b % len(chars)] for b in h])[:length]

# =============================================================================
# 3. MAIN UI FLOW (IMAGE RENDERER UPDATE)
# =============================================================================
class DaybreakApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = SecurityEngine()
        self.setWindowTitle("Daybreak Octave 8 - Native Build")
        self.setFixedSize(800, 650) 
        
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #0A0D10; color: #E1E1E1; font-family: 'Segoe UI'; }
            QLineEdit { background-color: #12161B; border: 1px solid #2A2F35; border-radius: 8px; padding: 12px; color: white; font-size: 14px;}
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00D4FF, stop:1 #090979); color: white; border-radius: 8px; padding: 12px; font-weight: bold; border: none; }
            QPushButton:hover { border: 1px solid #00D4FF; }
            QPushButton#ActionBtn { background: #161B22; border: 1px solid #30363D; color: white; }
            QPushButton#ActionBtn:hover { background: #1F6FEB; border: 1px solid #58A6FF; }
            QPushButton#DangerBtn { background: #161B22; border: 1px solid #30363D; color: #FF5F5F; }
            QPushButton#DangerBtn:hover { background: #DA3633; color: white; border: 1px solid #FF5F5F; }
            QPushButton#NavBtn { background: transparent; border: none; text-align: left; padding: 15px; color: #8B949E; border-radius: 4px; }
            QPushButton#NavBtn:hover { background: #161B22; color: white; }
            QPushButton#NavBtnActive { background: #1F6FEB; color: white; text-align: left; padding: 15px; border-radius: 4px; }
            QFrame#Sidebar { background-color: #0D1117; border-right: 1px solid #30363D; }
            QFrame#Card { background-color: #161B22; border-radius: 12px; border: 1px solid #30363D; }
            QListWidget { background: #0D1117; border: 1px solid #2A2F35; border-radius: 8px; padding: 5px; outline: 0;}
            QListWidget::item { padding: 10px; border-bottom: 1px solid #161B22; }
            QListWidget::item:selected { background: #1F6FEB; border-radius: 4px; color: white; }
        """)

        self.idle_timer = QTimer(); self.idle_timer.timeout.connect(self.lockdown)
        self.clip_timer = QTimer(); self.clip_timer.timeout.connect(lambda: QApplication.clipboard().clear())

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.init_signin()

    def init_signin(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(50, 20, 50, 50)
        
        # --- BULLETPROOF LOGO RENDERING ---
        logo_path = resource_path("Desktop Password Manager App Logo.jpg")
        if os.path.exists(logo_path):
            logo = QLabel()
            logo.setPixmap(QPixmap(logo_path).scaledToWidth(150, Qt.TransformationMode.SmoothTransformation))
            layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)
            
        # --- BULLETPROOF HERO IMAGE RENDERING (New Image) ---
        hero_path = resource_path("Desktop Password Manager App Logo.png")
        if os.path.exists(hero_path):
            hero_label = QLabel()
            pixmap = QPixmap(hero_path)
            hero_label.setPixmap(pixmap.scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            layout.addWidget(hero_label, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            fallback = QLabel("[ COVER IMAGE MISSING ]")
            fallback.setStyleSheet("color: #FF5F5F; font-size: 16px;")
            layout.addWidget(fallback, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- LOGIN CONTROLS ---
        self.u_in = QLineEdit(placeholderText="Username (Jheirom)"); self.u_in.setFixedWidth(300)
        self.p_in = QLineEdit(placeholderText="Master Key (1234)", echoMode=QLineEdit.EchoMode.Password); self.p_in.setFixedWidth(300)
        
        btn_layout = QHBoxLayout()
        login_btn = QPushButton("UNLOCK SURFACE"); login_btn.clicked.connect(self.login)
        recovery_btn = QPushButton("EMERGENCY RECOVERY"); recovery_btn.setObjectName("DangerBtn"); recovery_btn.clicked.connect(self.recovery_login)
        
        btn_layout.addWidget(recovery_btn); btn_layout.addWidget(login_btn)
        
        layout.addWidget(self.u_in, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.p_in, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(btn_layout)
        self.stack.addWidget(page)

    def login(self):
        if self.db.authenticate(self.u_in.text(), self.p_in.text()):
            self.show_dashboard()
            self.idle_timer.start(300000)
        else: QMessageBox.warning(self, "Denied", "Authentication Failed")

    def recovery_login(self):
        key, ok = QInputDialog.getText(self, "Emergency Protocol", "Enter Physical Recovery Key:", QLineEdit.EchoMode.Normal)
        if ok and self.db.authenticate_recovery(key):
            QMessageBox.information(self, "Recovery Active", "Vault decrypted via Emergency Protocol.")
            self.show_dashboard()
        elif ok: QMessageBox.critical(self, "Lockout", "Invalid Recovery Key.")

    def show_dashboard(self):
        self.hub = QWidget()
        main_layout = QHBoxLayout(self.hub); main_layout.setContentsMargins(0,0,0,0)
        
        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(200)
        side_layout = QVBoxLayout(sidebar)
        logo = QLabel("DAYBREAK"); logo.setStyleSheet("font-size: 20px; font-weight: bold; color: #00D4FF; margin: 10px;")
        side_layout.addWidget(logo)
        
        self.nav_btns = []
        for i, name in enumerate(["VAULT", "GENERATOR"]):
            btn = QPushButton(name); btn.setObjectName("NavBtn" if i > 0 else "NavBtnActive")
            btn.clicked.connect(lambda _, x=i: self.switch_tab(x))
            side_layout.addWidget(btn); self.nav_btns.append(btn)
            
        side_layout.addStretch()
        
        self.net_btn = QPushButton("STATUS: ONLINE"); self.net_btn.setObjectName("ActionBtn")
        self.net_btn.clicked.connect(self.toggle_network)
        side_layout.addWidget(self.net_btn)

        logout = QPushButton("LOGOUT"); logout.setObjectName("NavBtn"); logout.clicked.connect(self.lockdown)
        side_layout.addWidget(logout)

        self.content = QStackedWidget()
        self.content.addWidget(self.create_vault_tab())
        self.content.addWidget(self.create_gen_tab())
        
        main_layout.addWidget(sidebar); main_layout.addWidget(self.content)
        self.stack.addWidget(self.hub)
        
        self.opacity_effect = QGraphicsOpacityEffect(self.hub)
        self.hub.setGraphicsEffect(self.opacity_effect)
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(800) 
        self.anim.setStartValue(0); self.anim.setEndValue(1)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.stack.setCurrentIndex(1)
        self.anim.start()

    def toggle_network(self):
        self.db.is_online = not self.db.is_online
        if self.db.is_online:
            self.net_btn.setText("STATUS: ONLINE")
            self.net_btn.setStyleSheet("color: #00D4FF;")
        else:
            self.net_btn.setText("STATUS: OFFLINE (Read-Only)")
            self.net_btn.setStyleSheet("color: #FF5F5F;")

    def switch_tab(self, index):
        self.content.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.setObjectName("NavBtnActive" if i == index else "NavBtn")
        self.setStyleSheet(self.styleSheet()) 

    def create_vault_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(40,20,40,20)
        layout.addWidget(QLabel("## DATABASE VAULT"))
        
        self.list_w = QListWidget(); self.list_w.addItems(self.db.vault.keys())
        self.list_w.itemClicked.connect(self.populate_edit_fields)
        self.list_w.itemDoubleClicked.connect(self.view_entry)
        
        card = QFrame(); card.setObjectName("Card"); c_layout = QVBoxLayout(card)
        self.app_i = QLineEdit(placeholderText="App Name"); self.user_i = QLineEdit(placeholderText="Username"); self.pass_i = QLineEdit(placeholderText="Password")
        self.cat_i = QComboBox(); self.cat_i.addItems(["Social", "Work", "Banking", "Infrastructure", "Bath Spa"])
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("SECURE NEW"); add_btn.clicked.connect(self.add_entry)
        edit_btn = QPushButton("UPDATE"); edit_btn.setObjectName("ActionBtn"); edit_btn.clicked.connect(self.edit_entry)
        del_btn = QPushButton("DELETE"); del_btn.setObjectName("DangerBtn"); del_btn.clicked.connect(self.delete_entry)
        
        btn_layout.addWidget(add_btn); btn_layout.addWidget(edit_btn); btn_layout.addWidget(del_btn)
        
        c_layout.addWidget(self.app_i); c_layout.addWidget(self.user_i); c_layout.addWidget(self.pass_i)
        c_layout.addWidget(self.cat_i); c_layout.addLayout(btn_layout)
        
        layout.addWidget(QLabel("Double-click an entry to copy its password.", styleSheet="color: #8B949E; font-size: 11px;"))
        layout.addWidget(self.list_w); layout.addWidget(card); return page

    def populate_edit_fields(self, item):
        app_name = item.text()
        e = self.db.vault[app_name]
        self.app_i.setText(app_name); self.app_i.setReadOnly(True) 
        self.user_i.setText(e['user']); self.pass_i.setText(e['pass']); self.cat_i.setCurrentText(e['cat'])

    def edit_entry(self):
        if not self.db.is_online:
            QMessageBox.warning(self, "Offline Mode", "Modifications disabled while offline to prevent sync conflicts.")
            return
        app_name = self.app_i.text()
        if app_name in self.db.vault:
            key, ok = QInputDialog.getText(self, "Zero-Trust", "Enter Main Key to modify:", QLineEdit.EchoMode.Password)
            if ok and key == "1234":
                self.db.auto_vault_entry(app_name, self.user_i.text(), self.pass_i.text(), self.cat_i.currentText())
                QMessageBox.information(self, "Success", f"Entry for {app_name} updated securely.")
                self.clear_inputs()
            elif ok: QMessageBox.warning(self, "Denied", "Invalid Key.")

    def delete_entry(self):
        if not self.db.is_online:
            QMessageBox.warning(self, "Offline Mode", "Deletions disabled while offline to prevent sync conflicts.")
            return
        app_name = self.app_i.text()
        if app_name in self.db.vault:
            key, ok = QInputDialog.getText(self, "Zero-Trust", "Enter Main Key to DELETE:", QLineEdit.EchoMode.Password)
            if ok and key == "1234":
                self.db.delete_entry(app_name)
                self.list_w.clear(); self.list_w.addItems(self.db.vault.keys())
                self.clear_inputs()
            elif ok: QMessageBox.warning(self, "Denied", "Invalid Key.")

    def clear_inputs(self):
        self.app_i.clear(); self.app_i.setReadOnly(False)
        self.user_i.clear(); self.pass_i.clear(); self.list_w.clearSelection()

    def create_gen_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(40,40,40,40)
        title = QLabel("PASSWORD GENERATOR"); title.setStyleSheet("font-size: 18px; font-weight: bold; color: #8B949E;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignTop)
        
        self.gauge = StrengthGauge()
        layout.addWidget(self.gauge, alignment=Qt.AlignmentFlag.AlignCenter)
        
        card = QFrame(); card.setObjectName("Card"); c_layout = QVBoxLayout(card)
        self.seed = QLineEdit(placeholderText="App Seed (e.g., Target Site)")
        self.slid = QSlider(Qt.Orientation.Horizontal); self.slid.setRange(8, 64); self.slid.setValue(16)
        self.len_lbl = QLabel("Length: 16")
        self.out = QLineEdit(readOnly=True); self.out.setStyleSheet("font-family: Consolas; font-size: 16px; color: #00D4FF; text-align: center;")
        
        self.slid.valueChanged.connect(self.update_live_gen)
        self.seed.textChanged.connect(self.update_live_gen)
        btn = QPushButton("GENERATE & COPY"); btn.clicked.connect(self.copy_gen)
        
        c_layout.addWidget(QLabel("Seed Origin")); c_layout.addWidget(self.seed)
        c_layout.addWidget(self.len_lbl); c_layout.addWidget(self.slid)
        c_layout.addWidget(self.out); c_layout.addWidget(btn)
        
        layout.addWidget(card); layout.addStretch(); return page

    def update_live_gen(self):
        val = self.slid.value()
        self.len_lbl.setText(f"Length: {val}")
        if self.seed.text():
            pwd = self.db.generate_det(self.seed.text(), val)
            self.out.setText(pwd); self.gauge.update_strength(pwd)
        else:
            self.out.clear(); self.gauge.update_strength("")

    def copy_gen(self):
        pwd = self.out.text()
        if pwd:
            QApplication.clipboard().setText(pwd); self.clip_timer.start(30000)
            QMessageBox.information(self, "Copied", "Password copied. Auto-clearing in 30s.")

    def add_entry(self):
        if not self.db.is_online:
            QMessageBox.warning(self, "Offline Mode", "Creating new entries requires an authenticated connection.")
            return

        if self.app_i.text() and not self.app_i.isReadOnly():
            self.db.auto_vault_entry(self.app_i.text(), self.user_i.text(), self.pass_i.text(), self.cat_i.currentText())
            self.list_w.clear(); self.list_w.addItems(self.db.vault.keys())
            self.clear_inputs()

    def view_entry(self, item):
        key, ok = QInputDialog.getText(self, "Vault Security", "Enter Main Key to decrypt:", QLineEdit.EchoMode.Password)
        if ok and key == "1234":
            e = self.db.vault[item.text()]
            ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(e.get('timestamp', 0)))
            QMessageBox.information(self, item.text(), f"User: {e['user']}\nPassword: {e['pass']}\nCategory: {e['cat']}\nAuth Time: {ts}\n\n(Copied to clipboard for 30s)")
            QApplication.clipboard().setText(e['pass']); self.clip_timer.start(30000)
        elif ok: QMessageBox.warning(self, "Access Denied", "Invalid Key.")

    def lockdown(self):
        self.db.fernet = None
        self.db.vault = {} 
        gc.collect() 
        self.stack.setCurrentIndex(0)
        self.u_in.clear(); self.p_in.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = DaybreakApp(); ex.show()
    sys.exit(app.exec())