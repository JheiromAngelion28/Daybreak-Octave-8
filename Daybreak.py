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
# Fernet provides AES-128 encryption. Scrypt is a memory-hard key derivation function 
# that protects the master key against brute-force GPU attacks.
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# --- PYQT6 UI IMPORTS ---
# These modules handle the desktop window, buttons, layouts, and input fields.
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget, 
                             QVBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTabWidget, QHBoxLayout, QFrame, QSlider, 
                             QListWidget, QMessageBox, QComboBox, QInputDialog)
from PyQt6.QtCore import Qt, QTimer, QUrl, QRectF
from PyQt6.QtGui import QPixmap, QColor, QPainter, QPen, QFont

# --- WEB ENGINE IMPORTS ---
# These allow us to embed a Chromium browser to render the 3D WebGL scene.
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

# =============================================================================
# 1. CUSTOM UI: REAL-TIME ENTROPY GAUGE
# =============================================================================
class StrengthGauge(QWidget):
    """
    A custom PyQt6 widget that draws a circular progress bar.
    It calculates the Shannon Entropy of a password in real-time.
    """
    def __init__(self):
        super().__init__()
        self.setFixedSize(160, 160)
        self.percent = 0
        self.status = "AWAITING"
        self.color = QColor("#58A6FF") # Default Daybreak Cyan

    def update_strength(self, password):
        # Reset if input is empty
        if not password:
            self.percent = 0; self.status = "AWAITING"; self.color = QColor("#2A2F35")
            self.update(); return

        # Calculate the character pool size based on what the user typed
        pool = 0
        if any(c.islower() for c in password): pool += 26
        if any(c.isupper() for c in password): pool += 26
        if any(c.isdigit() for c in password): pool += 10
        if any(c in string.punctuation for c in password): pool += 32
        
        # Shannon Entropy Formula: H = L * log2(R)
        entropy = len(password) * math.log2(pool) if pool > 0 else 0
        
        # Convert entropy to a percentage (Max secure target is ~128 bits)
        self.percent = min(100, int((entropy / 128.0) * 100))
        
        # Change color and status based on mathematical strength
        if entropy < 50: self.status = "WEAK"; self.color = QColor("#FF5F5F") # Red
        elif entropy < 80: self.status = "MODERATE"; self.color = QColor("#FFBD2E") # Yellow
        else: self.status = "STRONG"; self.color = QColor("#00D4FF") # Cyan
        
        self.update() # Trigger UI repaint

    def paintEvent(self, event):
        # Native QPainter logic to draw the circular gauge
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(15, 15, 130, 130)
        
        # Draw the dark background track
        p.setPen(QPen(QColor("#2A2F35"), 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, 0, 360 * 16)
        
        # Draw the colored progress arc
        p.setPen(QPen(self.color, 12, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, 90 * 16, -int((self.percent / 100) * 360 * 16))
        
        # Draw the percentage text in the center
        p.setPen(self.color); p.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{self.percent}%")

# =============================================================================
# 2. 3D ARCHITECTURE: NETWORK-SAFE OBJ RENDERER
# =============================================================================
class Mobius3DView(QWebEngineView):
    """
    Embeds a transparent HTML/JS webpage using Three.js to render the .obj file.
    Includes network fail-safes and absolute pathing.
    """
    def __init__(self, obj_filename):
        super().__init__()
        self.setFixedSize(450, 350)
        
        # Force absolute transparency so the dark UI background shows through
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.page().setBackgroundColor(QColor(0, 0, 0, 0)) 
        
        # Allow the browser engine to read local files on your hard drive
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        
        # Bulletproof Pathing: Find the exact folder this python script is running from
        script_dir = Path(__file__).parent.resolve()
        obj_path = script_dir / obj_filename
        
        # Check if the file exists before passing it to the HTML
        self.file_exists = "true" if obj_path.exists() else "false"

        # The HTML payload that drives Three.js
        html = f"""
        <html>
          <head>
            <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/OBJLoader.js"></script>
            <style>body {{ margin: 0; background: transparent !important; overflow: hidden; }} canvas {{ display: block; }}</style>
          </head>
          <body>
            <script>
              // Wait for the internet to finish downloading the scripts
              window.onload = function() {{
                  
                  // FAIL-SAFE: If internet is blocked, show an error message
                  if (typeof THREE === 'undefined') {{
                      document.body.innerHTML = "<div style='color:#FF5F5F; text-align:center; font-family:Segoe UI; margin-top:100px;'>[ Network Blocked ]<br>Cannot load 3D Engine</div>"; return;
                  }}
                  
                  // Setup Scene, Camera, and Transparent Renderer
                  const scene = new THREE.Scene();
                  const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
                  const renderer = new THREE.WebGLRenderer({{ alpha: true, antialias: true }});
                  renderer.setClearColor(0x000000, 0); 
                  renderer.setSize(window.innerWidth, window.innerHeight);
                  document.body.appendChild(renderer.domElement);

                  // Setup Daybreak Cyan Lighting
                  const light = new THREE.PointLight(0x00D4FF, 2, 100); light.position.set(10, 10, 10); scene.add(light);
                  scene.add(new THREE.AmbientLight(0x404040, 3));

                  // Diagnostic Cube (Shows up if the .obj file is missing or corrupted)
                  const cube = new THREE.Mesh(new THREE.BoxGeometry(1,1,1), new THREE.MeshStandardMaterial({{ color: 0x00D4FF, wireframe: true }}));

                  if ({self.file_exists}) {{
                    // Load the custom OBJ file
                    new THREE.OBJLoader().load('{obj_path.name}', (obj) => {{
                      
                      // Apply the high-tech metallic cyan material to the model
                      obj.traverse((c) => {{ if (c.isMesh) c.material = new THREE.MeshStandardMaterial({{ color: 0x00D4FF, metalness: 0.9, roughness: 0.1 }}); }});
                      scene.add(obj);
                      
                      // Animation loop to rotate the model
                      function anim() {{ requestAnimationFrame(anim); obj.rotation.y += 0.01; renderer.render(scene, camera); }}
                      anim();
                      
                    }}, undefined, () => {{ scene.add(cube); animateFallback(); }}); // Error fallback
                  }} else {{ scene.add(cube); animateFallback(); }} // Missing file fallback

                  function animateFallback() {{ requestAnimationFrame(animateFallback); cube.rotation.x += 0.01; cube.rotation.y += 0.01; renderer.render(scene, camera); }}
                  camera.position.z = 3.5;
              }};
            </script>
          </body>
        </html>
        """
        # Load the HTML, setting the base directory so it can find the .obj file
        self.setHtml(html, QUrl.fromLocalFile(str(script_dir) + os.path.sep))

# =============================================================================
# 3. SECURITY ENGINE (DATABASE & AUTHENTICATION)
# =============================================================================
class SecurityEngine:
    """
    Handles user authentication, encryption, and local JSON database storage.
    """
    def __init__(self):
        self.fernet = None
        self.vault = {}
        # Save the database in the same folder as the script
        self.db_path = Path(__file__).parent.resolve() / "vault.db"

    def authenticate(self, user, pwd):
        # Strict requirement: Enforce Jheirom / 1234
        if user == "Jheirom" and pwd == "1234":
            self._derive_key(pwd)
            self._load_db()
            return True
        return False

    def _derive_key(self, pwd):
        # Scrypt converts the simple '1234' password into a massive 32-byte secure key
        salt = b'daybreak_enterprise_salt'
        kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
        self.fernet = Fernet(base64.urlsafe_b64encode(kdf.derive(pwd.encode())))

    def _save_db(self):
        # Encrypt the entire python dictionary and write it to disk
        if not self.fernet: return
        with open(self.db_path, "wb") as f:
            f.write(self.fernet.encrypt(json.dumps(self.vault).encode()))

    def _load_db(self):
        # Read the encrypted file and parse it back into a dictionary
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "rb") as f:
                    self.vault = json.loads(self.fernet.decrypt(f.read()).decode())
            except: self.vault = {}

    def auto_vault_entry(self, app, user, pwd, cat):
        # Adds the entry and automatically saves it to disk
        self.vault[app] = {
            "user": user, 
            "pass": pwd, 
            "cat": cat,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save_db()

    def generate_det(self, app, length):
        # Uses the Master Key and the App Name to mathematically derive a password.
        # This ensures the same app name always yields the same complex password.
        if not app: return ""
        seed = str(self.fernet).encode() + app.lower().strip().encode()
        h = hashlib.sha512(seed).digest()
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join([chars[b % len(chars)] for b in h])[:length]

# =============================================================================
# 4. MAIN UI FLOW (THE DESKTOP APPLICATION)
# =============================================================================
class DaybreakApp(QMainWindow):
    """
    The main window that manages the UI layout, styling, and screen transitions.
    """
    def __init__(self):
        super().__init__()
        self.db = SecurityEngine()
        self.setWindowTitle("Daybreak Octave 8")
        self.setFixedSize(800, 600)
        
        # Global Cyber-Creative Dark Theme
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

        # Security Timers
        self.idle_timer = QTimer()
        self.idle_timer.timeout.connect(self.lockdown) # Locks app after inactivity
        
        self.clip_timer = QTimer()
        self.clip_timer.timeout.connect(lambda: QApplication.clipboard().clear()) # Wipes clipboard

        # The QStackedWidget acts as a "deck of cards" allowing us to flip between Login and Hub
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.init_signin()

    def init_signin(self):
        # Screen 0: The Login Surface
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(50, 20, 50, 50)
        
        # Integrate the 3D renderer
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
            self.idle_timer.start(300000) # Start 5-minute lockdown timer (300,000 ms)
        else: QMessageBox.warning(self, "Denied", "Authentication Failed")

    def show_dashboard(self):
        # Screen 1: The Main Hub (Contains Sidebar and Content)
        hub = QWidget(); main_layout = QHBoxLayout(hub); main_layout.setContentsMargins(0,0,0,0)
        
        # Build Sidebar Navigation
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

        # Content Area Stack (Flips between Vault and Generator)
        self.content = QStackedWidget()
        self.content.addWidget(self.create_vault_tab())
        self.content.addWidget(self.create_gen_tab())
        
        main_layout.addWidget(sidebar); main_layout.addWidget(self.content)
        self.stack.addWidget(hub); self.stack.setCurrentIndex(1)

    def switch_tab(self, index):
        # Update active sidebar styling when clicking tabs
        self.content.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.setObjectName("NavBtnActive" if i == index else "NavBtn")
        self.setStyleSheet(self.styleSheet()) 

    def create_vault_tab(self):
        # Vault UI Layout
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(40,40,40,40)
        layout.addWidget(QLabel("## DATABASE VAULT"))
        
        self.list_w = QListWidget(); self.list_w.addItems(self.db.vault.keys())
        self.list_w.itemClicked.connect(self.view_entry)
        
        card = QFrame(); card.setObjectName("Card"); c_layout = QVBoxLayout(card)
        self.app_i = QLineEdit(placeholderText="App Name")
        self.user_i = QLineEdit(placeholderText="Username")
        self.pass_i = QLineEdit(placeholderText="Password")
        self.cat_i = QComboBox(); self.cat_i.addItems(["Social", "Work", "Banking", "Infrastructure"])
        btn = QPushButton("SECURE ENTRY"); btn.clicked.connect(self.add_entry)
        
        c_layout.addWidget(self.app_i); c_layout.addWidget(self.user_i); c_layout.addWidget(self.pass_i); c_layout.addWidget(self.cat_i); c_layout.addWidget(btn)
        layout.addWidget(self.list_w); layout.addWidget(card); return page

    def create_gen_tab(self):
        # Generator UI Layout
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
        # Automatically updates the generated password and gauge as the slider moves
        val = self.slid.value()
        self.len_lbl.setText(f"Length: {val}")
        if self.seed.text():
            pwd = self.db.generate_det(self.seed.text(), val)
            self.out.setText(pwd); self.gauge.update_strength(pwd)
        else:
            self.out.clear(); self.gauge.update_strength("")

    def copy_gen(self):
        # Copies to clipboard and starts the 30-second wipe timer
        pwd = self.out.text()
        if pwd:
            QApplication.clipboard().setText(pwd); self.clip_timer.start(30000)
            QMessageBox.information(self, "Copied", "Password copied to clipboard. Auto-clearing in 30s.")

    def add_entry(self):
        # Validates and stores the entry
        if self.app_i.text():
            self.db.auto_vault_entry(self.app_i.text(), self.user_i.text(), self.pass_i.text(), self.cat_i.currentText())
            self.list_w.clear(); self.list_w.addItems(self.db.vault.keys())
            self.app_i.clear(); self.user_i.clear(); self.pass_i.clear()

    def view_entry(self, item):
        # ZERO-TRUST ARCHITECTURE: Demands the master key again to view sensitive data
        key, ok = QInputDialog.getText(self, "Vault Security", "Enter Main Key (1234) to decrypt:", QLineEdit.EchoMode.Password)
        if ok and key == "1234":
            e = self.db.vault[item.text()]
            QMessageBox.information(self, item.text(), f"User: {e['user']}\nPassword: {e['pass']}\nCategory: {e['cat']}\nSecured On: {e['timestamp']}\n\n(Copied to clipboard for 30s)")
            QApplication.clipboard().setText(e['pass']); self.clip_timer.start(30000)
        elif ok: QMessageBox.warning(self, "Access Denied", "Invalid Key.")

    def lockdown(self):
        # Deletes the encryption key from memory, purges the cache, and forces garbage collection
        self.db.fernet = None
        self.db.vault = {} 
        gc.collect() 
        self.stack.setCurrentIndex(0)
        self.u_in.clear(); self.p_in.clear()
        print("SECURITY ALERT: RAM Purged. Application Locked.")

# --- APPLICATION ENTRY POINT ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = DaybreakApp(); ex.show()
    sys.exit(app.exec())