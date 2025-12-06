from PyQt5.QtGui import QImage, QPainter, QLinearGradient, QColor, QFont, QBrush, QPen
from PyQt5.QtCore import Qt, QRectF, QPointF
from PIL import Image
import sys

def create_icon():
    # Tamanho do ícone (256x256 é padrão para alta qualidade no Windows)
    size = 256
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    # Configurar o Gradiente (Cinza para Azul Claro)
    # Diagonal: Topo-Esquerda para Baixo-Direita
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor("#E0E0E0"))  # Cinza Claro
    gradient.setColorAt(1.0, QColor("#ADD8E6"))  # Azul Claro

    # Desenhar Retângulo com Cantos Arredondados (Estilo moderno)
    # Margem de 10px para não cortar
    margin = 20
    rect_width = size - (2 * margin)
    rect_height = size / 2 # Formato retangular (metade da altura)
    
    # Centralizar verticalmente
    top_y = (size - rect_height) / 2
    
    rect = QRectF(margin, top_y, rect_width, rect_height)
    
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.NoPen) # Sem borda preta
    painter.drawRoundedRect(rect, 20, 20) # Raio de 20px para cantos arredondados

    # Configurar Texto "Búlgaree"
    painter.setPen(QColor("#333333")) # Texto Cinza Escuro
    
    # Ajustar fonte para caber
    font_size = 40
    font = QFont("Segoe UI", font_size, QFont.Bold)
    painter.setFont(font)
    
    # Desenhar Texto Centralizado
    painter.drawText(rect, Qt.AlignCenter, "Búlgaree")

    painter.end()

    # Salvar como PNG temporário
    png_path = "icon_temp.png"
    image.save(png_path)
    
    # Converter para ICO usando Pillow
    try:
        img = Image.open(png_path)
        img.save("icon.ico", format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        print("Ícone criado com sucesso: icon.ico")
    except Exception as e:
        print(f"Erro ao converter para ICO: {e}")

if __name__ == "__main__":
    # Necessário para usar QFont/QPainter
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    create_icon()
