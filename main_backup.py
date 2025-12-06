import sys
import traceback
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSizeGrip, QComboBox, QFrame, QTableWidget, QTableWidgetItem,
    QMenu, QAction, QDialog, QSpinBox
)
from PyQt5.QtCore import Qt

# Tratamento de erros para evitar fechamento silencioso
def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("ERRO CRÍTICO:", tb)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

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

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
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
        self.btn_produtos.clicked.connect(self.toggle_produtos_panel)
        self.menu_layout.addWidget(self.btn_produtos)
        self.menu_layout.addStretch()
        self.menu_container.setFixedWidth(150)
        self.main_horizontal_layout.addWidget(self.menu_container)

        # --- Área de Exibição ---
        self.display_area = QWidget()
        self.display_layout = QVBoxLayout(self.display_area)
        self.display_layout.setContentsMargins(0, 0, 0, 0)

        # Painel de Produtos
        self.produtos_panel = QFrame()
        self.produtos_panel.setStyleSheet("""
            background-color: #ADD8E6; 
            border-radius: 15px;
            border: none;
        """)
        self.produtos_panel.hide()
        self.display_layout.addWidget(self.produtos_panel)
        self.main_horizontal_layout.addWidget(self.display_area)
        self.layout.addWidget(self.content)

        # --- Layout interno do painel Produtos ---
        produtos_layout = QVBoxLayout(self.produtos_panel)
        produtos_layout.setContentsMargins(15, 15, 15, 15)
        produtos_layout.setSpacing(10)

        label_planilha = QLabel("Controle Financeiro Pessoal")
        label_planilha.setStyleSheet("font-family: Segoe UI; font-size: 16px; font-weight: bold; color: #000080;")
        produtos_layout.addWidget(label_planilha)

        # Tabela
        self.finance_table = QTableWidget()
        self.finance_table.setColumnCount(8)
        self.finance_table.setHorizontalHeaderLabels(["Data", "Mercadorias", "Categoria", "Descrição", "Código", "Preço", "Estoque", "Quantidade"])
        self.finance_table.horizontalHeader().setStretchLastSection(True)
        self.finance_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.finance_table.customContextMenuRequested.connect(self.open_context_menu)
        produtos_layout.addWidget(self.finance_table)

        # Botões e Saldo
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
        produtos_layout.addLayout(buttons_layout)

        # Painel de Configurações
        self.settings_panel = QWidget(self)
        self.settings_panel.setStyleSheet("""
            background-color: #2E2E2E;
            border-radius: 10px;
            border: 1px solid #555;
        """)
        self.settings_panel.setFixedSize(220, 180)
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

    # --- Funções de controle financeiro ---
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

    def remove_row(self):
        row = self.finance_table.currentRow()
        if row >= 0:
            self.finance_table.removeRow(row)
        self.update_saldo()

    def update_saldo(self):
        total = 0
        for row in range(self.finance_table.rowCount()):
            # Coluna 5: Preço, Coluna 6: Estoque, Coluna 7: Quantidade
            valor_item = self.finance_table.item(row, 7)
            if valor_item:
                try:
                    valor = float(valor_item.text().replace(",", "."))
                    total += valor
                except:
                    continue
        self.saldo_label.setText(f"Saldo Total: R$ {total:.2f}")
        self.saldo_label.setStyleSheet(f"font-weight: bold; color: {'green' if total>=0 else 'red'};")

    # --- Funções de UI ---
    def toggle_produtos_panel(self):
        if self.produtos_panel.isVisible():
            self.produtos_panel.hide()
        else:
            self.produtos_panel.show()

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
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print("Erro fatal:", e)
        traceback.print_exc()
