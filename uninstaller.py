import sys
import os
import shutil
import winreg
import ctypes
import time
import subprocess
from PyQt5.QtWidgets import QApplication, QMessageBox

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def remove_shortcuts(app_name):
    try:
        # Desktop
        desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
        lnk_path = os.path.join(desktop, f"{app_name}.lnk")
        if os.path.exists(lnk_path):
            os.remove(lnk_path)
        
        # Start Menu
        start_menu = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs')
        lnk_path = os.path.join(start_menu, f"{app_name}.lnk")
        if os.path.exists(lnk_path):
            os.remove(lnk_path)
    except Exception as e:
        print(f"Erro ao remover atalhos: {e}")

def remove_registry_key(app_name):
    try:
        key_path = f"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}"
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
    except Exception as e:
        print(f"Erro ao remover registro: {e}")

def self_delete_and_remove_dir(install_dir):
    # Cria um script batch temporário para deletar a pasta após o processo terminar
    batch_file = os.path.join(os.environ['TEMP'], 'remove_bulgaree.bat')
    with open(batch_file, 'w') as f:
        f.write('@echo off\n')
        f.write('timeout /t 2 /nobreak > NUL\n') # Espera 2 segundos
        f.write(f'rmdir /s /q "{install_dir}"\n') # Remove a pasta
        f.write(f'del "%~f0"\n') # Deleta o próprio script batch
    
    # Executa o batch em background sem janela
    subprocess.Popen(batch_file, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

def main():
    app = QApplication(sys.argv)
    
    # Nome da aplicação
    APP_NAME = "Bulgaree"
    
    # Confirmação
    msg = QMessageBox()
    msg.setWindowTitle(f"Desinstalar {APP_NAME}")
    msg.setText(f"Tem certeza que deseja remover completamente o {APP_NAME} e todos os seus componentes?")
    msg.setIcon(QMessageBox.Question)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.No)
    
    if msg.exec_() == QMessageBox.Yes:
        # Diretório atual (onde está o desinstalador)
        install_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        
        # 1. Remover Atalhos
        remove_shortcuts(APP_NAME)
        
        # 2. Remover Registro
        remove_registry_key(APP_NAME)
        
        # 3. Mensagem de sucesso
        success_msg = QMessageBox()
        success_msg.setWindowTitle("Desinstalação Concluída")
        success_msg.setText(f"O {APP_NAME} foi removido com sucesso do seu computador.")
        success_msg.setIcon(QMessageBox.Information)
        success_msg.exec_()
        
        # 4. Agendar remoção da pasta e fechar
        self_delete_and_remove_dir(install_dir)
        sys.exit(0)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
