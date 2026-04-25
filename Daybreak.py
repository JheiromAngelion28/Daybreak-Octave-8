import sys
import os
import json
import time
import base64
import hashlib
import string
import gc
from pathlib import Path

# Cryptography Imports (Upgraded to Scrypt)
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# PyQt6 UI Imports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget, 
                             QVBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTabWidget, QHBoxLayout, QFrame, QSlider, 
                             QListWidget, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt, QTimer, QUrl, QRectF
from PyQt6.QtGui import QPixmap, QColor, QPainter, QPen, QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

# ---------------------------------------------------------
# 1. CUSTOM UI: REAL-TIME STRENGTH GAUGE (Matches Image)
# ---------------------------------------------------------
class StrengthGauge(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(160, 160)
        self.percent = 0
        self.status = "AWAITING"
        self.color = QColor("#58A6FF") # Default Cyan

    def update_strength(self, password):
        if not password:
            self.percent = 0; self.status = "AWAITING"; self.color = QColor("#2A2F35")
            self.update(); return

        # Calculate Shannon Entropy
        pool = 0
        if any(c.islower() for c in password): pool += 26
        if any(c.isupper() for c in password): pool += 26
        if any(c.isdigit() for c in password): pool += 10
        if any(c in string.punctuation for c in password): pool += 32
        
        entropy = len(password) * math.log2(pool) if pool > 0 else 0
        
        # Max standard entropy target ~ 128 bits
        self.percent = min(100, int((entropy / 128.0) * 100))
        
        if entropy < 50:
            self.status = "WEAK"
            self.color = QColor("#FF5F5F") # Red
        elif entropy < 80:
            self.status = "MODERATE"
            self.color = QColor("#FFBD2E") # Yellow
        else:
            self.status = "STRONG"
            self.color = QColor("#00D4FF") # Daybreak Cyan
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(15, 15, 130, 130)

        # Draw Background Track
        painter.setPen(QPen(QColor("#2A2F35"), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(rect, 0, 360 * 16)

        # Draw Progress Arc
        painter.setPen(QPen(self.color, 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        span_angle = int((self.percent / 100) * 360 * 16)
        painter.drawArc(rect, 90 * 16, -span_angle) # Start at top, draw clockwise

        # Draw Text
        painter.setPen(self.color)
        painter.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.percent}%")
        
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(QRectF(15, 105, 130, 30), Qt.AlignmentFlag.AlignCenter, self.status)

# ---------------------------------------------------------
# 2. 3D ARCHITECTURE: DIAGNOSTIC RENDERER
# ---------------------------------------------------------
import math # Required for entropy calc
class Mobius3DView(QWebEngineView):
    def __init__(self, obj_filename):
        super().__init__()
        self.setFixedSize(450, 350)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.page().setBackgroundColor(QColor(0, 0, 0, 0)) 
        
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        
        script_dir = Path(__file__).parent.resolve()
        obj_path = script_dir / obj_filename
        self.file_exists = "true" if obj_path.exists() else "false"

        html = f"""
        <html>
          <head>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/OBJLoader.js"></script>
            <style>body {{ margin: 0; background: transparent !important; overflow: hidden; }} canvas {{ display: block; }}</style>
          </head>
          <body>
            <script>
              const scene = new THREE.Scene();
              const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
              const renderer = new THREE.WebGLRenderer({{ alpha: true, antialias: true }});
              renderer.setClearColor(0x000000, 0); 
              renderer.setSize(window.innerWidth, window.innerHeight);
              document.body.appendChild(renderer.domElement);

              const light = new THREE.PointLight(0x00D4FF, 2, 100);
              light.position.set(10, 10, 10);
              scene.add(light);
              scene.add(new THREE.AmbientLight(0x404040, 3));

              const geometry = new THREE.BoxGeometry(1, 1, 1);
              const material = new THREE.MeshStandardMaterial({{ color: 0x00D4FF, wireframe: true }});
              const cube = new THREE.Mesh(geometry, material);

              if ({self.file_exists}) {{
                const loader = new THREE.OBJLoader();
                loader.load('{obj_path.name}', (obj) => {{
                  obj.traverse((c) => {{ if (c.isMesh) c.material = new THREE.MeshStandardMaterial({{ color: 0x00D4FF, metalness: 0.9, roughness: 0.1 }}); }});
                  scene.add(obj);
                  function anim() {{ requestAnimationFrame(anim); obj.rotation.y += 0.01; renderer.render(scene, camera); }}
                  anim();
                }}, undefined, (err) => {{ scene.add(cube); animateFallback(); }});
              }} else {{ scene.add(cube); animateFallback(); }}

              function animateFallback() {{ requestAnimationFrame(animateFallback); cube.rotation.x += 0.01; cube.rotation.y += 0.01; renderer.render(scene, camera); }}
              camera.position.z = 3.5;
            </script>
          </body>
        </html>
        """
        self.setHtml(html, QUrl.fromLocalFile(str(script_dir) + os.path.sep))

# ---------------------------------------------------------
# 3. ENTERPRISE SECURITY ENGINE (SCRYPT UPGRADE)
# ---------------------------------------------------------
class SecurityEngine:
    def __init__(self):
        self.fernet = None
        self.vault = {}
        self.db_path = Path(__file__).parent.resolve() / "vault.db"

    def authenticate(self, user, pwd):
        if user == "Jheirom" and pwd == "1234":
            self._derive_key(pwd)
            self._load_db()
            return True
        return False

    def _derive_key(self, pwd):
        # UPGRADE: Scrypt is memory-hard, protecting against GPU attacks
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

    def auto_vault_entry(self, app, user, pwd, cat="General"):
        self.vault[app] = {"user": user, "pass": pwd, "cat": cat}
        self._save_db()

    def generate_det(self, app, length):
        if not app: return ""
        seed = str(self.fernet).encode() + app.lower().strip().encode()
        h = hashlib.sha512(seed).digest()
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join([chars[b % len(chars)] for b in h])[:length]

# ---------------------------------------------------------
# 4. MAIN UI HUB (MATCHING VISUAL REFERENCE)
# ---------------------------------------------------------
class DaybreakApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = SecurityEngine()
        self.setWindowTitle("Daybreak Octave 8")
        self.setFixedSize(800, 600) # Wider aspect ratio for Sidebar layout
        
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #0A0D10; color: #E1E1E1; font-family: 'Segoe UI'; }
            QLineEdit { background-color: #12161B; border: 1px solid #2A2F35; border-radius: 8px; padding: 12px; color: white; font-size: 14px;}
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00D4FF, stop:1 #090979); color: white; border-radius: 8px; padding: 14px; font-weight: bold; border: none; }
            QPushButton#NavBtn { background: transparent; border: none; text-align: left; padding: 15px; color: #8B949E; border-radius: 4px; }
            QPushButton#NavBtn:hover { background: #161B22; color: white; }
            QPushButton#NavBtnActive { background: #1F6FEB; color: white; text-align: left; padding: 15px; border-radius: 4px; }
            QFrame#Sidebar { background-color: #0D1117; border-right: 1px solid #30363D; }
            QFrame#Card { background-color: #161B22; border-radius: 12px; border: 1px solid #30363D; }
        """)

        self.idle_timer = QTimer(); self.idle_timer.timeout.connect(self.lockdown)
        self.clip_timer = QTimer(); self.clip_timer.timeout.connect(lambda: QApplication.clipboard().clear())

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.init_signin()

    def init_signin(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(50, 20, 50, 50)
        layout.addWidget(Mobius3DView("Rotated Strip.obj"), alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.u_in = QLineEdit(placeholderText="Username (Jheirom)"); self.u_in.setFixedWidth(300)
        self.p_in = QLineEdit(placeholderText="Password (1234)", echoMode=QLineEdit.EchoMode.Password); self.p_in.setFixedWidth(300)
        btn = QPushButton("UNLOCK SURFACE"); btn.setFixedWidth(300)
        btn.clicked.connect(self.login)
        
        layout.addWidget(self.u_in, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.p_in, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(page)

    def login(self):
        if self.db.authenticate(self.u_in.text(), self.p_in.text()):
            self.show_dashboard()
            self.idle_timer.start(300000)
        else: QMessageBox.warning(self, "Denied", "Authentication Failed")

    def show_dashboard(self):
        hub = QWidget(); main_layout = QHBoxLayout(hub); main_layout.setContentsMargins(0,0,0,0)
        
        # Reference-Accurate Sidebar
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
        logout = QPushButton("LOGOUT"); logout.setObjectName("NavBtn"); logout.clicked.connect(self.lockdown)
        side_layout.addWidget(logout)

        # Content Area Stack
        self.content = QStackedWidget()
        self.content.addWidget(self.create_vault_tab())
        self.content.addWidget(self.create_gen_tab())
        
        main_layout.addWidget(sidebar); main_layout.addWidget(self.content)
        self.stack.addWidget(hub); self.stack.setCurrentIndex(1)

    def switch_tab(self, index):
        self.content.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.setObjectName("NavBtnActive" if i == index else "NavBtn")
        self.setStyleSheet(self.styleSheet()) # Force UI refresh

    def create_vault_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(40,40,40,40)
        layout.addWidget(QLabel("## DATABASE VAULT"))
        
        self.list_w = QListWidget(); self.list_w.addItems(self.db.vault.keys())
        self.list_w.itemClicked.connect(self.view_entry)
        
        card = QFrame(); card.setObjectName("Card"); c_layout = QVBoxLayout(card)
        self.app_i = QLineEdit(placeholderText="App Name")
        self.user_i = QLineEdit(placeholderText="Username")
        self.pass_i = QLineEdit(placeholderText="Password")
        btn = QPushButton("SECURE ENTRY"); btn.clicked.connect(self.add_entry)
        
        c_layout.addWidget(self.app_i); c_layout.addWidget(self.user_i); c_layout.addWidget(self.pass_i); c_layout.addWidget(btn)
        layout.addWidget(self.list_w); layout.addWidget(card); return page

    def create_gen_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(40,40,40,40)
        
        title = QLabel("PASSWORD GENERATOR"); title.setStyleSheet("font-size: 18px; font-weight: bold; color: #8B949E;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignTop)
        
        # Real-time Strength Gauge Layout
        self.gauge = StrengthGauge()
        layout.addWidget(self.gauge, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Interactive Controls
        card = QFrame(); card.setObjectName("Card"); c_layout = QVBoxLayout(card)
        
        self.seed = QLineEdit(placeholderText="App Seed (e.g., Target Site)")
        self.slid = QSlider(Qt.Orientation.Horizontal); self.slid.setRange(8, 64); self.slid.setValue(16)
        self.len_lbl = QLabel("Length: 16")
        
        self.out = QLineEdit(readOnly=True); self.out.setStyleSheet("font-family: Consolas; font-size: 16px; color: #00D4FF; text-align: center;")
        
        # Live Connectors
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
            self.out.setText(pwd)
            self.gauge.update_strength(pwd)
        else:
            self.out.clear()
            self.gauge.update_strength("")

    def copy_gen(self):
        pwd = self.out.text()
        if pwd:
            QApplication.clipboard().setText(pwd)
            self.clip_timer.start(30000)
            QMessageBox.information(self, "Copied", "Password copied to clipboard. Auto-clearing in 30s.")

    def add_entry(self):
        if self.app_i.text():
            self.db.auto_vault_entry(self.app_i.text(), self.user_i.text(), self.pass_i.text())
            self.list_w.clear(); self.list_w.addItems(self.db.vault.keys())
            self.app_i.clear(); self.user_i.clear(); self.pass_i.clear()

    def view_entry(self, item):
        e = self.db.vault[item.text()]
        QMessageBox.information(self, item.text(), f"User: {e['user']}\nPassword: {e['pass']}")
        QApplication.clipboard().setText(e['pass']); self.clip_timer.start(30000)

    def lockdown(self):
        # UPGRADE: Aggressive Memory Purging
        self.db.fernet = None
        self.db.vault = {} 
        gc.collect() # Force OS to reclaim purged keys
        
        self.stack.setCurrentIndex(0)
        self.u_in.clear(); self.p_in.clear()
        print("SECURITY ALERT: RAM Purged. Application Locked.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = DaybreakApp(); ex.show()
    sys.exit(app.exec())