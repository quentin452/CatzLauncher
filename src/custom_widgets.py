import os
import json
import random
import time
import threading
import subprocess
import sys
import requests
from PyQt5.QtCore import QSize, Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QPainter, QColor, QRadialGradient, QBrush, QPen, QFont, QMovie
from PyQt5.QtWidgets import (
    QTabWidget, QProgressBar, QListWidget, QWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QPushButton, QListWidgetItem, QMenu, QAction, QMessageBox
)
from PyQt5.QtCore import Qt as QtCoreQt

from .particles import ParticleSystem, Particle, AnimatedButton, LoadingSpinner
from .translation_manager import translations
from .utils import get_minecraft_directory

def load_qss_stylesheet(theme_name="vanilla.qss"):
    """Load the QSS stylesheet from file, trying multiple encodings."""
    styles_dir = os.path.join(os.path.dirname(__file__), "../assets/styles/")
    qss_file = os.path.join(styles_dir, theme_name)
    last_error = None
    for encoding in ("utf-8", "windows-1252", "latin-1"):
        try:
            with open(qss_file, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            last_error = e
    print(f"Warning: Could not load QSS file {theme_name}: {last_error}")
    return ""

def get_available_themes():
    """Returns a list of available .qss theme files."""
    try:
        styles_dir = os.path.join(os.path.dirname(__file__), "../assets/styles/")
        return [f for f in os.listdir(styles_dir) if f.endswith('.qss')]
    except FileNotFoundError:
        return []

def apply_css_class(widget, css_class):
    """Apply a CSS class to a widget and force stylesheet reapplication."""
    widget.setProperty("class", css_class)
    # Force stylesheet reapplication
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()

class AnimatedTabWidget(QTabWidget):
    """Enhanced tab widget with smooth transitions and particle effects."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particle_system = ParticleSystem(self)
        self.particle_system.raise_()
        self.setMouseTracking(True)
        
    def mouseMoveEvent(self, event):
        """Track mouse movement for particle effects."""
        super().mouseMoveEvent(event)
        self.particle_system.mouse_move_event(event.pos())

class AnimatedProgressBar(QProgressBar):
    """Enhanced progress bar with smooth animations and particle effects."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(500)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.particles = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(16)
        
    def setValue(self, value):
        """Animate the value change."""
        self.animation.setStartValue(self.value())
        self.animation.setEndValue(value)
        self.animation.start()
        
    def update_particles(self):
        """Update particles for progress bar."""
        if self.value() > 0 and self.value() < self.maximum():
            # Emit particles occasionally during progress
            if random.random() < 0.1:
                self.emit_particles()
                
        # Update existing particles
        for particle in self.particles[:]:
            if not particle.update(0.016):
                self.particles.remove(particle)
        self.update()
        
    def emit_particles(self):
        """Emit particles from progress bar."""        
        progress_width = (self.value() / self.maximum()) * self.width()
        for _ in range(2):
            particle = Particle(
                progress_width + random.uniform(-10, 10),
                random.randint(0, self.height()),
                color=QColor(100, 200, 255),
                size=random.uniform(1, 3),
                velocity=(random.uniform(-1, 1), random.uniform(-2, 0)),
                life=random.uniform(0.5, 1.0)
            )
            self.particles.append(particle)
            
    def paintEvent(self, event):
        """Custom paint event with particles."""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw particles
        for particle in self.particles:
            gradient = QRadialGradient(particle.x, particle.y, particle.size)
            color = QColor(particle.color)
            color.setAlpha(particle.alpha)
            gradient.setColorAt(0, color)
            gradient.setColorAt(1, QColor(0, 0, 0, 0))
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(particle.x - particle.size), int(particle.y - particle.size), 
                              int(particle.size * 2), int(particle.size * 2))

class ModpackListItem(QWidget):
    """Widget personnalisé pour afficher un modpack avec un bouton de vérification d'update."""
    
    def __init__(self, modpack_data, parent=None):
        super().__init__(parent)
        self.modpack_data = modpack_data
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)
        
        # Label avec le nom et la version
        self.name_label = QLabel(f"{modpack_data['name']} - {modpack_data['version']}")
        self.name_label.setProperty("class", "modpack-name")
        layout.addWidget(self.name_label)
        
        layout.addStretch()
        
        # Bouton de vérification d'update
        self.check_update_btn = AnimatedButton("🔄")
        self.check_update_btn.setFixedSize(16, 16)
        self.check_update_btn.setToolTip(str(translations.tr("modpack_item.check_update_tooltip")))
        self.check_update_btn.setProperty("class", "update-btn")
        layout.addWidget(self.check_update_btn)
        
        # Activer le menu contextuel
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def set_checking_state(self, checking=True):
        """Change l'état du bouton pendant la vérification."""
        if checking:
            self.check_update_btn.setText("⏳")
            self.check_update_btn.setEnabled(False)
            self.check_update_btn.setToolTip(str(translations.tr("modpack_item.checking_tooltip")))
        else:
            self.check_update_btn.setText("🔄")
            self.check_update_btn.setEnabled(True)
            self.check_update_btn.setToolTip(str(translations.tr("modpack_item.check_update_tooltip")))
    
    def show_context_menu(self, position):
        """Affiche le menu contextuel pour le modpack."""
        context_menu = QMenu(self)
        
        # Action pour ouvrir le dossier du modpack
        open_folder_action = QAction(str(translations.tr("modpack_item.context_menu.open_folder")), self)
        open_folder_action.triggered.connect(self.open_modpack_folder)
        context_menu.addAction(open_folder_action)
        
        # Action pour vérifier les mises à jour
        check_update_action = QAction(str(translations.tr("modpack_item.context_menu.check_updates")), self)
        check_update_action.triggered.connect(self.trigger_update_check)
        context_menu.addAction(check_update_action)
        
        # Action pour afficher les informations du modpack
        info_action = QAction(str(translations.tr("modpack_item.context_menu.show_info")), self)
        info_action.triggered.connect(self.show_modpack_info)
        context_menu.addAction(info_action)
        
        # Afficher le menu à la position du clic
        context_menu.exec_(self.mapToGlobal(position))
    
    def open_modpack_folder(self):
        """Ouvre le dossier du modpack dans l'explorateur de fichiers."""
        try:
            minecraft_dir = get_minecraft_directory()
            modpack_dir = os.path.join(minecraft_dir, "modpacks", self.modpack_data['name'])
            
            if os.path.exists(modpack_dir):
                # Ouvrir le dossier dans l'explorateur de fichiers
                if sys.platform == "win32":
                    os.startfile(modpack_dir)
                elif sys.platform == "darwin":  # macOS
                    subprocess.run(["open", modpack_dir])
                else:  # Linux
                    subprocess.run(["xdg-open", modpack_dir])
            else:
                QMessageBox.information(
                    self, 
                    str(translations.tr("modpack_item.folder.not_found_title")), 
                    str(translations.tr("modpack_item.folder.not_found_message", name=self.modpack_data['name'])) + "\n\n" + 
                    str(translations.tr("modpack_item.folder.expected_path", path=modpack_dir))
                )
        except Exception as e:
            QMessageBox.critical(
                self, 
                str(translations.tr("modpack_item.folder.error_title")), 
                str(translations.tr("modpack_item.folder.error_message", error=str(e)))
            )
    
    def trigger_update_check(self):
        """Déclenche la vérification des mises à jour pour ce modpack."""
        # Trouver le launcher principal en remontant la hiérarchie des widgets
        current_widget = self
        launcher = None
        
        while current_widget and not launcher:
            if hasattr(current_widget, 'check_single_modpack_update'):
                launcher = current_widget
                break
            current_widget = current_widget.parent()
        
        if launcher:
            launcher.check_single_modpack_update(self.modpack_data)
        else:
            # Fallback : essayer de trouver le launcher via la liste des modpacks
            try:
                # Chercher dans la liste des modpacks pour trouver le launcher
                list_widget = self.parent()
                if list_widget and hasattr(list_widget, 'parent'):
                    main_window = list_widget.parent()
                    if main_window and hasattr(main_window, 'check_single_modpack_update'):
                        main_window.check_single_modpack_update(self.modpack_data)
                    else:
                        print("Impossible de trouver le launcher principal pour la vérification des mises à jour")
            except Exception as e:
                print(f"Erreur lors de la vérification des mises à jour : {e}")
    
    def show_modpack_info(self):
        """Demande à la fenêtre principale d'afficher l'overlay d'informations du modpack."""
        main_window = self.window()
        if hasattr(main_window, 'show_modpack_info_with_data'):
            main_window.show_modpack_info_with_data(self.modpack_data)

class AnimatedListWidget(QListWidget):
    """Enhanced list widget with hover effects and animations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.hovered_item = None
        self.animations = {}
        
    def enterEvent(self, event):
        """Handle mouse enter."""
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Handle mouse leave."""
        super().leaveEvent(event)
        self.hovered_item = None
        
    def mouseMoveEvent(self, event):
        """Handle mouse movement for hover effects."""
        super().mouseMoveEvent(event)
        item = self.itemAt(event.pos())
        if item != self.hovered_item:
            self.hovered_item = item
            self.update()

class LoadingScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(18)

        # GIF de chat aléatoire (fond transparent)
        gif_files = [f"assets/loading gif/{i}.gif" for i in range(1, 6)]
        chosen_gif = random.choice(gif_files)
        self.cat_label = QLabel()
        self.cat_label.setFixedSize(180, 180)
        self.cat_label.setScaledContents(True)
        self.cat_movie = QMovie(chosen_gif)
        self.cat_label.setMovie(self.cat_movie)
        self.cat_movie.start()
        layout.addWidget(self.cat_label, alignment=Qt.AlignCenter)

        # Barre de chargement moderne
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(18)
        layout.addWidget(self.progress)

        # Tips multilingues depuis le fichier de langue courant
        tips = translations.tr("tips")
        if isinstance(tips, list):
            self.tips = tips
        elif isinstance(tips, str):
            # Si c'est une chaîne, on tente de splitter par saut de ligne ou point-virgule
            if '\n' in tips:
                self.tips = [t.strip() for t in tips.split('\n') if t.strip()]
            elif ';' in tips:
                self.tips = [t.strip() for t in tips.split(';') if t.strip()]
            else:
                self.tips = [tips]
        else:
            self.tips = [str(tips)]
        self.tip_label = QLabel(random.choice(self.tips))
        self.tip_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.tip_label, alignment=Qt.AlignCenter)

        self.tip_timer = QTimer(self)
        self.tip_timer.timeout.connect(self.show_random_tip)
        self.tip_timer.start(4000)

        # Animation de progression fluide
        self.progress_value = 0
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_timer.start(30)

    def show_random_tip(self):
        self.tip_label.setText(random.choice(self.tips))

    def update_progress(self):
        if self.progress_value < 100:
            self.progress_value += 1
            self.progress.setValue(self.progress_value)
        else:
            self.progress_timer.stop()

    # Optionnel : expose une méthode pour finir le chargement
    def finish(self):
        self.progress.setValue(100)
        self.progress_timer.stop() 