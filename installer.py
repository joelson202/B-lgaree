import sys
import os
import shutil
import traceback
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QPushButton, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
import win32com.client
import pythoncom
import winreg

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class InstallThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    status = pyqtSignal(str)

    def run(self):
        try:
            pythoncom.CoInitialize()
            # 1. Define paths
            app_name = "Bulgaree"
            exe_name = "Bulgaree.exe"
            install_dir = os.path.join(os.environ['LOCALAPPDATA'], app_name)
            
            self.status.emit(f"Preparando diretório: {install_dir}...")
            self.progress.emit(10)
            time.sleep(0.5)

            # 1.5 Kill existing process
            try:
                os.system(f"taskkill /f /im {exe_name} >nul 2>&1")
                time.sleep(1) # Give it a second to close
            except:
                pass

            # 2. Create directory
            if os.path.exists(install_dir):
                try:
                    shutil.rmtree(install_dir)
                except Exception as e:
                    # Try to rename if delete fails (process might be running)
                    try:
                        os.rename(install_dir, install_dir + "_old_" + str(int(time.time())))
                    except:
                        pass
            
            os.makedirs(install_dir, exist_ok=True)
            self.progress.emit(30)

            # 3. Copy executable
            self.status.emit("Copiando arquivos...")
            source_exe = resource_path(exe_name)
            dest_exe = os.path.join(install_dir, exe_name)
            
            if not os.path.exists(source_exe):
                raise Exception(f"Arquivo fonte não encontrado: {source_exe}")

            shutil.copy2(source_exe, dest_exe)
            
            # Copy config.json if exists
            config_name = "config.json"
            source_config = resource_path(config_name)
            dest_config = os.path.join(install_dir, config_name)
            
            if os.path.exists(source_config):
                shutil.copy2(source_config, dest_config)
            
            # Copy uninstaller
            unins_name = "uninstall.exe"
            source_unins = resource_path(unins_name)
            dest_unins = os.path.join(install_dir, unins_name)
            
            if os.path.exists(source_unins):
                shutil.copy2(source_unins, dest_unins)
            
            self.progress.emit(60)
            time.sleep(0.5)

            # 4. Create Shortcuts
            self.status.emit("Criando atalhos...")
            shell = win32com.client.Dispatch("WScript.Shell")
            
            # Desktop Shortcut
            desktop = shell.SpecialFolders("Desktop")
            shortcut_path = os.path.join(desktop, f"{app_name}.lnk")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = dest_exe
            shortcut.WorkingDirectory = install_dir
            shortcut.IconLocation = dest_exe
            shortcut.save()

            # Start Menu Shortcut
            start_menu = shell.SpecialFolders("StartMenu")
            programs_path = os.path.join(start_menu, "Programs")
            shortcut_path = os.path.join(programs_path, f"{app_name}.lnk")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = dest_exe
            shortcut.WorkingDirectory = install_dir
            shortcut.IconLocation = dest_exe
            shortcut.save()

            # 5. Register Uninstaller in Windows Registry
            self.status.emit("Registrando desinstalador...")
            try:
                key_path = f"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}"
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
                
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, app_name)
                winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, dest_exe)
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, dest_unins)
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Búlgaree Inc.")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
                
                winreg.CloseKey(key)
            except Exception as e:
                print(f"Erro ao registrar desinstalador: {e}")

            self.progress.emit(90)
            time.sleep(0.5)
            
            self.status.emit("Concluído!")
            self.progress.emit(100)
            self.finished.emit(True, "Instalação realizada com sucesso!")

        except Exception as e:
            self.finished.emit(False, str(e))
            traceback.print_exc()
        finally:
            pythoncom.CoUninitialize()

class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(500, 350)
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #E0E0E0;
                font-family: Segoe UI;
                border: 1px solid #333;
            }
            QLabel {
                border: none;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 5px;
                text-align: center;
                background-color: #2E2E2E;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #00CED1;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #00CED1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #00BFFF;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title
        title = QLabel("Instalador Búlgaree")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00FFFF;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Info Text
        self.info_label = QLabel(
            "Bem-vindo ao assistente de instalação.\n\n"
            "Este instalador irá configurar o Búlgaree no seu computador "
            "e criar atalhos na Área de Trabalho e Menu Iniciar.\n\n"
            "Clique em 'Instalar' para continuar."
        )
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)

        layout.addStretch()

        # Progress Bar
        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        self.pbar.setVisible(False)
        layout.addWidget(self.pbar)

        # Status Label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #AAAAAA; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Buttons
        self.btn_install = QPushButton("Instalar")
        self.btn_install.clicked.connect(self.start_installation)
        layout.addWidget(self.btn_install)

        self.btn_close = QPushButton("Cancelar")
        self.btn_close.setStyleSheet("background-color: #444; margin-top: 10px;")
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)

    def start_installation(self):
        self.btn_install.setEnabled(False)
        self.btn_close.setEnabled(False)
        self.pbar.setVisible(True)
        self.pbar.setValue(0)
        
        self.thread = InstallThread()
        self.thread.progress.connect(self.pbar.setValue)
        self.thread.status.connect(self.status_label.setText)
        self.thread.finished.connect(self.installation_finished)
        self.thread.start()

    def installation_finished(self, success, message):
        self.btn_close.setEnabled(True)
        self.btn_close.setText("Fechar")
        self.btn_close.setStyleSheet("background-color: #00CED1; margin-top: 10px;")
        
        if success:
            self.info_label.setText("Instalação Concluída com Sucesso!\n\nVocê já pode abrir o Búlgaree pelo atalho na Área de Trabalho.")
            self.status_label.setText("Pronto.")
            self.btn_install.hide()
        else:
            self.info_label.setText(f"Erro na instalação:\n{message}")
            self.status_label.setText("Falhou.")
            self.btn_install.setEnabled(True)
            self.btn_close.setText("Sair")

    # Allow dragging the window
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'old_pos') and event.buttons() == Qt.LeftButton:
            delta = event.globalPos() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InstallerWindow()
    window.show()
    sys.exit(app.exec_())
