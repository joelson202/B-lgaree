import sys
import traceback
import re
import requests
import json
import os
import subprocess
import tempfile
import speech_recognition as sr
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSizeGrip, QComboBox, QFrame, QTableWidget, QTableWidgetItem,
    QMenu, QAction, QDialog, QSpinBox, QMessageBox, QLineEdit, QInputDialog, QStackedWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QSettings
from PyQt5.QtGui import QDesktopServices
from database import DatabaseManager

# Tratamento de erros para evitar fechamento silencioso
def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("ERRO CRÍTICO:", tb)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

class VoiceWorker(QThread):
    finished = pyqtSignal(dict, str)
    error = pyqtSignal(str)
    listening = pyqtSignal()

    def run(self):
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                self.listening.emit()
                # Ajuste rápido de ruído
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                # Escuta
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                # Reconhece (Google Web Speech API)
                text = recognizer.recognize_google(audio, language='pt-BR')
                
                # Processa
                parsed = self.parse_text(text)
                self.finished.emit(parsed, text)
                
        except sr.WaitTimeoutError:
            self.error.emit("Nenhuma fala detectada. Tente novamente.")
        except sr.UnknownValueError:
            self.error.emit("Não entendi o que foi dito.")
        except sr.RequestError:
            self.error.emit("Erro de conexão ou configuração de voz.")
        except Exception as e:
            self.error.emit(f"Erro: {str(e)}")

    def parse_text(self, text):
        text = text.lower()
        data = {}
        
        # Mapeamento de palavras-chave para campos
        keywords = {
            "data": "Data",
            "mercadoria": "Mercadorias",
            "mercadorias": "Mercadorias",
            "produto": "Produto",
            "produtos": "Produto",
            "categoria": "Categoria",
            "descrição": "Descrição",
            "descricao": "Descrição",
            "código": "Código",
            "codigo": "Código",
            "preço": "Preço",
            "preco": "Preço",
            "valor": "Preço",
            "valor unitário": "Valor Unit.",
            "valor unitario": "Valor Unit.",
            "unitário": "Valor Unit.",
            "unitario": "Valor Unit.",
            "total": "Total",
            "estoque": "Estoque",
            "quantidade": "Quantidade",
            "quantas": "Quantidade",
            "caixa": "Caixa",
            "caixas": "Caixa",
            "unidade": "Unidade",
            "unidades": "Unidade"
        }
        
        # Ordenar keywords por tamanho decrescente para evitar matches parciais errados
        sorted_keys = sorted(keywords.keys(), key=len, reverse=True)
        
        found_indices = []
        for k in sorted_keys:
            # Encontrar todas as ocorrências (aqui simplificado para a primeira por campo)
            idx = text.find(k)
            if idx != -1:
                # Verifica se não é parte de outra palavra (opcional, mas bom)
                found_indices.append((idx, k, keywords[k]))
        
        found_indices.sort()
        
        for i, (idx, k, field) in enumerate(found_indices):
            start = idx + len(k)
            # O fim é o início da próxima keyword ou o fim da string
            if i + 1 < len(found_indices):
                end = found_indices[i+1][0]
            else:
                end = len(text)
            
            value = text[start:end].strip()
            
            # Limpeza de preposições comuns
            for prep in ["de ", "da ", "do ", "é ", ": "]:
                if value.startswith(prep):
                    value = value[len(prep):]
            
            data[field] = value.strip()
            
        return data

class VoiceInputDialog(QDialog):
    def __init__(self, parent=None, fields=None, title_text="Adicionar Produtos com Voz"):
        super().__init__(parent)
        self.setWindowTitle(title_text)
        self.setFixedSize(400, 550)
        self.setStyleSheet("""
            QDialog { background-color: #2E2E2E; color: white; border: 1px solid #00FFFF; border-radius: 10px; }
            QLabel { color: #E0E0E0; font-family: Segoe UI; font-size: 14px; }
            QLineEdit { background-color: #3E3E3E; color: white; padding: 8px; border: 1px solid #555; border-radius: 4px; }
            QPushButton { background-color: #00CED1; color: white; padding: 10px; border-radius: 5px; font-weight: bold; border: none; font-size: 14px; }
            QPushButton:hover { background-color: #00BFFF; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Comando de Voz")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00FFFF;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.status_label = QLabel("Clique no microfone para falar.\nEx: 'Adicione Data hoje Mercadoria Arroz Preço 10'")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px; color: #AAAAAA; margin-bottom: 10px;")
        layout.addWidget(self.status_label)
        
        self.btn_speak = QPushButton("🎤 Falar Agora")
        self.btn_speak.clicked.connect(self.start_listening)
        layout.addWidget(self.btn_speak)
        
        # Form Container
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0,0,0,0)
        form_layout.setSpacing(10)
        
        self.inputs = {}
        if fields is None:
            self.fields_list = ["Data", "Mercadorias", "Categoria", "Descrição", "Código", "Preço", "Quantidade"]
        else:
            self.fields_list = fields
        
        for field in self.fields_list:
            row = QHBoxLayout()
            lbl = QLabel(field + ":")
            lbl.setFixedWidth(80)
            inp = QLineEdit()
            self.inputs[field] = inp
            row.addWidget(lbl)
            row.addWidget(inp)
            form_layout.addLayout(row)
            
        # Add Tipo ComboBox
        row_type = QHBoxLayout()
        lbl_type = QLabel("Tipo:")
        lbl_type.setFixedWidth(80)
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Unidade", "Caixa"])
        self.combo_type.setStyleSheet("background-color: #3E3E3E; color: white; padding: 5px; border: 1px solid #555;")
        row_type.addWidget(lbl_type)
        row_type.addWidget(self.combo_type)
        form_layout.addLayout(row_type)
            
        layout.addWidget(form_widget)
        
        # Buttons
        btn_box = QHBoxLayout()
        self.btn_add = QPushButton("Confirmar Adição")
        self.btn_add.clicked.connect(self.accept)
        self.btn_add.setStyleSheet("background-color: #32CD32;") # Green
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet("background-color: #FF4500;") # Red
        
        btn_box.addWidget(self.btn_add)
        btn_box.addWidget(self.btn_cancel)
        layout.addLayout(btn_box)
        
    def start_listening(self):
        self.btn_speak.setEnabled(False)
        self.btn_speak.setText("Ouvindo...")
        self.status_label.setText("Escutando... Fale os campos agora.")
        self.status_label.setStyleSheet("color: #00FF00; font-weight: bold;")
        
        self.worker = VoiceWorker()
        self.worker.finished.connect(self.on_recognition_finished)
        self.worker.error.connect(self.on_recognition_error)
        self.worker.start()
        
    def on_recognition_finished(self, data, text):
        self.status_label.setText(f"Entendido: '{text}'")
        self.status_label.setStyleSheet("color: #E0E0E0;")
        self.btn_speak.setEnabled(True)
        self.btn_speak.setText("🎤 Falar Novamente")
        
        # Check for Type in data keys (Caixa/Unidade)
        if "Caixa" in data:
            self.combo_type.setCurrentText("Caixa")
        elif "Unidade" in data:
            self.combo_type.setCurrentText("Unidade")
        
        for field, value in data.items():
            if field in self.inputs:
                self.inputs[field].setText(value)
                
    def on_recognition_error(self, msg):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("color: #FF4500;")
        self.btn_speak.setEnabled(True)
        self.btn_speak.setText("🎤 Tentar Novamente")
        
    def get_data(self):
        data = {k: v.text() for k, v in self.inputs.items()}
        data["Tipo"] = self.combo_type.currentText()
        return data


CURRENT_VERSION = "1.1.3"
VERSION_URL = "https://raw.githubusercontent.com/joelson202/B-lgaree/main/version.json"

class UpdateChecker(QThread):
    update_available = pyqtSignal(str)

    def run(self):
        import time
        import random
        last_notified = None

        while True:
            try:
                # Prevent caching
                url = f"{VERSION_URL}?t={random.random()}"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    remote_version = data.get("version")
                    download_url = data.get("url")
                    
                    if remote_version and remote_version != CURRENT_VERSION:
                        # Simple check: if versions differ, assume update
                        if remote_version > CURRENT_VERSION:
                            # Notify only if not already notified for this version in this session
                            if remote_version != last_notified:
                                self.update_available.emit(download_url)
                                last_notified = remote_version
            except Exception:
                pass
            
            # Verifica a cada 60 segundos
            time.sleep(60)

class UpdateDownloader(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            response = requests.get(self.url, stream=True, timeout=30)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            if response.status_code == 200:
                temp_dir = tempfile.gettempdir()
                installer_path = os.path.join(temp_dir, "Instalador_Bulgaree_Update.exe")
                
                with open(installer_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                self.progress.emit(int((downloaded / total_size) * 100))
                                
                self.finished.emit(installer_path)
            else:
                self.error.emit(f"Erro ao baixar: {response.status_code}")
        except Exception as e:
            self.error.emit(str(e))

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setFixedHeight(35)
        self.setStyleSheet("background-color: #252526;")

        # Título
        self.title = QLabel("Búlgaree")
        self.title.setStyleSheet("""
            QLabel {
                color: #333;
                font-family: Segoe UI;
                font-size: 12px;
                padding: 6px;
                background: qlineargradient(
                    x1: 0, y1: 0,
                    x2: 1, y2: 0,
                    stop: 0 #E0E0E0,
                    stop: 1 #ADD8E6
                );
            }
        """)
        self.layout.addWidget(self.title)
        
        self.layout.addStretch()

        # Botão de configurações (engrenagem)
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setFixedSize(35, 35)
        self.btn_settings.setStyleSheet("""
            QPushButton {
                color: white;
                font-size: 18px;
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                color: #AAAAAA;
            }
        """)
        self.btn_settings.clicked.connect(self.parent.toggle_settings_panel)
        self.layout.addWidget(self.btn_settings)

        # Botões padrão
        self.btn_min = self.create_button("—", self.minimize_window)
        self.btn_max = self.create_button("☐", self.maximize_restore_window)
        self.btn_close = self.create_button("✕", self.close_window)

        # Variáveis para arrastar
        self.old_pos = None

    def create_button(self, text, slot):
        btn = QPushButton(text)
        btn.setFixedSize(45, 35)
        btn.clicked.connect(slot)

        if text == "✕":
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #cccccc;
                    border: none;
                    font-size: 12px;
                    font-family: Segoe UI;
                }
                QPushButton:hover {
                    color: #e81123;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #cccccc;
                    border: none;
                    font-size: 12px;
                    font-family: Segoe UI;
                }
                QPushButton:hover {
                    color: #ffffff;
                }
                QPushButton:pressed {
                    color: #aaaaaa;
                }
            """)
        self.layout.addWidget(btn)
        return btn

    def minimize_window(self):
        self.parent.showMinimized()

    def maximize_restore_window(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.btn_max.setText("☐")
        else:
            self.parent.showMaximized()
            self.btn_max.setText("❐")

    def close_window(self):
        self.parent.close()

    # Lógica de arrastar
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos and event.buttons() == Qt.LeftButton:
            if not self.parent.isMaximized():
                delta = event.globalPos() - self.old_pos
                self.parent.move(self.parent.x() + delta.x(), self.parent.y() + delta.y())
                self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

class StockLimitDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Limites de Estoque")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedSize(320, 160)
        self.setStyleSheet("""
            QDialog {
                background-color: #2E2E2E;
                border: 1px solid #00FFFF;
                border-radius: 10px;
            }
            QLabel {
                color: white;
                font-family: Segoe UI;
                font-size: 14px;
            }
            QSpinBox {
                background-color: #3E3E3E;
                color: white;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #00CED1;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00BFFF;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("Quantidade Minima / Quantidade Máxima")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Inputs
        input_layout = QHBoxLayout()
        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 100000)
        self.max_spin = QSpinBox()
        self.max_spin.setRange(0, 100000)
        
        input_layout.addWidget(QLabel("Min:"))
        input_layout.addWidget(self.min_spin)
        input_layout.addWidget(QLabel("Max:"))
        input_layout.addWidget(self.max_spin)
        layout.addLayout(input_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Confirmar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet("background-color: #FF4500; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-weight: bold;")
        
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Búlgaree - Login")
        self.setFixedSize(400, 500)
        self.setStyleSheet("background-color: #1E1E1E; color: white;")
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        # Database
        self.db = DatabaseManager()
        self.settings = QSettings("BulgareeSoft", "Bulgaree")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Logo/Title
        title = QLabel("Búlgaree")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #00CED1; font-family: Segoe UI;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Acesse seus dados de qualquer lugar")
        subtitle.setStyleSheet("font-size: 14px; color: #AAAAAA;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Inputs
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.email_input.setStyleSheet("""
            QLineEdit {
                background-color: #2E2E2E;
                border: 1px solid #3E3E3E;
                border-radius: 5px;
                padding: 10px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #00CED1;
            }
        """)
        layout.addWidget(self.email_input)
        
        # Restaurar email salvo
        saved_email = self.settings.value("email", "")
        if saved_email:
            self.email_input.setText(str(saved_email))
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Senha")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setStyleSheet(self.email_input.styleSheet())
        layout.addWidget(self.pass_input)
        
        # Buttons
        btn_login = QPushButton("Entrar")
        btn_login.setCursor(Qt.PointingHandCursor)
        btn_login.clicked.connect(self.handle_login)
        btn_login.setStyleSheet("""
            QPushButton {
                background-color: #00CED1;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00E0E4;
            }
        """)
        layout.addWidget(btn_login)
        
        btn_register = QPushButton("Criar Conta")
        btn_register.setCursor(Qt.PointingHandCursor)
        btn_register.clicked.connect(self.handle_register)
        btn_register.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #00CED1;
                border: 1px solid #00CED1;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(0, 206, 209, 0.1);
            }
        """)
        layout.addWidget(btn_register)
        
        # Close button (since frameless)
        btn_close = QPushButton("Sair")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        btn_close.setStyleSheet("background-color: transparent; color: #666; margin-top: 10px;")
        layout.addWidget(btn_close)

        if self.email_input.text():
            self.pass_input.setFocus()
        
    def handle_login(self):
        email = self.email_input.text()
        password = self.pass_input.text()
        if not email or not password:
            QMessageBox.warning(self, "Aviso", "Preencha email e senha.")
            return
            
        success, msg = self.db.login(email, password)
        if success:
            self.settings.setValue("email", email)
            self.accept()
        else:
            QMessageBox.critical(self, "Erro", msg)

    def handle_register(self):
        email = self.email_input.text()
        password = self.pass_input.text()
        if not email or not password:
            QMessageBox.warning(self, "Aviso", "Preencha email e senha para cadastrar.")
            return
            
        success, msg = self.db.register(email, password)
        if success:
            QMessageBox.information(self, "Sucesso", msg)
        else:
            QMessageBox.critical(self, "Erro", msg)

class MainWindow(QWidget):
    def __init__(self, db_manager=None):
        super().__init__()
        self.db = db_manager if db_manager else DatabaseManager()
        self.loading_data = False
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(800, 500)
        self.setStyleSheet("background-color: #1E1E1E; border: 1px solid #333;")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        self.layout.addWidget(self.title_bar)

        # Área de Conteúdo
        self.content = QWidget()
        self.content.setStyleSheet("background-color: #1E1E1E; border: none;") 
        self.main_horizontal_layout = QHBoxLayout(self.content)
        self.main_horizontal_layout.setContentsMargins(20, 20, 20, 20)
        self.main_horizontal_layout.setSpacing(20)

        # --- Menu Lateral ---
        self.menu_container = QWidget()
        self.menu_layout = QVBoxLayout(self.menu_container)
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.setSpacing(10)
        self.menu_layout.setAlignment(Qt.AlignTop)

        self.btn_produtos = QPushButton("Produtos")
        self.btn_produtos.setCursor(Qt.PointingHandCursor)
        self.btn_produtos.setStyleSheet("""
            QPushButton {
                color: #00FFFF;
                background-color: transparent;
                border: none;
                font-family: Segoe UI;
                font-size: 18px;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                color: #E0FFFF;
                text-decoration: underline;
            }
        """)
        self.btn_produtos.clicked.connect(self.show_produtos)
        self.menu_layout.addWidget(self.btn_produtos)

        self.btn_vendas = QPushButton("Vendas")
        self.btn_vendas.setCursor(Qt.PointingHandCursor)
        self.btn_vendas.setStyleSheet(self.btn_produtos.styleSheet())
        self.btn_vendas.clicked.connect(self.show_vendas)
        self.menu_layout.addWidget(self.btn_vendas)

        self.menu_layout.addStretch()
        self.menu_container.setFixedWidth(150)
        self.main_horizontal_layout.addWidget(self.menu_container)

        # --- Área de Exibição ---
        self.display_area = QWidget()
        self.display_layout = QVBoxLayout(self.display_area)
        self.display_layout.setContentsMargins(0, 0, 0, 0)

        # Painel de Stack (Produtos / Vendas)
        self.stack = QStackedWidget()
        self.display_layout.addWidget(self.stack)

        # --- Painel Vazio (Home) ---
        self.empty_panel = QWidget()
        self.empty_panel.setStyleSheet("background-color: transparent;")
        self.stack.addWidget(self.empty_panel)

        # --- Painel de Produtos ---
        self.produtos_panel = QFrame()
        self.produtos_panel.setStyleSheet("""
            background-color: #ADD8E6; 
            border-radius: 15px;
            border: none;
        """)
        self.stack.addWidget(self.produtos_panel)

        # --- Painel de Vendas ---
        self.vendas_panel = QFrame()
        self.vendas_panel.setStyleSheet("""
            background-color: #E6E6FA; 
            border-radius: 15px;
            border: none;
        """)
        self.stack.addWidget(self.vendas_panel)

        self.main_horizontal_layout.addWidget(self.display_area)
        self.layout.addWidget(self.content)

        # --- Layout interno do painel Produtos ---
        produtos_layout = QVBoxLayout(self.produtos_panel)
        produtos_layout.setContentsMargins(15, 15, 15, 15)
        produtos_layout.setSpacing(10)

        label_planilha = QLabel("Controle Financeiro Pessoal")
        label_planilha.setStyleSheet("font-family: Segoe UI; font-size: 16px; font-weight: bold; color: #000080;")
        produtos_layout.addWidget(label_planilha)

        # Tabela Produtos
        self.finance_table = QTableWidget()
        self.finance_table.setColumnCount(8)
        self.finance_table.setHorizontalHeaderLabels(["Data", "Mercadorias", "Categoria", "Descrição", "Código", "Preço", "Estoque", "Quantidade"])
        self.finance_table.horizontalHeader().setStretchLastSection(True)
        self.finance_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.finance_table.customContextMenuRequested.connect(self.open_context_menu)
        produtos_layout.addWidget(self.finance_table)

        # Botões Produtos
        buttons_layout = QHBoxLayout()
        self.btn_add = QPushButton("Adicionar")
        self.btn_add.setStyleSheet("background-color: #00CED1; color: white; font-weight: bold;")
        self.btn_add.clicked.connect(self.add_row)
        buttons_layout.addWidget(self.btn_add)

        self.btn_remove = QPushButton("Remover")
        self.btn_remove.setStyleSheet("background-color: #FF4500; color: white; font-weight: bold;")
        self.btn_remove.clicked.connect(self.remove_row)
        buttons_layout.addWidget(self.btn_remove)

        self.saldo_label = QLabel("Saldo Total: R$ 0,00")
        self.saldo_label.setStyleSheet("font-weight: bold; color: green;")
        buttons_layout.addWidget(self.saldo_label)
        
        self.btn_voice = QPushButton(" 🎤 Adicionar Produtos com Voz")
        self.btn_voice.setStyleSheet("background-color: #9370DB; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        self.btn_voice.clicked.connect(self.open_voice_dialog)
        buttons_layout.addWidget(self.btn_voice)
        
        produtos_layout.addLayout(buttons_layout)

        # --- Layout interno do painel Vendas ---
        vendas_layout = QVBoxLayout(self.vendas_panel)
        vendas_layout.setContentsMargins(15, 15, 15, 15)
        vendas_layout.setSpacing(10)

        label_vendas = QLabel("Registro de Vendas")
        label_vendas.setStyleSheet("font-family: Segoe UI; font-size: 16px; font-weight: bold; color: #4B0082;")
        vendas_layout.addWidget(label_vendas)

        # Tabela Vendas
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(5)
        self.sales_table.setHorizontalHeaderLabels(["Data", "Produto", "Quantidade", "Valor Unit.", "Total"])
        self.sales_table.horizontalHeader().setStretchLastSection(True)
        vendas_layout.addWidget(self.sales_table)

        # Botões Vendas
        vendas_buttons_layout = QHBoxLayout()
        self.btn_add_sale = QPushButton("Adicionar Venda")
        self.btn_add_sale.setStyleSheet("background-color: #32CD32; color: white; font-weight: bold;")
        self.btn_add_sale.clicked.connect(self.add_sale_row)
        vendas_buttons_layout.addWidget(self.btn_add_sale)

        self.btn_remove_sale = QPushButton("Remover Venda")
        self.btn_remove_sale.setStyleSheet("background-color: #FF4500; color: white; font-weight: bold;")
        self.btn_remove_sale.clicked.connect(self.remove_sale_row)
        vendas_buttons_layout.addWidget(self.btn_remove_sale)

        self.btn_voice_sales = QPushButton(" 🎤 Adicionar Vendas com Voz")
        self.btn_voice_sales.setStyleSheet("background-color: #9370DB; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        self.btn_voice_sales.clicked.connect(self.open_sales_voice_dialog)
        vendas_buttons_layout.addWidget(self.btn_voice_sales)

        self.sales_total_label = QLabel("Total Vendas: R$ 0,00")
        self.sales_total_label.setStyleSheet("font-weight: bold; color: blue;")
        vendas_buttons_layout.addWidget(self.sales_total_label)
        
        vendas_layout.addLayout(vendas_buttons_layout)

        # Painel de Configurações
        self.settings_panel = QWidget(self)
        self.settings_panel.setStyleSheet("""
            background-color: #2E2E2E;
            border-radius: 10px;
            border: 1px solid #555;
        """)
        self.settings_panel.setFixedSize(220, 400)
        self.settings_panel.hide()

        panel_layout = QVBoxLayout(self.settings_panel)
        panel_layout.setContentsMargins(15, 15, 15, 15)
        panel_layout.setSpacing(10)

        theme_label = QLabel("Tema:")
        theme_label.setStyleSheet("color: white; font-family: Segoe UI;")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Escuro", "Claro"])
        self.theme_combo.setStyleSheet("background-color: #3E3E3E; color: white;")
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        panel_layout.addWidget(theme_label)
        panel_layout.addWidget(self.theme_combo)

        lang_label = QLabel("Idioma:")
        lang_label.setStyleSheet("color: white; font-family: Segoe UI;")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Português", "English"])
        self.lang_combo.setStyleSheet("background-color: #3E3E3E; color: white;")
        self.lang_combo.currentIndexChanged.connect(self.change_language)
        panel_layout.addWidget(lang_label)
        panel_layout.addWidget(self.lang_combo)

        # SizeGrip
        self.sizegrip = QSizeGrip(self.content)
        self.sizegrip.setStyleSheet("width: 20px; height: 20px; background-color: transparent; border: none;")

        # --- Notification Bubble ---
        self.notification_bubble = QLabel("(Nova atualização ) Clique aqui para atualizar o Búlgaree")
        self.notification_bubble.setAlignment(Qt.AlignCenter)
        self.notification_bubble.setStyleSheet("""
            QLabel {
                background-color: white;
                color: black;
                border-radius: 15px;
                padding: 8px 20px;
                font-family: Segoe UI;
                font-weight: bold;
                font-size: 13px;
                margin: 10px;
                border: 1px solid #ccc;
            }
            QLabel:hover {
                background-color: #F0F0F0;
            }
        """)
        self.notification_bubble.setCursor(Qt.PointingHandCursor)
        self.notification_bubble.mousePressEvent = self.on_bubble_click
        self.notification_bubble.hide()
        self.layout.addWidget(self.notification_bubble, alignment=Qt.AlignHCenter)

        # Start Update Check
        self.check_updates()
        
        # Set Initial View (Produtos)
        self.stack.setCurrentWidget(self.produtos_panel)

        # Load Config to UI
        # self.supabase_url_input.setText(self.db.url)
        # self.supabase_key_input.setText(self.db.key)

        # Connect Item Changed
        self.finance_table.itemChanged.connect(self.on_item_changed)

        # Load Data
        self.load_data()

    # --- Persistência e Dados ---
    def get_table_data(self):
        data = []
        rows = self.finance_table.rowCount()
        keys = ["data", "mercadorias", "categoria", "descricao", "codigo", "preco", "estoque", "quantidade"]
        
        for r in range(rows):
            row_data = {}
            # Recuperar ID do produto (se existir) da coluna 0
            item_id = self.finance_table.item(r, 0)
            if item_id:
                prod_id = item_id.data(Qt.UserRole + 1)
                if prod_id:
                    row_data['id'] = prod_id

            for c, key in enumerate(keys):
                item = self.finance_table.item(r, c)
                text = item.text() if item else ""
                row_data[key] = text
                
                if key == "estoque" and item:
                    meta = item.data(Qt.UserRole)
                    if meta and isinstance(meta, dict):
                        row_data["estoque_meta"] = meta
            
            data.append(row_data)
        return data

    def load_data(self):
        self.loading_data = True
        try:
            # Carregar localmente para verificação
            local_data = self.db.load_local()
            
            # Tentar carregar da nuvem se estiver logado
            cloud_data = None
            if self.db.user:
                 cloud_data = self.db.load_from_supabase()

            # Decisão de qual fonte de dados usar
            if cloud_data is not None and len(cloud_data) > 0:
                # Nuvem tem dados, usa a nuvem (Server Wins)
                data = cloud_data
                # Atualiza backup local
                self.db.save_local(data)
            elif local_data:
                # Nuvem vazia ou erro (offline), mas temos dados locais
                data = local_data
                # Se a nuvem estava acessível mas vazia (primeiro login?), sincroniza dados locais para lá
                if cloud_data is not None and len(cloud_data) == 0:
                     threading.Thread(target=self.manual_sync, daemon=True).start()
            else:
                # Tudo vazio
                data = []

            self.finance_table.setRowCount(0)
            
            keys = ["data", "mercadorias", "categoria", "descricao", "codigo", "preco", "estoque", "quantidade"]
            
            for row_data in data:
                row = self.finance_table.rowCount()
                self.finance_table.insertRow(row)
                
                # Recuperar ID se existir (do Supabase)
                prod_id = row_data.get('id')

                for col, key in enumerate(keys):
                    val = row_data.get(key, "")
                    item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter)
                    
                    # Salvar ID na primeira coluna (oculto)
                    if col == 0 and prod_id:
                        item.setData(Qt.UserRole + 1, prod_id)

                    self.finance_table.setItem(row, col, item)
                    
                    # Restaurar metadados de estoque
                    if key == "estoque" and "estoque_meta" in row_data:
                        meta = row_data["estoque_meta"]
                        item.setData(Qt.UserRole, meta)
                        if isinstance(meta, dict):
                            self.update_stock_label(row, meta.get('min', 0), meta.get('max', 0))

            self.update_saldo()
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
            traceback.print_exc()
        finally:
            self.loading_data = False

    def save_data(self):
        if self.loading_data:
            return

        data = self.get_table_data()
        self.db.save_local(data)
        
        # Tenta sincronizar silenciosamente com a nuvem
        # Usando thread separada para não travar a UI
        import threading
        threading.Thread(target=self.manual_sync, daemon=True).start()

    def on_item_changed(self, item):
        if not self.loading_data:
            self.save_data()
            self.update_saldo()
            # Auto-sync após mudanças críticas se desejar, ou manter apenas no save_data
            # self.manual_sync() 

    def save_supabase_config(self):
        # Mantido apenas para compatibilidade interna se necessário, mas removido da UI
        pass

    def manual_sync(self):
        # Agora chamado automaticamente ou invisivelmente
        data = self.get_table_data()
        success, msg = self.db.sync_to_supabase(data)
        # Removido feedback visual intrusivo para operação automática
        if not success:
             print(f"Sync error: {msg}")

    def update_stock_label(self, row, min_qty, max_qty):
        label = QLabel()
        html_text = (
            f"<span style='color: black;'>{min_qty}</span> "
            f"<span style='color: #00FF00; font-weight: bold;'>↓</span> "
            f"&nbsp;&nbsp;"
            f"<span style='color: black;'>{max_qty}</span> "
            f"<span style='color: #00FF00; font-weight: bold;'>↑</span>"
        )
        label.setText(html_text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background-color: transparent; font-family: Segoe UI;")
        label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.finance_table.setCellWidget(row, 6, label)

    def check_updates(self):
        self.update_checker = UpdateChecker()
        self.update_checker.update_available.connect(self.show_update_notification)
        self.update_checker.start()

    def show_update_notification(self, url):
        self.update_url = url
        self.notification_bubble.show()

    def on_bubble_click(self, event):
        if event.button() == Qt.LeftButton:
            reply = QMessageBox.question(
                self, "Atualização Disponível",
                "Deseja baixar e instalar a nova versão agora?\nO programa será reiniciado.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.start_update_process()

    def start_update_process(self):
        self.notification_bubble.setText("Baixando atualização... 0%")
        self.notification_bubble.setEnabled(False)
        
        self.downloader = UpdateDownloader(self.update_url)
        self.downloader.finished.connect(self.install_update)
        self.downloader.error.connect(self.update_error)
        self.downloader.progress.connect(self.update_download_progress)
        self.downloader.start()

    def update_download_progress(self, percentage):
        self.notification_bubble.setText(f"Baixando atualização... {percentage}%")

    def install_update(self, installer_path):
        self.notification_bubble.setText("Instalando...")
        try:
            # Run the installer
            subprocess.Popen([installer_path], shell=True)
            # Close this app
            QApplication.quit()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao iniciar instalador: {e}")
            self.notification_bubble.setText("(Nova atualização ) Clique aqui para atualizar o Búlgaree")
            self.notification_bubble.setEnabled(True)

    def update_error(self, error_msg):
        QMessageBox.warning(self, "Erro no Download", f"Não foi possível baixar a atualização:\n{error_msg}")
        self.notification_bubble.setText("(Nova atualização ) Clique aqui para atualizar o Búlgaree")
        self.notification_bubble.setEnabled(True)

    # --- Funções de controle financeiro ---
    def open_voice_dialog(self):
        fields = ["Data", "Mercadorias", "Categoria", "Descrição", "Código", "Preço", "Quantidade"]
        dialog = VoiceInputDialog(self, fields=fields, title_text="Adicionar Produtos com Voz")
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            row_pos = self.finance_table.rowCount()
            self.finance_table.insertRow(row_pos)
            
            # Extract basic fields
            product = data.get("Mercadorias", "")
            
            self.finance_table.setItem(row_pos, 0, QTableWidgetItem(data.get("Data", "")))
            self.finance_table.setItem(row_pos, 1, QTableWidgetItem(product))
            self.finance_table.setItem(row_pos, 2, QTableWidgetItem(data.get("Categoria", "")))
            self.finance_table.setItem(row_pos, 3, QTableWidgetItem(data.get("Descrição", "")))
            self.finance_table.setItem(row_pos, 4, QTableWidgetItem(data.get("Código", "")))
            
            # Price Processing
            preco_str = data.get("Preço", "0.00")
            match_price = re.search(r'(\d+(?:[.,]\d{1,2})?)', preco_str)
            price_val = 0.0
            if match_price:
                price_clean = match_price.group(1).replace(",", ".")
                price_val = float(price_clean)
            else:
                price_clean = "0.00"
                
            # Quantity Processing
            qty_str = data.get("Quantidade", "0")
            match_qty = re.search(r'(\d+)', qty_str)
            qty_val = 0
            if match_qty:
                qty_val = int(match_qty.group(1))
            
            # Type Processing
            type_val = data.get("Tipo", "Unidade")
            
            # Calculate Total (If qty is 0/empty, assume 1 for total calculation but keep 0 in display if desired? 
            # Or just calc based on qty. If 0, total is 0. But usually user implies 1 if not specified.)
            # Let's assume if 0, use 1 for price check, but user explicitly asked for quantity logic.
            # If user doesn't say quantity, qty_val is 0. Total 0? That would be weird for "Arroz 10 reais".
            # Let's use 1 if qty_val is 0.
            calc_qty = qty_val if qty_val > 0 else 1
            total_val = price_val * calc_qty
            
            # Set Price Item with UserRole for Total
            item_price = QTableWidgetItem(f"{price_val:.2f}")
            item_price.setData(Qt.UserRole, total_val)
            self.finance_table.setItem(row_pos, 5, item_price)
            
            # Stock (Default 0)
            self.finance_table.setItem(row_pos, 6, QTableWidgetItem("0"))
            
            # Quantity Column Message
            msg = ""
            if qty_val > 0:
                if type_val == "Caixa":
                    msg = f"{qty_val} caixas de {product}, cada caixa custa {price_val:.2f}, e o valor final somado das {qty_val} caixas é {total_val:.2f}"
                else:
                    # Unidade
                    msg = f"{qty_val} {product}, Cada unidade custa {price_val:.2f}, valor final somado das {qty_val} {product} é {total_val:.2f}"
            else:
                msg = "0"
            
            item_qty = QTableWidgetItem(msg)
            item_qty.setToolTip(f"Valor Final Total: R$ {total_val:.2f}")
            self.finance_table.setItem(row_pos, 7, item_qty)
            
            self.update_saldo()
            self.save_data()

    def open_sales_voice_dialog(self):
        fields = ["Data", "Produto", "Quantidade", "Valor Unit.", "Total"]
        dialog = VoiceInputDialog(self, fields=fields, title_text="Adicionar Vendas com Voz")
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            row_pos = self.sales_table.rowCount()
            self.sales_table.insertRow(row_pos)
            
            # Extract basic fields
            date = data.get("Data", "")
            product = data.get("Produto", "")
            
            # Quantity
            qty_str = data.get("Quantidade", "0")
            match_qty = re.search(r'(\d+)', qty_str)
            qty_val = int(match_qty.group(1)) if match_qty else 0
            
            # Unit Value
            unit_str = data.get("Valor Unit.", "0.00")
            match_price = re.search(r'(\d+(?:[.,]\d{1,2})?)', unit_str)
            unit_val = float(match_price.group(1).replace(",", ".")) if match_price else 0.00
            
            # Total
            total_val = unit_val * qty_val
            
            self.sales_table.setItem(row_pos, 0, QTableWidgetItem(date))
            self.sales_table.setItem(row_pos, 1, QTableWidgetItem(product))
            self.sales_table.setItem(row_pos, 2, QTableWidgetItem(str(qty_val)))
            self.sales_table.setItem(row_pos, 3, QTableWidgetItem(f"{unit_val:.2f}"))
            self.sales_table.setItem(row_pos, 4, QTableWidgetItem(f"{total_val:.2f}"))
            
            self.update_sales_total()
            self.save_sales_data()

    def add_row(self):
        row_pos = self.finance_table.rowCount()
        self.finance_table.insertRow(row_pos)
        self.finance_table.setItem(row_pos, 0, QTableWidgetItem(""))
        self.finance_table.setItem(row_pos, 1, QTableWidgetItem(""))
        self.finance_table.setItem(row_pos, 2, QTableWidgetItem(""))
        self.finance_table.setItem(row_pos, 3, QTableWidgetItem(""))
        self.finance_table.setItem(row_pos, 4, QTableWidgetItem(""))
        self.finance_table.setItem(row_pos, 5, QTableWidgetItem("0.00"))
        self.finance_table.setItem(row_pos, 6, QTableWidgetItem(""))
        self.finance_table.setItem(row_pos, 7, QTableWidgetItem("0"))
        self.update_saldo()
        self.save_data()

    def remove_row(self):
        try:
            # Perguntar ao usuário qual linha (item) remover
            rows = self.finance_table.rowCount()
            if rows == 0:
                QMessageBox.warning(self, "Aviso", "Não há itens para remover.")
                return

            # Diálogo para escolher o número
            dialog = QInputDialog(self)
            dialog.setInputMode(QInputDialog.IntInput)
            dialog.setWindowTitle("Remover Item")
            dialog.setLabelText("Digite o número da linha (item) que deseja remover:")
            dialog.setIntRange(1, rows)
            dialog.setIntValue(rows) # Sugere o último
            dialog.setIntStep(1)
            
            # Estilo do Dialog
            dialog.setStyleSheet("""
                QDialog { background-color: #2E2E2E; color: white; border: 1px solid #FF4500; }
                QLabel { color: white; font-size: 14px; font-family: Segoe UI; }
                QSpinBox { background-color: #3E3E3E; color: white; border: 1px solid #555; padding: 5px; }
                QPushButton { background-color: #FF4500; color: white; padding: 5px 15px; border: none; }
                QPushButton:hover { background-color: #FF6347; }
            """)
            
            ok = dialog.exec_()
            val = dialog.intValue()
            
            if ok:
                # Índice é val - 1
                idx = val - 1
                if 0 <= idx < rows:
                    self.finance_table.removeRow(idx)
                    self.update_saldo()
                    self.save_data()
                else:
                    QMessageBox.warning(self, "Erro", "Número de linha inválido.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao tentar remover: {str(e)}")
            traceback.print_exc()

    def update_saldo(self):
        total = 0
        for row in range(self.finance_table.rowCount()):
            # Coluna 5: Preço
            item = self.finance_table.item(row, 5)
            if item:
                # Check for UserRole (Total calculated from Voice)
                user_data = item.data(Qt.UserRole)
                if user_data is not None:
                    try:
                        total += float(user_data)
                    except:
                        pass
                else:
                    # Fallback to text (Unit Price)
                    try:
                        valor = float(item.text().replace(",", "."))
                        total += valor
                    except:
                        continue
        self.saldo_label.setText(f"Saldo Total: R$ {total:.2f}")
        self.saldo_label.setStyleSheet(f"font-weight: bold; color: {'green' if total>=0 else 'red'};")

    # --- Navigation ---
    def show_produtos(self):
        if self.stack.currentWidget() == self.produtos_panel:
            self.stack.setCurrentWidget(self.empty_panel)
        else:
            self.stack.setCurrentWidget(self.produtos_panel)

    def show_vendas(self):
        if self.stack.currentWidget() == self.vendas_panel:
            self.stack.setCurrentWidget(self.empty_panel)
        else:
            self.stack.setCurrentWidget(self.vendas_panel)

    # --- Sales Logic ---
    def get_sales_data(self):
        data = []
        rows = self.sales_table.rowCount()
        keys = ["data", "produto", "quantidade", "valor_unit", "total"]
        
        for r in range(rows):
            row_data = {}
            # ID hidden in col 0
            item_id = self.sales_table.item(r, 0)
            if item_id:
                sale_id = item_id.data(Qt.UserRole + 1)
                if sale_id:
                    row_data['id'] = sale_id

            for c, key in enumerate(keys):
                item = self.sales_table.item(r, c)
                text = item.text() if item else ""
                row_data[key] = text
            
            data.append(row_data)
        return data

    def load_sales_data(self):
        try:
            local_data = self.db.load_local("sales.json")
            cloud_data = None
            if self.db.user:
                 cloud_data = self.db.load_from_supabase("vendas")

            if cloud_data is not None and len(cloud_data) > 0:
                data = cloud_data
                self.db.save_local(data, "sales.json")
            elif local_data:
                data = local_data
                if cloud_data is not None and len(cloud_data) == 0:
                     threading.Thread(target=self.manual_sync_sales, daemon=True).start()
            else:
                data = []

            self.sales_table.setRowCount(0)
            keys = ["data", "produto", "quantidade", "valor_unit", "total"]
            
            for row_data in data:
                row = self.sales_table.rowCount()
                self.sales_table.insertRow(row)
                
                sale_id = row_data.get('id')

                for col, key in enumerate(keys):
                    val = row_data.get(key, "")
                    item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter)
                    
                    if col == 0 and sale_id:
                        item.setData(Qt.UserRole + 1, sale_id)

                    self.sales_table.setItem(row, col, item)
            
            self.update_sales_total()
        except Exception as e:
            print(f"Erro ao carregar vendas: {e}")

    def save_sales_data(self):
        data = self.get_sales_data()
        self.db.save_local(data, "sales.json")
        threading.Thread(target=self.manual_sync_sales, daemon=True).start()

    def manual_sync_sales(self):
        data = self.get_sales_data()
        self.db.sync_to_supabase(data, "vendas")

    def on_sale_changed(self, item):
        self.update_sales_total()
        self.save_sales_data()

    def open_sales_voice_dialog(self):
        fields = ["Data", "Produto", "Quantidade", "Valor Unit.", "Total"]
        dialog = VoiceInputDialog(self, fields=fields, title_text="Adicionar Vendas com Voz")
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            row = self.sales_table.rowCount()
            self.sales_table.insertRow(row)
            
            # Helper to safely get float
            def get_float(val_str):
                try:
                    match = re.search(r'(\d+(?:[.,]\d{1,2})?)', val_str)
                    if match:
                        return float(match.group(1).replace(",", "."))
                    return 0.0
                except:
                    return 0.0

            # Data
            self.sales_table.setItem(row, 0, QTableWidgetItem(data.get("Data", "")))
            # Produto
            self.sales_table.setItem(row, 1, QTableWidgetItem(data.get("Produto", "")))
            
            # Quantidade
            qty_str = data.get("Quantidade", "0")
            try:
                match_qty = re.search(r'(\d+)', qty_str)
                qty = int(match_qty.group(1)) if match_qty else 0
            except:
                qty = 0
            self.sales_table.setItem(row, 2, QTableWidgetItem(str(qty)))
            
            # Valor Unit.
            val_unit_str = data.get("Valor Unit.", "0.00")
            val_unit = get_float(val_unit_str)
            self.sales_table.setItem(row, 3, QTableWidgetItem(f"{val_unit:.2f}"))
            
            # Total
            total_str = data.get("Total", "")
            if total_str:
                total = get_float(total_str)
            else:
                total = qty * val_unit
            
            self.sales_table.setItem(row, 4, QTableWidgetItem(f"{total:.2f}"))
            
            self.update_sales_total()
            self.save_sales_data()

    def add_sale_row(self):
        row = self.sales_table.rowCount()
        self.sales_table.insertRow(row)
        # Add empty items
        for i in range(5):
            self.sales_table.setItem(row, i, QTableWidgetItem(""))
        self.save_sales_data()

    def remove_sale_row(self):
        rows = self.sales_table.rowCount()
        if rows == 0:
            return
            
        dialog = QInputDialog(self)
        dialog.setInputMode(QInputDialog.IntInput)
        dialog.setWindowTitle("Remover Venda")
        dialog.setLabelText("Número da linha para remover:")
        dialog.setIntRange(1, rows)
        dialog.setIntValue(rows)
        dialog.setIntStep(1)
        
        dialog.setStyleSheet("""
            QDialog { background-color: #2E2E2E; color: white; border: 1px solid #FF4500; }
            QLabel { color: white; font-size: 14px; font-family: Segoe UI; }
            QSpinBox { background-color: #3E3E3E; color: white; border: 1px solid #555; padding: 5px; }
            QPushButton { background-color: #FF4500; color: white; padding: 5px 15px; border: none; }
            QPushButton:hover { background-color: #FF6347; }
        """)
        
        if dialog.exec_():
            idx = dialog.intValue() - 1
            if 0 <= idx < rows:
                self.sales_table.removeRow(idx)
                self.update_sales_total()
                self.save_sales_data()

    def update_sales_total(self):
        total = 0.0
        for row in range(self.sales_table.rowCount()):
            item = self.sales_table.item(row, 4) # Total column
            if item:
                try:
                    val = float(item.text().replace(",", "."))
                    total += val
                except:
                    pass
        self.sales_total_label.setText(f"Total Vendas: R$ {total:.2f}")

    # --- Funções de UI ---
    def toggle_settings_panel(self):
        if self.settings_panel.isVisible():
            self.settings_panel.hide()
        else:
            rect = self.geometry()
            self.settings_panel.move(rect.width() - self.settings_panel.width() - 5, self.title_bar.height())
            self.settings_panel.show()

    def change_theme(self):
        if self.theme_combo.currentText() == "Claro":
            self.setStyleSheet("background-color: #FFFFFF; border: 1px solid #333;")
            self.content.setStyleSheet("background-color: #FFFFFF; border: none;")
        else:
            self.setStyleSheet("background-color: #1E1E1E; border: 1px solid #333;")
            self.content.setStyleSheet("background-color: #1E1E1E; border: none;")

    def change_language(self):
        lang = self.lang_combo.currentText()
        self.title_bar.title.setText("Búlgaree" if lang == "Português" else "Búlgaree (EN)")

    def resizeEvent(self, event):
        if hasattr(self, 'sizegrip'):
            rect = self.rect()
            self.sizegrip.move(rect.width() - 22, rect.height() - 22)
            if self.settings_panel.isVisible():
                self.settings_panel.move(rect.width() - self.settings_panel.width() - 5, self.title_bar.height())
        super().resizeEvent(event)

    def open_context_menu(self, pos):
        item = self.finance_table.itemAt(pos)
        # Check if item exists and is in column 6 (Estoque)
        if item and item.column() == 6:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2E2E2E;
                    color: white;
                    border: 1px solid #555;
                }
                QMenu::item {
                    padding: 5px 20px;
                }
                QMenu::item:selected {
                    background-color: #00CED1;
                }
            """)
            action_limits = QAction("Definir Quantidade Min/Max", self)
            action_limits.triggered.connect(lambda: self.open_stock_limits_dialog(item))
            menu.addAction(action_limits)
            menu.exec_(self.finance_table.viewport().mapToGlobal(pos))

    def open_stock_limits_dialog(self, item):
        dialog = StockLimitDialog(self)
        # Load existing data
        data = item.data(Qt.UserRole)
        if data and isinstance(data, dict):
            dialog.min_spin.setValue(data.get('min', 0))
            dialog.max_spin.setValue(data.get('max', 0))
        
        if dialog.exec_() == QDialog.Accepted:
            min_qty = dialog.min_spin.value()
            max_qty = dialog.max_spin.value()
            item.setData(Qt.UserRole, {'min': min_qty, 'max': max_qty})
            
            # Visual feedback with HTML Label
            label = QLabel()
            html_text = (
                f"<span style='color: black;'>{min_qty}</span> "
                f"<span style='color: #00FF00; font-weight: bold;'>↓</span> "
                f"&nbsp;&nbsp;"  # Space
                f"<span style='color: black;'>{max_qty}</span> "
                f"<span style='color: #00FF00; font-weight: bold;'>↑</span>"
            )
            label.setText(html_text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("background-color: transparent; font-family: Segoe UI;")
            label.setAttribute(Qt.WA_TransparentForMouseEvents)
            
            self.finance_table.setCellWidget(item.row(), 6, label)
            
            # Tooltip as backup
            item.setToolTip(f"Min: {min_qty}, Max: {max_qty}")

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        
        # Login
        login = LoginWindow()
        if login.exec_() == QDialog.Accepted:
            # Se login com sucesso, abre a janela principal passando o DB autenticado
            window = MainWindow(db_manager=login.db)
            window.show()
            sys.exit(app.exec_())
        else:
            sys.exit(0)
            
    except Exception as e:
        print("Erro fatal:", e)
        traceback.print_exc()
