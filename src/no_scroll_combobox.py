from PyQt5.QtWidgets import QComboBox, QSlider, QApplication
from PyQt5.QtCore import Qt

class NoScrollComboBox(QComboBox):
    def wheelEvent(self, event):
        # Si la liste déroulante n'est pas ouverte, on ignore l'événement de molette
        if not self.view().isVisible():
            event.ignore()
            # Propager l'événement au parent pour que le QScrollArea le gère
            if self.parent():
                QApplication.sendEvent(self.parent(), event)
        else:
            super().wheelEvent(event)

class NoScrollSlider(QSlider):
    def wheelEvent(self, event):
        # Toujours ignorer la molette et la propager au parent (scroll vertical global)
        event.ignore()
        if self.parent():
            QApplication.sendEvent(self.parent(), event) 